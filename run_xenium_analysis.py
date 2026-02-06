#!/usr/bin/env python3
"""
Replicate the core Xenium workflow from intership1 as a reusable CLI pipeline.
"""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import seaborn as sns
from scipy import sparse

warnings.filterwarnings("ignore")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Xenium analysis from a dataset path.")
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Base directory containing output-* Xenium run folders.",
    )
    parser.add_argument(
        "--out-dir",
        default="analysis_output",
        help="Directory where outputs are written.",
    )
    parser.add_argument(
        "--run-prefix",
        default="output-",
        help="Prefix used to discover run directories.",
    )
    parser.add_argument("--min-counts", type=int, default=50, help="Filter threshold for min counts.")
    parser.add_argument("--min-genes", type=int, default=15, help="Filter threshold for min genes.")
    parser.add_argument(
        "--target-sum",
        type=float,
        default=100.0,
        help="Target sum used in normalize_total.",
    )
    parser.add_argument(
        "--n-neighbors",
        type=int,
        default=15,
        help="n_neighbors used by scanpy neighbors graph.",
    )
    parser.add_argument(
        "--n-pcs",
        type=int,
        default=30,
        help="Number of PCs used for neighbors graph.",
    )
    parser.add_argument(
        "--umap-min-dist",
        type=float,
        default=0.1,
        help="UMAP min_dist parameter.",
    )
    parser.add_argument(
        "--leiden-resolutions",
        default="0.1,0.5,1,1.5,2",
        help="Comma-separated Leiden resolutions.",
    )
    parser.add_argument(
        "--sample-id-split",
        default="__",
        help="Delimiter used to split run name for sample ID extraction.",
    )
    parser.add_argument(
        "--sample-id-index",
        type=int,
        default=2,
        help="Index in split run name used for sample ID extraction.",
    )
    return parser.parse_args()


def discover_runs(base_dir: Path, run_prefix: str) -> list[Path]:
    runs = [
        entry
        for entry in sorted(base_dir.iterdir())
        if entry.is_dir() and entry.name.startswith(run_prefix)
    ]
    return runs


def load_and_concat_runs(base_dir: Path, run_prefix: str) -> sc.AnnData:
    runs = discover_runs(base_dir, run_prefix)
    if not runs:
        raise FileNotFoundError(
            f"No run directories starting with '{run_prefix}' found in {base_dir}"
        )

    ad_list: list[sc.AnnData] = []
    for run in runs:
        h5_path = run / "cell_feature_matrix.h5"
        cell_info_path = run / "cells.csv.gz"
        if not h5_path.exists() or not cell_info_path.exists():
            print(f"Skipping {run} (missing cell_feature_matrix.h5 or cells.csv.gz)")
            continue

        print(f"Loading run: {run.name}")
        ad_int = sc.read_10x_h5(str(h5_path))
        cell_info = pd.read_csv(cell_info_path, index_col=0)

        if len(cell_info) != ad_int.n_obs:
            raise ValueError(
                f"Row mismatch in {run.name}: cell_info={len(cell_info)} vs matrix={ad_int.n_obs}"
            )

        ad_int.obs = cell_info
        ad_int.obs["run"] = run.name
        ad_list.append(ad_int)

    if not ad_list:
        raise RuntimeError(
            "No valid runs loaded. Ensure each run contains cell_feature_matrix.h5 and cells.csv.gz."
        )

    ad = sc.concat(ad_list)
    ad.layers["counts"] = ad.X.copy()
    return ad


def infer_sample_id(run_name: str, split_token: str, split_index: int) -> str:
    parts = run_name.split(split_token)
    if 0 <= split_index < len(parts):
        return parts[split_index]
    return run_name


def build_qc_outputs(ad: sc.AnnData, qc_dir: Path) -> None:
    run_col = "run"
    sample_col = "sample_id"
    cell_type_col = "cell_types"
    counts_col = "total_counts"
    ngenes_col = "n_genes_by_counts"

    ad.obs["cell_id"] = ad.obs.index.astype(str)

    def pctl(series: pd.Series, p: int) -> float:
        return float(np.nanpercentile(series, p))

    agg_dict: dict[str, tuple[str, object]] = {"n_cells": ("cell_id", "count")}
    if counts_col in ad.obs.columns:
        agg_dict |= {
            "counts_mean": (counts_col, "mean"),
            "counts_median": (counts_col, "median"),
            "counts_p10": (counts_col, lambda x: pctl(x, 10)),
            "counts_p90": (counts_col, lambda x: pctl(x, 90)),
        }
    if ngenes_col in ad.obs.columns:
        agg_dict |= {
            "genes_mean": (ngenes_col, "mean"),
            "genes_median": (ngenes_col, "median"),
            "genes_p10": (ngenes_col, lambda x: pctl(x, 10)),
            "genes_p90": (ngenes_col, lambda x: pctl(x, 90)),
        }

    summary = (
        ad.obs.groupby(sample_col)
        .agg(**agg_dict)
        .sort_values("n_cells", ascending=False)
    )
    summary.to_csv(qc_dir / "summary_by_run.csv")

    plt.figure(figsize=(9, 4.5))
    sns.barplot(y=summary.index, x=summary["n_cells"], palette="Set3")
    plt.title("Cells per Xenium run")
    plt.xlabel("# cells")
    plt.ylabel("Run")
    plt.tight_layout()
    plt.savefig(qc_dir / "cells_per_run_bar.png", dpi=200)
    plt.close()

    if ngenes_col in ad.obs.columns:
        plt.figure(figsize=(10, 4.5))
        sns.violinplot(
            data=ad.obs, x=sample_col, y=ngenes_col, inner="quartile", palette="rocket"
        )
        plt.title("n_genes_by_counts per run")
        plt.xlabel("Run")
        plt.ylabel("n_genes_by_counts")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(qc_dir / "ngenes_violin.png", dpi=200)
        plt.close()

    if counts_col in ad.obs.columns:
        plt.figure(figsize=(10, 4.5))
        sns.violinplot(
            data=ad.obs, x=sample_col, y=counts_col, inner="quartile", palette="mako"
        )
        plt.title("total_counts per run")
        plt.xlabel("Run")
        plt.ylabel("total_counts")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(qc_dir / "counts_violin.png", dpi=200)
        plt.close()

    if {counts_col, ngenes_col}.issubset(ad.obs.columns):
        plt.figure(figsize=(6, 5))
        plt.hexbin(ad.obs[counts_col], ad.obs[ngenes_col], gridsize=50, mincnt=1)
        plt.xlabel("total_counts")
        plt.ylabel("n_genes_by_counts")
        plt.title("Counts vs genes (all runs)")
        plt.tight_layout()
        plt.savefig(qc_dir / "counts_vs_genes_hex.png", dpi=200)
        plt.close()

    if cell_type_col in ad.obs.columns:
        ct_counts = ad.obs[cell_type_col].value_counts()
        plt.figure(figsize=(9, 5))
        sns.barplot(y=ct_counts.index[:20], x=ct_counts.values[:20], palette="Spectral")
        plt.title("Top cell types (all runs)")
        plt.xlabel("# cells")
        plt.ylabel("cell type")
        plt.tight_layout()
        plt.savefig(qc_dir / "celltypes_top20.png", dpi=200)
        plt.close()

        top_k = 14
        ct_top = ct_counts.index[:top_k].tolist()
        comp = (
            ad.obs.assign(
                ct_plot=lambda d: d[cell_type_col].where(d[cell_type_col].isin(ct_top), other="Other")
            )
            .groupby([sample_col, "ct_plot"])
            .size()
            .groupby(level=0)
            .apply(lambda x: x / x.sum())
            .unstack(fill_value=0)
        )
        comp.plot(kind="bar", stacked=True, figsize=(10, 5), colormap="tab20")
        plt.ylabel("fraction of cells")
        plt.title("Cell-type composition per run")
        plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", ncol=1)
        plt.tight_layout()
        plt.savefig(qc_dir / "celltypes_per_run_stacked.png", dpi=200)
        plt.close()

    x = ad.X
    is_sparse = sparse.issparse(x)
    if is_sparse:
        detected = (x > 0).astype(np.int8)
        det_overall = np.array(detected.sum(axis=0)).ravel() / ad.n_obs
    else:
        det_overall = np.asarray((x > 0).sum(axis=0)).ravel() / ad.n_obs

    det_overall_series = pd.Series(det_overall, index=ad.var_names, name="fraction_cells")
    det_overall_series.sort_values(ascending=False).to_csv(qc_dir / "gene_detection_overall.csv")

    top30 = det_overall_series.sort_values(ascending=False).head(30)
    plt.figure(figsize=(8, 5))
    sns.barplot(y=top30.index, x=top30.values, palette="coolwarm")
    plt.xlabel("fraction of cells detected")
    plt.ylabel("gene")
    plt.title("Panel coverage: top 30 genes")
    plt.tight_layout()
    plt.savefig(qc_dir / "gene_detection_top30.png", dpi=200)
    plt.close()

    runs = ad.obs[sample_col].astype(str).values
    run_idx = {run_name: np.where(runs == run_name)[0] for run_name in np.unique(runs)}
    det_run: dict[str, np.ndarray] = {}
    for run_name, idx in run_idx.items():
        if len(idx) == 0:
            continue
        if is_sparse:
            sub = x[idx, :]
            frac = np.array((sub > 0).sum(axis=0)).ravel() / len(idx)
        else:
            sub = x[idx, :]
            frac = np.asarray((sub > 0).sum(axis=0)).ravel() / len(idx)
        det_run[run_name] = frac

    if det_run:
        det_df = pd.DataFrame(det_run, index=ad.var_names).T
        var_rank = det_df.var(axis=0).sort_values(ascending=False)
        selected_genes = var_rank.head(40).index
        plt.figure(figsize=(min(12, len(selected_genes) * 0.3 + 4), max(4, len(det_df) * 0.35 + 2)))
        sns.heatmap(
            det_df[selected_genes],
            cmap="rocket",
            vmin=0,
            vmax=1,
            cbar_kws={"label": "fraction detected"},
        )
        plt.title("Gene detection per run (top variable genes)")
        plt.xlabel("gene")
        plt.ylabel("run")
        plt.tight_layout()
        plt.savefig(qc_dir / "gene_detection_heatmap_runs.png", dpi=200)
        plt.close()

    for cand in ["cell_area_um2", "cell_area", "area", "nucleus_area_um2"]:
        if cand in ad.obs.columns:
            plt.figure(figsize=(7, 4))
            sns.violinplot(
                data=ad.obs,
                x=sample_col,
                y=cand,
                inner="quartile",
                palette="PuBuGn",
            )
            plt.title(f"{cand} per run")
            plt.xlabel("Run")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(qc_dir / f"{cand}_violin.png", dpi=200)
            plt.close()
            break


def run_clustering(ad: sc.AnnData, args: argparse.Namespace, output_data_dir: Path) -> tuple[sc.AnnData, str]:
    sc.pp.filter_cells(ad, min_counts=args.min_counts)
    sc.pp.filter_cells(ad, min_genes=args.min_genes)

    sc.pp.normalize_total(ad, inplace=True, target_sum=args.target_sum)
    sc.pp.log1p(ad)

    sc.tl.pca(ad)
    sc.pp.neighbors(ad, n_neighbors=args.n_neighbors, n_pcs=args.n_pcs)
    sc.tl.umap(ad, min_dist=args.umap_min_dist)

    resolution_tokens = [token.strip() for token in args.leiden_resolutions.split(",") if token.strip()]
    if not resolution_tokens:
        raise ValueError("No valid leiden resolutions were provided.")

    last_key = ""
    for resolution_token in resolution_tokens:
        resolution = float(resolution_token)
        key = f"leiden_{resolution_token}"
        sc.tl.leiden(ad, resolution=resolution, key_added=key)
        last_key = key

    marker_path = output_data_dir / "markers_by_cluster.csv"
    sc.tl.rank_genes_groups(ad, groupby=last_key, method="t-test")
    markers = sc.get.rank_genes_groups_df(ad, group=None)
    markers.to_csv(marker_path, index=False)

    return ad, last_key


def main() -> None:
    args = parse_args()
    base_dir = Path(args.data_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    data_out_dir = out_dir / "data"
    qc_dir = out_dir / "xenium_qc"

    data_out_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    if not base_dir.exists() or not base_dir.is_dir():
        raise NotADirectoryError(f"Invalid data directory: {base_dir}")

    ad = load_and_concat_runs(base_dir=base_dir, run_prefix=args.run_prefix)
    sc.pp.calculate_qc_metrics(ad, percent_top=None, log1p=False, inplace=True)

    ad.obs["sample_id"] = ad.obs["run"].astype(str).apply(
        lambda run: infer_sample_id(run, args.sample_id_split, args.sample_id_index)
    )

    raw_path = data_out_dir / "raw.h5ad"
    ad.write(raw_path)
    print(f"Saved raw AnnData: {raw_path}")

    build_qc_outputs(ad, qc_dir)
    print(f"Saved QC outputs: {qc_dir}")

    ad_clustered, cluster_key = run_clustering(ad.copy(), args, data_out_dir)
    clustered_path = data_out_dir / "clustered.h5ad"
    ad_clustered.write(clustered_path)

    print(f"Saved clustered AnnData: {clustered_path}")
    print(f"Marker genes saved: {data_out_dir / 'markers_by_cluster.csv'}")
    print(f"Leiden key used for marker ranking: {cluster_key}")


if __name__ == "__main__":
    main()

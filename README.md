# Spatial Analysis for Dummies

Path-driven Xenium analysis workflow as:
- a reusable CLI script: `run_xenium_analysis.py`
- a step-by-step notebook: `01-path-driven-xenium-analysis.ipynb`

## What the pipeline does

1. Discovers run folders (default prefix: `output-`) under `--data-dir`.
2. Loads each run's:
   - `cell_feature_matrix.h5`
   - `cells.csv.gz`
3. Concatenates runs into one AnnData object and computes QC metrics.
4. Writes QC tables and plots.
5. Runs clustering workflow (normalize, log1p, PCA, neighbors, UMAP, Leiden).
6. Exports marker genes for the last Leiden resolution.

## Requirements

Python 3.10+ and these packages:
- `scanpy`
- `pandas`
- `numpy`
- `scipy`
- `matplotlib`
- `seaborn`

Install example:

```bash
pip install scanpy pandas numpy scipy matplotlib seaborn
```

## Expected input layout

`--data-dir` should look like:

```text
/path/to/dataset/
  output-.../
    cell_feature_matrix.h5
    cells.csv.gz
  output-.../
    cell_feature_matrix.h5
    cells.csv.gz
```

Runs missing either required file are skipped.

## Run

From this repo:

```bash
python3 run_xenium_analysis.py \
  --data-dir /absolute/path/to/new/dataset \
  --out-dir /absolute/path/to/output
```

### Useful flags

- `--run-prefix` (default: `output-`)
- `--min-counts` (default: `50`)
- `--min-genes` (default: `15`)
- `--target-sum` (default: `100`)
- `--n-neighbors` (default: `15`)
- `--n-pcs` (default: `30`)
- `--umap-min-dist` (default: `0.1`)
- `--leiden-resolutions` (default: `0.1,0.5,1,1.5,2`)
- `--sample-id-split` (default: `__`)
- `--sample-id-index` (default: `2`)

## Outputs

Written under `--out-dir`:

- `data/raw.h5ad`
- `data/clustered.h5ad`
- `data/markers_by_cluster.csv`
- `xenium_qc/summary_by_run.csv`
- `xenium_qc/gene_detection_overall.csv`
- `xenium_qc/*.png` (QC and composition plots)

## Notebook version

Use `01-path-driven-xenium-analysis.ipynb` if you want the guided workflow.

1. Set `DATA_DIR` and `OUT_DIR` in Step 1.
2. Run cells top-to-bottom.

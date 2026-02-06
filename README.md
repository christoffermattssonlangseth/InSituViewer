# Xenium Analysis (Path-Driven)

This reproduces the core workflow from `/Users/chrislangseth/work/spatialist/intership1/00-batch-processing.ipynb` as a script where you only provide the new dataset path.

## Run

```bash
python3 /Users/chrislangseth/work/spatialist/internship2/run_xenium_analysis.py \
  --data-dir /absolute/path/to/new/dataset \
  --out-dir /absolute/path/to/output
```

## Notebook Version

Use `/Users/chrislangseth/work/spatialist/internship2/01-path-driven-xenium-analysis.ipynb` if you want a guided, step-by-step workflow with explanations for each stage.
- In the notebook, update `DATA_DIR` and `OUT_DIR` in Step 1.
- Then run all cells top-to-bottom.

`--data-dir` should contain one or more run directories like `output-*`, and each run must include:
- `cell_feature_matrix.h5`
- `cells.csv.gz`

## Outputs

Written under `--out-dir`:
- `data/raw.h5ad`
- `data/clustered.h5ad`
- `data/markers_by_cluster.csv`
- `xenium_qc/*.png`
- `xenium_qc/summary_by_run.csv`
- `xenium_qc/gene_detection_overall.csv`

## Notes

- Default clustering resolutions: `0.1,0.5,1,1.5,2`
- You can override thresholds/params (filtering, neighbors, UMAP, Leiden) via CLI flags.

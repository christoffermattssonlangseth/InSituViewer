# Utils

This folder vendors two local toolsets so they can be imported from this repo.

## MANA

Source: `/Users/christoffer/work/karolinska/development/MANA/utils`

Available in `utils.mana`:
- `aggregate_neighbors_weighted`
- `aggregate_neighbors_weighted_simple`
- `plot_spatial_compact_fast`

See `utils/mana/README.md` for usage details.

## KaroSpace

Source: `/Users/christoffer/work/karolinska/development/spatial-viewer/karospace`

Available in `utils.karospace`:
- `load_spatial_data`
- `SpatialDataset`
- `export_to_html`
- CLI entry: `python -m utils.karospace.cli ...`

Logo asset is copied to `utils/assets/logo.png` for HTML export branding.

# 8.28 HiMCM Mock — Overleaf/GitHub project

- `main.tex` — existing full paper; retained unchanged during the bare-bones draft.
- `barebones.tex` — preservation-first revision through Section 6.3, about 15 pages of
  front matter and substantive content, with references afterward. Restores original
  background, applicable assumptions, forecast prose/figures and financial break-even
  equation/table. Revised sections explain behavioral demand, waiting/revenue TOPSIS,
  Phase-1-only budget and later financially viable expansion by schedule enumeration.
  Original forecast pixels are embedded for the native single-file preview; project builds
  use the original PNGs. Local frequency inputs and numerical queue results remain uncalibrated.
- `section4 newdraft.tex` — teammate's empty draft file retained from Overleaf.
- Existing `ev_*.png` and `temp_arima_forecast.png` — original paper figures; the old
  break-even/utilization-sweep assets are retained as history but no longer cited.
- `ev_capacity_profiles.png` — new figure of measured source weekly profiles.
- `capacity_model.py` — reproducible fitting and local-capacity evaluator.
- `capacity_config.json` — registration/local connector data and unset calibration.
- `capacity_profiles.json` — anonymous measured aggregate profiles and provenance.
- `capacity_results.json` — current pending-calibration report.
- `capacity_sources.json` — original dataset download manifest and hashes.
- `plot_capacity_profiles.py` — Matplotlib figure generator.
- `test_capacity_model.py` — numerical checks for the new capacity calculation.
- `CAPACITY_MODEL.txt` — equations, reproduction commands, filters and calibration steps.
- `.gitignore` — excludes Python caches and temporary LaTeX build output.

Raw datasets and discussion context are stored in the sibling `../charging-data/`;
the user requested a visible copy under `~/Desktop/EV Charging Data and Question/`.
Pull GitHub changes manually in Overleaf via Integrations → GitHub → Pull changes.

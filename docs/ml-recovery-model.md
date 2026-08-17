# CloudRescue ML recovery-time model

CloudRescue keeps **recoverability** and **recovery-time forecasting** separate.

The deterministic recovery engine decides whether a scenario is `READY`, `RECOVERABLE_WITH_GAPS`, or `UNRECOVERABLE` from explicit control dependencies such as protected backups, key recovery, isolated recovery identity, infrastructure-as-code, DNS rebuildability, and cross-region copies.

The ML layer never changes that status. It forecasts restore duration so recovery teams can reason about RTO pressure after the hard dependency checks are complete.

## Model

The lab uses a seeded `RandomForestRegressor` trained on 1,200 deterministic synthetic recovery-history records. A fixed train/test split reports held-out MAE and R² so the repository exposes reproducible model evidence rather than only a demo prediction.

Features include:

- baseline restore estimate and backup age;
- workload criticality;
- eight recovery-control states;
- cloud platform indicators;
- failure-scenario indicators.

The synthetic target represents observed exercise duration generated from a hidden recovery-duration process with scenario overhead, control-gap penalties, cloud/criticality effects, and bounded random variation.

## Safety boundary

For an `UNRECOVERABLE` scenario, the prediction is marked `forecast_only=true`. It means *conditional timing estimate if the blocker were remediated*, not evidence that recovery is possible.

All training and evaluation data is synthetic. Held-out metrics demonstrate that the implementation can learn the synthetic generator; they do not estimate performance on real AWS, Azure, or GCP recovery exercises.

Production use should train on authorized recovery/game-day history, model workload size and storage characteristics, monitor drift, calculate prediction intervals, and validate forecasts against observed restore exercises.

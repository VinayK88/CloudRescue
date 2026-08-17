# Model Monitoring and Recovery Robustness Testing

CloudRescue monitors the Random Forest restore-time forecaster separately from the deterministic recovery-dependency engine.

## Forecast monitoring

`cloudrescue.evaluation.monitoring_report` tracks two classes of evidence:

- Population Stability Index (PSI) across forecast features;
- prediction residual degradation using mean absolute error (MAE).

The default PSI alert threshold is `0.20`. Residual degradation is flagged when current MAE grows materially relative to the reference window. The test suite includes a steady-state window and a deterministic synthetic shifted window with longer baseline restores, older backups, and higher realized restore time.

The monitoring report publishes:

- model version: `cloudrescue-rf-rto-v1`;
- feature schema: `recovery-forecast-v1`;
- model random seed;
- reference/current MAE;
- per-feature PSI;
- report-generation timestamp.

A monitoring alert means the forecast distribution or residual behavior changed enough to warrant review. It does not change whether a workload is recoverable.

## Recovery robustness tests

The synthetic suite exercises:

1. a recoverable workload with a tight RTO and elevated restore pressure;
2. a KMS-loss case without an independent key-recovery path;
3. a region-loss case without a cross-region copy.

The second and third cases must remain `UNRECOVERABLE`, and their ML outputs must remain `forecast_only`. This test protects the design invariant that a statistical timing forecast can never override a missing hard recovery dependency.

## Safety boundary

All cloud profiles, recovery histories, timings, failures, and control states are synthetic. The suite does not change cloud resources, backup policies, keys, identities, or infrastructure.

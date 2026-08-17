from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import numpy as np

from .engine import assess
from .fixtures import PROFILES, SCENARIOS
from .ml import (
    FEATURE_NAMES,
    MODEL_NAME,
    RANDOM_STATE,
    _synthetic_history,
    _trained_model,
    forecast,
)
from .models import RecoveryProfile, Scenario

MODEL_VERSION = "cloudrescue-rf-rto-v1"
FEATURE_SCHEMA_VERSION = "recovery-forecast-v1"
PSI_ALERT_THRESHOLD = 0.20
MAE_DEGRADATION_RATIO = 1.30


def _psi(reference: np.ndarray, current: np.ndarray, bins: int = 8) -> float:
    edges = np.unique(np.quantile(reference, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_pct = np.clip(ref_counts / max(1, ref_counts.sum()), 1e-6, None)
    cur_pct = np.clip(cur_counts / max(1, cur_counts.sum()), 1e-6, None)
    return round(float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))), 4)


def _window(seed: int) -> tuple[np.ndarray, np.ndarray]:
    return _synthetic_history(samples=400, seed=seed)


def _shifted_window() -> tuple[np.ndarray, np.ndarray]:
    x, y = _window(89)
    x = x.copy()
    y = y.copy()
    count = len(x) // 3
    x[:count, FEATURE_NAMES.index("baseline_restore_minutes")] += 90.0
    x[:count, FEATURE_NAMES.index("log_backup_age_minutes")] += 0.8
    y[:count] += 70.0
    return x, y


def monitoring_report(
    reference: tuple[np.ndarray, np.ndarray],
    current: tuple[np.ndarray, np.ndarray],
) -> dict[str, object]:
    model, _ = _trained_model()
    ref_x, ref_y = reference
    cur_x, cur_y = current
    ref_pred = model.predict(ref_x)
    cur_pred = model.predict(cur_x)
    ref_mae = float(np.mean(np.abs(ref_y - ref_pred)))
    cur_mae = float(np.mean(np.abs(cur_y - cur_pred)))

    feature_psi = {
        name: _psi(ref_x[:, i], cur_x[:, i])
        for i, name in enumerate(FEATURE_NAMES)
    }
    feature_alerts = sorted(
        name for name, value in feature_psi.items() if value >= PSI_ALERT_THRESHOLD
    )
    residual_alert = cur_mae > max(ref_mae * MAE_DEGRADATION_RATIO, ref_mae + 5.0)

    return {
        "feature_metric": "population_stability_index",
        "psi_threshold": PSI_ALERT_THRESHOLD,
        "feature_psi": feature_psi,
        "feature_alerts": feature_alerts,
        "reference_mae_minutes": round(ref_mae, 1),
        "current_mae_minutes": round(cur_mae, 1),
        "mae_degradation_ratio_threshold": MAE_DEGRADATION_RATIO,
        "residual_alert": bool(residual_alert),
        "drift_alert": bool(feature_alerts or residual_alert),
    }


def _stress_cases() -> list[tuple[str, RecoveryProfile, Scenario]]:
    admin = next(s for s in SCENARIOS if s.scenario_id == "admin-compromise")
    kms = next(s for s in SCENARIOS if s.scenario_id == "kms-loss")
    region = next(s for s in SCENARIOS if s.scenario_id == "region-outage")
    return [
        (
            "tight_rto_high_restore_pressure",
            replace(
                PROFILES["payments-db-prod"],
                rto_target_minutes=45,
                estimated_restore_minutes=180,
            ),
            admin,
        ),
        (
            "missing_key_recovery_path",
            PROFILES["identity-store"],
            kms,
        ),
        (
            "missing_cross_region_copy",
            replace(PROFILES["orders-api"], cross_region_copy=False),
            region,
        ),
    ]


def robustness_evaluation() -> dict[str, object]:
    results = []
    for case_name, profile, scenario in _stress_cases():
        deterministic = assess(profile, scenario)
        prediction = forecast(
            profile,
            scenario,
            deterministic.status,
            deterministic.estimated_rto_minutes,
        )
        results.append({
            "case": case_name,
            "status": deterministic.status,
            "blockers": list(deterministic.blockers),
            "rto_target_minutes": profile.rto_target_minutes,
            "deterministic_rto_minutes": deterministic.estimated_rto_minutes,
            "predicted_restore_minutes": prediction.predicted_restore_minutes,
            "predicted_rto_margin_minutes": prediction.predicted_rto_margin_minutes,
            "forecast_only": prediction.forecast_only,
        })

    hard_blocker_cases = [row for row in results if row["blockers"]]
    hard_blockers_preserved = all(
        row["status"] == "UNRECOVERABLE" and row["forecast_only"]
        for row in hard_blocker_cases
    )
    return {
        "cases": results,
        "total": len(results),
        "hard_blocker_cases": len(hard_blocker_cases),
        "hard_blockers_preserved": hard_blockers_preserved,
        "meaning": "Synthetic recovery stress tests; ML forecasts timing but never overrides deterministic recoverability blockers.",
    }


def evaluation_summary() -> dict[str, object]:
    reference = _window(88)
    return {
        "model_metadata": {
            "model": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "random_state": RANDOM_STATE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "steady_state_monitoring": monitoring_report(reference, reference),
        "synthetic_shift_monitoring": monitoring_report(reference, _shifted_window()),
        "robustness_evaluation": robustness_evaluation(),
    }

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .models import RecoveryProfile, Scenario

MODEL_NAME = "RandomForestRegressor"
RANDOM_STATE = 47
HISTORY_SAMPLES = 1200

CONTROL_NAMES = (
    "backup_available",
    "backup_immutable",
    "cross_account_copy",
    "key_recoverable",
    "recovery_identity_isolated",
    "iac_available",
    "dns_rebuildable",
    "cross_region_copy",
)
SCENARIO_IDS = (
    "admin-compromise",
    "backup-tamper",
    "kms-loss",
    "region-outage",
    "recovery-identity-compromise",
    "cicd-state-loss",
)
CLOUDS = ("AWS", "Azure", "GCP")

FEATURE_NAMES = (
    "baseline_restore_minutes",
    "log_backup_age_minutes",
    "criticality",
    *CONTROL_NAMES,
    "cloud_aws",
    "cloud_azure",
    "cloud_gcp",
    *[f"scenario_{scenario}" for scenario in SCENARIO_IDS],
)


@dataclass(frozen=True)
class RestoreTimeFinding:
    scenario_id: str
    workload: str
    deterministic_status: str
    deterministic_rto_minutes: int
    predicted_restore_minutes: int
    rto_target_minutes: int
    predicted_rto_margin_minutes: int
    forecast_only: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _vector(
    cloud: str,
    criticality: str,
    controls: dict[str, bool],
    base_restore_minutes: int,
    backup_age_minutes: int,
    scenario_id: str,
) -> list[float]:
    return [
        float(base_restore_minutes),
        math.log1p(max(0, backup_age_minutes)),
        2.0 if criticality == "CRITICAL" else 1.0,
        *[float(bool(controls[name])) for name in CONTROL_NAMES],
        *[float(cloud == value) for value in CLOUDS],
        *[float(scenario_id == value) for value in SCENARIO_IDS],
    ]


def feature_vector(profile: RecoveryProfile, scenario: Scenario) -> np.ndarray:
    controls = {name: bool(getattr(profile, name)) for name in CONTROL_NAMES}
    return np.asarray(
        _vector(
            profile.cloud,
            profile.criticality,
            controls,
            profile.estimated_restore_minutes,
            profile.backup_age_minutes,
            scenario.scenario_id,
        ),
        dtype=float,
    )


def _synthetic_history(samples: int = HISTORY_SAMPLES, seed: int = RANDOM_STATE):
    rng = random.Random(seed)
    rows: list[list[float]] = []
    targets: list[float] = []

    control_probabilities = {
        "backup_available": 0.97,
        "backup_immutable": 0.88,
        "cross_account_copy": 0.82,
        "key_recoverable": 0.94,
        "recovery_identity_isolated": 0.91,
        "iac_available": 0.93,
        "dns_rebuildable": 0.95,
        "cross_region_copy": 0.84,
    }
    scenario_base = {
        "admin-compromise": 15,
        "backup-tamper": 10,
        "kms-loss": 20,
        "region-outage": 35,
        "recovery-identity-compromise": 20,
        "cicd-state-loss": 45,
    }

    for _ in range(samples):
        cloud = rng.choice(CLOUDS)
        criticality = rng.choice(("HIGH", "CRITICAL"))
        scenario_id = rng.choice(SCENARIO_IDS)
        controls = {
            name: rng.random() < probability
            for name, probability in control_probabilities.items()
        }
        base_restore = rng.randint(30, 220)
        backup_age = rng.randint(2, 120)

        actual = float(base_restore + scenario_base[scenario_id])
        actual += 18 * sum(not value for value in controls.values())

        if scenario_id == "cicd-state-loss" and not controls["iac_available"]:
            actual += 70
        if scenario_id == "region-outage" and not controls["cross_region_copy"]:
            actual += 45
        if scenario_id == "kms-loss" and not controls["key_recoverable"]:
            actual += 55
        if scenario_id == "backup-tamper" and not controls["backup_immutable"]:
            actual += 40
        if scenario_id == "recovery-identity-compromise" and not controls["recovery_identity_isolated"]:
            actual += 50
        if scenario_id == "admin-compromise":
            if not controls["backup_immutable"]:
                actual += 25
            if not controls["cross_account_copy"]:
                actual += 30

        if criticality == "CRITICAL":
            actual += 8
        actual += {"AWS": 0, "Azure": 7, "GCP": 4}[cloud]
        actual += rng.gauss(0, 10)

        rows.append(
            _vector(cloud, criticality, controls, base_restore, backup_age, scenario_id)
        )
        targets.append(max(1.0, actual))

    return np.asarray(rows, dtype=float), np.asarray(targets, dtype=float)


@lru_cache(maxsize=1)
def _trained_model():
    x, y = _synthetic_history()
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=RANDOM_STATE
    )
    model = RandomForestRegressor(
        n_estimators=240,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = {
        "heldout_mae_minutes": round(float(mean_absolute_error(y_test, predictions)), 1),
        "heldout_r2": round(float(r2_score(y_test, predictions)), 3),
        "train_samples": len(x_train),
        "test_samples": len(x_test),
    }
    importance = sorted(
        zip(FEATURE_NAMES, model.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )
    metrics["top_feature_importance"] = [
        {"feature": name, "importance": round(float(value), 3)}
        for name, value in importance[:6]
    ]
    return model, metrics


def forecast(
    profile: RecoveryProfile,
    scenario: Scenario,
    deterministic_status: str,
    deterministic_rto_minutes: int,
) -> RestoreTimeFinding:
    model, _ = _trained_model()
    prediction = max(1, round(float(model.predict([feature_vector(profile, scenario)])[0])))
    return RestoreTimeFinding(
        scenario_id=scenario.scenario_id,
        workload=profile.workload,
        deterministic_status=deterministic_status,
        deterministic_rto_minutes=deterministic_rto_minutes,
        predicted_restore_minutes=prediction,
        rto_target_minutes=profile.rto_target_minutes,
        predicted_rto_margin_minutes=profile.rto_target_minutes - prediction,
        forecast_only=deterministic_status == "UNRECOVERABLE",
    )


def model_summary() -> dict[str, object]:
    _, metrics = _trained_model()
    return {
        "model": MODEL_NAME,
        "synthetic_history_samples": HISTORY_SAMPLES,
        "features": list(FEATURE_NAMES),
        **metrics,
        "decision_boundary": "ML forecasts restore duration only. Deterministic hard blockers remain authoritative for recoverability.",
    }

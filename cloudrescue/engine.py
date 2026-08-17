from typing import Dict, List
from .models import RecoveryProfile, Scenario, Assessment
from .fixtures import PROFILES, SCENARIOS
from .ml import forecast, model_summary

RECOMMENDATIONS = {
    "backup_immutable": "enforce immutable retention / vault lock on recovery copies",
    "cross_account_copy": "maintain a recovery copy outside the production administrative boundary",
    "key_recoverable": "establish an independent, tested encryption-key recovery path",
    "recovery_identity_isolated": "separate recovery identities from production IAM and require strong MFA / break-glass controls",
    "iac_available": "store versioned infrastructure-as-code and recovery state outside the primary deployment plane",
    "dns_rebuildable": "document and test DNS / routing reconstruction",
    "cross_region_copy": "maintain tested cross-region recovery copies for region-loss scenarios",
    "backup_available": "ensure protected backups exist and are continuously verified",
}


def _controls(profile: RecoveryProfile) -> Dict[str, bool]:
    return {
        "backup_available": profile.backup_available,
        "backup_immutable": profile.backup_immutable,
        "cross_account_copy": profile.cross_account_copy,
        "key_recoverable": profile.key_recoverable,
        "recovery_identity_isolated": profile.recovery_identity_isolated,
        "iac_available": profile.iac_available,
        "dns_rebuildable": profile.dns_rebuildable,
        "cross_region_copy": profile.cross_region_copy,
    }


def assess(profile: RecoveryProfile, scenario: Scenario) -> Assessment:
    controls = _controls(profile)
    required = {"backup_available", "key_recoverable", "recovery_identity_isolated", "iac_available", "dns_rebuildable"}
    degraded: List[str] = []

    if scenario.scenario_id == "admin-compromise":
        required |= {"backup_immutable", "cross_account_copy"}
    elif scenario.scenario_id == "backup-tamper":
        required |= {"backup_immutable"}
    elif scenario.scenario_id == "kms-loss":
        required |= {"key_recoverable"}
    elif scenario.scenario_id == "region-outage":
        required |= {"cross_region_copy"}
    elif scenario.scenario_id == "recovery-identity-compromise":
        required |= {"recovery_identity_isolated"}
    elif scenario.scenario_id == "cicd-state-loss":
        required |= {"iac_available"}

    blockers = [name for name in sorted(required) if not controls[name]]
    for name, value in controls.items():
        if not value and name not in blockers:
            degraded.append(name)

    if blockers:
        status = "UNRECOVERABLE"
    elif degraded:
        status = "RECOVERABLE_WITH_GAPS"
    else:
        status = "READY"

    failed_count = len(blockers)
    degraded_count = len(degraded)
    confidence = max(0, 100 - 22 * failed_count - 6 * degraded_count)

    estimated_rto = profile.estimated_restore_minutes + 25 * failed_count
    if scenario.scenario_id == "region-outage":
        estimated_rto += 20
    if scenario.scenario_id == "cicd-state-loss" and not profile.iac_available:
        estimated_rto += 90

    estimated_rpo = profile.backup_age_minutes
    rto_met = estimated_rto <= profile.rto_target_minutes and status != "UNRECOVERABLE"
    rpo_met = estimated_rpo <= profile.rpo_target_minutes and profile.backup_available

    surviving = [name for name, value in controls.items() if value]
    actions = [RECOMMENDATIONS[name] for name in blockers + degraded]

    return Assessment(
        scenario.scenario_id,
        profile.workload,
        profile.cloud,
        status,
        confidence,
        estimated_rto,
        estimated_rpo,
        rto_met,
        rpo_met,
        blockers,
        degraded,
        surviving,
        actions,
    )


def run_baseline():
    assessments = [assess(PROFILES[s.workload], s) for s in SCENARIOS]
    forecasts = [
        forecast(
            PROFILES[scenario.workload],
            scenario,
            assessment.status,
            assessment.estimated_rto_minutes,
        )
        for assessment, scenario in zip(assessments, SCENARIOS)
    ]
    ml = model_summary()
    expected_matches = sum(a.status == s.expected_status for a, s in zip(assessments, SCENARIOS))
    ready = sum(a.status == "READY" for a in assessments)
    unrecoverable = sum(a.status == "UNRECOVERABLE" for a in assessments)
    rto_met = sum(a.rto_met for a in assessments)
    rpo_met = sum(a.rpo_met for a in assessments)
    avg_conf = round(sum(a.recovery_confidence for a in assessments) / len(assessments), 1)
    return {
        "summary": {
            "scenarios": len(assessments),
            "expected_status_matches": expected_matches,
            "ready": ready,
            "recoverable_with_gaps": sum(a.status == "RECOVERABLE_WITH_GAPS" for a in assessments),
            "unrecoverable": unrecoverable,
            "rto_targets_met": rto_met,
            "rpo_targets_met": rpo_met,
            "mean_recovery_confidence": avg_conf,
            "ml_model": ml["model"],
            "ml_heldout_mae_minutes": ml["heldout_mae_minutes"],
        },
        "ml": ml,
        "assessments": [a.to_dict() for a in assessments],
        "ml_restore_forecasts": [row.to_dict() for row in forecasts],
    }

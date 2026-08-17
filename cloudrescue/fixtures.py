from .models import RecoveryProfile, Scenario

PROFILES = {
    "payments-db-prod": RecoveryProfile(
        "payments-db-prod", "AWS", "CRITICAL", True, True, True, True, True,
        True, True, True, 90, 15, 62, 10
    ),
    "customer-analytics": RecoveryProfile(
        "customer-analytics", "Azure", "HIGH", True, False, True, True, True,
        True, True, True, 240, 60, 115, 35
    ),
    "identity-store": RecoveryProfile(
        "identity-store", "GCP", "CRITICAL", True, True, True, False, True,
        True, True, True, 60, 10, 40, 8
    ),
    "orders-api": RecoveryProfile(
        "orders-api", "AWS", "HIGH", True, True, True, True, True,
        True, True, True, 120, 30, 72, 18
    ),
    "ml-registry": RecoveryProfile(
        "ml-registry", "Azure", "HIGH", True, True, True, True, False,
        True, True, True, 180, 60, 96, 45
    ),
    "billing-service": RecoveryProfile(
        "billing-service", "GCP", "HIGH", True, True, True, True, True,
        False, True, True, 150, 30, 190, 20
    ),
}

SCENARIOS = [
    Scenario("admin-compromise", "Cloud administrator compromised", "payments-db-prod",
             "Production admin trust is removed; recovery must use isolated identities and protected copies.", "READY"),
    Scenario("backup-tamper", "Backup retention tampered", "customer-analytics",
             "Primary backup retention is assumed compromised; immutability becomes a hard requirement.", "UNRECOVERABLE"),
    Scenario("kms-loss", "Production KMS path lost", "identity-store",
             "The production key path is unavailable; recovery requires an independent key recovery path.", "UNRECOVERABLE"),
    Scenario("region-outage", "Primary region unavailable", "orders-api",
             "Primary region is unavailable; cross-region copies and rebuildable control-plane dependencies are required.", "READY"),
    Scenario("recovery-identity-compromise", "Recovery identity compromised", "ml-registry",
             "The recovery identity shares the production trust plane and is treated as compromised.", "UNRECOVERABLE"),
    Scenario("cicd-state-loss", "CI/CD and IaC state lost", "billing-service",
             "Application recovery must rebuild infrastructure without the primary deployment state.", "UNRECOVERABLE"),
]

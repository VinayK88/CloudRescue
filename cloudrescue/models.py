from dataclasses import dataclass, asdict
from typing import List

@dataclass(frozen=True)
class RecoveryProfile:
    workload: str
    cloud: str
    criticality: str
    backup_available: bool
    backup_immutable: bool
    cross_account_copy: bool
    key_recoverable: bool
    recovery_identity_isolated: bool
    iac_available: bool
    dns_rebuildable: bool
    cross_region_copy: bool
    rto_target_minutes: int
    rpo_target_minutes: int
    estimated_restore_minutes: int
    backup_age_minutes: int

@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    title: str
    workload: str
    description: str
    expected_status: str

@dataclass
class Assessment:
    scenario_id: str
    workload: str
    cloud: str
    status: str
    recovery_confidence: int
    estimated_rto_minutes: int
    estimated_rpo_minutes: int
    rto_met: bool
    rpo_met: bool
    blockers: List[str]
    degraded_controls: List[str]
    surviving_controls: List[str]
    recommended_actions: List[str]

    def to_dict(self):
        return asdict(self)

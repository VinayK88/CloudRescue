# Methodology

CloudRescue models recovery as a dependency problem. A workload is recoverable only when the required backup, key, identity, infrastructure-as-code, routing/DNS, and scenario-specific redundancy controls survive the assumed failure domain.

The current score is an explainable heuristic. Recovery confidence starts at 100 and subtracts 22 points per hard blocker and 6 points per non-blocking control gap. RTO and RPO are fixture values used to demonstrate decision logic. They are not measured provider performance.

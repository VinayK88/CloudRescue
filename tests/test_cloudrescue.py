import unittest
from cloudrescue.engine import assess, run_baseline
from cloudrescue.fixtures import PROFILES, SCENARIOS

class CloudRescueTests(unittest.TestCase):
    def test_baseline_has_six_scenarios(self):
        self.assertEqual(run_baseline()["summary"]["scenarios"], 6)

    def test_expected_statuses_match(self):
        self.assertEqual(run_baseline()["summary"]["expected_status_matches"], 6)

    def test_admin_compromise_is_recoverable(self):
        s = SCENARIOS[0]
        self.assertEqual(assess(PROFILES[s.workload], s).status, "READY")

    def test_backup_tamper_finds_immutability_gap(self):
        s = SCENARIOS[1]
        a = assess(PROFILES[s.workload], s)
        self.assertEqual(a.status, "UNRECOVERABLE")
        self.assertIn("backup_immutable", a.blockers)

    def test_kms_loss_finds_key_gap(self):
        s = SCENARIOS[2]
        self.assertIn("key_recoverable", assess(PROFILES[s.workload], s).blockers)

    def test_region_outage_ready(self):
        s = SCENARIOS[3]
        self.assertEqual(assess(PROFILES[s.workload], s).status, "READY")

    def test_recovery_identity_gap(self):
        s = SCENARIOS[4]
        self.assertIn("recovery_identity_isolated", assess(PROFILES[s.workload], s).blockers)

    def test_iac_loss_gap(self):
        s = SCENARIOS[5]
        self.assertIn("iac_available", assess(PROFILES[s.workload], s).blockers)

if __name__ == "__main__":
    unittest.main()

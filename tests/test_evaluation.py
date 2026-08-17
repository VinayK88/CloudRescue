import unittest

from cloudrescue.evaluation import (
    _shifted_window,
    _window,
    evaluation_summary,
    monitoring_report,
    robustness_evaluation,
)


class CloudRescueEvaluationTests(unittest.TestCase):
    def test_steady_state_has_no_drift(self):
        reference = _window(88)
        report = monitoring_report(reference, reference)
        self.assertFalse(report["drift_alert"])
        self.assertFalse(report["residual_alert"])
        self.assertEqual(report["feature_alerts"], [])

    def test_shifted_window_triggers_monitoring(self):
        reference = _window(88)
        report = monitoring_report(reference, _shifted_window())
        self.assertTrue(report["drift_alert"])
        self.assertTrue(report["residual_alert"] or len(report["feature_alerts"]) > 0)

    def test_hard_blockers_remain_authoritative(self):
        result = robustness_evaluation()
        self.assertEqual(result["total"], 3)
        self.assertGreaterEqual(result["hard_blocker_cases"], 2)
        self.assertTrue(result["hard_blockers_preserved"])

    def test_summary_contains_versioned_metadata(self):
        summary = evaluation_summary()
        self.assertEqual(summary["model_metadata"]["model_version"], "cloudrescue-rf-rto-v1")
        self.assertEqual(summary["model_metadata"]["feature_schema_version"], "recovery-forecast-v1")


if __name__ == "__main__":
    unittest.main()

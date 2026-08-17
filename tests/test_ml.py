import unittest

from cloudrescue.engine import assess
from cloudrescue.fixtures import PROFILES, SCENARIOS
from cloudrescue.ml import FEATURE_NAMES, MODEL_NAME, feature_vector, forecast, model_summary


class CloudRescueMLTests(unittest.TestCase):
    def test_feature_shape(self):
        scenario = SCENARIOS[0]
        self.assertEqual(
            len(feature_vector(PROFILES[scenario.workload], scenario)),
            len(FEATURE_NAMES),
        )

    def test_model_quality_on_synthetic_history(self):
        summary = model_summary()
        self.assertEqual(summary["model"], MODEL_NAME)
        self.assertLess(summary["heldout_mae_minutes"], 25.0)
        self.assertGreater(summary["heldout_r2"], 0.75)

    def test_predictions_are_positive(self):
        for scenario in SCENARIOS:
            profile = PROFILES[scenario.workload]
            deterministic = assess(profile, scenario)
            prediction = forecast(
                profile,
                scenario,
                deterministic.status,
                deterministic.estimated_rto_minutes,
            )
            self.assertGreater(prediction.predicted_restore_minutes, 0)

    def test_ml_does_not_override_hard_blocker(self):
        scenario = SCENARIOS[2]
        profile = PROFILES[scenario.workload]
        deterministic = assess(profile, scenario)
        prediction = forecast(
            profile,
            scenario,
            deterministic.status,
            deterministic.estimated_rto_minutes,
        )
        self.assertEqual(deterministic.status, "UNRECOVERABLE")
        self.assertTrue(prediction.forecast_only)
        self.assertIn("key_recoverable", deterministic.blockers)

    def test_ready_scenario_remains_deterministic(self):
        scenario = SCENARIOS[3]
        profile = PROFILES[scenario.workload]
        deterministic = assess(profile, scenario)
        self.assertEqual(deterministic.status, "READY")

    def test_model_is_deterministic(self):
        first = model_summary()
        second = model_summary()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

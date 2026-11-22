import unittest
from pipeline import prepare, export


def study(x=1, y=4, n=100, m=100):
    return {
        "experiment": "A/B",
        "randomized": True,
        "cohorts": [
            {
                "id": "return",
                "window_complete": True,
                "control": {"exposed": n, "converted": x},
                "treatment": {"exposed": m, "converted": y},
            }
        ],
    }


class ExperimentTests(unittest.TestCase):
    def test_lift_and_uncertainty(self):
        c = prepare(study(20, 25))["candidates"][0]
        self.assertEqual((c["difference_pp"], c["relative_lift_pct"]), (5, 25))
        self.assertLess(c["interval_low_pp"], 0)
        self.assertGreater(c["interval_high_pp"], 5)

    def test_zero_control_rate_and_zero_arm_differ(self):
        self.assertIsNone(prepare(study(0, 1))["candidates"][0]["relative_lift_pct"])
        c = prepare(study(0, 1, 0, 10))["candidates"][0]
        self.assertIsNone(c["difference_pp"])
        self.assertIn("Missing arm denominator", c["checks"])

    def test_allocation_screen_and_exported_warning(self):
        d = study(2, 10, 20, 180)
        r = prepare(d)
        c = r["candidates"][0]
        self.assertTrue(any("three" in s for s in c["checks"]))
        self.assertIn(
            "Validity review required", export(d, r, [c])["experiment-readout.md"]
        )
        self.assertNotIn("## return", export(d, r, [])["experiment-readout.md"])

    def test_invalid_conversions_and_unrandomized(self):
        with self.assertRaises(ValueError):
            prepare(study(101, 7))
        d = study()
        d["randomized"] = False
        self.assertIn(
            "Allocation was not randomized", prepare(d)["candidates"][0]["checks"]
        )

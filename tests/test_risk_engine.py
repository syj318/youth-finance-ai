import math
import unittest

from src.risk_engine import calculate_risk


class CalculateRiskTests(unittest.TestCase):
    def setUp(self):
        self.stable_metrics = {
            "monthly_income": 4_000_000,
            "fixed_expense": 1_000_000,
            "variable_expense": 700_000,
            "loan_payment": 200_000,
            "monthly_saving": 1_000_000,
            "current_savings": 10_000_000,
        }
        self.risky_metrics = {
            "monthly_income": 2_500_000,
            "fixed_expense": 1_300_000,
            "variable_expense": 900_000,
            "loan_payment": 700_000,
            "monthly_saving": 0,
            "current_savings": 500_000,
        }

    def test_rejects_missing_negative_and_non_finite_inputs(self):
        missing = dict(self.stable_metrics)
        del missing["monthly_income"]
        with self.assertRaises(ValueError):
            calculate_risk(missing)

        negative = dict(self.stable_metrics, fixed_expense=-1)
        with self.assertRaises(ValueError):
            calculate_risk(negative)

        non_finite = dict(self.stable_metrics, monthly_income=math.inf)
        with self.assertRaises(ValueError):
            calculate_risk(non_finite)

    def test_rejects_zero_income(self):
        with self.assertRaises(ValueError):
            calculate_risk(dict(self.stable_metrics, monthly_income=0))

    def test_expenses_greater_than_income_are_scored_as_deficit_risk(self):
        result = calculate_risk({
            "monthly_income": 2_000_000,
            "fixed_expense": 1_200_000,
            "variable_expense": 700_000,
            "loan_payment": 300_000,
            "monthly_saving": 0,
            "current_savings": 0,
        })

        reason_codes = {
            reason["code"]
            for reason in result["domains"]["cashflow"]["reasons"]
        }
        self.assertIn("NEGATIVE_SURPLUS", reason_codes)
        self.assertGreater(result["domains"]["cashflow"]["score"], 0)

    def test_zero_monthly_saving_increases_saving_risk(self):
        result = calculate_risk(dict(self.stable_metrics, monthly_saving=0))
        saving = result["domains"]["saving"]
        reason_codes = {reason["code"] for reason in saving["reasons"]}

        self.assertEqual(saving["metrics"]["saving_rate"], 0)
        self.assertIn("LOW_SAVING_RATE", reason_codes)
        self.assertGreaterEqual(saving["score"], 14)

    def test_debt_service_rate_at_forty_percent_is_high_risk(self):
        result = calculate_risk({
            "monthly_income": 3_000_000,
            "fixed_expense": 600_000,
            "variable_expense": 400_000,
            "loan_payment": 1_200_000,
            "monthly_saving": 200_000,
            "current_savings": 5_000_000,
        })
        debt = result["domains"]["debt"]
        reason_codes = {reason["code"] for reason in debt["reasons"]}

        self.assertEqual(debt["metrics"]["debt_service_rate"], 40)
        self.assertEqual(debt["score"], 18)
        self.assertIn("HIGH_DEBT_SERVICE", reason_codes)

    def test_zero_emergency_fund_receives_maximum_emergency_risk(self):
        result = calculate_risk(dict(self.stable_metrics, current_savings=0))
        emergency = result["domains"]["emergency"]
        reason_codes = {reason["code"] for reason in emergency["reasons"]}

        self.assertEqual(emergency["metrics"]["emergency_months"], 0)
        self.assertEqual(emergency["score"], emergency["max_score"])
        self.assertIn("VERY_LOW_EMERGENCY_FUND", reason_codes)

    def test_returns_all_explainable_domains(self):
        result = calculate_risk(self.stable_metrics)

        self.assertEqual(
            set(result["domains"]),
            {"cashflow", "debt", "saving", "emergency", "expense_structure"},
        )
        for domain in result["domains"].values():
            self.assertTrue(domain["explanation"])
            self.assertTrue(domain["breakdown"])
            self.assertAlmostEqual(
                sum(component["score"] for component in domain["breakdown"]),
                domain["score"],
                places=2,
            )
            for component in domain["breakdown"]:
                self.assertTrue(component["explanation"])
                self.assertEqual(component["health_deduction"], component["score"])

    def test_final_score_matches_domain_sum_and_applied_interaction(self):
        result = calculate_risk(self.risky_metrics)
        breakdown = result["score_breakdown"]
        domain_sum = sum(domain["score"] for domain in result["domains"].values())

        self.assertAlmostEqual(domain_sum, breakdown["base_score"], places=2)
        self.assertAlmostEqual(
            result["score"],
            min(100, domain_sum + breakdown["applied_interaction_score"]),
            places=2,
        )
        self.assertAlmostEqual(breakdown["health_score"], 100 - result["score"], places=2)
        self.assertTrue(breakdown["explanation"])

    def test_risk_score_stays_between_zero_and_one_hundred(self):
        stable = calculate_risk(self.stable_metrics)
        risky = calculate_risk(self.risky_metrics)

        self.assertGreaterEqual(stable["score"], 0)
        self.assertLessEqual(stable["score"], 100)
        self.assertGreater(risky["score"], stable["score"])
        self.assertLessEqual(risky["score"], 100)


if __name__ == "__main__":
    unittest.main()

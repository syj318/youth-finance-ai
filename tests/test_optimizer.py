import unittest

from src.metrics import calculate_metrics
from src.optimizer import find_improvement_plans, optimize_financial_plan
from src.risk_engine import calculate_risk


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {
            "income": 3_000_000,
            "fixed_expense": 1_200_000,
            "living_expense": 900_000,
            "debt_payment": 500_000,
            "monthly_savings": 300_000,
            "savings": 2_000_000,
        }

    def test_returns_up_to_three_named_improvement_plans(self):
        plans = find_improvement_plans(**self.inputs)

        self.assertGreaterEqual(len(plans), 1)
        self.assertLessEqual(len(plans), 3)
        self.assertEqual(
            [plan["name"] for plan in plans],
            ["부담 최소형", "균형형", "개선 효과형"][:len(plans)],
        )

    def test_each_plan_reduces_risk_and_contains_required_fields(self):
        current = calculate_risk(calculate_metrics(**self.inputs))
        required_fields = {
            "name",
            "living_expense_reduction",
            "income_increase",
            "extra_savings",
            "new_monthly_savings",
            "risk_score",
            "health_score",
            "risk_level",
        }

        for plan in find_improvement_plans(**self.inputs):
            self.assertTrue(required_fields.issubset(plan))
            self.assertLess(plan["risk_score"], current["score"])
            self.assertAlmostEqual(plan["health_score"], 100 - plan["risk_score"])
            self.assertEqual(
                plan["new_monthly_savings"],
                self.inputs["monthly_savings"] + plan["extra_savings"],
            )

    def test_plans_respect_realistic_search_limits(self):
        plans = find_improvement_plans(**self.inputs)

        for plan in plans:
            self.assertLessEqual(
                plan["living_expense_reduction"],
                min(self.inputs["living_expense"] * 0.3, 500_000),
            )
            self.assertLessEqual(
                plan["income_increase"],
                min(self.inputs["income"] * 0.2, 500_000),
            )
            self.assertGreaterEqual(
                self.inputs["living_expense"] - plan["living_expense_reduction"],
                0,
            )

    def test_uses_current_risk_band_without_target_score_input(self):
        current = calculate_risk(calculate_metrics(**self.inputs))
        plans = find_improvement_plans(**self.inputs)

        # 현재 점수가 40점 이상이면 가능한 경우 자동으로 40점 아래를 목표로 한다.
        self.assertGreaterEqual(current["score"], 40)
        self.assertTrue(all(plan["risk_score"] < 40 for plan in plans))

    def test_alias_and_result_limit(self):
        plans = optimize_financial_plan(**self.inputs, max_results=1)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["name"], "부담 최소형")

    def test_rejects_invalid_configuration_and_income(self):
        with self.assertRaises(ValueError):
            find_improvement_plans(**self.inputs, step=0)
        with self.assertRaises(ValueError):
            find_improvement_plans(**self.inputs, max_results=4)
        with self.assertRaises(ValueError):
            find_improvement_plans(**dict(self.inputs, income=0))


if __name__ == "__main__":
    unittest.main()

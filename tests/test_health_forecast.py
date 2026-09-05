import unittest

from src.health_forecast import forecast_financial_health, forecast_plan_health
from src.metrics import calculate_metrics
from src.risk_engine import calculate_risk


class HealthForecastTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {
            "income": 3_000_000,
            "fixed_expense": 1_200_000,
            "living_expense": 900_000,
            "debt_payment": 500_000,
            "monthly_savings": 300_000,
            "savings": 2_000_000,
        }
        self.plan = {
            "name": "균형형",
            "income_increase": 100_000,
            "living_expense_reduction": 200_000,
            "new_monthly_savings": 350_000,
        }

    def test_default_months_and_order(self):
        result = forecast_financial_health(**self.inputs)
        self.assertEqual([item["month"] for item in result], [0, 3, 6, 12])

    def test_zero_month_matches_current_engine_result(self):
        current_metrics = calculate_metrics(**self.inputs)
        current_risk = calculate_risk(current_metrics)
        result = forecast_financial_health(**self.inputs)[0]

        self.assertEqual(result["projected_savings"], self.inputs["savings"])
        self.assertEqual(result["risk_score"], current_risk["score"])
        self.assertEqual(result["health_score"], 100 - current_risk["score"])
        self.assertEqual(result["risk_level"], current_risk["level"])
        self.assertEqual(result["emergency_months"], current_metrics["emergency_months"])

    def test_three_month_projected_savings(self):
        result = forecast_financial_health(**self.inputs, months=(3,))[0]
        self.assertEqual(result["projected_savings"], 2_900_000)

    def test_six_month_projected_savings(self):
        result = forecast_financial_health(**self.inputs, months=(6,))[0]
        self.assertEqual(result["projected_savings"], 3_800_000)

    def test_twelve_month_projected_savings(self):
        result = forecast_financial_health(**self.inputs, months=(12,))[0]
        self.assertEqual(result["projected_savings"], 5_600_000)

    def test_custom_month_order_and_duplicates_are_preserved(self):
        result = forecast_financial_health(**self.inputs, months=(5, 1, 5))
        self.assertEqual([item["month"] for item in result], [5, 1, 5])

    def test_scores_stay_in_valid_range_and_fields_exist(self):
        for item in forecast_financial_health(**self.inputs, months=range(13)):
            self.assertGreaterEqual(item["health_score"], 0)
            self.assertLessEqual(item["health_score"], 100)
            self.assertGreaterEqual(item["risk_score"], 0)
            self.assertLessEqual(item["risk_score"], 100)
            self.assertIn("risk_level", item)
            self.assertIn("emergency_months", item)

    def test_zero_monthly_savings_does_not_raise(self):
        inputs = dict(self.inputs, monthly_savings=0)
        result = forecast_financial_health(**inputs)
        self.assertTrue(all(item["projected_savings"] == 2_000_000 for item in result))

    def test_zero_current_savings_does_not_raise(self):
        result = forecast_financial_health(**dict(self.inputs, savings=0))
        self.assertEqual(result[0]["projected_savings"], 0)

    def test_high_risk_inputs_do_not_raise(self):
        result = forecast_financial_health(
            income=2_000_000,
            fixed_expense=1_200_000,
            living_expense=700_000,
            debt_payment=600_000,
            monthly_savings=0,
            savings=0,
        )
        self.assertEqual(len(result), 4)

    def test_monthly_deficit_depletes_projected_savings(self):
        inputs = {
            "income": 2_500_000,
            "fixed_expense": 1_300_000,
            "living_expense": 900_000,
            "debt_payment": 700_000,
            "monthly_savings": 0,
            "savings": 500_000,
        }

        result = forecast_financial_health(**inputs, months=(0, 1, 2, 3, 6, 12))

        self.assertEqual(
            [item["projected_savings"] for item in result],
            [500_000, 100_000, 0, 0, 0, 0],
        )

    def test_savings_contribution_is_reduced_by_cashflow_shortfall(self):
        inputs = dict(
            self.inputs,
            income=2_800_000,
            monthly_savings=300_000,
            savings=500_000,
        )

        result = forecast_financial_health(**inputs, months=(1,))[0]

        self.assertEqual(result["projected_savings"], 700_000)

    def test_stable_inputs_do_not_raise(self):
        result = forecast_financial_health(
            income=4_000_000,
            fixed_expense=700_000,
            living_expense=800_000,
            debt_payment=0,
            monthly_savings=1_000_000,
            savings=20_000_000,
        )
        self.assertEqual(len(result), 4)

    def test_plan_forecast_uses_new_monthly_savings(self):
        result = forecast_plan_health(**self.inputs, plan=self.plan, months=(3,))[0]
        self.assertEqual(result["projected_savings"], 3_050_000)

    def test_plan_forecast_does_not_mutate_plan(self):
        original_plan = dict(self.plan)
        forecast_plan_health(**self.inputs, plan=self.plan)
        self.assertEqual(self.plan, original_plan)

    def test_plan_forecast_applies_income_and_living_expense_changes(self):
        result = forecast_plan_health(**self.inputs, plan=self.plan, months=(0,))[0]
        expected_metrics = calculate_metrics(
            self.inputs["income"] + self.plan["income_increase"],
            self.inputs["fixed_expense"],
            self.inputs["living_expense"] - self.plan["living_expense_reduction"],
            self.inputs["debt_payment"],
            self.plan["new_monthly_savings"],
            self.inputs["savings"],
        )
        expected_risk = calculate_risk(expected_metrics)

        self.assertEqual(result["risk_score"], expected_risk["score"])
        self.assertEqual(result["risk_level"], expected_risk["level"])
        self.assertEqual(result["emergency_months"], expected_metrics["emergency_months"])

    def test_living_expense_reduction_cannot_make_expense_negative(self):
        plan = dict(self.plan, living_expense_reduction=2_000_000)
        result = forecast_plan_health(**self.inputs, plan=plan, months=(0,))[0]
        expected = calculate_metrics(
            self.inputs["income"] + plan["income_increase"],
            self.inputs["fixed_expense"],
            0,
            self.inputs["debt_payment"],
            plan["new_monthly_savings"],
            self.inputs["savings"],
        )
        self.assertEqual(result["emergency_months"], expected["emergency_months"])

    def test_empty_and_invalid_plans_raise_clear_errors(self):
        for plan in ({}, None, [], {"income_increase": 0}):
            with self.subTest(plan=plan):
                with self.assertRaises(ValueError):
                    forecast_plan_health(**self.inputs, plan=plan)

    def test_invalid_plan_values_are_rejected(self):
        for value in (-1, float("inf"), True, "100000"):
            with self.subTest(value=value):
                plan = dict(self.plan, income_increase=value)
                with self.assertRaises(ValueError):
                    forecast_plan_health(**self.inputs, plan=plan)

    def test_negative_month_is_rejected(self):
        with self.assertRaises(ValueError):
            forecast_financial_health(**self.inputs, months=(0, -1))

    def test_non_integer_month_is_rejected(self):
        for months in ((1.5,), (True,), "3", None):
            with self.subTest(months=months):
                with self.assertRaises(ValueError):
                    forecast_financial_health(**self.inputs, months=months)

    def test_empty_months_returns_empty_list(self):
        self.assertEqual(forecast_financial_health(**self.inputs, months=()), [])


if __name__ == "__main__":
    unittest.main()

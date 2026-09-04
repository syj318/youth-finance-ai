import unittest

from src.metrics import calculate_metrics


class CalculateMetricsTests(unittest.TestCase):
    def test_calculates_cashflow_ratios_and_emergency_months(self):
        metrics = calculate_metrics(
            income=3_000_000,
            fixed_expense=1_000_000,
            living_expense=600_000,
            debt_payment=300_000,
            monthly_savings=500_000,
            savings=3_800_000,
        )

        self.assertEqual(metrics["total_expense"], 1_900_000)
        self.assertEqual(metrics["available_surplus"], 1_100_000)
        self.assertEqual(metrics["monthly_surplus"], 600_000)
        self.assertAlmostEqual(metrics["surplus_rate"], 20.0)
        self.assertAlmostEqual(metrics["savings_rate"], 500_000 / 3_000_000 * 100)
        self.assertAlmostEqual(metrics["debt_service_rate"], 10.0)
        self.assertAlmostEqual(metrics["emergency_months"], 2.0)

    def test_zero_income_returns_zero_income_based_ratios(self):
        metrics = calculate_metrics(0, 0, 0, 0, 0, 0)

        self.assertEqual(metrics["surplus_rate"], 0)
        self.assertEqual(metrics["savings_rate"], 0)
        self.assertEqual(metrics["debt_service_rate"], 0)
        self.assertEqual(metrics["emergency_months"], 0)

    def test_zero_essential_outflow_returns_zero_emergency_months(self):
        metrics = calculate_metrics(3_000_000, 0, 0, 0, 500_000, 2_000_000)

        self.assertEqual(metrics["emergency_months"], 0)
        self.assertEqual(metrics["monthly_surplus"], 2_500_000)

    def test_preserves_inputs_required_by_risk_engine(self):
        metrics = calculate_metrics(3_000_000, 1_000_000, 600_000, 300_000, 500_000, 2_000_000)

        self.assertEqual(metrics["monthly_income"], 3_000_000)
        self.assertEqual(metrics["fixed_expense"], 1_000_000)
        self.assertEqual(metrics["variable_expense"], 600_000)
        self.assertEqual(metrics["loan_payment"], 300_000)
        self.assertEqual(metrics["monthly_saving"], 500_000)
        self.assertEqual(metrics["current_savings"], 2_000_000)


if __name__ == "__main__":
    unittest.main()

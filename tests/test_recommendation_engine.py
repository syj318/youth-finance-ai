import unittest

from src.recommendation_engine import get_personalized_recommendations


class RecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "age": 26,
            "region": "서울",
            "employment_status": "재직자",
            "annual_income": 36_000_000,
            "preferred_term_months": 12,
        }
        self.risk = {
            "domains": {
                "cashflow": {"score": 5, "max_score": 30},
                "debt": {"score": 3, "max_score": 25},
                "saving": {"score": 16, "max_score": 20},
                "emergency": {"score": 4, "max_score": 15},
            }
        }
        self.saving = {
            "source": "FSS_FINLIFE",
            "product_type": "saving",
            "company_name": "은행",
            "product_name": "실제 적금",
            "product_code": "S1",
            "term_months": 12,
            "base_rate": 3.0,
            "max_rate": 4.0,
            "join_member": "개인",
        }
        self.deposit = {
            "source": "FSS_FINLIFE",
            "product_type": "deposit",
            "company_name": "은행",
            "product_name": "실제 예금",
            "product_code": "D1",
            "term_months": 12,
            "base_rate": 3.5,
            "max_rate": 4.5,
            "join_member": "개인",
        }
        self.policy = {
            "source": "ONTONG_YOUTH",
            "policy_id": "P1",
            "policy_name": "서울 청년 자산형성 지원",
            "region": "서울",
            "policy_category": "금융·복지",
            "support_content": "청년 자산형성 지원",
            "min_age": 19,
            "max_age": 34,
            "max_income": 40_000_000,
            "employment_condition": "재직자",
        }

    def recommend(self, metrics=None, **kwargs):
        return get_personalized_recommendations(
            metrics or {"monthly_surplus": 300_000, "emergency_months": 4},
            self.risk,
            self.profile,
            saving_products=[self.saving],
            deposit_products=[self.deposit],
            policies=[self.policy],
            **kwargs,
        )

    def test_returns_separate_product_policy_and_context(self):
        result = self.recommend()
        self.assertEqual(set(result), {"financial_products", "youth_policies", "recommendation_context"})
        self.assertEqual(result["financial_products"][0]["product"]["source"], "FSS_FINLIFE")
        self.assertEqual(result["youth_policies"][0]["policy"]["source"], "ONTONG_YOUTH")

    def test_deficit_user_defers_all_products(self):
        result = self.recommend(metrics={"monthly_surplus": -400_000, "emergency_months": 0.2})
        self.assertEqual(result["financial_products"], [])
        self.assertEqual(result["recommendation_context"]["product_recommendation_status"], "deferred")

    def test_saving_risk_prioritizes_saving_product(self):
        result = self.recommend()
        self.assertEqual(result["financial_products"][0]["product"]["product_type"], "saving")
        self.assertTrue(any("저축 영역" in reason for reason in result["financial_products"][0]["reasons"]))

    def test_deposit_is_candidate_with_sufficient_emergency_fund(self):
        products = self.recommend()["financial_products"]
        deposit = next(item for item in products if item["product"]["product_type"] == "deposit")
        self.assertTrue(any("예금도 후보" in reason for reason in deposit["reasons"]))

    def test_low_emergency_fund_penalizes_long_term_deposit(self):
        products = self.recommend(metrics={"monthly_surplus": 300_000, "emergency_months": 0.5})["financial_products"]
        deposit = next(item for item in products if item["product"]["product_type"] == "deposit")
        self.assertTrue(any("자금이 묶이지 않는지" in reason for reason in deposit["cautions"]))

    def test_match_scores_are_bounded(self):
        result = self.recommend()
        scores = [item["match_score"] for item in result["financial_products"] + result["youth_policies"]]
        self.assertTrue(all(0 <= score <= 100 for score in scores))

    def test_policy_matches_age_region_income_and_employment(self):
        match = self.recommend()["youth_policies"][0]
        self.assertEqual(set(match["matched_conditions"]), {"연령", "지역", "소득", "취업상태"})
        self.assertEqual(match["eligibility"], "확인 필요")

    def test_age_mismatch_excludes_policy(self):
        profile = dict(self.profile, age=40)
        result = get_personalized_recommendations({}, self.risk, profile, policies=[self.policy])
        self.assertEqual(result["youth_policies"], [])

    def test_region_mismatch_excludes_policy(self):
        profile = dict(self.profile, region="부산")
        result = get_personalized_recommendations({}, self.risk, profile, policies=[self.policy])
        self.assertEqual(result["youth_policies"], [])

    def test_income_mismatch_excludes_policy(self):
        profile = dict(self.profile, annual_income=50_000_000)
        result = get_personalized_recommendations({}, self.risk, profile, policies=[self.policy])
        self.assertEqual(result["youth_policies"], [])

    def test_employment_mismatch_excludes_policy(self):
        profile = dict(self.profile, employment_status="미취업자")
        result = get_personalized_recommendations({}, self.risk, profile, policies=[self.policy])
        self.assertEqual(result["youth_policies"], [])

    def test_missing_policy_conditions_remain_unverified(self):
        policy = {"source": "ONTONG_YOUTH", "policy_id": "P2", "policy_name": "청년 지원"}
        result = get_personalized_recommendations({}, self.risk, self.profile, policies=[policy])
        match = result["youth_policies"][0]
        self.assertEqual(match["eligibility"], "확인 필요")
        self.assertIn("세부 소득요건", match["unverified_conditions"])

    def test_financial_domains_influence_policy_reason(self):
        match = self.recommend()["youth_policies"][0]
        self.assertTrue(any("저축 위험" in reason for reason in match["reasons"]))

    def test_only_api_sourced_items_are_recommended(self):
        fake = dict(self.saving, source="MADE_UP")
        result = get_personalized_recommendations({}, self.risk, self.profile, saving_products=[fake], policies=[])
        self.assertEqual(result["financial_products"], [])

    def test_empty_and_structured_api_results_are_safe(self):
        result = get_personalized_recommendations(
            {}, {}, {}, saving_products={"available": False, "items": []}, policies={"available": True, "items": []}
        )
        self.assertEqual(result["financial_products"], [])
        self.assertEqual(result["youth_policies"], [])


if __name__ == "__main__":
    unittest.main()

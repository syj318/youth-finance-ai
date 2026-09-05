import unittest

from src.ai_advisor import generate_ai_advice


class AiAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {"monthly_income": 3000000, "monthly_surplus": 100000}
        self.risk = {
            "score": 47.5,
            "level": "주의",
            "reasons": ["현금흐름 여유가 적습니다."],
            "domains": {
                "cashflow": {
                    "score": 18,
                    "level": "위험",
                    "reasons": [
                        {
                            "severity": 18,
                            "recommendation": "반복 지출을 먼저 점검하세요.",
                        }
                    ],
                },
                "saving": {
                    "score": 9,
                    "level": "주의",
                    "reasons": [],
                },
            },
            "score_breakdown": {"health_score": 52.5},
        }
        self.plans = [
            {
                "name": "부담 최소형",
                "living_expense_reduction": 50000,
                "income_increase": 0,
                "extra_savings": 50000,
                "risk_score": 38,
                "risk_level": "안정",
                "health_score": 62,
                "risk_reduction": 9.5,
            }
        ]

    def test_returns_ui_ready_shape_and_uses_existing_scores(self):
        advice = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertEqual(
            set(advice), {"summary", "priority", "actions", "plan_comment"}
        )
        self.assertIn("52.5", advice["summary"])
        self.assertIn("47.5", advice["summary"])
        self.assertIn("주의", advice["summary"])
        self.assertIn("현금흐름", advice["priority"])
        self.assertIn("18", advice["priority"])

    def test_actions_and_comment_only_echo_plan_and_engine_results(self):
        advice = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertEqual(len(advice["actions"]), 2)
        self.assertIn("50000원", advice["actions"][0])
        self.assertNotIn("3000000", str(advice))
        for value in ("38", "안정", "62", "9.5"):
            self.assertIn(value, advice["plan_comment"])
        self.assertEqual(advice["actions"][1], "반복 지출을 먼저 점검하세요.")

    def test_does_not_derive_health_score_when_it_is_not_provided(self):
        risk = dict(self.risk)
        risk.pop("score_breakdown")

        advice = generate_ai_advice(self.metrics, risk, [])

        self.assertNotIn("52.5", advice["summary"])
        self.assertNotIn("금융 건강점수", advice["summary"])

    def test_does_not_append_copula_to_complete_reason_sentence(self):
        advice = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertIn(
            "주요 진단 사유는 다음과 같습니다. 현금흐름 여유가 적습니다.",
            advice["summary"],
        )
        self.assertNotIn("적습니다.입니다.", advice["summary"])

    def test_formats_multiple_complete_reasons_without_semicolons(self):
        risk = dict(self.risk)
        risk["reasons"] = [
            "지출과 저축 후 남는 비상 여유자금이 적어 예상치 못한 지출에 취약합니다.;",
            "소득 대비 생활지출 부담이 높은 편입니다.;",
            "비상자금이 1개월 미만 수준으로 예상치 못한 지출에 취약합니다.",
        ]

        summary = generate_ai_advice(self.metrics, risk, self.plans)["summary"]

        self.assertNotIn(".;", summary)
        self.assertNotIn(".입니다.", summary)
        self.assertIn(
            "주요 진단 사유는 다음과 같습니다. "
            "지출과 저축 후 남는 비상 여유자금이 적어 예상치 못한 지출에 취약합니다. "
            "소득 대비 생활지출 부담이 높은 편입니다. "
            "비상자금이 1개월 미만 수준으로 예상치 못한 지출에 취약합니다.",
            summary,
        )

    def test_fallback_handles_missing_or_invalid_inputs(self):
        advice = generate_ai_advice(None, None, None)

        self.assertEqual(advice["actions"], [])
        self.assertIn("진단 결과가 없습니다", advice["summary"])
        self.assertIn("자동 개선안이 없어", advice["plan_comment"])

    def test_does_not_mutate_inputs(self):
        metrics_before = dict(self.metrics)
        plans_before = [dict(self.plans[0])]

        generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertEqual(self.metrics, metrics_before)
        self.assertEqual(self.plans, plans_before)


if __name__ == "__main__":
    unittest.main()

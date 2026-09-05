import json
import os
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from src.ai_advisor import (
    _build_financial_context,
    _call_groq,
    generate_ai_advice,
    generate_ai_chat_reply,
)


class AiAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
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

    def test_context_excludes_unapproved_fields_and_personal_information(self):
        metrics = dict(
            self.metrics,
            savings_rate=10,
            debt_service_rate=20,
            emergency_months=1,
            account_number="123-456",
        )

        context = _build_financial_context(metrics, self.risk, self.plans)

        self.assertEqual(
            set(context["metrics"]),
            {"monthly_surplus", "savings_rate", "debt_service_rate", "emergency_months"},
        )
        self.assertNotIn("account_number", str(context))
        self.assertNotIn("monthly_income", context["metrics"])

    def test_groq_call_uses_configured_model_and_json_schema(self):
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                message = SimpleNamespace(content='{"ok": true}')
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        class FakeGroq:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.chat = SimpleNamespace(completions=FakeCompletions())

        fake_module = ModuleType("groq")
        fake_module.Groq = FakeGroq
        os.environ["GROQ_API_KEY"] = "test-key"
        os.environ["GROQ_MODEL"] = "openai/gpt-oss-120b"

        with patch.dict(sys.modules, {"groq": fake_module}):
            result = _call_groq(
                [{"role": "user", "content": "test"}], {"name": "test", "schema": {}}
            )

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(captured["model"], "openai/gpt-oss-120b")
        self.assertEqual(captured["client"]["api_key"], "test-key")
        self.assertEqual(captured["response_format"]["type"], "json_schema")

    @patch("src.ai_advisor._call_groq")
    def test_parses_successful_groq_advice(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"
        expected = {
            "summary": "위험점수는 47.5점입니다.",
            "priority": "현금흐름 위험점수 18을 먼저 확인하세요.",
            "actions": [
                "생활비를 50000원 줄여 보세요.",
                "50000원을 추가로 저축해 보세요.",
                "반복 지출을 점검하세요.",
            ],
            "plan_comment": "부담 최소형의 예상 위험점수는 38입니다.",
        }
        call_groq.return_value = json.dumps(expected, ensure_ascii=False)

        result = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertEqual(result, expected)
        self.assertIsNotNone(call_groq.call_args.args[1])

    @patch("src.ai_advisor._call_groq", side_effect=RuntimeError("rate limit 429"))
    def test_groq_error_uses_fallback_without_raising(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"

        result = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertEqual(set(result), {"summary", "priority", "actions", "plan_comment"})
        self.assertIn("47.5", result["summary"])

    @patch("src.ai_advisor._call_groq")
    def test_ungrounded_number_in_groq_response_uses_fallback(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"
        call_groq.return_value = json.dumps(
            {
                "summary": "금융 건강점수는 99점입니다.",
                "priority": "현금흐름을 확인하세요.",
                "actions": ["행동 가", "행동 나", "행동 다"],
                "plan_comment": "개선안을 확인하세요.",
            },
            ensure_ascii=False,
        )

        result = generate_ai_advice(self.metrics, self.risk, self.plans)

        self.assertNotIn("99", result["summary"])
        self.assertIn("47.5", result["summary"])

    def test_chat_handles_empty_question_and_missing_key(self):
        self.assertIsInstance(
            generate_ai_chat_reply("", self.metrics, self.risk, self.plans), str
        )
        reply = generate_ai_chat_reply(
            "왜 점수가 낮나요?", self.metrics, self.risk, self.plans
        )
        self.assertIsInstance(reply, str)
        self.assertIn("AI 연결", reply)
        self.assertIn("47.5", reply)

    def test_empty_reasons_and_plans_do_not_raise(self):
        risk = dict(self.risk, reasons=[], domains={})

        advice = generate_ai_advice(self.metrics, risk, [])
        reply = generate_ai_chat_reply("내 상태를 설명해 줘", self.metrics, risk, [])

        self.assertEqual(set(advice), {"summary", "priority", "actions", "plan_comment"})
        self.assertIsInstance(reply, str)

    def test_out_of_scope_question_is_refused_without_api_call(self):
        reply = generate_ai_chat_reply(
            "삼성전자 주식 지금 사도 돼?", self.metrics, self.risk, self.plans
        )

        self.assertEqual(
            reply,
            "현재 입력된 금융정보와 분석 결과만으로는 해당 내용을 판단할 수 없습니다.",
        )

    @patch("src.ai_advisor._call_groq")
    def test_chat_returns_groq_reply_and_accepts_history(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"
        call_groq.return_value = "위험점수 47.5의 주요 원인은 현금흐름입니다."

        reply = generate_ai_chat_reply(
            "왜 낮나요?",
            self.metrics,
            self.risk,
            self.plans,
            chat_history=[{"role": "user", "content": "진단을 설명해 줘"}],
        )

        self.assertEqual(reply, call_groq.return_value)
        messages = call_groq.call_args.args[0]
        self.assertEqual(messages[-2]["role"], "user")

    @patch("src.ai_advisor._call_groq")
    def test_chat_allows_echoing_user_budget_but_redacts_pii(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"
        call_groq.return_value = "사용자가 말한 20만원 한도 안에서 개선안을 확인하세요."

        reply = generate_ai_chat_reply(
            "월 20만원만 가능해. 계좌는 123-456-789012야.",
            self.metrics,
            self.risk,
            self.plans,
        )

        self.assertEqual(reply, call_groq.return_value)
        sent_messages = call_groq.call_args.args[0]
        self.assertNotIn("123-456-789012", str(sent_messages))
        self.assertIn("[개인정보 삭제]", str(sent_messages))

    @patch("src.ai_advisor._call_groq", side_effect=TimeoutError("timeout"))
    def test_chat_error_returns_string_fallback(self, call_groq):
        os.environ["GROQ_API_KEY"] = "test-key"

        reply = generate_ai_chat_reply(
            "어느 영역이 위험해?", self.metrics, self.risk, self.plans, None
        )

        self.assertIsInstance(reply, str)
        self.assertIn("기존 금융 진단 결과", reply)


if __name__ == "__main__":
    unittest.main()

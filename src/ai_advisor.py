"""검증된 금융 진단 결과를 Groq LLM 또는 fallback으로 설명한다.

이 모듈은 점수나 위험등급을 계산하지 않는다. LLM에는 허용된 엔진 결과만
전달하며, API 키가 없거나 호출이 실패하면 결정적인 설명을 반환한다.
"""

from __future__ import annotations

import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping


logger = logging.getLogger(__name__)

DOMAIN_LABELS = {
    "cashflow": "현금흐름",
    "debt": "부채 상환",
    "saving": "저축",
    "emergency": "비상자금",
    "expense_structure": "지출 구조",
}

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
METRIC_CONTEXT_FIELDS = (
    "monthly_surplus",
    "savings_rate",
    "debt_service_rate",
    "emergency_months",
)
PLAN_CONTEXT_FIELDS = (
    "name",
    "living_expense_reduction",
    "income_increase",
    "extra_savings",
    "new_monthly_savings",
    "risk_score",
    "health_score",
    "risk_level",
    "risk_reduction",
    "new_monthly_surplus",
    "change_count",
)

SYSTEM_PROMPT = """당신은 청년 사용자의 금융상태를 설명하는 AI 금융코치입니다.

금융 건강점수, 위험점수, 위험등급 및 자동 개선안은 이미 검증 가능한 금융 엔진에서 계산되었습니다.
제공된 데이터의 숫자를 임의로 변경하거나 새로운 금융 수치를 만들지 마세요.
metrics, risk, plans에 존재하는 정보만 근거로 답변하세요.
숫자는 제공된 표기를 그대로 사용하고 단위 변환이나 반올림도 하지 마세요.
제공되지 않은 금리, 신용점수, 금융상품, 예상 수익률, 정책 자격조건을 추측하지 마세요.
현재 금융상태의 중요한 문제와 optimizer가 산출한 행동을 이해하기 쉽게 설명하세요.
특정 주식·코인 매수/매도, 대출 또는 금융상품 가입을 직접 권유하지 마세요.
데이터에 없는 내용은 현재 제공된 정보만으로 판단할 수 없다고 설명하세요.
한국어로 자연스럽고 구체적이되 간결하게 답변하세요."""

CHAT_GROUNDING_RETRY_PROMPT = """직전 답변에는 제공되지 않은 숫자 또는 계산한 수치가 포함되어 사용할 수 없습니다.
표, 번호 목록, 기간 환산, 비율 계산, 가상의 사례, 일반적인 권장 기준을 모두 제외하세요.
금융 엔진 컨텍스트에 적힌 사실만 사용해 짧은 한국어 문단 하나로 다시 답하세요.
이번 답변에는 숫자나 숫자 기호를 한 글자도 쓰지 마세요.
컨텍스트에 없는 내용은 판단할 수 없다고 설명하세요."""

ADVICE_SCHEMA = {
    "name": "financial_advice",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "priority": {"type": "string"},
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "plan_comment": {"type": "string"},
        },
        "required": ["summary", "priority", "actions", "plan_comment"],
        "additionalProperties": False,
    },
}


def _display(value: Any) -> str:
    """값을 반올림하거나 새로 계산하지 않고 표시용 문자열로 바꾼다."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _format_reasons(reasons: List[Any]) -> str:
    """완결된 진단 사유들을 중복 종결어나 세미콜론 없이 연결한다."""
    sentences = []
    for reason in reasons:
        sentence = _display(reason).strip().rstrip(";").strip()
        if not sentence:
            continue
        if sentence[-1] not in ".!?。！？":
            sentence += "."
        sentences.append(sentence)
    return " ".join(sentences)


def _health_score(metrics: Mapping[str, Any], risk: Mapping[str, Any]) -> Any:
    breakdown = risk.get("score_breakdown")
    if isinstance(breakdown, Mapping) and "health_score" in breakdown:
        return breakdown["health_score"]

    # 다른 호출자가 이미 계산한 건강점수를 metrics에 넣어 전달하는 경우도 지원한다.
    for key in ("financial_health_score", "health_score"):
        if key in metrics:
            return metrics[key]
    return None


def _ranked_domain_reasons(
    domains: Mapping[str, Any],
) -> Iterable[Mapping[str, Any]]:
    reasons: List[Mapping[str, Any]] = []
    for domain in domains.values():
        if not isinstance(domain, Mapping):
            continue
        domain_reasons = domain.get("reasons", [])
        if not isinstance(domain_reasons, list):
            continue
        reasons.extend(item for item in domain_reasons if isinstance(item, Mapping))

    # severity는 엔진이 산출한 기존 값이며 여기서는 정렬에만 사용한다.
    return sorted(
        reasons,
        key=lambda item: item.get("severity", float("-inf"))
        if isinstance(item.get("severity"), (int, float))
        else float("-inf"),
        reverse=True,
    )


def _priority(risk: Mapping[str, Any]) -> str:
    domains = risk.get("domains", {})
    if not isinstance(domains, Mapping) or not domains:
        reasons = risk.get("reasons", [])
        if isinstance(reasons, list) and reasons:
            return f"가장 먼저 확인할 위험 요인은 '{reasons[0]}'입니다."
        return "우선순위를 정할 수 있는 위험 영역 정보가 없습니다."

    scored = [
        (key, value)
        for key, value in domains.items()
        if isinstance(value, Mapping) and isinstance(value.get("score"), (int, float))
    ]
    if not scored:
        return "우선순위를 정할 수 있는 위험 영역 점수가 없습니다."

    key, domain = max(scored, key=lambda item: item[1]["score"])
    label = DOMAIN_LABELS.get(key, key)
    reason = None
    domain_reasons = domain.get("reasons")
    if isinstance(domain_reasons, list):
        for item in domain_reasons:
            if isinstance(item, Mapping) and isinstance(item.get("message"), str):
                reason = item["message"].strip()
                if reason:
                    break
    if not reason and isinstance(domain.get("explanation"), str):
        reason = domain["explanation"].strip()

    if reason:
        if reason[-1] not in ".!?。！？":
            reason += "."
        return (
            f"현재 가장 먼저 점검할 영역은 {label}이며, "
            f"'{reason}'라는 진단 사유가 제시되었기 때문입니다."
        )

    details = [f"영역 위험점수가 {_display(domain['score'])}점"]
    if domain.get("level") is not None:
        details.append(f"위험등급이 {_display(domain['level'])}")
    return (
        f"현재 가장 먼저 점검할 영역은 {label}이며, "
        f"{'이고 '.join(details)}이기 때문입니다."
    )


def _plan_action(plan: Mapping[str, Any]) -> str:
    changes = []
    fields = (
        ("living_expense_reduction", "생활비 절감"),
        ("income_increase", "소득 증가"),
        ("extra_savings", "추가 저축"),
    )
    for key, label in fields:
        value = plan.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            changes.append(f"{label} {_display(value)}원")

    name = plan.get("name")
    prefix = f"{name}: " if name else ""
    if changes:
        return f"{prefix}{', '.join(changes)}을 실행해 보세요."
    return f"{prefix}자동 개선안의 실행 항목을 확인해 보세요."


def _actions(risk: Mapping[str, Any], plans: List[Any]) -> List[str]:
    actions = [_plan_action(plan) for plan in plans if isinstance(plan, Mapping)][:3]
    if len(actions) >= 3:
        return actions

    domains = risk.get("domains", {})
    if isinstance(domains, Mapping):
        for reason in _ranked_domain_reasons(domains):
            recommendation = reason.get("recommendation")
            if isinstance(recommendation, str) and recommendation and recommendation not in actions:
                actions.append(recommendation)
            if len(actions) >= 3:
                break
    return actions


def _plan_comment(plans: List[Any]) -> str:
    valid_plans = [plan for plan in plans if isinstance(plan, Mapping)]
    if not valid_plans:
        return "제공된 자동 개선안이 없어 현재 결과만 설명했습니다."

    first = valid_plans[0]
    name = first.get("name", "첫 번째 개선안")
    facts = []
    for key, label in (
        ("risk_score", "예상 위험점수"),
        ("risk_level", "예상 위험등급"),
        ("health_score", "예상 금융 건강점수"),
        ("risk_reduction", "위험점수 감소"),
    ):
        if first.get(key) is not None:
            facts.append(f"{label} {_display(first[key])}")

    if facts:
        return f"자동 개선안 중 '{name}'의 결과는 {', '.join(facts)}로 제시되었습니다. 실행 가능성을 확인해 선택하세요."
    return f"자동 개선안 중 '{name}'에 제시된 실행 항목을 기준으로 검토하세요."


def _generate_fallback_advice(metrics, risk, plans) -> Dict[str, Any]:
    """엔진 결과만 인용하는 기존 deterministic 설명을 반환한다."""
    safe_metrics = metrics if isinstance(metrics, Mapping) else {}
    safe_risk = risk if isinstance(risk, Mapping) else {}
    safe_plans = plans if isinstance(plans, list) else []

    summary_facts = []
    health_score = _health_score(safe_metrics, safe_risk)
    if health_score is not None:
        summary_facts.append(f"금융 건강점수는 {_display(health_score)}점")
    if safe_risk.get("score") is not None:
        summary_facts.append(f"위험점수는 {_display(safe_risk['score'])}점")
    if safe_risk.get("level") is not None:
        summary_facts.append(f"위험등급은 {_display(safe_risk['level'])}")

    if summary_facts:
        summary = f"현재 {', '.join(summary_facts)}입니다."
    else:
        summary = "현재 금융상태를 요약할 수 있는 진단 결과가 없습니다."

    reasons = safe_risk.get("reasons", [])
    if isinstance(reasons, list) and reasons:
        reason_text = _format_reasons(reasons)
        if reason_text:
            summary += f" 주요 진단 사유는 다음과 같습니다. {reason_text}"

    return {
        "summary": summary,
        "priority": _priority(safe_risk),
        "actions": _actions(safe_risk, safe_plans),
        "plan_comment": _plan_comment(safe_plans),
    }


def _copy_reason(reason: Any) -> Any:
    if isinstance(reason, str):
        return reason
    if not isinstance(reason, Mapping):
        return None
    return {
        key: reason[key]
        for key in ("code", "severity", "message", "recommendation")
        if key in reason
    }


def _build_financial_context(metrics, risk, plans) -> Dict[str, Any]:
    """LLM에 전달할 엔진 결과를 명시적인 allowlist로 제한한다."""
    safe_metrics = metrics if isinstance(metrics, Mapping) else {}
    safe_risk = risk if isinstance(risk, Mapping) else {}
    safe_plans = plans if isinstance(plans, list) else []

    metric_context = {
        key: safe_metrics[key] for key in METRIC_CONTEXT_FIELDS if key in safe_metrics
    }

    domain_context = {}
    domains = safe_risk.get("domains", {})
    if isinstance(domains, Mapping):
        for name, domain in domains.items():
            if not isinstance(domain, Mapping):
                continue
            item = {
                key: domain[key]
                for key in ("score", "max_score", "level", "explanation")
                if key in domain
            }
            reasons = domain.get("reasons")
            if isinstance(reasons, list):
                item["reasons"] = [
                    copied for reason in reasons if (copied := _copy_reason(reason)) is not None
                ]
            domain_context[str(name)] = item

    risk_context = {
        key: safe_risk[key] for key in ("score", "level") if key in safe_risk
    }
    reasons = safe_risk.get("reasons")
    if isinstance(reasons, list):
        risk_context["reasons"] = [
            copied for reason in reasons if (copied := _copy_reason(reason)) is not None
        ]
    risk_context["domains"] = domain_context
    health_score = _health_score(safe_metrics, safe_risk)
    if health_score is not None:
        risk_context["health_score"] = health_score

    plan_context = [
        {key: plan[key] for key in PLAN_CONTEXT_FIELDS if key in plan}
        for plan in safe_plans
        if isinstance(plan, Mapping)
    ]
    return {"metrics": metric_context, "risk": risk_context, "plans": plan_context}


def _call_groq(messages: List[Dict[str, str]], response_schema=None) -> str:
    """Groq SDK를 지연 import하여 API 미설치 환경의 fallback도 보장한다."""
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=8.0)
    request = {
        "model": os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        "messages": messages,
        "reasoning_effort": "low",
        "max_completion_tokens": 250,
    }
    if response_schema is not None:
        request["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }
    completion = client.chat.completions.create(**request)
    content = completion.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq가 빈 응답을 반환했습니다.")
    return content.strip()


def _valid_advice(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"summary", "priority", "actions", "plan_comment"}
        and isinstance(value["summary"], str) and bool(value["summary"].strip())
        and isinstance(value["priority"], str) and bool(value["priority"].strip())
        and isinstance(value["plan_comment"], str) and bool(value["plan_comment"].strip())
        and isinstance(value["actions"], list)
        and len(value["actions"]) == 3
        and all(isinstance(action, str) and action.strip() for action in value["actions"])
    )


def _uses_only_context_numbers(text: str, context: Mapping[str, Any]) -> bool:
    """LLM 출력의 금융 수치가 컨텍스트에 실제로 존재하는지 확인한다.

    같은 값의 소수점/천 단위 표기 차이는 허용하고, 줄 시작의 목록 번호는
    금융 수치가 아니므로 검사에서 제외한다.
    """
    number_pattern = re.compile(
        r"(?<![\d.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d.])"
    )

    def numeric_value(raw: str) -> Decimal | None:
        try:
            return Decimal(raw.replace(",", ""))
        except InvalidOperation:
            return None

    context_text = json.dumps(context, ensure_ascii=False)
    allowed = {
        value
        for match in number_pattern.finditer(context_text)
        if (value := numeric_value(match.group())) is not None
    }
    negative_magnitudes = {abs(value) for value in allowed if value < 0}
    negative_meaning = re.compile(r"적자|부족|마이너스|음수|초과")

    for match in number_pattern.finditer(text):
        line_prefix = text[text.rfind("\n", 0, match.start()) + 1 : match.start()]
        following = text[match.end() :]
        if not line_prefix.strip() and re.match(r"[.)]\s", following):
            continue
        if re.match(r"\s*(?:가지|단계|번째|순위|개(?!월)(?:의)?)", following):
            continue
        value = numeric_value(match.group())
        if value in allowed:
            continue
        sentence_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind("\n", 0, match.start()),
        )
        sentence_ends = [
            position
            for delimiter in ".!?\n"
            if (position := text.find(delimiter, match.end())) != -1
        ]
        sentence_end = min(sentence_ends) if sentence_ends else len(text)
        sentence = text[sentence_start + 1 : sentence_end]
        if value in negative_magnitudes and negative_meaning.search(sentence):
            continue
        if value not in allowed:
            logger.debug("컨텍스트에 없는 응답 숫자 표기: %s", match.group())
            return False
    return True


def _redact_personal_information(text: str) -> str:
    """질문/대화 이력의 대표적인 개인식별정보 형식을 LLM 전송 전에 가린다."""
    patterns = (
        r"(?<!\d)\d{6}-?\d{7}(?!\d)",  # 주민등록번호
        r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)",  # 휴대전화 번호
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",  # 이메일
        r"(?<!\d)\d{2,6}[ -]\d{2,6}[ -]\d{2,6}(?!\d)",  # 일반적인 계좌번호 형식
    )
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[개인정보 삭제]", redacted)
    return redacted


def _is_out_of_scope_question(question: str) -> bool:
    blocked_terms = (
        "삼성전자",
        "주식",
        "종목",
        "코인",
        "비트코인",
        "매수",
        "매도",
        "대출상품",
        "대출 상품",
        "대출을 받아",
        "적금",
        "예금",
        "금리",
        "신용점수",
    )
    return any(term in question for term in blocked_terms)


def generate_ai_advice(metrics, risk, plans) -> Dict[str, Any]:
    """Groq 사용 가능 시 개인화 설명을, 아니면 기존 fallback을 반환한다."""
    fallback = _generate_fallback_advice(metrics, risk, plans)
    if not os.getenv("GROQ_API_KEY"):
        return fallback

    context = _build_financial_context(metrics, risk, plans)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "다음 금융 엔진 결과만 사용해 지정된 JSON 형식의 금융 코칭을 작성하세요. "
                "actions는 정확히 3개의 문자열이어야 합니다.\n"
                + json.dumps(context, ensure_ascii=False)
            ),
        },
    ]
    try:
        advice = json.loads(_call_groq(messages, ADVICE_SCHEMA))
        if not _valid_advice(advice):
            return fallback
        if not _uses_only_context_numbers(
            json.dumps(advice, ensure_ascii=False),
            context
        ):
            return fallback
        advice["priority"] = _priority(risk if isinstance(risk, Mapping) else {})
        return advice
        
    except Exception:
        return fallback


def _generate_fallback_chat_reply(question, metrics, risk, plans) -> str:
    advice = _generate_fallback_advice(metrics, risk, plans)
    return (
        "현재 AI 연결을 일시적으로 사용할 수 없어 기존 금융 진단 결과를 기준으로 "
        f"안내합니다. {advice['summary']} {advice['priority']}"
    )


def _safe_chat_history(chat_history) -> List[Dict[str, str]]:
    if not isinstance(chat_history, list):
        return []
    safe_history = []
    for message in chat_history[-4:]:
        if not isinstance(message, Mapping):
            continue
        role = message.get("role")
        content = message.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            safe_history.append(
                {"role": role, "content": _redact_personal_information(content[:1500])}
            )
    return safe_history

def generate_ai_chat_reply(
    question,
    metrics,
    risk,
    plans,
    chat_history=None,
) -> str:
    """현재 금융 엔진 결과에 근거해 사용자의 후속 질문에 답한다."""
    if not isinstance(question, str) or not question.strip():
        return "궁금한 금융 진단 내용을 입력해 주세요."

    clean_question = _redact_personal_information(question.strip())

    if _is_out_of_scope_question(clean_question):
        return "현재 입력된 금융정보와 분석 결과만으로는 해당 내용을 판단할 수 없습니다."

    fallback = _generate_fallback_chat_reply(
        question,
        metrics,
        risk,
        plans
    )

    if not os.getenv("GROQ_API_KEY"):
        return fallback

    context = _build_financial_context(
        metrics,
        risk,
        plans
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(
        _safe_chat_history(chat_history)
    )

    messages.append(
        {
            "role": "user",
            "content": (
                "금융 엔진 컨텍스트:\n"
                + json.dumps(
                    context,
                    ensure_ascii=False
                )
                + "\n\n사용자 질문:\n"
                + clean_question
            ),
        }
    )

    try:
        reply = _call_groq(messages)

        grounded_context = {
            **context,
            "user_provided_text": [
                *(
                    message["content"]
                    for message in messages[1:-1]
                    if message["role"] == "user"
                ),
                clean_question,
            ],
        }

        # 첫 응답에 근거 없는 숫자가 포함되면 한 번만 재시도
        if not _uses_only_context_numbers(
            reply,
            grounded_context
        ):
            retry_messages = [
                *messages,
                {
                    "role": "assistant",
                    "content": reply,
                },
                {
                    "role": "system",
                    "content": CHAT_GROUNDING_RETRY_PROMPT,
                },
            ]

            retry_reply = _call_groq(
                retry_messages
            )

            # 재시도까지 근거 검증에 실패하면 안전한 fallback 사용
            if not _uses_only_context_numbers(
                retry_reply,
                grounded_context
            ):
                return fallback

            return retry_reply

        return reply

    except Exception:
        return fallback

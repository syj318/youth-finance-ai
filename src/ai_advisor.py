"""기존 금융 진단 결과를 사용자가 이해하기 쉬운 문장으로 설명한다.

이 모듈은 점수나 위험등급을 계산하지 않는다. 외부 AI API가 없어도 동작하도록
결정적인(deterministic) 설명을 생성하며, 전달받은 metrics/risk/plans의 값만
문장에 사용한다.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


DOMAIN_LABELS = {
    "cashflow": "현금흐름",
    "debt": "부채 상환",
    "saving": "저축",
    "emergency": "비상자금",
    "expense_structure": "지출 구조",
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
    details = []
    if "score" in domain:
        details.append(f"위험점수 {_display(domain['score'])}")
    if domain.get("level") is not None:
        details.append(f"등급 {_display(domain['level'])}")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"현재 영역별 결과에서는 {label}{suffix}을(를) 가장 먼저 점검하는 것이 좋습니다."


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


def generate_ai_advice(metrics, risk, plans) -> Dict[str, Any]:
    """엔진과 최적화 결과만 인용해 UI용 금융 코치 설명을 반환한다.

    외부 API를 호출하지 않으므로 네트워크나 API 키가 없는 환경에서도 동일하게
    동작한다. 입력이 일부 비어 있어도 가능한 범위에서 안전한 fallback 문구를 낸다.
    """
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

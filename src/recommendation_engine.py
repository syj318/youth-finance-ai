"""검증된 금융진단과 실제 API 항목을 결합하는 결정적 추천 엔진."""

from __future__ import annotations

import re
from typing import Any, Mapping


def _items(value):
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping) and isinstance(value.get("items"), list):
        return value["items"]
    return []


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _domain_need(risk, name):
    domains = risk.get("domains", {}) if isinstance(risk, Mapping) else {}
    domain = domains.get(name, {}) if isinstance(domains, Mapping) else {}
    score = _number(domain.get("score")) if isinstance(domain, Mapping) else None
    maximum = _number(domain.get("max_score")) if isinstance(domain, Mapping) else None
    if score is None:
        return 0.0
    return min(1.0, max(0.0, score / maximum)) if maximum and maximum > 0 else min(1.0, score / 100)


def _rank_products(metrics, risk, profile, saving_products, deposit_products, limit):
    surplus = _number(metrics.get("monthly_surplus")) if isinstance(metrics, Mapping) else None
    emergency = _number(metrics.get("emergency_months")) if isinstance(metrics, Mapping) else None
    if surplus is not None and surplus < 0:
        return "deferred", []

    preferred = _number(profile.get("preferred_term_months")) if isinstance(profile, Mapping) else None
    saving_need = _domain_need(risk, "saving")
    candidates = []
    for product in [*_items(saving_products), *_items(deposit_products)]:
        if not isinstance(product, Mapping) or product.get("source") != "FSS_FINLIFE":
            continue
        kind = product.get("product_type")
        score = 25.0
        reasons = []
        cautions = []

        if surplus is not None and surplus >= 0:
            score += 15
            reasons.append("현재 월 현금흐름이 적자가 아닙니다.")
        if kind == "saving":
            score += 30 * saving_need
            if saving_need >= 0.5:
                reasons.append("저축 영역의 개선 필요도가 높아 적립식 상품을 우선 검토합니다.")
        elif kind == "deposit":
            if emergency is not None and emergency >= 3:
                score += 20
                reasons.append("비상자금과 월 현금흐름을 고려할 때 예금도 후보가 될 수 있습니다.")
            else:
                score -= 15
                cautions.append("비상자금이 충분하지 않아 장기간 자금이 묶이지 않는지 확인이 필요합니다.")

        term = _number(product.get("term_months"))
        if preferred is not None and term is not None:
            difference = abs(preferred - term)
            score += max(0, 15 - difference)
            if difference == 0:
                reasons.append("선호 가입기간과 상품 기간이 일치합니다.")
        elif term is not None:
            score += 5
            reasons.append("가입기간 정보가 확인된 상품입니다.")

        rate = _number(product.get("max_rate"))
        if rate is None:
            rate = _number(product.get("base_rate"))
        if rate is not None:
            score += min(15, max(0, rate * 2))
            reasons.append("공식 API에서 금리정보가 제공된 상품입니다.")

        if product.get("join_member"):
            score += 5
            cautions.append("가입대상과 우대조건의 세부 충족 여부를 확인해야 합니다.")
        candidates.append(
            {
                "product": dict(product),
                "match_score": round(min(100, max(0, score)), 2),
                "reasons": reasons,
                "cautions": cautions,
                "eligibility": "가입조건 확인 필요",
            }
        )
    candidates.sort(key=lambda item: (-item["match_score"], str(item["product"].get("product_name") or "")))
    return "available", candidates[: max(0, int(limit))]


def _bounds(policy, text_key, min_key, max_key):
    minimum = _number(policy.get(min_key))
    maximum = _number(policy.get(max_key))
    text = str(policy.get(text_key) or "")
    if minimum is None:
        match = re.search(r"(?:만\s*)?(\d+)\s*세\s*이상", text)
        minimum = _number(match.group(1)) if match else None
    if maximum is None:
        match = re.search(r"(?:만\s*)?(\d+)\s*세\s*이하", text)
        maximum = _number(match.group(1)) if match else None
    return minimum, maximum


def _policy_financial_relevance(policy, metrics, risk, profile):
    text = " ".join(str(policy.get(key) or "") for key in ("policy_name", "policy_category", "support_content"))
    score = 0
    reasons = []
    connections = (
        ("cashflow", ("생활", "금융지원", "취업", "생계"), "현금흐름 위험과 관련된 지원 분야입니다."),
        ("debt", ("채무", "부채", "금융상담"), "부채 위험과 관련된 상담·부담완화 분야입니다."),
        ("saving", ("자산형성", "저축", "금융", "복지"), "저축 위험과 관련된 자산형성 분야입니다."),
        ("emergency", ("생활", "복지", "금융", "자산형성"), "비상자금 위험과 관련된 지원 분야입니다."),
    )
    for domain, keywords, reason in connections:
        if _domain_need(risk, domain) >= 0.5 and any(word in text for word in keywords):
            score += 15
            reasons.append(reason)
    surplus = _number(metrics.get("monthly_surplus")) if isinstance(metrics, Mapping) else None
    employment = str(profile.get("employment_status") or "")
    if surplus is not None and surplus < 0 and any(word in text for word in ("생활", "금융", "취업", "복지")):
        score += 10
        reasons.append("월 현금흐름이 적자인 사용자의 지원 필요와 관련성이 있습니다.")
    if "미취업" in employment and any(word in text for word in ("취업", "구직", "일자리")):
        score += 15
        reasons.append("미취업 상태와 취업지원 분야가 관련됩니다.")
    return min(40, score), reasons


def _match_policy(policy, metrics, risk, profile):
    age = _number(profile.get("age"))
    income = _number(profile.get("annual_income"))
    region = str(profile.get("region") or "").strip()
    employment = str(profile.get("employment_status") or "").strip()
    matched = []
    unverified = []
    score = 20.0

    minimum, maximum = _bounds(policy, "age_condition", "min_age", "max_age")
    if age is not None and ((minimum is not None and age < minimum) or (maximum is not None and age > maximum)):
        return None
    if age is not None and (minimum is not None or maximum is not None):
        matched.append("연령")
        score += 15
    else:
        unverified.append("세부 연령요건")

    policy_region = str(policy.get("region") or "").strip()
    if policy_region and not any(word in policy_region for word in ("전국", "제한없음")):
        if region and region not in policy_region:
            return None
        if region:
            matched.append("지역")
            score += 15
        else:
            unverified.append("지역")
    elif policy_region:
        matched.append("지역")
        score += 10
    else:
        unverified.append("지역")

    min_income = _number(policy.get("min_income"))
    max_income = _number(policy.get("max_income"))
    if income is not None and ((min_income is not None and income < min_income) or (max_income is not None and income > max_income)):
        return None
    if income is not None and (min_income is not None or max_income is not None):
        matched.append("소득")
        score += 15
    else:
        unverified.append("세부 소득요건")

    condition = str(policy.get("employment_condition") or "").strip()
    if condition and not any(word in condition for word in ("제한없음", "무관")):
        if employment and employment not in condition:
            return None
        if employment:
            matched.append("취업상태")
            score += 15
        else:
            unverified.append("취업상태")
    elif condition:
        matched.append("취업상태")
        score += 10
    else:
        unverified.append("취업상태")

    relevance, reasons = _policy_financial_relevance(policy, metrics, risk, profile)
    score += relevance
    reasons.extend(f"사용자 {condition_name} 조건과 정책 조건이 관련됩니다." for condition_name in matched)
    if unverified:
        reasons.append("API 정보만으로 확인되지 않는 세부 자격은 신청 전에 확인해야 합니다.")
    return {
        "policy": dict(policy),
        "match_score": round(min(100, max(0, score)), 2),
        "eligibility": "확인 필요",
        "matched_conditions": matched,
        "unverified_conditions": unverified,
        "reasons": reasons,
    }


def get_personalized_recommendations(
    metrics,
    risk,
    user_profile,
    saving_products=None,
    deposit_products=None,
    policies=None,
    max_products=3,
    max_policies=3,
):
    """실제 API에서 전달된 항목만 결정적으로 필터링·정렬한다."""
    safe_metrics = metrics if isinstance(metrics, Mapping) else {}
    safe_risk = risk if isinstance(risk, Mapping) else {}
    profile = user_profile if isinstance(user_profile, Mapping) else {}
    product_status, products = _rank_products(
        safe_metrics, safe_risk, profile, saving_products, deposit_products, max_products
    )
    policy_matches = []
    for policy in _items(policies):
        if isinstance(policy, Mapping) and policy.get("source") == "ONTONG_YOUTH":
            match = _match_policy(policy, safe_metrics, safe_risk, profile)
            if match is not None:
                policy_matches.append(match)
    policy_matches.sort(key=lambda item: (-item["match_score"], str(item["policy"].get("policy_name") or "")))

    domains = safe_risk.get("domains", {})
    ranked_domains = []
    if isinstance(domains, Mapping):
        ranked_domains = [
            name
            for name, value in sorted(
                domains.items(),
                key=lambda pair: _number(pair[1].get("score")) or 0
                if isinstance(pair[1], Mapping)
                else 0,
                reverse=True,
            )
        ]
    return {
        "financial_products": products,
        "youth_policies": policy_matches[: max(0, int(max_policies))],
        "recommendation_context": {
            "product_recommendation_status": product_status,
            "priority_domains": ranked_domains,
            "profile_fields_used": [
                key
                for key in ("age", "region", "employment_status", "annual_income", "preferred_term_months")
                if profile.get(key) is not None
            ],
        },
    }

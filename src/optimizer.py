"""금융 위험을 낮추는 현실적인 행동 조합 탐색기."""

from __future__ import annotations

from itertools import product
from typing import Any, Dict, List

from src.metrics import calculate_metrics
from src.risk_engine import calculate_risk


DEFAULT_STEP = 50_000
MAX_ABSOLUTE_CHANGE = 500_000
PLAN_NAMES = ("부담 최소형", "균형형", "개선 효과형")


def _amount_options(limit: float, step: int) -> List[int]:
    """0부터 limit까지의 탐색 금액을 만들고, limit도 후보에 포함한다."""
    integer_limit = max(0, int(limit))
    options = list(range(0, integer_limit + 1, step))
    if options[-1] != integer_limit:
        options.append(integer_limit)
    return options


def _next_safer_score_limit(score: float) -> float | None:
    """현재 위험등급보다 한 단계 안전해지는 점수 상한을 반환한다."""
    if score >= 80:
        return 80
    if score >= 60:
        return 60
    if score >= 40:
        return 40
    if score >= 20:
        return 20
    return None


def _weighted_effort(candidate: Dict[str, Any], income: float) -> float:
    """행동 난이도를 소득 대비 비율로 환산한다."""
    scale = max(income, 1.0)
    return (
        candidate["living_expense_reduction"]
        + candidate["income_increase"] * 1.5
        + candidate["extra_savings"] * 0.7
    ) / scale


def _select_distinct_plans(
    candidates: List[Dict[str, Any]],
    income: float,
    max_results: int,
) -> List[Dict[str, Any]]:
    """부담, 균형, 효과 기준으로 중복되지 않는 후보를 선택한다."""
    if not candidates:
        return []

    for candidate in candidates:
        candidate["_effort"] = _weighted_effort(candidate, income)

    minimum_effort = min(candidate["_effort"] for candidate in candidates)
    maximum_effort = max(candidate["_effort"] for candidate in candidates)
    minimum_risk = min(candidate["risk_score"] for candidate in candidates)
    maximum_risk = max(candidate["risk_score"] for candidate in candidates)

    effort_range = maximum_effort - minimum_effort or 1.0
    risk_range = maximum_risk - minimum_risk or 1.0

    burden = min(
        candidates,
        key=lambda item: (
            item["_effort"],
            item["risk_score"],
            item["change_count"],
        ),
    )
    balanced = min(
        candidates,
        key=lambda item: (
            0.5 * ((item["_effort"] - minimum_effort) / effort_range)
            + 0.5 * ((item["risk_score"] - minimum_risk) / risk_range),
            item["_effort"],
        ),
    )
    effect = min(
        candidates,
        key=lambda item: (
            item["risk_score"],
            item["_effort"],
            item["change_count"],
        ),
    )

    selected = []
    seen = set()
    for name, candidate in zip(PLAN_NAMES, (burden, balanced, effect)):
        identity = (
            candidate["living_expense_reduction"],
            candidate["income_increase"],
            candidate["extra_savings"],
        )
        if identity in seen:
            continue
        seen.add(identity)
        plan = {key: value for key, value in candidate.items() if not key.startswith("_")}
        plan["name"] = name
        selected.append(plan)
        if len(selected) >= max_results:
            break

    return selected


def find_improvement_plans(
    income: float,
    fixed_expense: float,
    living_expense: float,
    debt_payment: float,
    monthly_savings: float,
    savings: float,
    *,
    step: int = DEFAULT_STEP,
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """현재 상태보다 안전한 행동 조합을 최대 3개 반환한다.

    사용자가 목표점수를 입력하지 않아도 현재 위험점수의 바로 아래
    등급 경계를 자동 목표로 사용한다. 해당 경계에 도달 가능한 후보가
    없으면 탐색 범위 안에서 위험점수가 실제로 낮아지는 후보를 사용한다.
    """
    if not isinstance(step, int) or isinstance(step, bool) or step <= 0:
        raise ValueError("step은 0보다 큰 정수여야 합니다.")
    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise ValueError("max_results는 정수여야 합니다.")
    if not 1 <= max_results <= 3:
        raise ValueError("max_results는 1부터 3 사이여야 합니다.")

    current_metrics = calculate_metrics(
        income,
        fixed_expense,
        living_expense,
        debt_payment,
        monthly_savings,
        savings,
    )
    current_risk = calculate_risk(current_metrics)
    normalized_income = current_metrics["monthly_income"]
    normalized_living_expense = current_metrics["variable_expense"]
    normalized_monthly_savings = current_metrics["monthly_saving"]

    living_limit = min(normalized_living_expense * 0.3, MAX_ABSOLUTE_CHANGE)
    income_limit = min(normalized_income * 0.2, MAX_ABSOLUTE_CHANGE)
    saving_limit = min(normalized_income * 0.15, MAX_ABSOLUTE_CHANGE)

    candidates: List[Dict[str, Any]] = []
    combinations = product(
        _amount_options(living_limit, step),
        _amount_options(income_limit, step),
        _amount_options(saving_limit, step),
    )

    for living_reduction, income_increase, extra_savings in combinations:
        if living_reduction == income_increase == extra_savings == 0:
            continue

        new_income = normalized_income + income_increase
        new_living_expense = normalized_living_expense - living_reduction
        new_monthly_savings = normalized_monthly_savings + extra_savings
        available_for_saving = (
            new_income - fixed_expense - new_living_expense - debt_payment
        )

        # 추가 저축은 필수지출 후 실제로 남는 금액 안에서만 제안한다.
        if extra_savings > 0 and new_monthly_savings > available_for_saving:
            continue

        new_metrics = calculate_metrics(
            new_income,
            fixed_expense,
            new_living_expense,
            debt_payment,
            new_monthly_savings,
            savings,
        )
        new_risk = calculate_risk(new_metrics)
        if new_risk["score"] >= current_risk["score"]:
            continue

        candidates.append({
            "living_expense_reduction": living_reduction,
            "income_increase": income_increase,
            "extra_savings": extra_savings,
            "new_monthly_savings": new_monthly_savings,
            "risk_score": new_risk["score"],
            "health_score": round(100 - new_risk["score"], 2),
            "risk_level": new_risk["level"],
            "risk_reduction": round(current_risk["score"] - new_risk["score"], 2),
            "new_monthly_surplus": new_metrics["monthly_surplus"],
            "change_count": sum(
                amount > 0
                for amount in (living_reduction, income_increase, extra_savings)
            ),
        })

    safer_limit = _next_safer_score_limit(current_risk["score"])
    safer_candidates = (
        [candidate for candidate in candidates if candidate["risk_score"] < safer_limit]
        if safer_limit is not None
        else []
    )
    selection_pool = safer_candidates or candidates

    return _select_distinct_plans(selection_pool, normalized_income, max_results)


# 호출부에서 더 짧은 이름을 선호할 때 사용할 수 있는 별칭이다.
optimize_financial_plan = find_improvement_plans

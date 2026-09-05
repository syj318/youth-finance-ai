"""현재 금융행동 유지 가정에 따른 시나리오 기반 금융건강 전망."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from src.metrics import calculate_metrics
from src.risk_engine import calculate_risk


DEFAULT_MONTHS = (0, 3, 6, 12)
PLAN_REQUIRED_FIELDS = (
    "income_increase",
    "living_expense_reduction",
    "new_monthly_savings",
)


def _validate_months(months: Iterable[int]) -> list[int]:
    if isinstance(months, (str, bytes)) or not isinstance(months, Iterable):
        raise ValueError("months는 0 이상의 정수로 구성된 iterable이어야 합니다.")

    validated = []
    for month in months:
        if isinstance(month, bool) or not isinstance(month, int):
            raise ValueError("각 month는 0 이상의 정수여야 합니다.")
        if month < 0:
            raise ValueError("음수 month는 사용할 수 없습니다.")
        validated.append(month)
    return validated


def _project_health(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings,
    months,
) -> list[dict[str, Any]]:
    results = []
    for month in _validate_months(months):
        projected_savings = max(0, savings + monthly_savings * month)
        projected_metrics = calculate_metrics(
            income,
            fixed_expense,
            living_expense,
            debt_payment,
            monthly_savings,
            projected_savings,
        )
        projected_risk = calculate_risk(projected_metrics)
        risk_score = max(0, min(100, projected_risk["score"]))
        health_score = max(0, min(100, 100 - risk_score))

        results.append(
            {
                "month": month,
                "projected_savings": projected_savings,
                "health_score": round(health_score, 2),
                "risk_score": risk_score,
                "risk_level": projected_risk["level"],
                "emergency_months": projected_metrics["emergency_months"],
            }
        )
    return results


def forecast_financial_health(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings,
    months=DEFAULT_MONTHS,
):
    """현재 월 금융행동이 유지될 때 시점별 금융건강을 전망한다."""
    return _project_health(
        income,
        fixed_expense,
        living_expense,
        debt_payment,
        monthly_savings,
        savings,
        months,
    )


def _validate_plan(plan: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(plan, Mapping):
        raise ValueError("plan은 optimizer가 반환한 dict 형식이어야 합니다.")

    missing = [field for field in PLAN_REQUIRED_FIELDS if field not in plan]
    if missing:
        raise ValueError(f"plan 필수 필드가 없습니다: {', '.join(missing)}")

    validated = {}
    for field in PLAN_REQUIRED_FIELDS:
        value = plan[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"plan의 {field}는 숫자여야 합니다.")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"plan의 {field}는 0 이상의 유한한 숫자여야 합니다.")
        validated[field] = value
    return validated


def forecast_plan_health(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings,
    plan,
    months=DEFAULT_MONTHS,
):
    """optimizer가 산출한 개선안을 적용한 시점별 금융건강을 전망한다."""
    validated_plan = _validate_plan(plan)
    new_income = income + validated_plan["income_increase"]
    new_living_expense = max(
        0,
        living_expense - validated_plan["living_expense_reduction"],
    )
    new_monthly_savings = validated_plan["new_monthly_savings"]

    return _project_health(
        new_income,
        fixed_expense,
        new_living_expense,
        debt_payment,
        new_monthly_savings,
        savings,
        months,
    )

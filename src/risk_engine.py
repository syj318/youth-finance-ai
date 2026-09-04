"""
청년 금융건강 진단 - 금융위험도 엔진

Risk Score:
    0   = 매우 안정
    100 = 매우 위험

영역별 최대 점수:
    cashflow          30
    debt              25
    saving            20
    emergency         15
    expense_structure 10
    ----------------------
    total            100
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


# ============================================================
# 1. Score Configuration
# ============================================================

DOMAIN_MAX_SCORES = {
    "cashflow": 30.0,
    "debt": 25.0,
    "saving": 20.0,
    "emergency": 15.0,
    "expense_structure": 10.0,
}


# 위험등급
RISK_LEVELS = [
    (20, "매우 안정"),
    (40, "안정"),
    (60, "주의"),
    (80, "위험"),
    (101, "매우 위험"),
]


# 상호작용 보정 최대치
MAX_INTERACTION_ADJUSTMENT = 8.0


# ============================================================
# 2. Validation / Normalization
# ============================================================

MONEY_FIELDS = [
    "monthly_income",
    "fixed_expense",
    "variable_expense",
    "loan_payment",
    "monthly_saving",
    "current_savings",
]

OPTIONAL_DERIVED_FIELDS = [
    "monthly_surplus",
    "surplus_rate",
    "debt_service_rate",
]

REQUIRED_FIELDS = [
    "monthly_income",
    "fixed_expense",
    "variable_expense",
    "loan_payment",
    "monthly_saving",
    "current_savings",
]


def _to_float(value: Any, field_name: str) -> float:
    """
    숫자 / 숫자 문자열을 float으로 변환한다.
    """
    if value is None:
        raise ValueError(f"{field_name} 값이 없습니다.")

    if isinstance(value, bool):
        raise ValueError(f"{field_name}에 boolean 값을 사용할 수 없습니다.")

    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name}은 숫자 또는 숫자로 변환 가능한 문자열이어야 합니다."
        )

    if result != result:  # NaN
        raise ValueError(f"{field_name}에 NaN을 사용할 수 없습니다.")

    if result == float("inf") or result == float("-inf"):
        raise ValueError(f"{field_name}에 무한값을 사용할 수 없습니다.")

    return result


def validate_metrics(metrics: Dict[str, Any]) -> Dict[str, float]:
    """
    입력값 검증 및 숫자형 정규화.

    derived metric은 외부에서 들어와도 다시 계산한다.
    이를 통해 서로 모순되는 입력값을 방지한다.
    """

    if not isinstance(metrics, dict):
        raise ValueError("metrics는 dict 타입이어야 합니다.")

    normalized = {}

    for field in REQUIRED_FIELDS:
        if field not in metrics:
            raise ValueError(f"필수 금융지표가 없습니다: {field}")

    for field in MONEY_FIELDS:
        value = _to_float(metrics[field], field)

        if value < 0:
            raise ValueError(f"{field}은 음수가 될 수 없습니다.")

        normalized[field] = value

    return normalized


# ============================================================
# 3. Derived Metrics
# ============================================================

def calculate_derived_metrics(
    metrics: Dict[str, float]
) -> Dict[str, float]:

    income = metrics["monthly_income"]

    fixed = metrics["fixed_expense"]
    variable = metrics["variable_expense"]
    loan = metrics["loan_payment"]
    saving = metrics["monthly_saving"]
    current_savings = metrics["current_savings"]

    if income <= 0:
        raise ValueError("월 소득은 0보다 커야 합니다.")

    living_expense = fixed + variable
    essential_outflow = living_expense + loan

    available_for_saving = income - essential_outflow
    monthly_surplus = available_for_saving - saving

    living_expense_rate = (living_expense / income) * 100
    total_expense_rate = (essential_outflow / income) * 100

    surplus_rate = (monthly_surplus / income) * 100
    debt_service_rate = (loan / income) * 100

    saving_rate = (saving / income) * 100

    if essential_outflow > 0:
        emergency_months = current_savings / essential_outflow
    else:
        emergency_months = 0

    # 저축 지속가능성
    if available_for_saving > 0:
        saving_to_surplus_ratio = saving / available_for_saving
    else:
        saving_to_surplus_ratio = float("inf")

    return {
        **metrics,
        "living_expense": living_expense,
        "total_outflow": essential_outflow,
        "available_for_saving": available_for_saving,
        "monthly_surplus": monthly_surplus,
        "living_expense_rate": living_expense_rate,
        "total_expense_rate": total_expense_rate,
        "surplus_rate": surplus_rate,
        "debt_service_rate": debt_service_rate,
        "saving_rate": saving_rate,
        "emergency_months": emergency_months,
        "saving_to_surplus_ratio": saving_to_surplus_ratio,
    }


# ============================================================
# 4. Generic Piecewise Risk Score
# ============================================================

def piecewise_score(
    value: float,
    points: List[Tuple[float, float]]
) -> float:
    """
    [(지표값, 위험점수)] 형태의 구간을 선형 보간한다.

    예:
        [(10, 0), (20, 5), (30, 12)]
    """

    if not points:
        return 0.0

    points = sorted(points)

    if value <= points[0][0]:
        return points[0][1]

    if value >= points[-1][0]:
        return points[-1][1]

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            ratio = (value - x1) / (x2 - x1)
            return y1 + (y2 - y1) * ratio

    return points[-1][1]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def round_score(value: float) -> float:
    return round(clamp(value, 0, 100), 2)


def make_score_component(
    name: str,
    score: float,
    max_score: float,
    metric: str,
    value: float,
    unit: str,
    explanation: str,
) -> Dict[str, Any]:
    """영역 점수를 구성하는 세부 항목을 화면 표시용으로 정리한다."""
    rounded_score = round(score, 2)
    return {
        "name": name,
        "score": rounded_score,
        "max_score": max_score,
        "health_deduction": rounded_score,
        "metric": metric,
        "value": round(value, 2),
        "unit": unit,
        "explanation": explanation,
    }


# ============================================================
# 5. Risk Level
# ============================================================

def get_risk_level(score: float) -> str:

    score = clamp(score, 0, 100)

    for threshold, level in RISK_LEVELS:
        if score < threshold:
            return level

    return "매우 위험"


def get_domain_level(score: float, max_score: float) -> str:

    if max_score <= 0:
        return "알 수 없음"

    ratio = score / max_score

    if ratio < 0.2:
        return "안정"

    if ratio < 0.4:
        return "양호"

    if ratio < 0.6:
        return "주의"

    if ratio < 0.8:
        return "위험"

    return "매우 위험"


# ============================================================
# 6. Cashflow Risk
# ============================================================

def calculate_cashflow_risk(
    m: Dict[str, float]
) -> Dict[str, Any]:

    living_expense_rate = m["living_expense_rate"]
    surplus_rate = m["surplus_rate"]

    # 생활지출률 최대 18점
    living_score = piecewise_score(
        living_expense_rate,
        [
            (45, 0),
            (55, 4),
            (65, 9),
            (75, 14),
            (85, 18),
        ],
    )

    # 저축 후 남는 비상 여유자금 비율, 최대 12점
    surplus_score = piecewise_score(
        surplus_rate,
        [
            (-10, 12),
            (0, 6),
            (5, 3),
            (10, 1),
            (15, 0),
        ],
    )

    score = round_score(living_score + surplus_score)

    breakdown = [
        make_score_component(
            "생활지출 부담",
            living_score,
            18,
            "living_expense_rate",
            living_expense_rate,
            "%",
            f"생활지출이 소득의 {living_expense_rate:.1f}%여서 위험점수 "
            f"{living_score:.2f}점이 추가되었습니다.",
        ),
        make_score_component(
            "월 잔여금 부족",
            surplus_score,
            12,
            "surplus_rate",
            surplus_rate,
            "%",
            f"지출과 저축 후 잔여금이 소득의 {surplus_rate:.1f}%여서 위험점수 "
            f"{surplus_score:.2f}점이 추가되었습니다.",
        ),
    ]

    reasons = []

    if surplus_rate < 0:
        reasons.append({
            "code": "NEGATIVE_SURPLUS",
            "severity": score,
            "message": "지출과 저축을 합친 금액이 소득을 초과하여 월 현금흐름이 적자입니다.",
            "recommendation": "생활비와 월저축액을 조정해 매월 사용할 수 있는 비상 여유자금을 확보하세요.",
        })
    elif surplus_rate < 10:
        reasons.append({
            "code": "LOW_SURPLUS",
            "severity": score,
            "message": "지출과 저축 후 남는 비상 여유자금이 적어 예상치 못한 지출에 취약합니다.",
            "recommendation": "저축을 유지하되 소득의 일부가 월말 여유자금으로 남도록 생활비를 점검하세요.",
        })

    if living_expense_rate >= 65:
        reasons.append({
            "code": "HIGH_LIVING_EXPENSE",
            "severity": living_score,
            "message": "소득 대비 생활지출 부담이 높은 편입니다.",
            "recommendation": "고정지출과 반복적으로 발생하는 생활비를 우선 점검하세요.",
        })

    return {
        "score": score,
        "max_score": 30,
        "level": get_domain_level(score, 30),
        "explanation": f"생활지출 {living_score:.2f}점 + 잔여금 {surplus_score:.2f}점 = 현금흐름 위험 {score:.2f}점입니다.",
        "breakdown": breakdown,
        "reasons": reasons,
        "metrics": {
            "living_expense_rate": round(living_expense_rate, 2),
            "surplus_rate": round(surplus_rate, 2),
        },
    }


# ============================================================
# 7. Debt Risk
# ============================================================

def calculate_debt_risk(
    m: Dict[str, float]
) -> Dict[str, Any]:

    rate = m["debt_service_rate"]

    score = piecewise_score(
        rate,
        [
            (10, 0),
            (20, 5),
            (30, 12),
            (40, 18),
            (50, 22),
            (60, 25),
        ],
    )

    score = round_score(score)

    breakdown = [
        make_score_component(
            "부채상환 부담",
            score,
            25,
            "debt_service_rate",
            rate,
            "%",
            f"월 대출상환액이 소득의 {rate:.1f}%여서 위험점수 "
            f"{score:.2f}점이 추가되었습니다.",
        ),
    ]

    reasons = []

    if rate >= 40:
        reasons.append({
            "code": "HIGH_DEBT_SERVICE",
            "severity": score,
            "message": "소득 대비 대출상환 부담이 매우 높습니다.",
            "recommendation": "새로운 대출이나 추가적인 고정지출을 늘리기 전에 현재 부채상환 구조를 먼저 점검하세요.",
        })
    elif rate >= 30:
        reasons.append({
            "code": "ELEVATED_DEBT_SERVICE",
            "severity": score,
            "message": "소득에서 대출상환에 사용되는 비중이 높은 편입니다.",
            "recommendation": "월 상환액과 잔여 현금흐름을 함께 확인해 부채 부담을 관리하세요.",
        })

    return {
        "score": score,
        "max_score": 25,
        "level": get_domain_level(score, 25),
        "explanation": f"부채상환비율 {rate:.1f}%를 기준으로 부채 위험 {score:.2f}점이 산정되었습니다.",
        "breakdown": breakdown,
        "reasons": reasons,
        "metrics": {
            "debt_service_rate": round(rate, 2),
        },
    }


# ============================================================
# 8. Saving Risk
# ============================================================

def calculate_saving_risk(
    m: Dict[str, float]
) -> Dict[str, Any]:

    saving_rate = m["saving_rate"]
    available_for_saving = m["available_for_saving"]
    saving_to_surplus = m["saving_to_surplus_ratio"]

    # 저축률 최대 14점
    saving_rate_score = piecewise_score(
        saving_rate,
        [
            (0, 14),
            (5, 11),
            (10, 7),
            (15, 3),
            (20, 0),
        ],
    )

    # 저축 지속가능성 최대 6점
    if available_for_saving <= 0:
        sustainability_score = 6
    elif saving_to_surplus <= 0.5:
        sustainability_score = 0
    elif saving_to_surplus <= 0.75:
        sustainability_score = 2
    elif saving_to_surplus <= 1:
        sustainability_score = 4
    else:
        sustainability_score = 6

    score = round_score(
        saving_rate_score + sustainability_score
    )

    sustainability_value = (
        0.0 if saving_to_surplus == float("inf") else saving_to_surplus * 100
    )
    breakdown = [
        make_score_component(
            "저축률 부족",
            saving_rate_score,
            14,
            "saving_rate",
            saving_rate,
            "%",
            f"월 저축액이 소득의 {saving_rate:.1f}%여서 위험점수 "
            f"{saving_rate_score:.2f}점이 추가되었습니다.",
        ),
        make_score_component(
            "저축 지속가능성",
            sustainability_score,
            6,
            "saving_to_surplus_ratio",
            sustainability_value,
            "%",
            (
                "필수지출 후 저축 가능한 금액이 없어 현재 저축을 지속하기 어렵기 때문에 "
                f"위험점수 {sustainability_score:.2f}점이 추가되었습니다."
                if available_for_saving <= 0
                else f"저축액이 필수지출 후 가용금액의 {sustainability_value:.1f}%여서 "
                f"위험점수 {sustainability_score:.2f}점이 추가되었습니다."
            ),
        ),
    ]

    reasons = []

    if saving_rate < 10:
        reasons.append({
            "code": "LOW_SAVING_RATE",
            "severity": saving_rate_score,
            "message": "소득 대비 저축률이 낮아 미래 재무여력을 확보하기 어렵습니다.",
            "recommendation": "월급일 직후 일정 금액을 자동저축하는 방식으로 저축을 먼저 확보해 보세요.",
        })

    if available_for_saving <= 0 and m["monthly_saving"] > 0:
        reasons.append({
            "code": "UNSUSTAINABLE_SAVING",
            "severity": sustainability_score,
            "message": "필수지출 후 여유금이 없어 현재 월저축을 지속하기 어려울 가능성이 있습니다.",
            "recommendation": "무리하게 저축액을 늘리기보다 현재 현금흐름을 안정화하는 것을 우선하세요.",
        })
    elif saving_to_surplus > 1:
        reasons.append({
            "code": "HIGH_SAVING_TO_SURPLUS",
            "severity": sustainability_score,
            "message": "저축액이 월 잔여금보다 커 현재 소비구조에서 지속 가능한 저축인지 점검이 필요합니다.",
            "recommendation": "월 잔여금 범위 안에서 지속 가능한 저축액을 설정하세요.",
        })

    return {
        "score": score,
        "max_score": 20,
        "level": get_domain_level(score, 20),
        "explanation": f"저축률 {saving_rate_score:.2f}점 + 지속가능성 {sustainability_score:.2f}점 = 저축 위험 {score:.2f}점입니다.",
        "breakdown": breakdown,
        "reasons": reasons,
        "metrics": {
            "saving_rate": round(saving_rate, 2),
            "saving_to_surplus_ratio": (
                None
                if saving_to_surplus == float("inf")
                else round(saving_to_surplus, 2)
            ),
        },
    }


# ============================================================
# 9. Emergency Fund Risk
# ============================================================

def calculate_emergency_risk(
    m: Dict[str, float]
) -> Dict[str, Any]:

    months = m["emergency_months"]

    score = piecewise_score(
        months,
        [
            (0, 15),
            (1, 9),
            (3, 4),
            (6, 0),
        ],
    )

    score = round_score(score)

    breakdown = [
        make_score_component(
            "비상자금 보유기간",
            score,
            15,
            "emergency_months",
            months,
            "개월",
            f"현재 비상자금으로 필수지출을 {months:.1f}개월 감당할 수 있어 "
            f"위험점수 {score:.2f}점이 추가되었습니다.",
        ),
    ]

    reasons = []

    if months < 1:
        reasons.append({
            "code": "VERY_LOW_EMERGENCY_FUND",
            "severity": score,
            "message": "비상자금이 1개월 미만 수준으로 예상치 못한 지출에 취약합니다.",
            "recommendation": "우선 생활비 1개월 수준의 비상자금을 확보한 뒤 3개월 이상으로 확대하는 것을 권장합니다.",
        })
    elif months < 3:
        reasons.append({
            "code": "LOW_EMERGENCY_FUND",
            "severity": score,
            "message": "비상자금이 충분하지 않아 갑작스러운 소득 감소나 지출에 취약할 수 있습니다.",
            "recommendation": "생활비 기준 최소 3개월 수준의 비상자금 확보를 목표로 하세요.",
        })

    return {
        "score": score,
        "max_score": 15,
        "level": get_domain_level(score, 15),
        "explanation": f"비상자금 보유기간 {months:.1f}개월을 기준으로 비상자금 위험 {score:.2f}점이 산정되었습니다.",
        "breakdown": breakdown,
        "reasons": reasons,
        "metrics": {
            "emergency_months": round(months, 2),
        },
    }


# ============================================================
# 10. Expense Structure Risk
# ============================================================

def calculate_expense_structure_risk(
    m: Dict[str, float]
) -> Dict[str, Any]:

    income = m["monthly_income"]

    fixed_rate = (m["fixed_expense"] / income) * 100
    variable_rate = (m["variable_expense"] / income) * 100

    # 고정지출 최대 7점
    fixed_score = piecewise_score(
        fixed_rate,
        [
            (30, 0),
            (40, 1),
            (50, 3),
            (60, 5),
            (70, 7),
        ],
    )

    # 변동지출 최대 3점
    variable_score = piecewise_score(
        variable_rate,
        [
            (15, 0),
            (25, 1),
            (35, 2),
            (45, 3),
        ],
    )

    score = round_score(fixed_score + variable_score)

    breakdown = [
        make_score_component(
            "고정지출 부담",
            fixed_score,
            7,
            "fixed_expense_rate",
            fixed_rate,
            "%",
            f"고정지출이 소득의 {fixed_rate:.1f}%여서 위험점수 "
            f"{fixed_score:.2f}점이 추가되었습니다.",
        ),
        make_score_component(
            "변동지출 부담",
            variable_score,
            3,
            "variable_expense_rate",
            variable_rate,
            "%",
            f"변동지출이 소득의 {variable_rate:.1f}%여서 위험점수 "
            f"{variable_score:.2f}점이 추가되었습니다.",
        ),
    ]

    reasons = []

    if fixed_rate >= 50:
        reasons.append({
            "code": "HIGH_FIXED_EXPENSE",
            "severity": fixed_score,
            "message": "소득 대비 고정지출 비중이 높아 단기간에 지출을 줄이기 어렵습니다.",
            "recommendation": "주거비·통신비·구독료 등 반복적으로 발생하는 고정지출을 우선 점검하세요.",
        })

    if variable_rate >= 35:
        reasons.append({
            "code": "HIGH_VARIABLE_EXPENSE",
            "severity": variable_score,
            "message": "소득 대비 변동지출 비중이 높은 편입니다.",
            "recommendation": "외식·쇼핑·여가 등 월별 변동성이 큰 지출을 먼저 점검하세요.",
        })

    return {
        "score": score,
        "max_score": 10,
        "level": get_domain_level(score, 10),
        "explanation": f"고정지출 {fixed_score:.2f}점 + 변동지출 {variable_score:.2f}점 = 지출구조 위험 {score:.2f}점입니다.",
        "breakdown": breakdown,
        "reasons": reasons,
        "metrics": {
            "fixed_expense_rate": round(fixed_rate, 2),
            "variable_expense_rate": round(variable_rate, 2),
        },
    }


# ============================================================
# 11. Interaction Risk
# ============================================================

def calculate_interaction_adjustment(
    m: Dict[str, float]
) -> Dict[str, Any]:

    adjustment = 0.0
    reasons = []

    # 적자 + 높은 부채상환 부담
    if (
        m["monthly_surplus"] < 0
        and m["debt_service_rate"] >= 40
    ):
        adjustment += 4
        reasons.append({
            "code": "DEFICIT_AND_HIGH_DEBT",
            "severity": 4,
            "message": "현금흐름 적자와 높은 부채상환 부담이 동시에 발생하고 있습니다.",
            "recommendation": "소비 절감뿐 아니라 부채상환 구조와 월 현금흐름을 함께 점검해야 합니다.",
        })

    # 저축 부족 + 비상자금 부족
    if (
        m["saving_rate"] < 5
        and m["emergency_months"] < 1
    ):
        adjustment += 3
        reasons.append({
            "code": "LOW_SAVING_AND_EMERGENCY",
            "severity": 3,
            "message": "저축 여력과 비상자금이 모두 부족해 금융충격 대응력이 낮습니다.",
            "recommendation": "투자나 소비 확대보다 기본적인 현금성 안전자금 확보를 우선하세요.",
        })

    # 높은 고정지출 + 낮은 잔여금
    fixed_rate = (
        m["fixed_expense"] / m["monthly_income"]
    ) * 100

    if fixed_rate >= 60 and m["surplus_rate"] < 10:
        adjustment += 2
        reasons.append({
            "code": "HIGH_FIXED_AND_LOW_SURPLUS",
            "severity": 2,
            "message": "고정지출 부담이 높고 월 잔여금도 낮아 지출 조정 여력이 제한적입니다.",
            "recommendation": "변동지출을 줄이는 동시에 장기 고정비를 점검하세요.",
        })

    # 높은 변동지출 + 낮은 잔여금
    variable_rate = (
        m["variable_expense"] / m["monthly_income"]
    ) * 100

    if variable_rate >= 40 and m["surplus_rate"] < 10:
        adjustment += 1
        reasons.append({
            "code": "HIGH_VARIABLE_AND_LOW_SURPLUS",
            "severity": 1,
            "message": "변동지출 비중이 높고 잔여금이 적어 소비 조정이 필요합니다.",
            "recommendation": "변동지출 항목 중 반복적으로 발생하는 소비부터 점검하세요.",
        })

    adjustment = min(
        adjustment,
        MAX_INTERACTION_ADJUSTMENT
    )

    return {
        "score": round(adjustment, 2),
        "max_score": MAX_INTERACTION_ADJUSTMENT,
        "explanation": (
            f"여러 위험이 동시에 나타나 추가 위험점수 {adjustment:.2f}점이 반영되었습니다."
            if adjustment > 0
            else "동시에 발생한 복합 위험요인이 없어 추가 점수가 없습니다."
        ),
        "breakdown": [
            {
                "name": reason["code"],
                "score": reason["severity"],
                "max_score": reason["severity"],
                "health_deduction": reason["severity"],
                "explanation": reason["message"],
            }
            for reason in reasons
        ],
        "reasons": reasons,
    }


# ============================================================
# 12. Main Risk Engine
# ============================================================

def calculate_risk(metrics):
    # 1. 입력값 검증
    validated = validate_metrics(metrics)

    # 2. 파생지표 계산
    m = calculate_derived_metrics(validated)

    # 3. 영역별 위험도 계산
    cashflow = calculate_cashflow_risk(m)
    debt = calculate_debt_risk(m)
    saving = calculate_saving_risk(m)
    emergency = calculate_emergency_risk(m)
    expense_structure = calculate_expense_structure_risk(m)

    # 4. 영역별 점수 합산
    base_score = (
        cashflow["score"]
        + debt["score"]
        + saving["score"]
        + emergency["score"]
        + expense_structure["score"]
    )

    # 5. 상호작용 위험 보정
    interaction = calculate_interaction_adjustment(m)

    remaining_headroom = 100 - base_score

    applied_adjustment = min(
        interaction["score"],
        max(0, remaining_headroom)
    )

    # 6. 최종 위험점수
    final_score = round_score(
        base_score + applied_adjustment
    )

    # 7. 위험요인 통합
    risk_factors = []

    domains = [
        cashflow,
        debt,
        saving,
        emergency,
        expense_structure,
    ]

    for domain in domains:
        for reason in domain["reasons"]:
            risk_factors.append(reason)

    # 상호작용 위험요인 추가
    for reason in interaction["reasons"]:
        risk_factors.append(reason)

    # 영향도가 높은 위험요인부터 정렬
    risk_factors.sort(
        key=lambda x: x["severity"],
        reverse=True
    )

    # 8. 이유만 추출
    reasons = [
        reason["message"]
        for reason in risk_factors
    ]

    # 중복 제거
    reasons = list(dict.fromkeys(reasons))

    # 최대 5개까지만 반환
    reasons = reasons[:5]

    # 9. 최종 반환
    return {
        "score": final_score,
        "level": get_risk_level(final_score),
        "reasons": reasons,
        "domains": {
            "cashflow": cashflow,
            "debt": debt,
            "saving": saving,
            "emergency": emergency,
            "expense_structure": expense_structure,
        },
        "score_breakdown": {
            "base_score": round(base_score, 2),
            "interaction_score": round(interaction["score"], 2),
            "applied_interaction_score": round(applied_adjustment, 2),
            "final_risk_score": final_score,
            "health_score": round(100 - final_score, 2),
            "explanation": (
                f"영역별 위험점수 합계 {base_score:.2f}점에 복합위험 "
                f"{applied_adjustment:.2f}점을 더해 최종 위험점수는 "
                f"{final_score:.2f}점입니다. 건강점수에서는 같은 점수만큼 차감됩니다."
            ),
        },
        "interaction": interaction,
    }

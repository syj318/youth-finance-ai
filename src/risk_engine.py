def calculate_risk(metrics):

    score = 0
    reasons = []

    if metrics["monthly_surplus"] < 0:
        score += 35
        reasons.append("월 지출이 월 소득보다 많습니다.")

    if metrics["surplus_rate"] < 10:
        score += 20
        reasons.append("저축 여력이 부족합니다.")

    elif metrics["surplus_rate"] < 20:
        score += 10

    if metrics["debt_service_rate"] >= 40:
        score += 25
        reasons.append("부채 상환 부담이 매우 높습니다.")

    elif metrics["debt_service_rate"] >= 30:
        score += 15
        reasons.append("부채 상환 부담이 다소 높습니다.")

    if metrics["emergency_months"] < 1:
        score += 20
        reasons.append("비상자금이 매우 부족합니다.")

    elif metrics["emergency_months"] < 3:
        score += 10
        reasons.append("비상자금 확보가 필요합니다.")

    score = min(score, 100)

    if score < 30:
        level = "안정"

    elif score < 60:
        level = "주의"

    else:
        level = "위험"

    return {
        "score": score,
        "level": level,
        "reasons": reasons
    }
def calculate_metrics(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings
):
    essential_outflow = (
        fixed_expense
        + living_expense
        + debt_payment
    )

    available_surplus = income - essential_outflow
    monthly_surplus = available_surplus - monthly_savings

    if income > 0:
        surplus_rate = monthly_surplus / income * 100
        savings_rate = monthly_savings / income * 100
        debt_service_rate = debt_payment / income * 100
    else:
        surplus_rate = 0
        savings_rate = 0
        debt_service_rate = 0

    if essential_outflow > 0:
        emergency_months = savings / essential_outflow
    else:
        emergency_months = 0

    return {
        # 위험 엔진에서 사용하는 원본 입력값
        "monthly_income": income,
        "fixed_expense": fixed_expense,
        "variable_expense": living_expense,
        "loan_payment": debt_payment,
        "monthly_saving": monthly_savings,
        "current_savings": savings,

        # 대시보드와 예측에서 사용하는 파생지표
        "total_expense": essential_outflow,
        "available_for_saving": available_surplus,
        "available_surplus": available_surplus,
        "monthly_surplus": monthly_surplus,
        "surplus_rate": surplus_rate,
        "savings_rate": savings_rate,
        "debt_service_rate": debt_service_rate,
        "emergency_months": emergency_months,
    }

def calculate_metrics(
    income,
    fixed_expense,
    living_cost,
    debt_payment,
    monthly_saving,
    current_savings
):
    essential_outflow = (
        fixed_expense
        + living_cost
        + debt_payment
    )

    available_for_saving = income - essential_outflow
    monthly_surplus = available_for_saving - monthly_saving

    if income > 0:
        surplus_rate = monthly_surplus / income * 100
        debt_service_rate = debt_payment / income * 100
    else:
        surplus_rate = 0
        debt_service_rate = 0

    living_expense = fixed_expense + living_cost

    if essential_outflow > 0:
        emergency_months = current_savings / essential_outflow
    else:
        emergency_months = 0

    return {
        "monthly_income": income,
        "fixed_expense": fixed_expense,
        "variable_expense": living_cost,
        "loan_payment": debt_payment,
        "monthly_saving": monthly_saving,
        "current_savings": current_savings,

        "total_expense": essential_outflow,
        "available_for_saving": available_for_saving,
        "monthly_surplus": monthly_surplus,
        "surplus_rate": surplus_rate,
        "debt_service_rate": debt_service_rate,
        "emergency_months": emergency_months,
    }

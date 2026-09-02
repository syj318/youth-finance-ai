def calculate_metrics(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings
):
    total_expense = (
        fixed_expense
        + living_expense
        + debt_payment
    )

    available_surplus = income - total_expense

    monthly_surplus = (
        available_surplus
        - monthly_savings
    )

    if income > 0:
        surplus_rate = available_surplus / income * 100
        savings_rate = monthly_savings / income * 100
        debt_service_rate = debt_payment / income * 100
    else:
        surplus_rate = 0
        savings_rate = 0
        debt_service_rate = 0

    living_cost = fixed_expense + living_expense

    if living_cost > 0:
        emergency_months = savings / living_cost
    else:
        emergency_months = 0

    return {
        "total_expense": total_expense,
        "available_surplus": available_surplus,
        "monthly_surplus": monthly_surplus,
        "surplus_rate": surplus_rate,
        "savings_rate": savings_rate,
        "debt_service_rate": debt_service_rate,
        "emergency_months": emergency_months
    }
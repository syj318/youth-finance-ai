def calculate_metrics(
    income,
    fixed_expense,
    variable_expense,
    debt_payment,
    savings
):
    total_expense = (
        fixed_expense
        + variable_expense
        + debt_payment
    )

    monthly_surplus = income - total_expense

    if income > 0:
        surplus_rate = monthly_surplus / income * 100
        debt_service_rate = debt_payment / income * 100
    else:
        surplus_rate = 0
        debt_service_rate = 0

    living_expense = fixed_expense + variable_expense

    if living_expense > 0:
        emergency_months = savings / living_expense
    else:
        emergency_months = 0

    return {
        "total_expense": total_expense,
        "monthly_surplus": monthly_surplus,
        "surplus_rate": surplus_rate,
        "debt_service_rate": debt_service_rate,
        "emergency_months": emergency_months
    }
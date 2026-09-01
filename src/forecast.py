import pandas as pd


def forecast_assets(
    current_savings,
    monthly_surplus,
    months=12
):
    results = []

    asset = current_savings

    for month in range(1, months + 1):
        asset += monthly_surplus

        results.append({
            "month": month,
            "asset": asset
        })

    return pd.DataFrame(results)
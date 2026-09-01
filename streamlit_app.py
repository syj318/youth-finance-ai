import streamlit as st

from src.metrics import calculate_metrics
from src.risk_engine import calculate_risk
from src.forecast import forecast_assets


st.set_page_config(
    page_title="청년 금융 AI",
    page_icon="💰",
    layout="wide"
)


st.title("💰 청년 금융 건강 AI")

st.write(
    "현재 금융상태를 입력하면 "
    "금융 건강도와 위험요인을 분석합니다."
)


st.header("1. 금융정보 입력")


income = st.number_input(
    "월 소득",
    min_value=0,
    value=3000000,
    step=100000
)


fixed_expense = st.number_input(
    "월 고정지출",
    min_value=0,
    value=1200000,
    step=100000
)


variable_expense = st.number_input(
    "월 변동지출",
    min_value=0,
    value=900000,
    step=100000
)


debt_payment = st.number_input(
    "월 대출상환액",
    min_value=0,
    value=500000,
    step=100000
)


savings = st.number_input(
    "현재 저축액",
    min_value=0,
    value=2000000,
    step=100000
)


if st.button("금융상태 분석"):

    st.session_state["analyzed"] = True

if st.session_state.get("analyzed", False):
    metrics = calculate_metrics(
        income,
        fixed_expense,
        variable_expense,
        debt_payment,
        savings
    )

    risk = calculate_risk(metrics)

    st.header("2. 금융 건강 진단")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "월 잉여금",
        f'{metrics["monthly_surplus"]:,.0f}원'
    )

    col2.metric(
        "저축 여력",
        f'{metrics["surplus_rate"]:.1f}%'
    )

    col3.metric(
        "부채상환 비율",
        f'{metrics["debt_service_rate"]:.1f}%'
    )

    col4.metric(
        "비상자금",
        f'{metrics["emergency_months"]:.1f}개월'
    )


    st.header("3. 금융 위험도")

    st.metric(
        "위험 점수",
        f'{risk["score"]} / 100'
    )


    if risk["level"] == "안정":
        st.success("🟢 안정")

    elif risk["level"] == "주의":
        st.warning("🟡 주의")

    else:
        st.error("🔴 위험")

    st.subheader("주요 위험요인")

    if risk["reasons"]:
        for reason in risk["reasons"]:
            st.write("•", reason)
    else:
        st.write(
            "현재 주요 금융 위험요인이 발견되지 않았습니다."
        )

    st.header("4. 12개월 금융상태 전망")

    forecast = forecast_assets(
        savings,
        metrics["monthly_surplus"],
        months=12
    )

    st.line_chart(
        forecast,
        x="month",
        y="asset"
    )

    final_asset = forecast.iloc[-1]["asset"]

    st.metric(
        "12개월 후 예상 금융자산",
        f"{final_asset:,.0f}원"
    )

    st.header("5. What-if 시뮬레이션")

    st.write(
        "소득이나 지출 습관을 변경했을 때 "
        "미래 금융상태가 어떻게 달라지는지 확인해보세요."
    )

    expense_reduction = st.slider(
        "월 변동지출 줄이기",
        min_value=0,
        max_value=1000000,
        value=0,
        step=50000,
        format="%d원"
    )

    income_increase = st.slider(
        "월 소득 늘리기",
        min_value=0,
        max_value=1000000,
        value=0,
        step=50000,
        format="%d원"
    )

    new_income = income + income_increase

    new_variable_expense = max(
        variable_expense - expense_reduction,
        0
    )

    new_metrics = calculate_metrics(
        new_income,
        fixed_expense,
        new_variable_expense,
        debt_payment,
        savings
    )

    new_risk = calculate_risk(new_metrics)

    new_forecast = forecast_assets(
        savings,
        new_metrics["monthly_surplus"],
        months=12
    )

    new_final_asset = new_forecast.iloc[-1]["asset"]

    st.subheader("시뮬레이션 결과")

    before_col, after_col = st.columns(2)

    with before_col:
        st.write("### 현재 상태")

        st.metric(
            "월 잉여금",
            f'{metrics["monthly_surplus"]:,.0f}원'
        )

        st.metric(
            "위험 점수",
            f'{risk["score"]}점'
        )

        st.metric(
            "12개월 후 예상자산",
            f"{final_asset:,.0f}원"
        )

    with after_col:
        st.write("### 변경 후")

        st.metric(
            "월 잉여금",
            f'{new_metrics["monthly_surplus"]:,.0f}원',
            delta=(
                f'{new_metrics["monthly_surplus"] - metrics["monthly_surplus"]:,.0f}원'
            )
        )

        st.metric(
            "위험 점수",
            f'{new_risk["score"]}점',
            delta=f'{new_risk["score"] - risk["score"]}점',
            delta_color="inverse"
        )

        st.metric(
            "12개월 후 예상자산",
            f"{new_final_asset:,.0f}원",
            delta=f"{new_final_asset - final_asset:,.0f}원"
        )

    st.subheader("현재 vs 개선 후 12개월 전망")

    comparison = forecast.copy()

    comparison = comparison.rename(
        columns={
            "asset": "현재 예상자산"
            }
    )

    comparison["개선 후 예상자산"] = new_forecast["asset"]

    st.line_chart(
        comparison,
        x="month",
        y=[
                "현재 예상자산",
                "개선 후 예상자산"
            ]
    )
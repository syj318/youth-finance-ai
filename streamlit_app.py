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
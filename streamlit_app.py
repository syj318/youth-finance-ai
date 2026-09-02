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

st.markdown(
    "나의 현재 금융상태를 진단하고, "
    "미래 금융위험과 개선 가능성을 시뮬레이션 해보세요!"
)
st.divider()

if "income" not in st.session_state:
    st.session_state["income"] = 3000000

if "fixed_expense" not in st.session_state:
    st.session_state["fixed_expense"] = 1200000

if "living_expense" not in st.session_state:
    st.session_state["living_expense"] = 900000

if "monthly_savings" not in st.session_state:
    st.session_state["monthly_savings"] = 300000

if "debt_payment" not in st.session_state:
    st.session_state["debt_payment"] = 500000

if "savings" not in st.session_state:
    st.session_state["savings"] = 2000000

st.header("1. 금융정보 입력")
st.write("테스트용 금융 프로필을 선택하거나 직접 입력할 수 있습니다.")

demo1, demo2, demo3 = st.columns(3)

with demo1:
    if st.button("🟢 안정 사용자"):
        st.session_state["income"] = 4000000
        st.session_state["fixed_expense"] = 1000000
        st.session_state["living_expense"] = 700000
        st.session_state["debt_payment"] = 200000
        st.session_state["monthly_savings"] = 1000000
        st.session_state["savings"] = 10000000
        st.session_state["analyzed"] = True

with demo2:
    if st.button("🟡 주의 사용자"):
        st.session_state["income"] = 3000000
        st.session_state["fixed_expense"] = 1200000
        st.session_state["living_expense"] = 900000
        st.session_state["debt_payment"] = 500000
        st.session_state["monthly_savings"] = 300000
        st.session_state["savings"] = 2000000
        st.session_state["analyzed"] = True

with demo3:
    if st.button("🔴 위험 사용자"):
        st.session_state["income"] = 2500000
        st.session_state["fixed_expense"] = 1300000
        st.session_state["living_expense"] = 900000
        st.session_state["debt_payment"] = 700000
        st.session_state["monthly_savings"] = 0
        st.session_state["savings"] = 500000
        st.session_state["analyzed"] = True


input_col1, input_col2 = st.columns(2)

with input_col1:
    income = st.number_input(
        "💵 월 소득",
        min_value=0,
        step=100000,
        key="income"
    )

    fixed_expense = st.number_input(
        "🏠 월 고정지출",
        min_value=0,
        step=100000,
        key="fixed_expense"
    )

    monthly_savings = st.number_input(
        "🏦 월 저축금액",
        min_value=0,
        step=50000,
        key="monthly_savings"
    )

with input_col2:
    living_expense = st.number_input(
        "🛒 월 생활비",
        min_value=0,
        step=100000,
        key="living_expense"
    )

    debt_payment = st.number_input(
        "💳 월 대출상환액",
        min_value=0,
        step=100000,
        key="debt_payment"
    )

    savings = st.number_input(
        "💰 현재 저축액",
        min_value=0,
        step=100000,
        key="savings"
    )

monthly_outflow = (
    fixed_expense
    + living_expense
    + debt_payment
    + monthly_savings
)

expected_balance = income - monthly_outflow

st.subheader("월 현금흐름 확인")

cash_col1, cash_col2, cash_col3 = st.columns(3)

cash_col1.metric(
    "월 소득",
    f"{income:,.0f}원"
)

cash_col2.metric(
    "월 지출·저축 합계",
    f"{monthly_outflow:,.0f}원"
)

cash_col3.metric(
    "월 잔여금",
    f"{expected_balance:,.0f}원"
)

if expected_balance < 0:
    st.error(
        f"⚠️ 현재 입력값 기준으로 매월 "
        f"{abs(expected_balance):,.0f}원이 부족합니다."
    )

elif expected_balance == 0:
    st.warning(
        "월 소득이 지출과 저축으로 모두 사용되고 있습니다. "
        "예상치 못한 지출에 대비할 여유자금이 없습니다."
    )

else:
    st.success(
        f"현재 계획대로라면 매월 "
        f"{expected_balance:,.0f}원의 여유자금이 남습니다."
    )


if st.button(
    "🔍 금융상태 분석하기",
    type="primary",
    use_container_width=True
):
    if income == 0:
        st.error("월 소득을 입력해주세요.")
        st.session_state["analyzed"] = False

    elif expected_balance < 0:
        st.warning(
            "현재 소득보다 지출과 저축 계획이 큽니다. "
            "분석 결과에서 적자 상태로 진단됩니다."
        )
        st.session_state["analyzed"] = True

    else:
        st.session_state["analyzed"] = True
        
if st.session_state.get("analyzed", False):
    metrics = calculate_metrics(
        income,
        fixed_expense,
        living_expense,
        debt_payment,
        monthly_savings,
        savings
    )

    risk = calculate_risk(metrics)

    health_score = 100 - risk["score"]

    st.header("2. 금융 건강 진단")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "월 잉여금",
        f'{metrics["monthly_surplus"]:,.0f}원'
    )

    col2.metric(
        "월 저축률",
        f'{metrics["savings_rate"]:.1f}%'
    )

    col3.metric(
        "부채상환 비율",
        f'{metrics["debt_service_rate"]:.1f}%'
    )

    col4.metric(
        "비상자금",
        f'{metrics["emergency_months"]:.1f}개월'
    )


    st.header("3. 금융 건강도")

    health_col1, health_col2 = st.columns(2)

    with health_col1:
        st.metric(
            "💚 금융 건강점수",
            f"{health_score} / 100"
        )

    with health_col2:
        st.metric(
            "⚠️ 금융 위험점수",
            f"{risk['score']} / 100"
        )
    
    st.progress(health_score)

    if risk["level"] == "안정":
        st.success("🟢 안정")

    elif risk["level"] == "주의":
        st.warning("🟡 주의")

    else:
        st.error("🔴 위험")

    if health_score >= 80:
        st.write("현재 전반적인 금융상태가 안정적입니다.")

    elif health_score >= 50:
        st.write(
            "일부 금융지표에 개선이 필요합니다. "
            "지출과 부채상환 부담을 점검해보세요."
        )
    
    else:
        st.write(
            "현재 금융 위험도가 높은 상태입니다. "
            "지출 구조와 비상자금 확보를 우선적으로 점검할 필요가 있습니다."
        )

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
        monthly_savings,
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
        "월 생활비 줄이기",
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

    new_living_expense = max(
        living_expense - expense_reduction,
        0
    )

    new_monthly_savings = (
        monthly_savings 
        + expense_reduction
        + income_increase 
    )

    new_metrics = calculate_metrics(
        new_income,
        fixed_expense,
        new_living_expense,
        debt_payment,
        new_monthly_savings,
        savings
    )

    new_risk = calculate_risk(new_metrics)
    new_health_score = 100 - new_risk["score"]

    new_forecast = forecast_assets(
        savings,
        new_monthly_savings,
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
            "금융 건강점수",
            f"{health_score}점"
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
            "금융 건강점수",
            f"{new_health_score}점",
            delta=f"{new_health_score - health_score}점"
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
st.divider()

st.caption(
    "※ 본 서비스는 금융상태 진단 및 금융교육을 위한 MVP 프로토타입입니다. "
    "분석 결과는 실제 투자, 대출 또는 금융상품 가입에 대한 전문적인 금융 자문을 의미하지 않습니다."
)
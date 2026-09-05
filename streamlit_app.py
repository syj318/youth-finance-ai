import streamlit as st
import pandas as pd
import html
from dotenv import load_dotenv

load_dotenv(".env")

from src.metrics import calculate_metrics
from src.risk_engine import calculate_risk
from src.forecast import forecast_assets
from src.optimizer import find_improvement_plans
from src.health_forecast import (
    forecast_financial_health,
    forecast_plan_health,
)
from src.ai_advisor import generate_ai_advice, generate_ai_chat_reply
from src.financial_product_api import fetch_saving_products, fetch_deposit_products
from src.recommendation_engine import get_personalized_recommendations


st.set_page_config(
    page_title="MONEYFIT | 나에게 맞는 금융 건강관리",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -----------------------------
# Design system
# -----------------------------
st.markdown(
    """
    <style>
        :root {
            --mf-bg: #F6F9FF;
            --mf-surface: #FFFFFF;
            --mf-surface-soft: #F1F6FF;
            --mf-text: #0F172A;
            --mf-heading: #0A1F44;
            --mf-muted: #56647A;
            --mf-border: #D9E4F5;
            --mf-blue: #1769E0;
            --mf-blue-deep: #0B3E91;
            --mf-blue-dark: #082E6B;
            --mf-blue-soft: #EAF2FF;
            --mf-positive: #137A54;
            --mf-warning: #A86514;
            --mf-danger: #B33E4A;
        }

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Pretendard",
                         "Noto Sans KR", "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(69, 132, 255, 0.10), transparent 28rem),
                linear-gradient(180deg, #F8FBFF 0%, #F5F8FD 100%);
            color: var(--mf-text);
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.25rem;
            padding-bottom: 4rem;
        }

        /* Sidebar is not used in this version */
        [data-testid="stSidebar"] {
            display: none;
        }

        h1, h2, h3, h4, p, label {
            color: var(--mf-text);
        }

        h1, h2, h3 {
            letter-spacing: -0.035em;
        }

        h1 {
            font-size: 2.75rem !important;
            line-height: 1.14 !important;
        }

        h2 {
            font-size: 1.65rem !important;
        }

        h3 {
            font-size: 1.1rem !important;
        }

        p, .stMarkdown, [data-testid="stCaptionContainer"] {
            line-height: 1.65;
        }

        /* top navigation */
        .mf-topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding: 0.2rem 0.15rem;
        }

        .mf-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .mf-brand-mark {
            width: 40px;
            height: 40px;
            border-radius: 13px;
            background: linear-gradient(145deg, #1769E0, #0B3E91);
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95rem;
            font-weight: 850;
            box-shadow: 0 8px 22px rgba(23, 105, 224, 0.22);
        }

        .mf-brand-name {
            font-size: 1.15rem;
            font-weight: 850;
            color: var(--mf-heading);
            letter-spacing: -0.035em;
        }

        .mf-brand-sub {
            font-size: 0.74rem;
            color: #6B7890;
            margin-top: 1px;
        }

        .mf-top-label {
            color: #54709A;
            background: #EDF4FF;
            border: 1px solid #D8E7FF;
            border-radius: 999px;
            padding: 0.45rem 0.8rem;
            font-size: 0.76rem;
            font-weight: 750;
        }

        /* hero */
        .mf-hero {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at 88% 22%, rgba(120, 178, 255, 0.34), transparent 18rem),
                linear-gradient(135deg, #0A3E91 0%, #1769E0 55%, #3F8BFA 100%);
            border: 1px solid rgba(255,255,255,0.20);
            border-radius: 30px;
            padding: 3rem 3.1rem;
            margin-bottom: 1.5rem;
            color: white;
            box-shadow: 0 18px 48px rgba(14, 71, 160, 0.20);
        }

        .mf-hero:after {
            content: "";
            position: absolute;
            width: 280px;
            height: 280px;
            right: -90px;
            bottom: -120px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
        }

        .mf-hero-eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.68rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.13);
            border: 1px solid rgba(255,255,255,0.20);
            font-size: 0.74rem;
            font-weight: 750;
            letter-spacing: 0.06em;
            color: #EAF3FF;
            margin-bottom: 1rem;
        }

        .mf-hero h1 {
            color: #FFFFFF !important;
            margin: 0 0 0.9rem 0 !important;
            max-width: 820px;
            text-shadow: 0 1px 1px rgba(0,0,0,0.05);
        }

        .mf-hero p {
            color: #EAF2FF !important;
            font-size: 1.04rem;
            font-weight: 480;
            line-height: 1.75;
            max-width: 820px;
            margin: 0;
        }

        .mf-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.58rem;
            margin-top: 1.55rem;
        }

        .mf-chip {
            border: 1px solid rgba(255,255,255,0.22);
            background: rgba(255,255,255,0.11);
            color: #FFFFFF;
            border-radius: 999px;
            padding: 0.45rem 0.76rem;
            font-size: 0.79rem;
            font-weight: 620;
        }

        /* section header */
        .mf-section {
            margin-top: 2.35rem;
            margin-bottom: 1rem;
        }

        .mf-eyebrow {
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.09em;
            color: #3870C7;
            margin-bottom: 0.32rem;
        }

        .mf-section-title {
            font-size: 1.65rem;
            font-weight: 850;
            color: var(--mf-heading);
            letter-spacing: -0.04em;
            margin-bottom: 0.32rem;
        }

        .mf-section-desc {
            font-size: 0.94rem;
            font-weight: 450;
            line-height: 1.65;
            color: var(--mf-muted);
            margin-bottom: 1rem;
        }

        /* main input panel */
        .mf-input-head {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.35rem;
        }

        .mf-input-title {
            font-size: 1.25rem;
            font-weight: 850;
            color: var(--mf-heading);
            letter-spacing: -0.035em;
        }

        .mf-input-desc {
            color: var(--mf-muted);
            font-size: 0.86rem;
            margin-top: 0.2rem;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255,255,255,0.98);
            border: 1px solid #D5E3F7 !important;
            border-radius: 22px !important;
            box-shadow: 0 10px 34px rgba(32, 86, 160, 0.07);
        }

        /* cards */
        .mf-card {
            background: #FFFFFF;
            border: 1px solid #D8E4F4;
            border-radius: 20px;
            padding: 1.18rem 1.22rem;
            box-shadow: 0 7px 22px rgba(31, 74, 135, 0.055);
            min-height: 126px;
        }

        .mf-card-label {
            color: #61708A;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.62rem;
        }

        .mf-card-value {
            color: #0B1F40;
            font-size: 1.65rem;
            font-weight: 850;
            letter-spacing: -0.04em;
            line-height: 1.15;
        }

        .mf-card-sub {
            color: #697790;
            font-size: 0.78rem;
            font-weight: 460;
            margin-top: 0.55rem;
            line-height: 1.5;
        }

        /* 같은 행의 KPI 카드 높이 고정 */
        .mf-card {
            height: 138px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        .mf-card-sub {
            min-height: 2.35rem;
        }

        .mf-card-positive { border-top: 4px solid #2A9B72; }
        .mf-card-warning { border-top: 4px solid #D89A37; }
        .mf-card-danger  { border-top: 4px solid #CF5A68; }
        .mf-card-neutral { border-top: 4px solid #4E84D6; }

        .mf-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.42rem 0.72rem;
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
        }

        .mf-status-positive {
            background: #E8F7F1;
            color: #176A4E;
        }

        .mf-status-warning {
            background: #FFF4E2;
            color: #8A5810;
        }

        .mf-status-danger {
            background: #FDECEF;
            color: #A33A47;
        }

        .mf-status-neutral {
            background: #EAF2FF;
            color: #265CA7;
        }

        .mf-feature-card {
            background: #FFFFFF;
            border: 1px solid #D7E4F5;
            border-radius: 20px;
            padding: 1.3rem;
            min-height: 158px;
            box-shadow: 0 6px 18px rgba(32, 86, 160, 0.045);
        }

        .mf-feature-kicker {
            color: #4E7FC7;
            font-size: 0.72rem;
            font-weight: 820;
            letter-spacing: 0.07em;
        }

        .mf-feature-title {
            color: #0B2147;
            font-size: 1.03rem;
            font-weight: 850;
            margin-top: 0.45rem;
            margin-bottom: 0.45rem;
        }

        .mf-feature-desc {
            color: #5F6E86;
            font-size: 0.84rem;
            line-height: 1.62;
        }

        .mf-callout {
            background: #FFFFFF;
            border: 1px solid #D8E6F8;
            border-left: 5px solid #2E73DD;
            border-radius: 15px;
            padding: 1rem 1.1rem;
            color: #263A59;
            font-size: 0.92rem;
            font-weight: 470;
            line-height: 1.65;
            margin: 0.7rem 0 1rem 0;
            box-shadow: 0 4px 16px rgba(32, 86, 160, 0.035);
        }

        /* native streamlit widgets */
        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #D9E5F4;
            border-radius: 17px;
            padding: 1rem 1.05rem;
            box-shadow: 0 5px 16px rgba(28, 70, 128, 0.04);
        }

        div[data-testid="stMetric"] label {
            color: #596A83 !important;
            font-size: 0.8rem !important;
            font-weight: 650 !important;
        }

        div[data-testid="stMetricValue"] {
            color: #0C1E3A !important;
            font-weight: 850 !important;
            letter-spacing: -0.035em !important;
        }

        div[data-testid="stMetricDelta"] {
            font-weight: 650 !important;
        }

        .stButton > button {
            border-radius: 12px;
            min-height: 44px;
            border: 1px solid #CADAF0;
            background: #FFFFFF;
            color: #174C93;
            font-weight: 760;
        }

        .stButton > button:hover {
            border-color: #6F9DDD;
            color: #0B3E91;
            background: #F7FAFF;
        }

        .stButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"] {
            min-height: 52px !important;
            background: linear-gradient(135deg, #0B4FA8, #083D82) !important;
            border: 1px solid #073873 !important;
            color: #FFFFFF !important;
            box-shadow: 0 8px 20px rgba(8, 61, 130, 0.25);
        }

        .stButton > button[kind="primary"] p,
        button[data-testid="stBaseButton-primary"] p {
            color: #FFFFFF !important;
            font-size: 1rem !important;
            font-weight: 820 !important;
        }

        .stButton > button[kind="primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover {
            background: linear-gradient(135deg, #083F89, #062F66) !important;
            border-color: #062F66 !important;
            color: #FFFFFF !important;
        }

        /* Bigger and more readable inputs */
        div[data-baseweb="input"] > div {
            min-height: 48px !important;
            border-radius: 12px !important;
            border: 1px solid #C9D8EC !important;
            background: #FFFFFF !important;
        }

        div[data-baseweb="input"] input {
            font-size: 0.98rem !important;
            font-weight: 620 !important;
            color: #10213D !important;
        }

        label[data-testid="stWidgetLabel"] p {
            color: #233958 !important;
            font-size: 0.87rem !important;
            font-weight: 730 !important;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #D8E5F5;
            border-radius: 17px;
            background: #FFFFFF;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(32, 86, 160, 0.035);
        }

        [role="tablist"] {
            display: flex !important;
            width: 100% !important;
            gap: 0.7rem;
            padding: 0.7rem;
            border: 1px solid #C9D8EC;
            border-radius: 18px;
            background: #F4F8FD;
            box-shadow: 0 5px 16px rgba(32, 86, 160, 0.06);
        }

        [data-testid="stTab"] {
            flex: 0 0 calc(20% - 0.56rem) !important;
            width: calc(20% - 0.56rem) !important;
            max-width: calc(20% - 0.56rem) !important;
            justify-content: center !important;
            min-height: 70px;
            padding: 0.9rem 1.25rem;
            border: 1px solid #C9D8EC;
            border-bottom: 1px solid #C9D8EC !important;
            border-radius: 13px;
            background: #FFFFFF;
            color: #385376;
            font-weight: 780;
            font-size: 1.12rem;
            transition: background 0.18s ease, border-color 0.18s ease,
                color 0.18s ease, box-shadow 0.18s ease;
        }

        [data-testid="stTab"]:hover {
            border-color: #4A7FC1;
            background: #EAF2FC;
            color: #174F91;
        }

        [data-testid="stTab"][aria-selected="true"] {
            border-color: #1F64AE;
            border-bottom-color: #1F64AE !important;
            background: #1F64AE;
            color: #FFFFFF;
            box-shadow: 0 4px 11px rgba(31, 100, 174, 0.24);
        }

        [data-testid="stTab"][aria-selected="true"] p {
            color: #FFFFFF !important;
            font-weight: 820 !important;
        }

        [data-testid="stTab"] p {
            width: 100%;
            text-align: center;
            font-size: 1.12rem !important;
        }

        .react-aria-SelectionIndicator {
            display: none !important;
        }

        [data-testid="stChatMessage"] {
            background: #FFFFFF;
            border: 1px solid #D8E5F5;
            border-radius: 17px;
            padding: 0.35rem 0.58rem;
            margin-bottom: 0.6rem;
        }

        .mf-divider {
            height: 1px;
            background: #DCE6F3;
            margin: 2.2rem 0 1rem 0;
        }

        .mf-footer {
            color: #6A7890;
            font-size: 0.76rem;
            line-height: 1.65;
            padding: 1rem 0 2rem 0;
        }


        /* Remove the black Streamlit chrome at the top */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        /* Expanders: never use a dark/black summary bar */
        div[data-testid="stExpander"] details > summary {
            background: #F5F9FF !important;
            color: #12315D !important;
            border-bottom: 1px solid #D9E6F5 !important;
            min-height: 52px;
            padding: 0.75rem 1rem !important;
        }

        div[data-testid="stExpander"] details > summary:hover {
            background: #ECF4FF !important;
            color: #0B3E91 !important;
        }

        div[data-testid="stExpander"] details > summary p,
        div[data-testid="stExpander"] details > summary span {
            color: #12315D !important;
            font-weight: 780 !important;
        }

        div[data-testid="stExpander"] details > summary svg {
            fill: #2B67B5 !important;
            color: #2B67B5 !important;
        }

        /* AI coach premium grid */
        .mf-coach-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-top: 0.4rem;
            margin-bottom: 1rem;
        }

        .mf-coach-card {
            background: #FFFFFF;
            border: 1px solid #D6E4F6;
            border-radius: 18px;
            padding: 1.2rem 1.25rem;
            box-shadow: 0 7px 22px rgba(28, 75, 145, 0.055);
            min-height: 180px;
        }

        .mf-coach-card.blue {
            background: linear-gradient(180deg, #F4F8FF 0%, #EDF4FF 100%);
            border-color: #C9DDF8;
        }

        .mf-coach-card.yellow {
            background: linear-gradient(180deg, #FFFDF4 0%, #FFF9DD 100%);
            border-color: #F1E1A8;
        }

        .mf-coach-card.green {
            background: linear-gradient(180deg, #F4FBF8 0%, #EAF8F1 100%);
            border-color: #CBE9D9;
        }

        .mf-coach-card.soft {
            background: linear-gradient(180deg, #F8FAFD 0%, #F2F6FB 100%);
            border-color: #D7E1EE;
        }

        .mf-coach-kicker {
            color: #3A6EBA;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.07em;
            margin-bottom: 0.42rem;
        }

        .mf-coach-title {
            color: #102A50;
            font-size: 1.05rem;
            font-weight: 850;
            letter-spacing: -0.025em;
            margin-bottom: 0.75rem;
        }

        .mf-coach-body {
            color: #253A59;
            font-size: 0.91rem;
            font-weight: 500;
            line-height: 1.72;
        }

        .mf-coach-actions {
            margin: 0;
            padding-left: 1.25rem;
        }

        .mf-coach-actions li {
            color: #253A59;
            margin-bottom: 0.58rem;
            padding-left: 0.15rem;
            line-height: 1.58;
            font-weight: 520;
        }

        /* Chat input: keep it bright and legible even on a dark system/browser theme */
        [data-testid="stBottomBlockContainer"] {
            background: rgba(246, 249, 255, 0.97) !important;
            border-top: 1px solid #D9E5F4 !important;
            box-shadow: 0 -6px 24px rgba(29, 70, 130, 0.05) !important;
            padding-top: 0.65rem !important;
        }

        [data-testid="stChatInput"] {
            background: #FFFFFF !important;
            border: 1px solid #BFD2EA !important;
            border-radius: 15px !important;
            box-shadow: 0 5px 18px rgba(28, 75, 145, 0.08) !important;
        }

        [data-testid="stChatInput"] textarea {
            background: #FFFFFF !important;
            color: #0F213D !important;
            caret-color: #1769E0 !important;
            font-size: 0.96rem !important;
            font-weight: 560 !important;
        }

        [data-testid="stChatInput"] textarea::placeholder {
            color: #7A879B !important;
            opacity: 1 !important;
        }

        [data-testid="stChatInput"] button {
            background: #1769E0 !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
        }

        [data-testid="stChatInput"] button svg {
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
        }

        @media (max-width: 900px) {
            .mf-coach-grid {
                grid-template-columns: 1fr;
            }

            .mf-coach-card {
                min-height: auto;
            }
        }


        /* Inline finance coach chat area */
        .mf-chat-shell {
            background: #FFFFFF;
            border: 1px solid #D6E4F6;
            border-radius: 20px;
            padding: 1.1rem 1.15rem 0.85rem 1.15rem;
            box-shadow: 0 7px 22px rgba(28, 75, 145, 0.055);
            margin-top: 0.75rem;
            margin-bottom: 1.35rem;
        }

        .mf-chat-title {
            color: #102A50;
            font-size: 1rem;
            font-weight: 850;
            letter-spacing: -0.025em;
            margin-bottom: 0.2rem;
        }

        .mf-chat-desc {
            color: #66758D;
            font-size: 0.84rem;
            line-height: 1.55;
            margin-bottom: 0.8rem;
        }

        /* text input used instead of sticky st.chat_input */
        [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid #D6E4F6;
            border-radius: 18px;
            padding: 1rem 1rem 0.4rem 1rem;
            box-shadow: 0 6px 20px rgba(28, 75, 145, 0.045);
        }

        [data-testid="stForm"] div[data-baseweb="input"] > div {
            background: #FFFFFF !important;
            border: 1px solid #BDD0EA !important;
            min-height: 50px !important;
            border-radius: 13px !important;
        }

        [data-testid="stForm"] div[data-baseweb="input"] input {
            color: #0F213D !important;
            background: #FFFFFF !important;
            font-size: 0.96rem !important;
            font-weight: 560 !important;
        }

        [data-testid="stForm"] div[data-baseweb="input"] input::placeholder {
            color: #7C899D !important;
            opacity: 1 !important;
        }

        [data-testid="stForm"] button {
            min-height: 50px !important;
            border: 1px solid #073873 !important;
            background: linear-gradient(135deg, #0B4FA8, #083D82) !important;
            color: #FFFFFF !important;
            box-shadow: 0 7px 18px rgba(8, 61, 130, 0.22) !important;
        }

        [data-testid="stForm"] button p,
        [data-testid="stForm"] button span {
            color: #FFFFFF !important;
            font-size: 1rem !important;
            font-weight: 820 !important;
        }

        [data-testid="stForm"] button:hover {
            border-color: #062F66 !important;
            background: linear-gradient(135deg, #083F89, #062F66) !important;
            color: #FFFFFF !important;
        }

        [data-testid="stForm"] button[kind="primaryFormSubmit"] {
            background: linear-gradient(135deg, #1769E0, #0F56C5) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            min-height: 46px !important;
            font-weight: 780 !important;
        }

        /* Make chat history readable */
        [data-testid="stChatMessage"] {
            background: #FFFFFF !important;
            border: 1px solid #D8E5F5 !important;
            color: #10213D !important;
            border-radius: 17px !important;
            box-shadow: 0 4px 14px rgba(28, 75, 145, 0.035);
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div {
            color: #10213D !important;
        }

        [data-testid="stChatMessage"] [data-testid="stStatusWidget"] {
            background: #F4F8FF !important;
            border: 1px solid #D7E6FA !important;
            border-radius: 12px !important;
            color: #315C97 !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        @media (max-width: 900px) {
            .block-container {
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }

            .mf-top-label {
                display: none;
            }

            .mf-hero {
                padding: 2rem 1.55rem;
                border-radius: 23px;
            }

            .mf-hero h1 {
                font-size: 2rem !important;
            }

            .mf-hero p {
                font-size: 0.95rem;
            }

            .mf-card-value {
                font-size: 1.35rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_financial_products():
    saving_result = fetch_saving_products(timeout=30)
    deposit_result = fetch_deposit_products(timeout=30)
    return saving_result, deposit_result


def money(value):
    return f"{value:,.0f}원"


def section_header(eyebrow, title, description=None):
    desc_html = (
        f'<div class="mf-section-desc">{description}</div>'
        if description
        else ""
    )
    st.markdown(
        f"""
        <div class="mf-section">
            <div class="mf-eyebrow">{eyebrow}</div>
            <div class="mf-section-title">{title}</div>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_tone(level):
    if level in {"매우 안정", "안정", "양호"}:
        return "positive"
    if level == "주의":
        return "warning"
    if level in {"위험", "매우 위험"}:
        return "danger"
    return "neutral"


def metric_card(label, value, subtitle="", tone="neutral"):
    st.markdown(
        f"""
        <div class="mf-card mf-card-{tone}">
            <div class="mf-card-label">{label}</div>
            <div class="mf-card-value">{value}</div>
            <div class="mf-card-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text, tone="neutral"):
    st.markdown(
        f'<span class="mf-status mf-status-{tone}">{text}</span>',
        unsafe_allow_html=True,
    )


# -----------------------------
# Session defaults
# -----------------------------
defaults = {
    "income": 3000000,
    "fixed_expense": 1200000,
    "living_expense": 900000,
    "monthly_savings": 300000,
    "debt_payment": 500000,
    "savings": 2000000,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _normalize_money_input(value_key, display_key, synced_key):
    """쉼표와 원 단위를 허용하면서 계산용 정수 상태를 유지한다."""
    raw_value = str(st.session_state.get(display_key, ""))
    digits = raw_value.replace(",", "").replace("원", "").replace(" ", "")

    if digits.isdigit():
        value = int(digits)
        st.session_state[value_key] = value
        st.session_state[synced_key] = value
        st.session_state[display_key] = f"{value:,}"
        st.session_state.pop(f"{display_key}_error", None)
        return

    previous_value = int(st.session_state.get(value_key, 0))
    st.session_state[display_key] = f"{previous_value:,}"
    st.session_state[f"{display_key}_error"] = True


def money_input(label, key):
    """천 단위 쉼표가 표시되는 원화 입력 위젯을 반환한다."""
    display_key = f"{key}_won_display"
    synced_key = f"{key}_won_synced"
    current_value = int(st.session_state.get(key, 0))

    if st.session_state.get(synced_key) != current_value:
        st.session_state[display_key] = f"{current_value:,}"
        st.session_state[synced_key] = current_value

    st.text_input(
        f"{label} (원)",
        key=display_key,
        placeholder="예: 3,000,000",
        on_change=_normalize_money_input,
        args=(key, display_key, synced_key),
    )

    if st.session_state.pop(f"{display_key}_error", False):
        st.caption("숫자, 쉼표 또는 '원'만 입력할 수 있습니다.")
    else:
        st.caption(f"입력 금액: {int(st.session_state[key]):,}원")

    return int(st.session_state[key])


# -----------------------------
# Top bar + Hero
# -----------------------------
st.markdown(
    """
    <div class="mf-topbar">
        <div class="mf-brand">
            <div class="mf-brand-mark">M</div>
            <div>
                <div class="mf-brand-name">MONEYFIT</div>
                <div class="mf-brand-sub">Personal Finance Health Platform</div>
            </div>
        </div>
        <div class="mf-top-label">금융 진단 · 시뮬레이션 · 상품 매칭</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="mf-hero">
        <div class="mf-hero-eyebrow">PERSONAL FINANCE HEALTH</div>
        <h1>내 돈의 흐름을 한눈에 보고,<br>더 나은 다음 선택을 만드세요.</h1>
        <p>
            현재 금융상태를 이해하기 쉬운 점수로 진단하고,
            앞으로의 변화와 실천 가능한 개선안, 실제 금융상품까지 연결합니다.
        </p>
        <div class="mf-chip-row">
            <span class="mf-chip">금융 건강 진단</span>
            <span class="mf-chip">미래 시나리오</span>
            <span class="mf-chip">What-if</span>
            <span class="mf-chip">맞춤 개선안</span>
            <span class="mf-chip">금융상품 매칭</span>
            <span class="mf-chip">AI 금융코치</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Main financial input panel
# -----------------------------
section_header(
    "START HERE",
    "내 금융정보 입력",
    "현재 상황에 가까운 금액을 입력하면 아래 분석 결과가 즉시 갱신됩니다.",
)

with st.container(border=True):
    st.markdown(
        """
        <div class="mf-input-head">
            <div>
                <div class="mf-input-title">빠른 프로필</div>
                <div class="mf-input-desc">데모를 선택하거나 직접 값을 입력할 수 있습니다.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    demo1, demo2, demo3 = st.columns(3)

    with demo1:
        if st.button("안정형 프로필", use_container_width=True):
            st.session_state["income"] = 4000000
            st.session_state["fixed_expense"] = 1000000
            st.session_state["living_expense"] = 700000
            st.session_state["debt_payment"] = 200000
            st.session_state["monthly_savings"] = 1000000
            st.session_state["savings"] = 10000000
            st.session_state["analyzed"] = True
            st.rerun()

    with demo2:
        if st.button("주의형 프로필", use_container_width=True):
            st.session_state["income"] = 3000000
            st.session_state["fixed_expense"] = 1200000
            st.session_state["living_expense"] = 900000
            st.session_state["debt_payment"] = 500000
            st.session_state["monthly_savings"] = 300000
            st.session_state["savings"] = 2000000
            st.session_state["analyzed"] = True
            st.rerun()

    with demo3:
        if st.button("위험형 프로필", use_container_width=True):
            st.session_state["income"] = 2500000
            st.session_state["fixed_expense"] = 1300000
            st.session_state["living_expense"] = 900000
            st.session_state["debt_payment"] = 700000
            st.session_state["monthly_savings"] = 0
            st.session_state["savings"] = 500000
            st.session_state["analyzed"] = True
            st.rerun()

    st.markdown("---")

    # First row: income / fixed / living
    input1, input2, input3 = st.columns(3, gap="large")

    with input1:
        income = money_input("월 소득", "income")

    with input2:
        fixed_expense = money_input("월 고정지출", "fixed_expense")

    with input3:
        living_expense = money_input("월 생활비", "living_expense")

    # Second row: debt / savings contribution / current savings
    input4, input5, input6 = st.columns(3, gap="large")

    with input4:
        debt_payment = money_input("월 대출상환액", "debt_payment")

    with input5:
        monthly_savings = money_input("월 저축금액", "monthly_savings")

    with input6:
        savings = money_input("현재 저축액", "savings")

    monthly_outflow = (
        fixed_expense
        + living_expense
        + debt_payment
        + monthly_savings
    )
    expected_balance = income - monthly_outflow

    st.markdown("#### 입력값 요약")
    sum1, sum2, sum3 = st.columns(3)

    sum1.metric("월 소득", money(income))
    sum2.metric("월 지출·저축 합계", money(monthly_outflow))
    sum3.metric("월 잔여금", money(expected_balance))

    if expected_balance < 0:
        st.error(
            f"현재 입력값 기준으로 매월 {abs(expected_balance):,.0f}원이 부족합니다. "
            "분석에서는 적자 상태로 반영됩니다."
        )
    elif expected_balance == 0:
        st.warning(
            "현재 입력값 기준 월 잔여금이 없습니다. 예상치 못한 지출에 대비할 여유가 적습니다."
        )
    else:
        st.success(
            f"현재 입력값 기준 매월 {expected_balance:,.0f}원의 여유자금이 남습니다."
        )

    analyze_clicked = st.button(
        "금융상태 분석 시작",
        type="primary",
        use_container_width=True,
    )

    if analyze_clicked:
        st.session_state["financial_chat_history"] = []

        if income == 0:
            st.error("월 소득을 입력해 주세요.")
            st.session_state["analyzed"] = False
        else:
            st.session_state["analyzed"] = True
            st.rerun()


# -----------------------------
# Pre-analysis landing
# -----------------------------
if not st.session_state.get("analyzed", False):
    section_header(
        "HOW IT WORKS",
        "복잡한 금융 데이터를, 실행 가능한 다음 행동으로.",
        "위 입력 영역에서 현재 금융정보를 입력한 뒤 분석을 시작해 보세요.",
    )

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        st.markdown(
            """
            <div class="mf-feature-card">
                <div class="mf-feature-kicker">01 · DIAGNOSE</div>
                <div class="mf-feature-title">금융 건강 진단</div>
                <div class="mf-feature-desc">
                    현금흐름, 부채, 저축, 비상자금, 지출 구조를 함께 봅니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f2:
        st.markdown(
            """
            <div class="mf-feature-card">
                <div class="mf-feature-kicker">02 · FORECAST</div>
                <div class="mf-feature-title">미래 상태 전망</div>
                <div class="mf-feature-desc">
                    현재 행동이 이어질 때 금융 건강과 자산의 변화를 시나리오로 확인합니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f3:
        st.markdown(
            """
            <div class="mf-feature-card">
                <div class="mf-feature-kicker">03 · OPTIMIZE</div>
                <div class="mf-feature-title">맞춤 개선안</div>
                <div class="mf-feature-desc">
                    생활비, 소득, 저축의 조합을 탐색해 위험을 낮출 수 있는 행동을 제안합니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f4:
        st.markdown(
            """
            <div class="mf-feature-card">
                <div class="mf-feature-kicker">04 · MATCH</div>
                <div class="mf-feature-title">금융상품 연결</div>
                <div class="mf-feature-desc">
                    금융감독원 공개 데이터를 바탕으로 현재 상태에 맞는 실제 상품을 비교합니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="mf-footer">
            MONEYFIT은 개인 금융상태를 이해하고 개선 방향을 탐색하기 위한 금융 건강관리 서비스입니다.
            분석 결과는 전문적인 금융 자문이나 특정 금융상품 가입 권유를 의미하지 않습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# -----------------------------
# Analysis
# -----------------------------
metrics = calculate_metrics(
    income,
    fixed_expense,
    living_expense,
    debt_payment,
    monthly_savings,
    savings,
)

risk = calculate_risk(metrics)
health_score = max(0, min(100, 100 - risk["score"]))
risk_tone = status_tone(risk["level"])


diagnosis_tab, plan_tab, forecast_tab, product_tab, ai_tab = st.tabs(
    [
        "금융진단",
        "개선계획",
        "미래전망",
        "금융상품",
        "AI 금융코치",
    ]
)


with diagnosis_tab:
    section_header(
        "OVERVIEW",
        "오늘의 금융 상태",
        "현재 입력값을 기반으로 가장 중요한 지표를 한눈에 정리했습니다.",
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        metric_card(
            "금융 건강점수",
            f"{health_score:.1f}",
            "100점 만점 · 높을수록 안정적",
            risk_tone,
        )

    with k2:
        surplus_tone = "positive" if metrics["monthly_surplus"] > 0 else (
            "danger" if metrics["monthly_surplus"] < 0 else "warning"
        )
        metric_card(
            "월 잉여금",
            money(metrics["monthly_surplus"]),
            "소득에서 지출·저축을 제외한 금액",
            surplus_tone,
        )

    with k3:
        metric_card(
            "비상자금",
            f'{metrics["emergency_months"]:.1f}개월',
            "현재 지출 기준 버틸 수 있는 기간",
            "neutral",
        )

    with k4:
        metric_card(
            "위험등급",
            risk["level"],
            f'위험점수 {risk["score"]:.1f} / 100',
            risk_tone,
        )


    # -----------------------------
    # Financial diagnosis
    # -----------------------------
    section_header(
        "DIAGNOSIS",
        "금융 건강 진단",
        "핵심 비율과 위험영역을 함께 보고, 점수가 낮아진 이유를 추적합니다.",
    )

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("월 잉여금", money(metrics["monthly_surplus"]))
    d2.metric("월 저축률", f'{metrics["savings_rate"]:.1f}%')
    d3.metric("부채상환 비율", f'{metrics["debt_service_rate"]:.1f}%')
    d4.metric("비상자금", f'{metrics["emergency_months"]:.1f}개월')

    st.markdown("<br>", unsafe_allow_html=True)
    status_badge(f"현재 위험등급 · {risk['level']}", risk_tone)
    st.progress(health_score / 100)

    if health_score >= 80:
        st.markdown(
            '<div class="mf-callout">현재 전반적인 금융상태가 안정적입니다. '
            '현재의 현금흐름과 저축 습관을 유지하는 것이 중요합니다.</div>',
            unsafe_allow_html=True,
        )
    elif health_score >= 50:
        st.markdown(
            '<div class="mf-callout">일부 금융지표에 개선 여지가 있습니다. '
            '지출 구조와 부채상환 부담, 저축 여력을 함께 점검해 보세요.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mf-callout">현재 금융 위험도가 높은 편입니다. '
            '지출 구조와 현금흐름 안정, 비상자금 확보를 우선적으로 점검할 필요가 있습니다.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("### 주요 위험요인")
    if risk["reasons"]:
        for reason in risk["reasons"]:
            st.write("•", reason)
    else:
        st.write("현재 주요 금융 위험요인이 발견되지 않았습니다.")

    st.markdown("### 영역별 위험 분석")

    domain_labels = {
        "cashflow": "현금흐름",
        "debt": "부채",
        "saving": "저축",
        "emergency": "비상자금",
        "expense_structure": "지출 구조",
    }

    for domain_key, domain in risk["domains"].items():
        domain_name = domain_labels.get(domain_key, domain_key)

        with st.expander(
            f"{domain_name} · {domain['level']} · "
            f"{domain['score']:.2f}/{domain['max_score']:.0f}"
        ):
            st.write(domain["explanation"])

            for component in domain["breakdown"]:
                st.markdown(
                    f"**{component['name']}** · "
                    f"+{component['score']:.2f} / {component['max_score']:.0f}"
                )
                st.caption(component["explanation"])

    st.caption(
        "영역별 점수는 위험점수입니다. 위험점수가 높을수록 금융 건강점수에서 더 많이 차감됩니다."
    )

    st.markdown("### 점수 산정 근거")
    breakdown = risk["score_breakdown"]

    b1, b2, b3 = st.columns(3)
    b1.metric("영역별 위험 합계", f"{breakdown['base_score']:.2f}점")
    b2.metric(
        "복합위험 추가점수",
        f"+{breakdown['applied_interaction_score']:.2f}점",
    )
    b3.metric("최종 건강점수", f"{breakdown['health_score']:.2f}점")

    st.info(breakdown["explanation"])



with forecast_tab:
    # -----------------------------
    # Forecast
    # -----------------------------
    section_header(
        "FORECAST",
        "앞으로의 금융 건강",
        "현재의 소득·지출·저축 행동이 유지된다고 가정한 시나리오입니다.",
    )

    health_forecast = forecast_financial_health(
        income=income,
        fixed_expense=fixed_expense,
        living_expense=living_expense,
        debt_payment=debt_payment,
        monthly_savings=monthly_savings,
        savings=savings,
        months=(0, 3, 6, 12),
    )

    health_forecast_df = pd.DataFrame(health_forecast)
    health_forecast_df["시점"] = health_forecast_df["month"].map(
        {0: "현재", 3: "3개월", 6: "6개월", 12: "12개월"}
    )

    forecast_cols = st.columns(4)

    for column, row in zip(
        forecast_cols,
        health_forecast_df.to_dict("records"),
    ):
        with column:
            forecast_tone = status_tone(row["risk_level"])
            metric_card(
                row["시점"],
                f"{row['health_score']:.1f}점",
                (
                    f"위험 {row['risk_score']:.1f} · "
                    f"비상자금 {row['emergency_months']:.1f}개월<br>"
                    f"예상 저축액 {row['projected_savings']:,.0f}원"
                ),
                forecast_tone,
            )

    st.markdown("### 건강점수 변화")
    health_chart_df = health_forecast_df[
        ["month", "health_score"]
    ].rename(columns={"health_score": "금융 건강점수"})

    st.line_chart(
        health_chart_df,
        x="month",
        y="금융 건강점수",
    )

    st.markdown("### 위험점수 변화")
    risk_chart_df = health_forecast_df[
        ["month", "risk_score"]
    ].rename(columns={"risk_score": "금융 위험점수"})

    st.line_chart(
        risk_chart_df,
        x="month",
        y="금융 위험점수",
    )

    current_asset_change = (
        monthly_savings
        + min(0, metrics["monthly_surplus"])
    )

    forecast = forecast_assets(
        savings,
        current_asset_change,
        months=12,
    )

    final_asset = forecast.iloc[-1]["asset"]

    st.markdown("### 12개월 금융자산 전망")
    st.line_chart(
        forecast,
        x="month",
        y="asset",
    )

    asset_now_col, asset_future_col = st.columns(2)
    asset_now_col.metric("현재 금융자산", money(savings))
    asset_future_col.metric("12개월 후 예상 금융자산", money(final_asset))

    st.caption(
        "본 전망은 현재 행동이 동일하게 유지된다는 가정에 따른 시나리오이며, ML 기반 미래 예측값은 아닙니다."
    )


    # -----------------------------
    # What-if
    # -----------------------------
    section_header(
        "SIMULATOR",
        "내 재무 What-if",
        "생활비, 소득, 저축을 바꿔 보며 금융상태가 얼마나 달라지는지 즉시 확인하세요.",
    )

    s1, s2, s3 = st.columns(3)

    with s1:
        expense_reduction = st.slider(
            "월 생활비 줄이기",
            min_value=0,
            max_value=1000000,
            value=0,
            step=50000,
            format="%d원",
        )

    with s2:
        income_increase = st.slider(
            "월 소득 늘리기",
            min_value=0,
            max_value=1000000,
            value=0,
            step=50000,
            format="%d원",
        )

    with s3:
        extra_savings = st.slider(
            "월 추가 저축하기",
            min_value=0,
            max_value=1000000,
            value=0,
            step=50000,
            format="%d원",
        )

    new_income = income + income_increase
    actual_expense_reduction = min(expense_reduction, living_expense)
    new_living_expense = living_expense - actual_expense_reduction

    new_monthly_savings = (
        monthly_savings
        + extra_savings
    )

    new_monthly_outflow = (
        fixed_expense
        + new_living_expense
        + debt_payment
        + new_monthly_savings
    )

    new_expected_balance = new_income - new_monthly_outflow

    if new_expected_balance < 0:
        st.error(
            f"이 계획은 매월 {abs(new_expected_balance):,.0f}원이 부족합니다. "
            "추가 저축을 줄이거나 소득·지출 계획을 조정해 주세요."
        )
    else:
        st.success(
            f"실행 가능한 계획입니다. 변경 후 월 {new_expected_balance:,.0f}원의 여유자금이 남습니다."
        )

    new_metrics = calculate_metrics(
        new_income,
        fixed_expense,
        new_living_expense,
        debt_payment,
        new_monthly_savings,
        savings,
    )

    new_risk = calculate_risk(new_metrics)
    new_health_score = max(0, min(100, 100 - new_risk["score"]))

    new_asset_change = (
        new_monthly_savings
        + min(0, new_metrics["monthly_surplus"])
    )

    new_forecast = forecast_assets(
        savings,
        new_asset_change,
        months=12,
    )

    new_final_asset = new_forecast.iloc[-1]["asset"]

    st.markdown("### 시뮬레이션 결과")

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        metric_card(
            "금융 건강점수",
            f"{new_health_score:.1f}점",
            f"현재 대비 {new_health_score - health_score:+.1f}점",
            status_tone(new_risk["level"]),
        )

    with r2:
        metric_card(
            "월 잉여금",
            money(new_metrics["monthly_surplus"]),
            f"현재 대비 {new_metrics['monthly_surplus'] - metrics['monthly_surplus']:+,.0f}원",
            "positive" if new_metrics["monthly_surplus"] >= 0 else "danger",
        )

    with r3:
        metric_card(
            "월 저축",
            money(new_monthly_savings),
            f"현재 대비 {new_monthly_savings - monthly_savings:+,.0f}원",
            "neutral",
        )

    with r4:
        metric_card(
            "12개월 후 자산",
            money(new_final_asset),
            f"현재 시나리오 대비 {new_final_asset - final_asset:+,.0f}원",
            "neutral",
        )

    st.markdown(
        f"""
        <div class="mf-callout">
            위험등급 변화&nbsp;&nbsp;
            <strong>{risk['level']}</strong>
            &nbsp;→&nbsp;
            <strong>{new_risk['level']}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    comparison = forecast.copy().rename(
        columns={"asset": "현재 예상자산"}
    )
    comparison["개선 후 예상자산"] = new_forecast["asset"]

    st.line_chart(
        comparison,
        x="month",
        y=["현재 예상자산", "개선 후 예상자산"],
    )



with plan_tab:
    # -----------------------------
    # Optimizer
    # -----------------------------
    section_header(
        "ACTION PLAN",
        "자동 맞춤 개선안",
        "현재 조건에서 위험점수를 낮출 수 있는 행동 조합을 탐색해 세 가지 관점으로 정리합니다.",
    )

    plans = find_improvement_plans(
        income=income,
        fixed_expense=fixed_expense,
        living_expense=living_expense,
        debt_payment=debt_payment,
        monthly_savings=monthly_savings,
        savings=savings,
    )

    if not plans:
        st.info("현재 조건에서는 추가적인 현실적 개선안을 찾지 못했습니다.")
    else:
        tabs = st.tabs(
            [plan["name"] for plan in plans]
        )

        for tab, plan in zip(tabs, plans):
            with tab:
                st.markdown(f"### {plan['name']}")
                st.caption("현재 금융상태를 기준으로 자동 탐색된 개선 행동입니다.")

                a1, a2, a3 = st.columns(3)

                a1.metric(
                    "생활비 절감",
                    f"{plan['living_expense_reduction']:,.0f}원/월",
                )
                a2.metric(
                    "소득 증가",
                    f"{plan['income_increase']:,.0f}원/월",
                )
                a3.metric(
                    "추가 저축",
                    f"{plan['extra_savings']:,.0f}원/월",
                )

                st.markdown("### 예상 개선 결과")

                p1, p2, p3, p4 = st.columns(4)

                with p1:
                    metric_card(
                        "금융 건강점수",
                        f"{plan['health_score']:.1f}점",
                        f"현재 대비 {plan['health_score'] - health_score:+.1f}점",
                        status_tone(plan["risk_level"]),
                    )

                with p2:
                    metric_card(
                        "위험점수",
                        f"{plan['risk_score']:.1f}점",
                        f"현재 대비 -{plan['risk_reduction']:.1f}점",
                        status_tone(plan["risk_level"]),
                    )

                with p3:
                    metric_card(
                        "위험등급",
                        plan["risk_level"],
                        "개선안 적용 후 예상 등급",
                        status_tone(plan["risk_level"]),
                    )

                with p4:
                    metric_card(
                        "월 잉여금",
                        money(plan["new_monthly_surplus"]),
                        "개선안 적용 후 예상 잉여금",
                        (
                            "positive"
                            if plan["new_monthly_surplus"] >= 0
                            else "danger"
                        ),
                    )

                st.markdown(
                    f"""
                    <div class="mf-callout">
                        월 저축액은 <strong>{monthly_savings:,.0f}원</strong>에서
                        <strong>{plan['new_monthly_savings']:,.0f}원</strong>으로 변경됩니다.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                plan_asset_change = (
                    plan["new_monthly_savings"]
                    + min(0, plan["new_monthly_surplus"])
                )

                plan_forecast = forecast_assets(
                    savings,
                    plan_asset_change,
                    months=12,
                )

                plan_comparison = forecast.copy().rename(
                    columns={"asset": "현재 예상자산"}
                )
                plan_comparison["개선안 적용 후"] = plan_forecast["asset"]

                st.markdown("### 12개월 자산 전망 비교")
                st.line_chart(
                    plan_comparison,
                    x="month",
                    y=["현재 예상자산", "개선안 적용 후"],
                )

                current_12m_asset = forecast.iloc[-1]["asset"]
                improved_12m_asset = plan_forecast.iloc[-1]["asset"]

                q1, q2, q3 = st.columns(3)
                q1.metric("현재 12개월 후 자산", money(current_12m_asset))
                q2.metric("개선 후 12개월 자산", money(improved_12m_asset))
                q3.metric(
                    "12개월 자산 증가",
                    money(improved_12m_asset - current_12m_asset),
                )

                st.markdown("### 금융 건강점수 미래 비교")

                plan_health_forecast = forecast_plan_health(
                    income=income,
                    fixed_expense=fixed_expense,
                    living_expense=living_expense,
                    debt_payment=debt_payment,
                    monthly_savings=monthly_savings,
                    savings=savings,
                    plan=plan,
                    months=(0, 3, 6, 12),
                )

                plan_health_df = pd.DataFrame(plan_health_forecast)

                health_comparison = health_forecast_df[
                    ["month", "health_score"]
                ].rename(
                    columns={"health_score": "현재 행동 유지"}
                )

                health_comparison["개선안 적용"] = plan_health_df["health_score"]

                st.line_chart(
                    health_comparison,
                    x="month",
                    y=["현재 행동 유지", "개선안 적용"],
                )

                current_12m_health = health_comparison.iloc[-1]["현재 행동 유지"]
                improved_12m_health = health_comparison.iloc[-1]["개선안 적용"]

                h1, h2 = st.columns(2)

                with h1:
                    metric_card(
                        "현재 행동 유지 시 12개월 건강점수",
                        f"{current_12m_health:.1f}점",
                        "현재 금융습관을 그대로 유지한 경우",
                        status_tone(risk["level"]),
                    )

                with h2:
                    metric_card(
                        "개선안 적용 시 12개월 건강점수",
                        f"{improved_12m_health:.1f}점",
                        (
                            "현재 대비 "
                            f"{improved_12m_health - current_12m_health:+.1f}점"
                        ),
                        status_tone(plan["risk_level"]),
                    )



with product_tab:
    # -----------------------------
    # Financial products
    # -----------------------------
    section_header(
        "PRODUCT MATCH",
        "내 상태에 맞는 금융상품",
        "현재 금융상태와 위험진단 결과를 바탕으로 실제 적금·예금 상품 중 우선 확인할 상품을 선별합니다.",
    )

    with st.spinner("금융감독원 금융상품 정보를 불러오는 중입니다..."):
        saving_result, deposit_result = load_financial_products()

    saving_products = (
        saving_result.get("items", [])
        if saving_result.get("available")
        else []
    )

    deposit_products = (
        deposit_result.get("items", [])
        if deposit_result.get("available")
        else []
    )

    recommendations = get_personalized_recommendations(
        metrics=metrics,
        risk=risk,
        user_profile={},
        saving_products=saving_products,
        deposit_products=deposit_products,
        policies=[],
        max_products=3,
        max_policies=0,
    )

    product_recommendations = recommendations.get(
        "financial_products",
        []
    )

    recommendation_context = recommendations.get(
        "recommendation_context",
        {}
    )

    product_api_available = (
        saving_result.get("available")
        or deposit_result.get("available")
    )

    if not product_api_available:
        product_error = (
            saving_result.get("error_code")
            or deposit_result.get("error_code")
            or "API_UNAVAILABLE"
        )

        st.warning(
            "현재 금융상품 정보를 불러오지 못했습니다. "
            f"오류 코드: {product_error}"
        )

    elif (
        recommendation_context.get("product_recommendation_status")
        == "deferred"
    ):
        st.markdown(
            """
            <div class="mf-callout">
                현재 월 현금흐름이 적자이므로 금융상품 가입보다
                월 적자 해소와 현금흐름 개선을 우선하는 것이 적절합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif not product_recommendations:
        st.info("현재 조건에서 우선 추천할 금융상품을 찾지 못했습니다.")

    else:
        for index, item in enumerate(
            product_recommendations,
            start=1,
        ):
            product = item.get("product", {})
            score = float(item.get("match_score", 0) or 0)

            company_name = (
                product.get("company_name")
                or "금융회사 정보 없음"
            )

            product_name = (
                product.get("product_name")
                or "상품명 정보 없음"
            )

            with st.expander(
                f"{index:02d} · {company_name} · {product_name} · 적합도 {score:.0f}점",
                expanded=(index == 1),
            ):
                product_type = product.get("product_type")
                product_type_label = {
                    "saving": "적금",
                    "deposit": "예금",
                }.get(
                    product_type,
                    product_type or "정보 없음",
                )

                term_months = product.get("term_months")
                base_rate = product.get("base_rate")
                max_rate = product.get("max_rate")

                pr1, pr2, pr3, pr4 = st.columns(4)

                pr1.metric("상품유형", product_type_label)
                pr2.metric(
                    "가입기간",
                    f"{term_months}개월"
                    if term_months is not None
                    else "정보 없음",
                )
                pr3.metric(
                    "기본금리",
                    f"{float(base_rate):.2f}%"
                    if base_rate is not None
                    else "정보 없음",
                )
                pr4.metric(
                    "최고금리",
                    f"{float(max_rate):.2f}%"
                    if max_rate is not None
                    else "정보 없음",
                )

                detail1, detail2 = st.columns(2)
                detail1.write(
                    "**가입대상**  \n"
                    + (product.get("join_member") or "정보 없음")
                )
                detail2.write(
                    "**가입방법**  \n"
                    + (product.get("join_way") or "정보 없음")
                )

                reasons = item.get("reasons", [])
                if reasons:
                    st.markdown("**왜 이 상품을 먼저 볼까요?**")
                    for reason in reasons:
                        st.write("•", reason)

                cautions = item.get("cautions", [])
                if cautions:
                    st.markdown("**가입 전 확인할 점**")
                    for caution in cautions:
                        st.write("•", caution)

                special_conditions = product.get("special_conditions")
                if special_conditions:
                    with st.expander("우대조건·특이사항"):
                        st.write(special_conditions)

                etc_note = product.get("etc_note")
                if etc_note:
                    st.caption(f"기타 안내 · {etc_note}")

    st.caption(
        "금융상품 정보는 금융감독원 금융상품통합비교공시 API 조회값을 기반으로 합니다. "
        "실제 가입 전에는 해당 금융회사의 최신 상품설명과 가입조건을 다시 확인해야 합니다."
    )



with ai_tab:
    # -----------------------------
    # AI coach
    # -----------------------------
    section_header(
        "AI COACH",
        "내 금융상태를 이해하기 쉽게",
        "진단과 개선안에 근거해 현재 상태와 우선 행동을 자연어로 설명합니다.",
    )

    financial_signature = (
        income,
        fixed_expense,
        living_expense,
        debt_payment,
        monthly_savings,
        savings,
    )

    if (
        st.session_state.get("chat_financial_signature")
        != financial_signature
    ):
        st.session_state["financial_chat_history"] = []
        st.session_state["chat_financial_signature"] = financial_signature

    if (
        "ai_advice" not in st.session_state
        or st.session_state.get("ai_advice_signature") != financial_signature
    ):
        st.session_state["ai_advice"] = generate_ai_advice(
            metrics,
            risk,
            plans,
        )
        st.session_state["ai_advice_signature"] = financial_signature

    advice = st.session_state["ai_advice"]

    summary_html = html.escape(str(advice["summary"]))
    priority_html = html.escape(str(advice["priority"]))
    plan_comment_html = html.escape(str(advice["plan_comment"]))

    actions_html = "".join(
        f"<li>{html.escape(str(action))}</li>"
        for action in advice["actions"]
    )

    coach_cards_html = (
        '<div class="mf-coach-grid">'
        '<div class="mf-coach-card blue">'
        '<div class="mf-coach-kicker">CURRENT STATUS</div>'
        '<div class="mf-coach-title">현재 금융상태 요약</div>'
        f'<div class="mf-coach-body">{summary_html}</div>'
        '</div>'
        '<div class="mf-coach-card soft">'
        '<div class="mf-coach-kicker">NEXT ACTION</div>'
        '<div class="mf-coach-title">추천 행동</div>'
        f'<div class="mf-coach-body"><ol class="mf-coach-actions">{actions_html}</ol></div>'
        '</div>'
        '<div class="mf-coach-card yellow">'
        '<div class="mf-coach-kicker">PRIORITY</div>'
        '<div class="mf-coach-title">가장 먼저 점검할 부분</div>'
        f'<div class="mf-coach-body">{priority_html}</div>'
        '</div>'
        '<div class="mf-coach-card green">'
        '<div class="mf-coach-kicker">PLAN COMMENT</div>'
        '<div class="mf-coach-title">개선안 코멘트</div>'
        f'<div class="mf-coach-body">{plan_comment_html}</div>'
        '</div>'
        '</div>'
    )

    st.markdown(
        coach_cards_html,
        unsafe_allow_html=True,
    )

    st.markdown("<div style=\"height:0.15rem\"></div>", unsafe_allow_html=True)

    st.caption(
        "금융코치는 기존 금융 진단 및 최적화 결과를 설명하며, "
        "별도의 투자·대출·금융상품 가입 판단을 수행하지 않습니다."
    )

    st.markdown(
        """
        <div class="mf-chat-shell">
            <div class="mf-chat-title">금융코치에게 질문하기</div>
            <div class="mf-chat-desc">
                현재 금융상태나 개선 방향에 대해 궁금한 점을 자유롭게 물어보세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "financial_chat_history" not in st.session_state:
        st.session_state["financial_chat_history"] = []

    for message in st.session_state["financial_chat_history"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # 새 질문과 로딩 상태를 입력창 "위"에 자연스럽게 보여주기 위한 자리
    pending_user = st.empty()
    pending_assistant = st.empty()

    with st.form("finance_coach_question_form", clear_on_submit=True):
        question = st.text_input(
            "질문",
            placeholder="현재 금융상태에서 궁금한 점을 입력해 주세요",
            label_visibility="collapsed",
        )
        ask_clicked = st.form_submit_button(
            "금융코치에게 물어보기",
            type="primary",
            use_container_width=True,
        )

    if ask_clicked and question:
        previous_history = st.session_state[
            "financial_chat_history"
        ].copy()

        # 사용자가 방금 보낸 질문을 입력창 위에 즉시 표시
        with pending_user.container():
            with st.chat_message("user"):
                st.write(question)

        # 로딩도 입력창 아래가 아니라, 답변이 나올 자리에서 표시
        with pending_assistant.container():
            with st.chat_message("assistant"):
                with st.status(
                    "답변을 정리하고 있어요",
                    state="running",
                    expanded=False,
                ):
                    reply = generate_ai_chat_reply(
                        question,
                        metrics,
                        risk,
                        plans,
                        chat_history=previous_history,
                    )

        st.session_state["financial_chat_history"].append(
            {
                "role": "user",
                "content": question,
            }
        )

        st.session_state["financial_chat_history"].append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        # 저장 후 다시 그리면 정식 대화 내역으로 자리잡음
        st.rerun()


st.markdown('<div class="mf-divider"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="mf-footer">
        MONEYFIT은 개인 금융상태를 이해하고 개선 방향을 탐색하기 위한 금융 건강관리 서비스입니다.
        분석 결과는 실제 투자, 대출 또는 금융상품 가입에 대한 전문적인 금융 자문을 의미하지 않습니다.
    </div>
    """,
    unsafe_allow_html=True,
)

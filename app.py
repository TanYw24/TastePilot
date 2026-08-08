from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from agent import parse_free_text_request
from db import (
    authenticate_user,
    create_user,
    get_action_totals,
    get_favorite_recipes,
    get_preference_summary,
    get_recent_recipe_actions,
    get_user_preferences,
    init_db,
    record_action,
    save_user_preferences,
)
from recommendation_tools import get_recipe_by_id, recommend_recipes


st.set_page_config(page_title="TastePilot", layout="wide")

init_db()

st.markdown(
    """
    <style>
    .stApp {
        background-image:
            linear-gradient(rgba(255, 252, 248, 0.78), rgba(255, 248, 241, 0.82)),
            url("https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1800&q=80");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }
    .main * {
        font-family: Georgia, "Times New Roman", serif;
    }
    .hero-card {
        position: relative;
        overflow: hidden;
        padding: 2.2rem 2.25rem;
        border-radius: 34px;
        background: linear-gradient(
            145deg,
            rgba(255, 248, 240, 0.78) 0%,
            rgba(255, 241, 228, 0.58) 100%
        );
        color: #4f2f24;
        box-shadow:
            0 20px 44px rgba(151, 77, 39, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.34);
        margin-bottom: 1.25rem;
        border: 1px solid rgba(255, 255, 255, 0.26);
        backdrop-filter: blur(10px) saturate(118%);
        -webkit-backdrop-filter: blur(10px) saturate(118%);
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.55rem;
        color: #7d3127;
    }
    .hero-subtitle {
        font-size: 1.08rem;
        line-height: 1.8;
        color: #7a5644;
        max-width: 560px;
    }
    .hero-shell {
        display: grid;
        grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
        gap: 1.4rem;
        align-items: center;
    }
    .hero-kicker {
        display: inline-block;
        padding: 0.36rem 0.7rem;
        border-radius: 999px;
        background: rgba(209, 108, 66, 0.12);
        color: #b25b33;
        font-size: 0.8rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .hero-visual {
        position: relative;
        height: 290px;
        border-radius: 28px;
        background:
            radial-gradient(circle at 30% 28%, rgba(255, 214, 170, 0.9), transparent 22%),
            radial-gradient(circle at 72% 30%, rgba(255, 159, 109, 0.48), transparent 20%),
            linear-gradient(145deg, rgba(255, 223, 194, 0.72) 0%, rgba(255, 198, 144, 0.56) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.42),
            0 12px 28px rgba(176, 112, 73, 0.08);
    }
    .hero-shape {
        position: absolute;
        border-radius: 28px;
        transform: rotate(-7deg);
    }
    .hero-shape.one {
        width: 158px;
        height: 124px;
        top: 38px;
        left: 26px;
        background: linear-gradient(145deg, #fff5ee 0%, #ffe1cd 100%);
        box-shadow: 0 18px 40px rgba(199, 109, 58, 0.18);
    }
    .hero-shape.two {
        width: 138px;
        height: 156px;
        right: 34px;
        top: 28px;
        background: linear-gradient(145deg, #d66a41 0%, #f29d62 100%);
        transform: rotate(10deg);
        box-shadow: 0 18px 38px rgba(188, 96, 44, 0.22);
    }
    .hero-shape.three {
        width: 208px;
        height: 118px;
        bottom: 26px;
        left: 78px;
        background: linear-gradient(145deg, #82372d 0%, #ab4f33 100%);
        transform: rotate(-2deg);
        box-shadow: 0 18px 44px rgba(125, 57, 33, 0.18);
    }
    .hero-dot {
        position: absolute;
        border-radius: 999px;
        background: rgba(255, 246, 236, 0.72);
    }
    .hero-dot.a {
        width: 18px;
        height: 18px;
        right: 168px;
        top: 46px;
    }
    .hero-dot.b {
        width: 12px;
        height: 12px;
        right: 60px;
        bottom: 108px;
    }
    .hero-mini-card {
        position: absolute;
        padding: 0.8rem 0.95rem;
        border-radius: 18px;
        background: rgba(255, 250, 244, 0.54);
        backdrop-filter: blur(12px) saturate(118%);
        -webkit-backdrop-filter: blur(12px) saturate(118%);
        box-shadow:
            0 10px 22px rgba(157, 94, 55, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.24);
        color: #714430;
        font-size: 0.92rem;
    }
    .hero-mini-card.top {
        top: 26px;
        left: 122px;
    }
    .hero-mini-card.bottom {
        right: 24px;
        bottom: 20px;
    }
    .hero-mini-title {
        font-size: 0.76rem;
        color: #b16742;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }
    .hero-emoji {
        font-size: 1.4rem;
        margin-right: 0.3rem;
    }
    .section-note {
        padding: 1.1rem 1.2rem;
        border-radius: 22px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.72), rgba(255, 247, 239, 0.6));
        border: 1px solid rgba(255, 255, 255, 0.24);
        color: #6b4530;
        margin: 0.45rem 0 1.2rem 0;
        box-shadow:
            0 10px 22px rgba(168, 110, 76, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    .skill-chip {
        display: inline-block;
        padding: 0.3rem 0.78rem;
        border-radius: 999px;
        background: #fff1e1;
        color: #a45b31;
        font-size: 0.88rem;
        margin: 0 0.35rem 0.35rem 0;
        border: 1px solid rgba(189, 122, 81, 0.2);
    }
    .selected-tags-label {
        color: #fff6ee;
        font-weight: 600;
        font-size: 0.95rem;
        padding-top: 0.24rem;
        margin-bottom: 0.22rem;
    }
    .selected-skill-row {
        margin-bottom: 0.38rem;
    }
    .selected-skill-button div[data-testid="stButton"] > button {
        min-height: 2.35rem;
        height: 2.35rem;
        border-radius: 999px;
        padding: 0.16rem 0.9rem !important;
        background: linear-gradient(180deg, rgba(255, 249, 242, 0.86) 0%, rgba(255, 242, 230, 0.76) 100%);
        color: #9a5931;
        border: 1px solid rgba(219, 176, 141, 0.72);
        font-size: 0.92rem;
        font-weight: 600;
        box-shadow:
            0 8px 18px rgba(159, 110, 79, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.42);
        white-space: nowrap;
    }
    .selected-skill-button div[data-testid="stButton"] > button:hover {
        color: #87471f;
        border-color: rgba(205, 154, 116, 0.84);
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.94) 0%, rgba(255, 245, 236, 0.82) 100%);
    }
    .selected-skill-button div[data-testid="stButton"] > button p {
        font-size: 0.92rem;
        line-height: 1;
    }
    .recipe-card {
        padding: 1.1rem 1.1rem;
        border-radius: 20px;
        background: rgba(255, 251, 246, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.24);
        box-shadow:
            0 10px 24px rgba(149, 97, 63, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 0.9rem;
        color: #5e3b2a;
    }
    .recipe-title {
        font-size: 1.34rem;
        font-weight: 700;
        color: #7a311f;
        margin-bottom: 0.35rem;
    }
    .recipe-card p,
    .recipe-card strong {
        color: #6a4330;
    }
    .recipe-card p {
        line-height: 1.72;
    }
    .metric-line {
        color: #744a34;
        margin: 0.2rem 0 0.4rem 0;
        font-weight: 600;
    }
    .prompt-card {
        padding: 1.35rem;
        border-radius: 28px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.76), rgba(255, 247, 239, 0.62));
        border: 1px solid rgba(255, 255, 255, 0.24);
        box-shadow:
            0 12px 28px rgba(154, 102, 72, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    .section-heading {
        font-size: 1.85rem;
        font-weight: 700;
        color: #7d3127;
        margin-bottom: 0.35rem;
    }
    .section-copy {
        color: #7b5a47;
        line-height: 1.7;
        margin-bottom: 0.6rem;
    }
    .skill-section {
        margin: 0.55rem 0 0.8rem 0;
    }
    .skill-popover-note {
        color: rgba(126, 90, 67, 0.78);
        font-size: 0.82rem;
        margin: 0.05rem 0 0.3rem 0.05rem;
    }
    .skill-group-label {
        font-size: 0.76rem;
        color: rgba(154, 113, 88, 0.72);
        letter-spacing: 0.06em;
        margin: 0.08rem 0 0.18rem 0.15rem;
    }
    .skill-hint {
        color: rgba(142, 116, 99, 0.74);
        font-size: 0.86rem;
        margin: 0.02rem 0 0.22rem 0.1rem;
    }
    .stTextArea textarea {
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.96) 0%,
            rgba(255, 246, 239, 0.92) 42%,
            rgba(255, 241, 231, 0.88) 100%
        ) !important;
        color: #6b3e2c !important;
        border-radius: 22px !important;
        border: 1px solid rgba(225, 196, 173, 0.9) !important;
        box-shadow:
            0 10px 24px rgba(176, 128, 95, 0.08),
            0 0 0 1px rgba(255, 248, 241, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(14px) saturate(112%) !important;
        -webkit-backdrop-filter: blur(14px) saturate(112%) !important;
        outline: none !important;
        padding: 1rem 1.05rem !important;
    }
    .stTextArea [data-baseweb="base-input"] > div,
    .stTextArea [data-baseweb="textarea"] {
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.94) 0%,
            rgba(255, 244, 236, 0.86) 100%
        ) !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 22px !important;
    }
    .stTextArea [data-baseweb="base-input"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        border-radius: 22px !important;
    }
    .stTextArea [data-testid="stTextAreaRootElement"] > div {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    .stTextArea textarea:focus {
        border: 1px solid rgba(214, 175, 145, 0.96) !important;
        box-shadow:
            0 12px 28px rgba(176, 128, 95, 0.11),
            0 0 0 2px rgba(245, 221, 202, 0.55),
            inset 0 1px 0 rgba(255, 255, 255, 0.82) !important;
    }
    .stTextArea textarea::placeholder {
        color: rgba(137, 84, 61, 0.62) !important;
    }
    .stButton > button {
        min-height: 2.95rem;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: linear-gradient(180deg, rgba(255, 248, 240, 0.62) 0%, rgba(255, 243, 232, 0.52) 100%);
        color: #82533a;
        font-weight: 600;
        box-shadow:
            0 8px 18px rgba(140, 95, 64, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.22);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .stButton > button:hover {
        border-color: rgba(255, 255, 255, 0.28);
        color: #774229;
        background: linear-gradient(180deg, rgba(255, 244, 233, 0.74) 0%, rgba(255, 236, 222, 0.64) 100%);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, rgba(201, 79, 55, 0.82) 0%, rgba(234, 122, 77, 0.72) 100%);
        border: 1px solid rgba(255, 226, 204, 0.24);
        box-shadow:
            0 12px 24px rgba(201, 87, 52, 0.16),
            inset 0 1px 0 rgba(255, 255, 255, 0.16);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(217, 91, 63, 0.84) 0%, rgba(239, 134, 88, 0.76) 100%);
    }
    .skill-section div[data-testid="stButton"] > button {
        min-height: 1.62rem;
        border-radius: 999px;
        padding: 0 0.46rem;
        background: linear-gradient(
            180deg,
            rgba(255, 252, 248, 0.7) 0%,
            rgba(255, 246, 239, 0.54) 100%
        );
        color: rgba(123, 78, 54, 0.96);
        border: 1px solid rgba(255, 255, 255, 0.34);
        box-shadow:
            0 4px 10px rgba(170, 115, 78, 0.03),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        font-size: 0.78rem;
        font-weight: 400;
        backdrop-filter: blur(8px) saturate(108%);
        -webkit-backdrop-filter: blur(8px) saturate(108%);
    }
    .skill-section div[data-testid="stButton"] > button:hover {
        background: linear-gradient(
            180deg,
            rgba(255, 250, 244, 0.88) 0%,
            rgba(255, 243, 234, 0.68) 100%
        );
        color: #8a5335;
        border-color: rgba(255, 255, 255, 0.42);
        box-shadow:
            0 6px 14px rgba(170, 115, 78, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.32);
    }
    div[data-testid="stPopover"] > button {
        min-height: 2.3rem;
        min-width: 2.3rem;
        border-radius: 999px;
        padding: 0 0.15rem !important;
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.92) 0%,
            rgba(255, 244, 236, 0.84) 100%
        );
        color: #8c5538;
        border: 1px solid rgba(226, 197, 175, 0.88);
        box-shadow:
            0 8px 20px rgba(163, 118, 85, 0.08),
            0 0 0 1px rgba(255, 248, 241, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.58);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        font-size: 1.15rem;
        font-weight: 500;
    }
    div[data-testid="stPopover"] > button:hover {
        background: linear-gradient(180deg, rgba(255, 249, 242, 0.98) 0%, rgba(255, 241, 231, 0.9) 100%);
        color: #774229;
        border-color: rgba(214, 178, 150, 0.95);
    }
    div[data-testid="stPopoverContent"],
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div {
        background: linear-gradient(
            180deg,
            rgba(255, 252, 248, 0.84) 0%,
            rgba(255, 246, 238, 0.74) 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.42) !important;
        border-radius: 24px !important;
        box-shadow:
            0 20px 48px rgba(126, 76, 47, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.32) !important;
        backdrop-filter: blur(20px) saturate(112%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(112%) !important;
    }
    div[data-baseweb="popover"] * {
        color: #7b5037;
    }
    div[data-testid="stAlert"] {
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.82) 0%,
            rgba(255, 245, 237, 0.72) 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.34) !important;
        color: #6c4531 !important;
        border-radius: 18px !important;
        box-shadow:
            0 10px 22px rgba(153, 98, 66, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
    }
    div[data-testid="stAlert"] * {
        color: #6c4531 !important;
    }
    .auth-kicker {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #fff2e0;
        margin-bottom: 0.6rem;
    }
    .auth-title {
        font-size: 3rem;
        font-weight: 700;
        color: #fff9f1;
        margin-bottom: 0.5rem;
    }
    .auth-subtitle {
        max-width: 760px;
        color: #ffecd9;
        line-height: 1.75;
        font-size: 1.02rem;
        margin: 0 auto;
    }
    .auth-stage {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 1.5rem;
    }
    .auth-copy-block {
        max-width: 820px;
    }
    .auth-form-shell {
        width: 100%;
        max-width: 520px;
    }
    @media (max-width: 900px) {
        .hero-shell {
            grid-template-columns: 1fr;
        }
        .hero-visual {
            height: 240px;
        }
        .hero-title {
            font-size: 2.45rem;
        }
        .section-heading {
            font-size: 1.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


TIME_BASED_SKILL_GROUPS = {
    "morning": [
        ("此刻适合", [("咖啡搭子", "想来点适合配咖啡的小食"), ("轻一点", "想吃清淡一点"), ("快手", "最好 15 分钟内")]),
        ("偏好方向", [("高蛋白", "高蛋白一点"), ("奶香", "想吃奶香一点"), ("一个人", "适合一个人吃"), ("暖胃", "想吃点热乎的"), ("低糖", "想控制甜度")]),
    ],
    "lunch": [
        ("此刻适合", [("下饭", "来点下饭的"), ("快手", "最好 15 分钟内"), ("省钱", "预算低一点")]),
        ("偏好方向", [("香辣", "想吃辣一点"), ("高蛋白", "高蛋白一点"), ("一个人", "适合一个人吃"), ("聚餐", "适合朋友聚餐"), ("解馋", "想吃更满足一点"), ("汤面", "想来点带汤的")]),
    ],
    "afternoon": [
        ("此刻适合", [("下午茶", "想吃点下午茶"), ("甜一点", "想吃甜一点"), ("咖啡搭子", "想来点适合配咖啡的小食")]),
        ("偏好方向", [("奶香", "想吃奶香一点"), ("果香", "想吃果香一点"), ("轻一点", "想吃清淡一点"), ("茶点", "想配茶吃点东西"), ("低糖", "想控制甜度"), ("治愈一点", "想来点让人开心的小甜点")]),
    ],
    "evening": [
        ("此刻适合", [("治愈一点", "想吃点有安慰感的"), ("下饭", "来点下饭的"), ("聚餐", "适合朋友聚餐")]),
        ("偏好方向", [("香辣", "想吃辣一点"), ("清淡", "想吃清淡一点"), ("高蛋白", "高蛋白一点"), ("一个人", "适合一个人吃"), ("汤锅", "想吃热一点"), ("家常", "想吃熟悉一点的味道")]),
    ],
    "night": [
        ("此刻适合", [("夜宵", "想吃夜宵"), ("暖胃", "想吃点热乎的"), ("快手", "最好 15 分钟内")]),
        ("偏好方向", [("治愈一点", "想吃点有安慰感的"), ("清淡", "想吃清淡一点"), ("甜一点", "想吃甜一点"), ("不油腻", "想轻一点"), ("一人食", "只给自己准备")]),
    ],
}

MOOD_SKILL_GROUP = (
    "心情",
    [
        ("安慰系", "偏治愈、柔和、能安慰人的方向"),
        ("解压系", "偏过瘾、满足、能释放情绪的方向"),
        ("暖胃系", "偏热乎、带汤、让人舒服的方向"),
        ("提神系", "偏清爽、清醒、适合补状态的方向"),
        ("犒赏系", "偏有仪式感、适合奖励自己的方向"),
    ],
)


SKILL_APPEND_TEXT = {
    "香辣": "想吃辣一点",
    "清淡": "清淡一点",
    "下饭": "下饭",
    "减脂": "减脂",
    "高蛋白": "高蛋白",
    "省钱": "别太贵",
    "15 分钟": "15 分钟内",
    "一个人": "一个人吃",
    "聚餐": "朋友聚餐",
    "下午茶": "下午茶",
    "甜一点": "想吃点甜的",
    "咖啡搭子": "适合配咖啡的下午茶",
    "奶香": "奶香一点",
    "果香": "果香一点",
    "轻一点": "清淡一点",
    "快手": "15 分钟内",
    "治愈一点": "想吃点有安慰感的",
    "暖胃": "想吃点热乎的",
    "夜宵": "夜宵",
    "低糖": "甜度低一点",
    "解馋": "想吃得过瘾一点",
    "汤面": "想吃带汤的面",
    "茶点": "适合配茶的小点心",
    "汤锅": "想吃热一点的锅物",
    "家常": "家常一点",
    "不油腻": "不要太油",
    "一人食": "一个人吃",
    "安慰系": "想吃点安慰的",
    "解压系": "想吃点解压发泄的",
    "暖胃系": "想吃点暖胃的",
    "提神系": "想来点提神的",
    "犒赏系": "想奖励自己一下",
}


if "user" not in st.session_state:
    st.session_state.user = None
if "prompt_text" not in st.session_state:
    st.session_state.prompt_text = ""
if "prompt_text_input" not in st.session_state:
    st.session_state.prompt_text_input = st.session_state.prompt_text
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = []
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "last_query" not in st.session_state:
    st.session_state.last_query = {}
if "excluded_recipe_ids" not in st.session_state:
    st.session_state.excluded_recipe_ids = []
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "sync_prompt_input" not in st.session_state:
    st.session_state.sync_prompt_input = False


def render_tag_pills(tags: list[str]) -> str:
    unique_tags = list(dict.fromkeys(tag for tag in tags if tag))
    return "".join(f'<span class="skill-chip">{tag}</span>' for tag in unique_tags)


def logout() -> None:
    st.session_state.user = None
    st.session_state.prompt_text = ""
    st.session_state.prompt_text_input = ""
    st.session_state.selected_skills = []
    st.session_state.recommendations = []
    st.session_state.last_query = {}
    st.session_state.excluded_recipe_ids = []
    st.rerun()


def apply_skill(skill_name: str) -> None:
    if skill_name not in st.session_state.selected_skills:
        st.session_state.selected_skills.append(skill_name)

    snippet = SKILL_APPEND_TEXT[skill_name]
    if snippet not in st.session_state.prompt_text:
        separator = "，" if st.session_state.prompt_text.strip() else ""
        st.session_state.prompt_text = f"{st.session_state.prompt_text}{separator}{snippet}"
        st.session_state.sync_prompt_input = True


def remove_skill(skill_name: str) -> None:
    if skill_name in st.session_state.selected_skills:
        st.session_state.selected_skills = [skill for skill in st.session_state.selected_skills if skill != skill_name]

    snippet = SKILL_APPEND_TEXT.get(skill_name, "")
    if snippet:
        for key in ["prompt_text", "prompt_text_input"]:
            text = st.session_state.get(key, "")
            text = text.replace(f"，{snippet}", "")
            text = text.replace(f"{snippet}，", "")
            text = text.replace(snippet, "")
            text = text.replace("，，", "，").strip("， ")
            st.session_state[key] = text
    st.session_state.sync_prompt_input = True


def clear_prompt() -> None:
    st.session_state.prompt_text = ""
    st.session_state.prompt_text_input = ""
    st.session_state.selected_skills = []
    st.session_state.recommendations = []
    st.session_state.last_query = {}
    st.session_state.excluded_recipe_ids = []
    st.session_state.sync_prompt_input = False


def get_dynamic_skill_groups() -> tuple[str, list[tuple[str, list[tuple[str, str]]]]]:
    current_hour = datetime.now(ZoneInfo("Asia/Shanghai")).hour
    if 5 <= current_hour < 11:
        return "早上", TIME_BASED_SKILL_GROUPS["morning"] + [MOOD_SKILL_GROUP]
    if 11 <= current_hour < 15:
        return "中午", TIME_BASED_SKILL_GROUPS["lunch"] + [MOOD_SKILL_GROUP]
    if 15 <= current_hour < 18:
        return "下午", TIME_BASED_SKILL_GROUPS["afternoon"] + [MOOD_SKILL_GROUP]
    if 18 <= current_hour < 22:
        return "晚上", TIME_BASED_SKILL_GROUPS["evening"] + [MOOD_SKILL_GROUP]
    return "深夜", TIME_BASED_SKILL_GROUPS["night"] + [MOOD_SKILL_GROUP]


def render_selected_skills() -> None:
    if not st.session_state.selected_skills:
        st.write("")
        return

    st.markdown('<div class="selected-tags-label">已选标签：</div>', unsafe_allow_html=True)
    row_size = 5
    skills = st.session_state.selected_skills[:]
    for start_index in range(0, len(skills), row_size):
        row_skills = skills[start_index : start_index + row_size]
        st.markdown('<div class="selected-skill-row">', unsafe_allow_html=True)
        column_weights = [max(1.0, len(skill_name) * 0.55 + 1.4) for skill_name in row_skills]
        pill_cols = st.columns(column_weights, gap="small")
        for idx, skill_name in enumerate(row_skills):
            with pill_cols[idx]:
                st.markdown('<div class="selected-skill-button">', unsafe_allow_html=True)
                button_label = f"{skill_name} ×"
                st.button(
                    button_label,
                    key=f"remove_skill_{start_index}_{idx}_{skill_name}",
                    on_click=remove_skill,
                    args=(skill_name,),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_auth_screen() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-image:
                linear-gradient(rgba(26, 19, 15, 0.42), rgba(26, 19, 15, 0.48)),
                url("https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1800&q=80");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"] > .main {
            background: transparent;
        }
        .main .block-container {
            max-width: 1200px;
            min-height: calc(100vh - 3rem);
            padding-top: 3.5rem;
            padding-bottom: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        div[data-testid="stForm"] {
            background: linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.32),
                rgba(255, 248, 241, 0.18)
            );
            backdrop-filter: blur(18px) saturate(145%);
            -webkit-backdrop-filter: blur(18px) saturate(145%);
            border: 1px solid rgba(255, 255, 255, 0.42);
            border-radius: 26px;
            padding: 1.35rem 1.35rem 1.1rem 1.35rem;
            box-shadow:
                0 26px 70px rgba(28, 19, 14, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.32);
        }
        div[data-testid="stForm"] button[kind="primary"],
        div[data-testid="stForm"] button[kind="secondary"] {
            min-height: 3.2rem;
            border-radius: 16px;
            font-size: 1.02rem;
            font-weight: 600;
        }
        div[data-testid="stForm"] [data-baseweb="input"] {
            background: rgba(35, 36, 46, 0.96);
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        div[data-testid="stForm"] input {
            color: #f7f7fb;
        }
        div[data-testid="stForm"] input::placeholder {
            color: rgba(236, 228, 220, 0.62);
        }
        @media (prefers-color-scheme: light) {
            div[data-testid="stForm"] [data-baseweb="input"] {
                background: rgba(255, 250, 245, 0.96);
                border: 1px solid rgba(219, 188, 163, 0.62);
                box-shadow:
                    0 8px 18px rgba(175, 129, 95, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.68);
            }
            div[data-testid="stForm"] input {
                color: #2f241d !important;
            }
            div[data-testid="stForm"] input::placeholder {
                color: rgba(111, 84, 66, 0.58) !important;
            }
        }
        @media (prefers-color-scheme: dark) {
            div[data-testid="stForm"] [data-baseweb="input"] {
                background: rgba(35, 36, 46, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            div[data-testid="stForm"] input {
                color: #f7f7fb !important;
            }
            div[data-testid="stForm"] input::placeholder {
                color: rgba(236, 228, 220, 0.62) !important;
            }
        }
        @media (max-width: 900px) {
            .main .block-container {
                min-height: auto;
                padding-top: 2rem;
            }
            .auth-title {
                font-size: 2.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-stage">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="auth-copy-block">
            <div class="auth-kicker">Personal Recipe Guide</div>
            <div class="auth-title">TastePilot</div>
            <div class="auth-subtitle">
                把你现在想吃的感觉告诉我，我来帮你决定今晚吃什么。少一点筛选，多一点被理解，
                这是一个会记住你口味偏好的个人菜谱顾问。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-form-shell">', unsafe_allow_html=True)
    with st.container():
        if st.session_state.auth_mode == "login":
            st.subheader("登录")
            st.caption("已经有账号了，直接回来继续选菜。")
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("邮箱", placeholder="you@example.com")
                password = st.text_input("密码", type="password")
                submitted = st.form_submit_button("登录并进入", use_container_width=True)
            if submitted:
                user = authenticate_user(email.strip(), password)
                if user is None:
                    st.error("邮箱或密码不正确。")
                else:
                    st.session_state.user = user
                    st.rerun()

            st.write("新用户第一次来这里？")
            st.button(
                "去注册",
                on_click=lambda: st.session_state.update({"auth_mode": "register"}),
                use_container_width=True,
            )
        else:
            st.subheader("新用户注册")
            st.caption("创建一个账号，TastePilot 就能开始记住你的口味。")
            with st.form("register_form", clear_on_submit=False):
                nickname = st.text_input("昵称", placeholder="比如：小周")
                email = st.text_input("注册邮箱", placeholder="you@example.com")
                password = st.text_input("设置密码", type="password")
                submitted = st.form_submit_button("创建账号", use_container_width=True)
            if submitted:
                try:
                    user_id = create_user(nickname.strip(), email.strip(), password)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.user = {"id": user_id, "nickname": nickname.strip(), "email": email.strip()}
                    st.success("注册成功。现在可以开始选今晚吃什么了。")
                    st.rerun()

            st.write("已经注册过了？")
            st.button(
                "返回登录",
                on_click=lambda: st.session_state.update({"auth_mode": "login"}),
                use_container_width=True,
            )
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_sidebar(preferences: dict) -> None:
    with st.sidebar:
        user_id = st.session_state.user["id"]
        action_totals = get_action_totals(user_id)
        recent_views = get_recent_recipe_actions(user_id, "view", limit=5)
        recent_skips = get_recent_recipe_actions(user_id, "skip", limit=5)

        st.markdown(f"## 欢迎你，{st.session_state.user['nickname']}")
        st.write(st.session_state.user["email"])
        st.button("退出登录", on_click=logout, use_container_width=True)
        st.markdown("---")
        st.markdown("## 这阵子的口味轨迹")
        view_total = action_totals.get("view", 0)
        favorite_total = action_totals.get("favorite", 0)
        skip_total = action_totals.get("skip", 0)
        st.caption(f"最近一共看过 {view_total} 次，收藏 {favorite_total} 次，跳过 {skip_total} 次。")
        if favorite_total > skip_total and favorite_total > 0:
            st.write("今天的 TastePilot 记忆更偏向你喜欢的方向。")
        elif skip_total > favorite_total and skip_total > 0:
            st.write("你这阵子在认真排除不想吃的类型，推荐会继续收窄。")
        else:
            st.write("再多选几轮，我会更快摸准你现在的口味。")

        st.markdown("---")
        st.markdown("## 长期偏好")
        summary_lines = get_preference_summary(preferences)
        if summary_lines:
            for line in summary_lines:
                st.write(line)
        else:
            st.write("你还没有保存偏好。")

        with st.expander("修改偏好", expanded=False):
            flavor_options = ["香辣", "酸甜", "清淡", "蒜香", "鲜香", "重口", "家常", "酱香"]
            saved_flavors = preferences.get("favorite_flavors", "").split("|") if preferences.get("favorite_flavors") else []
            saved_disliked = preferences.get("disliked_ingredients", "")
            saved_goal = preferences.get("diet_goal", "均衡饮食")
            saved_budget = preferences.get("budget_level", "中等预算")
            saved_time = preferences.get("cooking_time_limit", "30 分钟内")
            saved_veg = preferences.get("vegetarian_preference", "不限")

            with st.form("preference_form"):
                favorite_flavors = st.multiselect("平时偏爱口味", flavor_options, default=saved_flavors)
                disliked_ingredients = st.text_input("忌口", value=saved_disliked, placeholder="比如：香菜、花生")
                diet_goal = st.selectbox("长期目标", ["均衡饮食", "减脂清爽", "高蛋白增肌", "下饭解馋", "朋友聚餐", "夜宵安慰"], index=["均衡饮食", "减脂清爽", "高蛋白增肌", "下饭解馋", "朋友聚餐", "夜宵安慰"].index(saved_goal))
                budget_level = st.selectbox("常见预算", ["低预算", "中等预算", "高预算"], index=["低预算", "中等预算", "高预算"].index(saved_budget))
                cooking_time_limit = st.selectbox("平时做饭时间", ["15 分钟内", "30 分钟内", "45 分钟内", "60 分钟内"], index=["15 分钟内", "30 分钟内", "45 分钟内", "60 分钟内"].index(saved_time))
                vegetarian_preference = st.selectbox("饮食倾向", ["不限", "希望多素食", "严格素食"], index=["不限", "希望多素食", "严格素食"].index(saved_veg))
                submitted = st.form_submit_button("保存偏好")

            if submitted:
                save_user_preferences(
                    st.session_state.user["id"],
                    {
                        "favorite_flavors": "|".join(favorite_flavors),
                        "disliked_ingredients": disliked_ingredients.strip(),
                        "diet_goal": diet_goal,
                        "budget_level": budget_level,
                        "cooking_time_limit": cooking_time_limit,
                        "vegetarian_preference": vegetarian_preference,
                    },
                )
                st.success("偏好已更新。")

        st.markdown("---")
        favorites = get_favorite_recipes(user_id)
        st.markdown("## 我的收藏")
        if not favorites:
            st.write("还没有收藏。")
        else:
            for recipe_id in favorites[:5]:
                recipe = get_recipe_by_id(recipe_id)
                if recipe:
                    st.write(f"• {recipe['name']}")

        st.markdown("---")
        st.markdown("## 最近看过")
        if not recent_views:
            st.write("还没有浏览记录。")
        else:
            for item in recent_views:
                recipe = get_recipe_by_id(item["recipe_id"])
                if recipe:
                    st.write(f"• {recipe['name']}")

        with st.expander("最近跳过了什么", expanded=False):
            if not recent_skips:
                st.write("还没有跳过记录。")
            else:
                for item in recent_skips:
                    recipe = get_recipe_by_id(item["recipe_id"])
                    if recipe:
                        st.write(f"• {recipe['name']}")


def build_query_from_prompt(preferences: dict, prompt_override: str | None = None) -> tuple[dict, dict]:
    prompt_text = (prompt_override if prompt_override is not None else st.session_state.prompt_text_input).strip()
    st.session_state.prompt_text = prompt_text
    parsed = parse_free_text_request(prompt_text)
    preferred_flavors = list(
        dict.fromkeys(
            [item for item in preferences.get("favorite_flavors", "").split("|") if item]
            + parsed.get("favorite_flavors", [])
        )
    )
    query = {
        "scene": parsed.get("scene", ""),
        "favorite_flavors": preferred_flavors,
        "required_flavors": parsed.get("required_flavors", []),
        "diet_goal": parsed.get("diet_goal", ""),
        "budget_level": parsed.get("budget_level", preferences.get("budget_level", "中等预算")),
        "cooking_time_limit": parsed.get("cooking_time_limit", preferences.get("cooking_time_limit", "30 分钟内")),
        "vegetarian_preference": parsed.get("vegetarian_preference", preferences.get("vegetarian_preference", "不限")),
        "disliked_ingredients": "、".join(
            filter(None, [preferences.get("disliked_ingredients", ""), parsed.get("disliked_ingredients", "")])
        ),
        "preferred_course_types": parsed.get("preferred_course_types", []),
        "avoid_course_types": parsed.get("avoid_course_types", []),
        "intent_tags": parsed.get("intent_tags", []),
        "mood_search_tags": parsed.get("mood_search_tags", []),
        "beverage_categories": parsed.get("beverage_categories", []),
        "solar_terms": parsed.get("solar_terms", []),
        "cuisine_groups": parsed.get("cuisine_groups", []),
        "primary_bucket": parsed.get("primary_bucket"),
        "mood_bucket": parsed.get("mood_bucket"),
        "mood_detected": parsed.get("mood_detected"),
    }
    return query, parsed


def run_recommendation(preferences: dict, append_skill: str | None = None, replace_mode: bool = False) -> None:
    prompt_override = None
    if append_skill:
        apply_skill(append_skill)
        prompt_override = st.session_state.prompt_text

    query, parsed = build_query_from_prompt(preferences, prompt_override=prompt_override)
    excluded_ids = st.session_state.excluded_recipe_ids if replace_mode else []
    recommendations = recommend_recipes(
        query=query,
        preferences=preferences,
        user_id=st.session_state.user["id"],
        limit=3,
        exclude_recipe_ids=excluded_ids,
    )
    st.session_state.last_query = query

    if replace_mode and recommendations:
        st.session_state.excluded_recipe_ids.extend([item["id"] for item in recommendations])
        st.session_state.excluded_recipe_ids = list(dict.fromkeys(st.session_state.excluded_recipe_ids))
    elif recommendations:
        st.session_state.excluded_recipe_ids = [item["id"] for item in recommendations]

    st.session_state.recommendations = recommendations
    st.session_state.last_parsed = parsed


FOLLOW_UP_ACTION_CATALOG = [
    {"label": "更辣一点", "skill": "香辣", "tags": {"香辣", "解馋", "重口"}, "buckets": {"main"}},
    {"label": "更清爽一点", "skill": "清淡", "tags": {"清爽", "清淡", "轻负担", "果香"}, "buckets": {"main", "light_meal", "drink", "dessert"}},
    {"label": "更下饭一点", "skill": "下饭", "tags": {"下饭", "正餐", "咸口"}, "buckets": {"main"}},
    {"label": "更高蛋白一点", "skill": "高蛋白", "tags": {"高蛋白"}, "buckets": {"main", "light_meal", "drink"}},
    {"label": "更奶香一点", "skill": "奶香", "tags": {"奶香", "治愈"}, "buckets": {"dessert", "drink", "main"}},
    {"label": "更果香一点", "skill": "果香", "tags": {"果香", "清爽", "下午茶"}, "buckets": {"drink", "dessert", "light_meal"}},
    {"label": "更提神一点", "skill": "提神系", "tags": {"提神", "咖啡搭子", "清爽"}, "buckets": {"drink", "dessert"}},
    {"label": "更暖胃一点", "skill": "暖胃系", "tags": {"暖胃", "热乎", "汤面", "汤锅"}, "buckets": {"main"}},
    {"label": "更安慰一点", "skill": "安慰系", "tags": {"治愈", "奶香", "甜品", "家常"}, "buckets": {"main", "dessert", "drink"}},
    {"label": "更解压一点", "skill": "解压系", "tags": {"解馋", "香辣", "重口", "热食"}, "buckets": {"main"}},
    {"label": "更犒赏一点", "skill": "犒赏系", "tags": {"仪式感", "精致", "甜品", "分享"}, "buckets": {"dessert", "drink", "main"}},
    {"label": "更适合下午茶", "skill": "下午茶", "tags": {"下午茶", "茶点", "咖啡搭子"}, "buckets": {"dessert", "drink", "light_meal"}},
    {"label": "更快一点", "skill": "15 分钟", "tags": {"快手"}, "buckets": {"main", "light_meal", "drink", "dessert"}},
    {"label": "更省钱一点", "skill": "省钱", "tags": {"省钱", "一人食"}, "buckets": {"main", "light_meal", "drink", "dessert"}},
    {"label": "更适合一个人", "skill": "一个人", "tags": {"一人食"}, "buckets": {"main", "light_meal", "drink", "dessert"}},
]


def get_follow_up_actions() -> list[tuple[str, str]]:
    query = st.session_state.get("last_query", {}) or {}
    parsed = st.session_state.get("last_parsed", {}) or {}
    recommendations = st.session_state.get("recommendations", []) or []
    selected_skills = set(st.session_state.get("selected_skills", []))

    primary_bucket = query.get("primary_bucket")
    favorite_flavors = set(query.get("favorite_flavors", []))
    intent_tags = set(query.get("intent_tags", []))
    mood_detected = parsed.get("mood_detected")

    aggregated_tags = set()
    for recipe in recommendations:
        aggregated_tags.update(recipe.get("display_tags", []))
        aggregated_tags.update(str(recipe.get("feature_tags", "")).split("|"))
        aggregated_tags.update(str(recipe.get("flavor_tags", "")).split("|"))

    aggregated_tags = {tag for tag in aggregated_tags if tag}

    bucket_name = primary_bucket or "main"
    scored_candidates: list[tuple[int, str, str]] = []
    for action in FOLLOW_UP_ACTION_CATALOG:
        skill = action["skill"]
        if skill in selected_skills or skill not in SKILL_APPEND_TEXT:
            continue
        if bucket_name not in action["buckets"]:
            continue

        overlap_count = len(action["tags"].intersection(aggregated_tags))
        context_bonus = 0
        if skill in favorite_flavors or skill in intent_tags:
            context_bonus += 2
        if skill == "15 分钟" and query.get("cooking_time_limit") != "15 分钟内":
            context_bonus += 3
        if skill == "省钱" and query.get("budget_level") != "低预算":
            context_bonus += 3
        if skill == "一个人" and query.get("scene") != "一个人吃":
            context_bonus += 2
        if mood_detected == "安慰系" and skill in {"暖胃系", "安慰系", "奶香"}:
            context_bonus += 3
        if mood_detected == "解压系" and skill in {"解压系", "香辣", "下饭"}:
            context_bonus += 3
        if mood_detected == "暖胃系" and skill in {"暖胃系", "清淡", "奶香"}:
            context_bonus += 3
        if mood_detected == "提神系" and skill in {"提神系", "果香", "清淡"}:
            context_bonus += 3
        if mood_detected == "犒赏系" and skill in {"犒赏系", "奶香", "下午茶"}:
            context_bonus += 3

        if overlap_count > 0 or context_bonus > 0:
            scored_candidates.append((overlap_count + context_bonus, action["label"], skill))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)

    deduped: list[tuple[str, str]] = []
    seen_skills = set()
    for _, label, skill in scored_candidates:
        if skill in seen_skills:
            continue
        seen_skills.add(skill)
        deduped.append((label, skill))

    if not deduped:
        deduped = [
            ("更快一点", "15 分钟"),
            ("更省钱一点", "省钱"),
            ("更适合一个人", "一个人"),
            ("更高蛋白一点", "高蛋白"),
        ]

    return deduped[:4]


def render_input_area(preferences: dict) -> None:
    time_label, active_skill_groups = get_dynamic_skill_groups()
    if st.session_state.sync_prompt_input:
        st.session_state.prompt_text_input = st.session_state.prompt_text
        st.session_state.sync_prompt_input = False

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-shell">
                <div>
                    <div class="hero-kicker">Smart Dinner Picks</div>
                    <div class="hero-title">TastePilot</div>
                    <div class="hero-subtitle">
                        把你现在想吃的感觉告诉我，我来帮你决定今晚吃什么。少一点筛选，多一点被理解，
                        这是一个会记住你口味偏好的个人菜谱顾问。
                    </div>
                </div>
                <div class="hero-visual">
                    <div class="hero-shape one"></div>
                    <div class="hero-shape two"></div>
                    <div class="hero-shape three"></div>
                    <div class="hero-dot a"></div>
                    <div class="hero-dot b"></div>
                    <div class="hero-mini-card top">
                        <div class="hero-mini-title">Tonight</div>
                        <span class="hero-emoji">🍲</span> 快一点，也好吃一点
                    </div>
                    <div class="hero-mini-card bottom">
                        <div class="hero-mini-title">Mood Board</div>
                        <span class="hero-emoji">✨</span> 香辣 / 家常 / 放松
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="prompt-card">
            <div class="section-heading">告诉我你现在想吃什么</div>
            <div class="section-copy">
                你可以直接输入一句模糊需求，比如“想吃热乎一点、别太贵、一个人吃”，
                也可以先点下面的 skill，让我们更快接近今晚那道对的菜。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.text_area(
        "输入一句话",
        key="prompt_text_input",
        placeholder="比如：我今天想吃辣一点，一个人吃，最好 15 分钟内能搞定",
        height=110,
        label_visibility="collapsed",
    )

    picker_col, selected_col = st.columns([0.12, 0.88], gap="small")
    with picker_col:
        with st.popover("＋"):
            for group_name, group_skills in active_skill_groups:
                st.markdown(
                    f'<div class="skill-section"><div class="skill-group-label">{group_name}</div></div>',
                    unsafe_allow_html=True,
                )
                cols = st.columns(3)
                for index, (skill_name, skill_desc) in enumerate(group_skills):
                    with cols[index % 3]:
                        st.button(
                            skill_name,
                            key=f"skill_{skill_name}",
                            help=skill_desc,
                            on_click=apply_skill,
                            args=(skill_name,),
                            use_container_width=True,
                        )

    with selected_col:
        render_selected_skills()

    action_col1, action_col2, action_col3 = st.columns([1.2, 1.1, 0.9])
    with action_col1:
        if st.button("立即推荐今晚吃什么", type="primary", use_container_width=True):
            run_recommendation(preferences)
    with action_col2:
        if st.button("换一批候选菜", use_container_width=True):
            run_recommendation(preferences, replace_mode=True)
    with action_col3:
        st.button("清空", on_click=clear_prompt, use_container_width=True)

    parsed = (
        parse_free_text_request(st.session_state.prompt_text_input)
        if st.session_state.prompt_text_input.strip()
        else {}
    )
    if parsed.get("recognized_hints"):
        st.info(f"我先帮你理解成：{'、'.join(parsed['recognized_hints'])}")
        st.markdown(
            f"""
            <div class="section-note">
                <strong>理解标签：</strong> {render_tag_pills(parsed['recognized_hints'])}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recipe_cards() -> None:
    recommendations = st.session_state.recommendations
    if not recommendations:
        return

    st.subheader("今晚先看这 3 个")
    for recipe in recommendations:
        st.markdown(
            f"""
            <div class="recipe-card">
                <div class="recipe-title">{recipe['name']}</div>
                <div>{render_tag_pills(recipe['display_tags'])}</div>
                <p><strong>为什么推荐你：</strong>{recipe['reason']}</p>
                <p class="metric-line">
                    {recipe['cook_time_minutes']} 分钟 ｜ {recipe['budget_level']} ｜ {recipe['difficulty']}难度
                </p>
                <p><strong>主要食材：</strong>{recipe['ingredients']}</p>
                <p>{recipe['description']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([0.95, 0.95, 1.1])
        if col1.button(f"就吃这个", key=f"pick_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "favorite")
            st.success(f"已帮你记住你喜欢 {recipe['name']}。")
        if col2.button(f"先收藏", key=f"favorite_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "favorite")
            st.success(f"已收藏 {recipe['name']}。")
        if col3.button(f"不太像我想吃的", key=f"skip_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "skip")
            st.info(f"已记下你这次不太想吃 {recipe['name']}。")


def render_follow_up_actions(preferences: dict) -> None:
    if not st.session_state.recommendations:
        return

    st.subheader("还想再收窄一点吗")
    st.write("如果这 3 个里还没有特别心动的，我们可以继续往前推一步。")
    follow_up_actions = get_follow_up_actions()
    cols = st.columns(len(follow_up_actions))
    for index, (label, skill) in enumerate(follow_up_actions):
        with cols[index]:
            if st.button(label, key=f"followup_{skill}_{index}", use_container_width=True):
                run_recommendation(preferences, append_skill=skill)


def main() -> None:
    if st.session_state.user is None:
        render_auth_screen()
        return

    preferences = get_user_preferences(st.session_state.user["id"])
    render_sidebar(preferences)
    render_input_area(preferences)
    render_recipe_cards()
    render_follow_up_actions(preferences)


main()

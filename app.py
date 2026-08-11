import base64
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from random import randint
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from agent import parse_free_text_request
from db import (
    authenticate_user,
    create_user,
    create_login_session,
    create_password_reset_code,
    delete_login_session,
    get_action_totals,
    get_user_by_email,
    get_favorite_recipes,
    get_preference_summary,
    record_profile_feedback,
    get_recent_recipe_actions,
    get_user_by_session_token,
    get_user_preferences,
    init_db,
    record_action,
    remove_favorite_recipe,
    reset_password_with_code,
    save_user_preferences,
)
from recommendation_tools import get_recipe_by_id, recommend_recipes
from recommendation_tools import build_user_profile, persist_query_profile_signal


st.set_page_config(page_title="TastePilot", layout="wide", initial_sidebar_state="expanded")

init_db()

LOGIN_COOKIE_NAME = "tastepilot_session"
LOGIN_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "inspiration"
LIQIU_CARD_PATH = ASSET_DIR / "liqiu-card.png"
LICHUN_CARD_PATH = ASSET_DIR / "lichun-card.png"
YUSHUI_CARD_PATH = ASSET_DIR / "yushui-card.png"
JINGZHE_CARD_PATH = ASSET_DIR / "jingzhe-card.png"
CHUNFEN_CARD_PATH = ASSET_DIR / "chunfen-card.png"
QINGMING_CARD_PATH = ASSET_DIR / "qingming-card.png"
GUYU_CARD_PATH = ASSET_DIR / "guyu-card.png"
LIXIA_CARD_PATH = ASSET_DIR / "lixia-card.png"
XIAOMAN_CARD_PATH = ASSET_DIR / "xiaoman-card.png"
MANGZHONG_CARD_PATH = ASSET_DIR / "mangzhong-card.png"
XIAZHI_CARD_PATH = ASSET_DIR / "xiazhi-card.png"
XIAOSHU_CARD_PATH = ASSET_DIR / "xiaoshu-card.png"
DASHU_CARD_PATH = ASSET_DIR / "dashu-card.png"
LIDONG_CARD_PATH = ASSET_DIR / "lidong-card.png"
CHUSHU_CARD_PATH = ASSET_DIR / "chushu-card.png"
BAILU_CARD_PATH = ASSET_DIR / "bailu-card.png"
QIUFEN_CARD_PATH = ASSET_DIR / "qiufen-card.png"
HANLU_CARD_PATH = ASSET_DIR / "hanlu-card.png"
SHUANGJIANG_CARD_PATH = ASSET_DIR / "shuangjiang-card.png"
XIAOXUE_CARD_PATH = ASSET_DIR / "xiaoxue-card.png"
DAXUE_CARD_PATH = ASSET_DIR / "daxue-card.png"
DONGZHI_CARD_PATH = ASSET_DIR / "dongzhi-card.png"
XIAOHAN_CARD_PATH = ASSET_DIR / "xiaohan-card.png"
DAHAN_CARD_PATH = ASSET_DIR / "dahan-card.png"
LIQIU_SCENIC_BG_URL = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1800&q=80"
LICHUN_CARD_BG_URL = "https://images.unsplash.com/photo-1523978591478-c753949ff840?auto=format&fit=crop&w=1400&q=80"
LIXIA_CARD_BG_URL = "https://images.unsplash.com/photo-1467453678174-768ec283a940?auto=format&fit=crop&w=1400&q=80"
LIDONG_CARD_BG_URL = "https://images.unsplash.com/photo-1484318571209-661cf29a69c3?auto=format&fit=crop&w=1400&q=80"
LICHUN_SCENIC_BG_URL = "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1800&q=80"
LIXIA_SCENIC_BG_URL = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1800&q=80"
LIDONG_SCENIC_BG_URL = "https://images.unsplash.com/photo-1483664852095-d6cc6870702d?auto=format&fit=crop&w=1800&q=80"
HERO_DATE_FONT_STYLE = "editorial"

_IMAGE_DATA_URI_CACHE: dict[Path, str] = {}


def get_image_data_uri(path: Path) -> str:
    if path in _IMAGE_DATA_URI_CACHE:
        return _IMAGE_DATA_URI_CACHE[path]

    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower())
    if not mime_type:
        return ""

    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""

    data_uri = f"data:{mime_type};base64,{encoded}"
    _IMAGE_DATA_URI_CACHE[path] = data_uri
    return data_uri


def resolve_image_source(image_ref: str | Path) -> str:
    if isinstance(image_ref, Path):
        return get_image_data_uri(image_ref)
    return image_ref


def format_hero_date_label(now: datetime | None = None) -> str:
    current_dt = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    return f"{current_dt.month}月{current_dt.day}日"

st.markdown(
    """
    <style>
    :root,
    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] * {
        color-scheme: light !important;
    }
    .stApp {
        background-image:
            linear-gradient(rgba(255, 252, 248, 0.91), rgba(255, 247, 240, 0.94)),
            url("https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1800&q=80");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    [data-testid="stToolbar"] {
        display: flex !important;
        position: fixed;
        top: 0;
        left: 0;
        width: 72px;
        height: 72px;
        z-index: 999;
        background: transparent !important;
        pointer-events: none;
    }
    [data-testid="stToolbar"] button:not([data-testid="stExpandSidebarButton"]) {
        display: none !important;
    }
    [data-testid="stDecoration"] {
        display: none;
    }
    #MainMenu,
    footer {
        display: none !important;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1.35rem;
    }
    [data-testid="collapsedControl"],
    [data-testid="stExpandSidebarButton"] {
        display: flex !important;
        position: fixed;
        top: 1rem;
        left: 0.9rem;
        z-index: 1000;
        border-radius: 999px;
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.96) 0%,
            rgba(255, 242, 231, 0.9) 100%
        ) !important;
        border: 1px solid rgba(221, 186, 157, 0.92) !important;
        box-shadow:
            0 10px 22px rgba(151, 104, 71, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.72) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="stExpandSidebarButton"] svg {
        fill: #8c5538 !important;
    }
    [data-testid="stExpandSidebarButton"] {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
        overflow: hidden !important;
        pointer-events: auto !important;
    }
    [data-testid="stExpandSidebarButton"] > button,
    [data-testid="stExpandSidebarButton"] button {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        border-radius: 999px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        color: #8c5538 !important;
    }
    [data-testid="stExpandSidebarButton"] span,
    [data-testid="stExpandSidebarButton"] svg {
        color: #8c5538 !important;
        fill: #8c5538 !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            rgba(255, 250, 244, 0.92) 0%,
            rgba(255, 245, 237, 0.84) 100%
        ) !important;
        backdrop-filter: blur(14px) saturate(112%);
        -webkit-backdrop-filter: blur(14px) saturate(112%);
        border-right: 1px solid rgba(255, 255, 255, 0.4);
    }
    [data-testid="stSidebar"] * {
        color: #6e4531;
    }
    .sidebar-panel {
        padding: 1rem 0.95rem;
        margin: 0.35rem 0 0.8rem 0;
        border-radius: 22px;
        background: linear-gradient(
            180deg,
            rgba(255, 248, 241, 0.72) 0%,
            rgba(255, 242, 233, 0.54) 100%
        );
        border: 1px solid rgba(255, 255, 255, 0.34);
        box-shadow:
            0 14px 28px rgba(146, 100, 70, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.46);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    .sidebar-panel h2,
    .sidebar-panel p,
    .sidebar-panel div,
    .sidebar-panel span {
        color: #6d4531;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] > button {
        box-shadow:
            0 12px 22px rgba(150, 102, 71, 0.09),
            0 0 0 1px rgba(255, 247, 240, 0.42),
            inset 0 1px 0 rgba(255, 255, 255, 0.44);
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
        box-shadow:
            0 16px 28px rgba(150, 102, 71, 0.12),
            0 0 0 1px rgba(255, 247, 240, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.5);
    }
    [data-testid="stSidebar"] div[data-testid="stExpander"] details {
        border: none !important;
        background: transparent !important;
    }
    [data-testid="stSidebar"] div[data-testid="stExpander"] summary {
        min-height: 2.45rem;
        margin: 0.35rem 0 0.6rem 0;
        padding: 0.48rem 0.72rem !important;
        border-radius: 14px !important;
        border: 1px solid rgba(232, 207, 188, 0.34) !important;
        background: linear-gradient(
            180deg,
            rgba(255, 250, 244, 0.74) 0%,
            rgba(255, 244, 236, 0.58) 100%
        ) !important;
        box-shadow:
            0 12px 24px rgba(150, 102, 71, 0.1),
            0 0 0 1px rgba(255, 248, 241, 0.34),
            inset 0 1px 0 rgba(255, 255, 255, 0.56) !important;
        cursor: pointer;
        transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
    }
    [data-testid="stSidebar"] div[data-testid="stExpander"] summary:hover {
        transform: translateY(-1px);
        background: linear-gradient(
            180deg,
            rgba(255, 252, 248, 0.82) 0%,
            rgba(255, 247, 240, 0.66) 100%
        ) !important;
        box-shadow:
            0 15px 28px rgba(150, 102, 71, 0.13),
            0 0 0 1px rgba(255, 248, 241, 0.42),
            inset 0 1px 0 rgba(255, 255, 255, 0.62) !important;
    }
    [data-testid="stSidebar"] div[data-testid="stExpander"] summary svg,
    [data-testid="stSidebar"] div[data-testid="stExpander"] summary span,
    [data-testid="stSidebar"] div[data-testid="stExpander"] summary p {
        color: #6e4531 !important;
        fill: #6e4531 !important;
        font-weight: 600;
    }
    .main * {
        font-family: Georgia, "Times New Roman", serif;
    }
    .hero-card {
        position: relative;
        overflow: hidden;
        padding: 1.6rem 1.7rem;
        border-radius: 34px;
        background: linear-gradient(
            145deg,
            rgba(255, 249, 243, 0.82) 0%,
            rgba(255, 243, 232, 0.62) 100%
        );
        color: #4f2f24;
        box-shadow:
            0 16px 34px rgba(151, 77, 39, 0.07),
            inset 0 1px 0 rgba(255, 255, 255, 0.34);
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.26);
        backdrop-filter: blur(10px) saturate(118%);
        -webkit-backdrop-filter: blur(10px) saturate(118%);
    }
    .hero-date {
        position: absolute;
        top: 1.25rem;
        right: 1.45rem;
        z-index: 2;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 112px;
        padding: 0.52rem 0.9rem 0.46rem;
        border-radius: 999px;
        background: rgba(255, 249, 242, 0.5);
        border: 1px solid rgba(230, 205, 184, 0.58);
        box-shadow:
            0 10px 22px rgba(152, 99, 66, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.55);
        color: #9a5b3a;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        line-height: 1;
        white-space: nowrap;
    }
    .hero-date--editorial {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.08rem;
        font-weight: 600;
        letter-spacing: 0.08em;
    }
    .hero-date--songti {
        font-family: "Songti SC", "STSong", "Songti TC", serif;
        font-size: 1.02rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .hero-date--modern {
        font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hero-title {
        font-size: 2.7rem;
        font-weight: 700;
        margin-bottom: 0.42rem;
        color: #7d3127;
    }
    .hero-subtitle {
        font-size: 1rem;
        line-height: 1.68;
        color: #7a5644;
        max-width: 520px;
    }
    .hero-shell {
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(240px, 0.8fr);
        gap: 1rem;
        align-items: center;
    }
    .hero-kicker {
        display: inline-block;
        padding: 0.3rem 0.62rem;
        border-radius: 999px;
        background: rgba(209, 108, 66, 0.12);
        color: #b25b33;
        font-size: 0.74rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.78rem;
    }
    .hero-visual {
        position: relative;
        height: 220px;
        border-radius: 24px;
        background:
            radial-gradient(circle at 28% 24%, rgba(255, 214, 170, 0.64), transparent 20%),
            radial-gradient(circle at 74% 30%, rgba(255, 159, 109, 0.34), transparent 18%),
            linear-gradient(145deg, rgba(255, 227, 201, 0.56) 0%, rgba(255, 206, 158, 0.42) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.42),
            0 10px 20px rgba(176, 112, 73, 0.06);
    }
    .hero-shape {
        position: absolute;
        border-radius: 28px;
        transform: rotate(-7deg);
    }
    .hero-shape.one {
        width: 112px;
        height: 88px;
        top: 30px;
        left: 22px;
        background: linear-gradient(145deg, #fff5ee 0%, #ffe1cd 100%);
        box-shadow: 0 12px 26px rgba(199, 109, 58, 0.14);
    }
    .hero-shape.two {
        width: 102px;
        height: 122px;
        right: 24px;
        top: 22px;
        background: linear-gradient(145deg, #d66a41 0%, #f29d62 100%);
        transform: rotate(10deg);
        box-shadow: 0 14px 28px rgba(188, 96, 44, 0.18);
    }
    .hero-shape.three {
        width: 160px;
        height: 90px;
        bottom: 20px;
        left: 58px;
        background: linear-gradient(145deg, #82372d 0%, #ab4f33 100%);
        transform: rotate(-2deg);
        box-shadow: 0 14px 30px rgba(125, 57, 33, 0.14);
    }
    .hero-dot {
        position: absolute;
        border-radius: 999px;
        background: rgba(255, 246, 236, 0.72);
    }
    .hero-dot.a {
        width: 14px;
        height: 14px;
        right: 150px;
        top: 42px;
    }
    .hero-dot.b {
        width: 10px;
        height: 10px;
        right: 52px;
        bottom: 82px;
    }
    .hero-mini-card {
        position: absolute;
        padding: 0.62rem 0.78rem;
        border-radius: 16px;
        background: rgba(255, 250, 244, 0.6);
        backdrop-filter: blur(12px) saturate(118%);
        -webkit-backdrop-filter: blur(12px) saturate(118%);
        box-shadow:
            0 8px 18px rgba(157, 94, 55, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.24);
        color: #714430;
        font-size: 0.84rem;
    }
    .hero-mini-card.top {
        top: 18px;
        left: 88px;
    }
    .hero-mini-card.bottom {
        right: 16px;
        bottom: 16px;
    }
    .hero-mini-title {
        font-size: 0.68rem;
        color: #b16742;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.18rem;
    }
    .hero-emoji {
        font-size: 1.4rem;
        margin-right: 0.3rem;
    }
    .seasonal-card-shell {
        margin: 0.2rem 0 1rem;
    }
    .seasonal-card {
        position: relative;
        min-height: 340px;
        border-radius: 30px;
        overflow: hidden;
        background-size: cover;
        background-position: center;
        box-shadow:
            0 20px 40px rgba(130, 82, 49, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.32);
        cursor: pointer;
        user-select: none;
        -webkit-user-select: none;
    }
    .seasonal-card * {
        user-select: none;
        -webkit-user-select: none;
    }
    .seasonal-card-overlay {
        min-height: 340px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: flex-start;
        padding: 1.6rem 1.7rem 1.55rem;
        background:
            linear-gradient(90deg, rgba(76, 49, 32, 0.1) 0%, rgba(76, 49, 32, 0.04) 25%, rgba(76, 49, 32, 0) 58%),
            linear-gradient(180deg, rgba(255, 252, 245, 0.03) 0%, rgba(79, 46, 29, 0.16) 100%);
    }
    .seasonal-card-link,
    .seasonal-card-link:link,
    .seasonal-card-link:visited,
    .seasonal-card-link:hover,
    .seasonal-card-link:active {
        position: absolute;
        top: 1.15rem;
        right: 1.2rem;
        color: rgba(255, 250, 244, 0.94) !important;
        font-size: 0.9rem;
        font-weight: 600;
        line-height: 1.4;
        text-decoration: none !important;
        text-shadow: 0 8px 18px rgba(68, 39, 22, 0.22);
        border-bottom: none !important;
        padding-bottom: 0;
        transition: opacity 160ms ease;
        -webkit-text-fill-color: rgba(255, 250, 244, 0.94) !important;
        transform: none !important;
    }
    .seasonal-card-link:hover {
        opacity: 0.86;
        font-size: 0.9rem !important;
    }
    .st-key-seasonal_card_trigger {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    .st-key-seasonal_card_trigger [data-testid="stButton"] {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
    }
    .st-key-seasonal_card_trigger [data-testid="stButton"] > button {
        width: 0 !important;
        min-height: 0 !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        background: transparent !important;
        color: transparent !important;
        box-shadow: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    .st-key-seasonal_card_trigger [data-testid="stButton"] > button:hover,
    .st-key-seasonal_card_trigger [data-testid="stButton"] > button:focus,
    .st-key-seasonal_card_trigger [data-testid="stButton"] > button:active {
        background: transparent !important;
        color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        transform: none !important;
        opacity: 0 !important;
    }
    .seasonal-card-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.36rem;
        padding: 0.36rem 0.72rem;
        border-radius: 999px;
        background: rgba(255, 250, 244, 0.76);
        border: 1px solid rgba(255, 255, 255, 0.5);
        color: #9a5a35;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        margin-bottom: 0.82rem;
        box-shadow: 0 8px 16px rgba(125, 76, 48, 0.08);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .seasonal-card-title {
        color: #fffaf4;
        font-size: 3rem;
        line-height: 1;
        margin-bottom: 0.55rem;
        text-shadow: 0 10px 24px rgba(68, 39, 22, 0.26);
    }
    .seasonal-card-title-songti {
        font-family: "Songti SC", "STSong", "Songti TC", serif;
        font-weight: 700;
        letter-spacing: 0.06em;
    }
    .seasonal-card-subtitle {
        max-width: 360px;
        color: rgba(255, 250, 244, 0.94);
        font-size: 1rem;
        line-height: 1.7;
        margin-bottom: 0.85rem;
        text-shadow: 0 8px 18px rgba(68, 39, 22, 0.2);
    }
    .seasonal-card-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .seasonal-card-tag {
        display: inline-flex;
        align-items: center;
        padding: 0.34rem 0.74rem;
        border-radius: 999px;
        background: rgba(255, 249, 241, 0.82);
        border: 1px solid rgba(255, 255, 255, 0.46);
        color: #865137;
        font-size: 0.84rem;
        box-shadow: 0 8px 18px rgba(130, 82, 49, 0.08);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .seasonal-page-hero {
        position: relative;
        overflow: hidden;
        min-height: 420px;
        border-radius: 34px;
        background-size: cover;
        background-position: center;
        border: 1px solid rgba(255, 255, 255, 0.28);
        box-shadow:
            0 22px 48px rgba(130, 82, 49, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        margin-bottom: 1.1rem;
    }
    .seasonal-page-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            radial-gradient(circle at 18% 22%, rgba(255, 239, 215, 0.22), transparent 22%),
            linear-gradient(135deg, rgba(109, 72, 46, 0.18), transparent 45%);
        pointer-events: none;
    }
    .seasonal-page-overlay {
        position: relative;
        min-height: 420px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 1.8rem 1.9rem;
        background:
            linear-gradient(90deg, rgba(62, 38, 25, 0.34) 0%, rgba(62, 38, 25, 0.12) 44%, rgba(62, 38, 25, 0.04) 100%),
            linear-gradient(180deg, rgba(255, 252, 245, 0.06) 0%, rgba(54, 34, 23, 0.32) 100%);
    }
    .seasonal-page-route {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        margin-bottom: 0.72rem;
        padding: 0.32rem 0.68rem;
        border-radius: 999px;
        background: rgba(77, 47, 28, 0.28);
        border: 1px solid rgba(255, 244, 233, 0.22);
        color: rgba(255, 248, 240, 0.88);
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .seasonal-page-kicker {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        padding: 0.42rem 0.82rem;
        border-radius: 999px;
        background: rgba(255, 250, 244, 0.8);
        color: #9a5a35;
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        margin-bottom: 0.92rem;
        border: 1px solid rgba(255, 255, 255, 0.52);
    }
    .seasonal-page-title {
        color: #fffaf4;
        font-family: "Songti SC", "STSong", "Songti TC", serif;
        font-size: 3.15rem;
        line-height: 1.04;
        letter-spacing: 0.05em;
        margin-bottom: 0.58rem;
        text-shadow: 0 12px 28px rgba(60, 35, 20, 0.3);
    }
    .seasonal-page-copy {
        max-width: 680px;
        color: rgba(255, 250, 244, 0.96);
        font-size: 1.02rem;
        line-height: 1.75;
        margin-bottom: 0.92rem;
        text-shadow: 0 8px 20px rgba(60, 35, 20, 0.22);
    }
    .seasonal-page-meta {
        max-width: 620px;
        color: rgba(255, 250, 244, 0.9);
        font-size: 0.92rem;
        line-height: 1.65;
        margin-bottom: 0.92rem;
    }
    .seasonal-switch-label {
        color: rgba(138, 55, 40, 0.74);
        font-size: 0.84rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 0 0 0.55rem 0.15rem;
    }
    .st-key-seasonal_term_switcher [data-testid="stHorizontalBlock"] {
        gap: 0.52rem !important;
    }
    .st-key-seasonal_term_switcher [data-testid="stButton"] > button {
        min-height: 2.25rem;
        border-radius: 999px;
        padding: 0.18rem 0.9rem !important;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.88), rgba(255, 244, 234, 0.78)) !important;
        color: #8b5334 !important;
        border: 1px solid rgba(221, 186, 157, 0.62) !important;
        box-shadow:
            0 8px 18px rgba(149, 97, 63, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
    }
    .st-key-seasonal_term_switcher [data-testid="stButton"] > button:hover {
        color: #7b4225 !important;
        border-color: rgba(210, 167, 133, 0.82) !important;
        background: linear-gradient(180deg, rgba(255, 253, 249, 0.96), rgba(255, 247, 238, 0.86)) !important;
    }
    .seasonal-page-actions {
        margin: 0.15rem 0 1.15rem;
    }
    .st-key-seasonal_main_type_filter_shell {
        padding: 0.95rem 1.05rem 0.85rem;
        margin: 0.15rem 0 1rem;
        border-radius: 22px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.82), rgba(255, 246, 238, 0.7));
        border: 1px solid rgba(255, 255, 255, 0.32);
        box-shadow: 0 10px 24px rgba(149, 97, 63, 0.05);
    }
    .st-key-seasonal_main_type_filter_shell [data-testid="stSelectbox"] label {
        color: #7d3127 !important;
        font-weight: 700 !important;
    }
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] > div {
        min-height: 2.9rem;
        border-radius: 15px !important;
        background: rgba(255, 253, 249, 0.92) !important;
        border-color: rgba(221, 186, 157, 0.62) !important;
    }
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] *,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input {
        color: #7b4d37 !important;
        -webkit-text-fill-color: #7b4d37 !important;
    }
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input {
        cursor: pointer !important;
    }
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input {
        caret-color: transparent !important;
        user-select: none !important;
    }
    .st-key-seasonal_main_type_filter_shell [data-testid="stCaptionContainer"],
    .st-key-seasonal_main_type_filter_shell [data-testid="stCaptionContainer"] * {
        color: rgba(123, 77, 55, 0.78) !important;
        -webkit-text-fill-color: rgba(123, 77, 55, 0.78) !important;
    }
    .st-key-seasonal_action_shell [data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
    }
    .st-key-seasonal_action_shell [data-testid="stButton"] > button {
        min-height: 3.05rem;
        border-radius: 18px;
        font-weight: 700;
    }
    .st-key-seasonal_action_shell [data-testid="stColumn"]:first-child [data-testid="stButton"] > button {
        background: linear-gradient(135deg, rgba(196, 88, 57, 0.92) 0%, rgba(229, 126, 79, 0.84) 100%) !important;
        color: #fff7f0 !important;
        border: 1px solid rgba(255, 231, 216, 0.26) !important;
        box-shadow:
            0 14px 28px rgba(176, 83, 49, 0.18),
            inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
    }
    .st-key-seasonal_action_shell [data-testid="stColumn"]:first-child [data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, rgba(205, 93, 61, 0.95) 0%, rgba(236, 134, 87, 0.88) 100%) !important;
    }
    .st-key-seasonal_action_shell [data-testid="stColumn"]:last-child [data-testid="stButton"] > button {
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.78) 0%, rgba(255, 245, 237, 0.68) 100%) !important;
        color: #8b5b42 !important;
        border: 1px solid rgba(223, 192, 169, 0.78) !important;
        box-shadow:
            0 10px 20px rgba(154, 102, 72, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.52) !important;
    }
    .st-key-seasonal_action_shell [data-testid="stColumn"]:last-child [data-testid="stButton"] > button:hover {
        background: linear-gradient(180deg, rgba(255, 252, 248, 0.9) 0%, rgba(255, 247, 240, 0.8) 100%) !important;
        color: #7b4d36 !important;
    }
    .seasonal-section-card {
        padding: 1.25rem 1.28rem;
        border-radius: 28px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.78), rgba(255, 247, 239, 0.64));
        border: 1px solid rgba(255, 255, 255, 0.24);
        box-shadow:
            0 12px 28px rgba(154, 102, 72, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        color: #6c4531;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    .seasonal-section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #7d3127;
        margin-bottom: 0.35rem;
    }
    .seasonal-section-copy {
        color: #7b5a47;
        line-height: 1.7;
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
    .seasonal-tag-groups {
        display: flex;
        flex-wrap: wrap;
        gap: 0.7rem;
        margin: 0.1rem 0 0.7rem 0;
    }
    .seasonal-tag-group {
        min-width: 180px;
        padding: 0.78rem 0.86rem 0.58rem;
        border-radius: 18px;
        background: rgba(255, 248, 240, 0.14);
        border: 1px solid rgba(255, 245, 236, 0.22);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .seasonal-tag-group-title {
        color: rgba(255, 245, 236, 0.82);
        font-size: 0.74rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.48rem;
    }
    .seasonal-tag-group .skill-chip {
        background: rgba(255, 245, 233, 0.92);
        color: #9f5b34;
        border: 1px solid rgba(214, 169, 137, 0.34);
        margin: 0 0.32rem 0.32rem 0;
    }
    .main-type-card {
        padding: 0.82rem 1.04rem 0.62rem;
        border-radius: 20px 20px 8px 8px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.76), rgba(255, 246, 238, 0.52));
        border: 1px solid rgba(219, 176, 141, 0.3);
        border-bottom: none;
        box-shadow:
            0 8px 18px rgba(149, 97, 63, 0.04),
            inset 0 1px 0 rgba(255, 255, 255, 0.34);
        color: #6b4530;
        margin: 0.66rem 0 0;
    }
    .main-type-title {
        color: #8a3728;
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 0.16rem;
    }
    .main-type-copy {
        color: rgba(107, 69, 48, 0.72);
        font-size: 0.84rem;
        line-height: 1.45;
        margin-bottom: 0;
    }
    .main-type-warning {
        color: rgba(138, 55, 40, 0.84);
        font-weight: 650;
        font-size: 0.9rem;
        margin: 0.28rem 0 0.2rem;
    }
    .st-key-selected_main_types div[data-baseweb="select"] > div,
    .st-key-selected_main_types div[data-baseweb="select"] > div > div,
    .st-key-main_type_picker div[data-baseweb="select"] > div,
    .st-key-main_type_picker div[data-baseweb="select"] > div > div,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] > div,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] > div > div {
        background: linear-gradient(180deg, rgba(255, 253, 249, 0.98), rgba(255, 248, 241, 0.94)) !important;
        border: 1px solid rgba(203, 133, 89, 0.48) !important;
        border-radius: 0 0 18px 18px !important;
        box-shadow:
            0 10px 22px rgba(159, 95, 58, 0.055),
            inset 0 1px 0 rgba(255, 255, 255, 0.46) !important;
        color: #5e3b2a !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"],
    .st-key-main_type_picker [data-baseweb="tag"],
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] {
        background: linear-gradient(180deg, rgba(248, 234, 223, 0.96) 0%, rgba(231, 203, 182, 0.92) 100%) !important;
        color: #7b4f39 !important;
        border: 1px solid rgba(177, 136, 109, 0.28) !important;
        border-radius: 999px !important;
        box-shadow:
            0 6px 14px rgba(137, 102, 80, 0.10),
            inset 0 1px 0 rgba(255, 255, 255, 0.42) !important;
        font-weight: 700 !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"] > *,
    .st-key-main_type_picker [data-baseweb="tag"] > *,
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] > * {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"] span,
    .st-key-selected_main_types [data-baseweb="tag"] svg,
    .st-key-selected_main_types [data-baseweb="tag"] path,
    .st-key-selected_main_types [class*="multiValue"],
    .st-key-main_type_picker [data-baseweb="tag"] span,
    .st-key-main_type_picker [data-baseweb="tag"] svg,
    .st-key-main_type_picker [data-baseweb="tag"] path,
    .st-key-main_type_picker [class*="multiValue"],
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] span,
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] svg,
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] path,
    .st-key-seasonal_main_type_filter_shell [class*="multiValue"] {
        color: #7b4f39 !important;
        fill: #7b4f39 !important;
        background: transparent !important;
        -webkit-text-fill-color: #7b4f39 !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"] [role="button"],
    .st-key-main_type_picker [data-baseweb="tag"] [role="button"],
    .st-key-seasonal_main_type_filter_shell [data-baseweb="tag"] [role="button"] {
        background: transparent !important;
        color: #7b4f39 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [data-baseweb="tag"],
    .st-key-main_type_picker div[data-baseweb="select"] [data-baseweb="tag"],
    .st-key-selected_main_types div[data-baseweb="select"] span[data-baseweb="tag"],
    .st-key-main_type_picker div[data-baseweb="select"] span[data-baseweb="tag"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [data-baseweb="tag"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] span[data-baseweb="tag"] {
        background: linear-gradient(180deg, rgba(248, 234, 223, 0.98), rgba(231, 203, 182, 0.94)) !important;
        background-color: rgba(238, 214, 197, 0.98) !important;
        color: #7b4f39 !important;
        border: 1px solid rgba(177, 136, 109, 0.34) !important;
        border-radius: 999px !important;
        box-shadow:
            0 6px 14px rgba(137, 102, 80, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.46) !important;
        -webkit-text-fill-color: #7b4f39 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [data-baseweb="tag"] *,
    .st-key-main_type_picker div[data-baseweb="select"] [data-baseweb="tag"] *,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [data-baseweb="tag"] * {
        color: #7b4f39 !important;
        fill: #7b4f39 !important;
        background-color: transparent !important;
        -webkit-text-fill-color: #7b4f39 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] svg,
    .st-key-selected_main_types div[data-baseweb="select"] path,
    .st-key-main_type_picker div[data-baseweb="select"] svg,
    .st-key-main_type_picker div[data-baseweb="select"] path,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] svg,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] path {
        color: #8a4d2b !important;
        fill: #8a4d2b !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] input::placeholder,
    .st-key-main_type_picker div[data-baseweb="select"] input::placeholder,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input::placeholder {
        color: #8a4d2b !important;
        opacity: 1 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"],
    .st-key-main_type_picker div[data-baseweb="select"],
    .st-key-selected_main_types div[data-baseweb="select"] input,
    .st-key-main_type_picker div[data-baseweb="select"] input,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input {
        cursor: pointer !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] input,
    .st-key-main_type_picker div[data-baseweb="select"] input,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] input {
        caret-color: transparent !important;
        user-select: none !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [role="combobox"],
    .st-key-main_type_picker div[data-baseweb="select"] [role="combobox"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [role="combobox"] {
        caret-color: transparent !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [data-baseweb="tag"] + div input,
    .st-key-main_type_picker div[data-baseweb="select"] [data-baseweb="tag"] + div input,
    .st-key-selected_main_types div[data-baseweb="select"] [class*="multiValue"] + div input,
    .st-key-main_type_picker div[data-baseweb="select"] [class*="multiValue"] + div input,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [data-baseweb="tag"] + div input,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [class*="multiValue"] + div input {
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        padding: 0 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [class*="placeholder"],
    .st-key-selected_main_types div[data-baseweb="select"] [class*="Placeholder"],
    .st-key-main_type_picker div[data-baseweb="select"] [class*="placeholder"],
    .st-key-main_type_picker div[data-baseweb="select"] [class*="Placeholder"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [class*="placeholder"],
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] [class*="Placeholder"] {
        color: #8a4d2b !important;
        -webkit-text-fill-color: #8a4d2b !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] .st-dg.st-cq,
    .st-key-main_type_picker div[data-baseweb="select"] .st-dg.st-cq,
    .st-key-selected_main_types div[data-baseweb="select"] .st-dg.st-cq *,
    .st-key-main_type_picker div[data-baseweb="select"] .st-dg.st-cq *,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] .st-dg.st-cq,
    .st-key-seasonal_main_type_filter_shell div[data-baseweb="select"] .st-dg.st-cq * {
        color: #8a4d2b !important;
        -webkit-text-fill-color: #8a4d2b !important;
        opacity: 1 !important;
    }
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] ul[role="listbox"],
    div[data-baseweb="popover"] [data-baseweb="menu"],
    div[data-baseweb="popover"] [role="listbox"] {
        background: linear-gradient(180deg, rgba(255, 247, 237, 0.98), rgba(249, 226, 207, 0.96)) !important;
        border: 1px solid rgba(203, 133, 89, 0.38) !important;
        box-shadow: 0 14px 28px rgba(101, 63, 43, 0.16) !important;
    }
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] [role="option"] {
        color: #6b3f2a !important;
        background: transparent !important;
    }
    div[data-baseweb="popover"] li *,
    div[data-baseweb="popover"] [role="option"] * {
        color: #6b3f2a !important;
        -webkit-text-fill-color: #6b3f2a !important;
    }
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] [role="option"]:hover,
    div[data-baseweb="popover"] li[aria-selected="true"],
    div[data-baseweb="popover"] [aria-selected="true"] {
        background: rgba(232, 151, 104, 0.18) !important;
        color: #7a3423 !important;
    }
    .st-key-selected_main_types input,
    .st-key-main_type_picker input {
        color: #5e3b2a !important;
        -webkit-text-fill-color: #5e3b2a !important;
    }
    .selected-tags-label {
        color: rgba(138, 55, 40, 0.72);
        font-weight: 600;
        font-size: 0.9rem;
        padding-top: 0.1rem;
        margin: 0 0 0.18rem 0;
    }
    .selected-skill-row {
        margin-bottom: 0.2rem;
    }
    .prompt-skill-shell {
        position: relative;
        margin: 0 0 0.2rem 0.72rem;
        width: calc(100% - 1.44rem);
        min-height: 0;
        height: 0;
        z-index: 3;
        pointer-events: none;
    }
    .prompt-skill-toggle {
        padding-top: 0;
        pointer-events: auto;
    }
    .prompt-skill-toggle [data-testid="stPopover"] > div:first-child {
        width: 40px;
        min-width: 40px;
        max-width: 40px;
    }
    .prompt-skill-toggle [data-testid="stPopoverButton"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0 !important;
        text-align: center !important;
        padding: 0 !important;
    }
    .prompt-skill-toggle [data-testid="stPopoverButton"] > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    .prompt-skill-toggle [data-testid="stPopoverButton"] svg,
    .prompt-skill-toggle [data-testid="stPopoverButton"] path {
        display: none !important;
    }
    .prompt-skill-tags {
        padding-top: 0.08rem;
        pointer-events: auto;
    }
    .st-key-prompt_skill_shell {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        position: relative;
        z-index: 5;
    }
    .st-key-prompt_skill_shell [data-testid="stHorizontalBlock"] {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
    }
    .st-key-prompt_actions {
        margin-top: -4.1rem !important;
        position: relative;
        z-index: 10;
        pointer-events: auto !important;
        isolation: isolate;
    }
    .followup-shell {
        margin-top: 1rem;
        margin-bottom: 0.75rem;
    }
    .followup-title {
        font-size: 1.7rem;
        font-weight: 700;
        color: #8a3728;
        line-height: 1.15;
        margin-bottom: 0.32rem;
    }
    .followup-copy {
        color: rgba(138, 55, 40, 0.72);
        font-size: 1rem;
        line-height: 1.65;
    }
    .selected-skill-button div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 2.05rem;
        height: 2.05rem;
        border-radius: 999px;
        padding: 0.1rem 0.52rem !important;
        background: linear-gradient(180deg, rgba(255, 249, 242, 0.86) 0%, rgba(255, 242, 230, 0.76) 100%);
        color: #9a5931;
        border: 1px solid rgba(219, 176, 141, 0.72);
        font-size: 0.84rem;
        font-weight: 600;
        box-shadow:
            0 8px 18px rgba(159, 110, 79, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.42);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .selected-skill-button div[data-testid="stButton"] > button:hover {
        color: #87471f;
        border-color: rgba(205, 154, 116, 0.84);
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.94) 0%, rgba(255, 245, 236, 0.82) 100%);
    }
    .selected-skill-button div[data-testid="stButton"] > button p {
        font-size: 0.84rem;
        line-height: 1;
    }
    @media (max-width: 700px) {
        .selected-tags-label {
            color: rgba(138, 55, 40, 0.72);
            font-size: 0.82rem;
            margin: 0 0 0.12rem 0;
            padding-top: 0;
        }
        .selected-skill-row {
            display: flex !important;
            flex-wrap: wrap !important;
            align-items: flex-start !important;
            justify-content: flex-start !important;
            gap: 0.38rem 0.42rem !important;
            margin: 0 0 0.32rem 0 !important;
        }
        .selected-skill-row [data-testid="stColumn"] {
            width: auto !important;
            min-width: 0 !important;
            flex: 0 0 auto !important;
        }
        .selected-skill-row [data-testid="stVerticalBlock"] {
            width: auto !important;
            min-width: 0 !important;
        }
        .selected-skill-button div[data-testid="stButton"] {
            width: auto !important;
        }
        .selected-skill-button div[data-testid="stButton"] > button {
            width: auto !important;
            min-width: 4.9rem;
            max-width: 7.1rem;
            min-height: 1.82rem;
            height: 1.82rem;
            padding: 0.06rem 0.58rem !important;
            font-size: 0.78rem;
            box-shadow:
                0 6px 12px rgba(159, 110, 79, 0.055),
                inset 0 1px 0 rgba(255, 255, 255, 0.4);
        }
        .selected-skill-button div[data-testid="stButton"] > button p {
            font-size: 0.78rem;
        }
        .main-type-card {
            padding: 0.72rem 0.86rem 0.54rem;
            margin: 0.52rem 0 0;
        }
        .main-type-title {
            font-size: 0.94rem;
        }
        .main-type-copy,
        .main-type-warning {
            font-size: 0.8rem;
        }
        .seasonal-card,
        .seasonal-card-overlay {
            min-height: 286px;
        }
        .seasonal-card-overlay {
            padding: 1.15rem 1.15rem 1.18rem;
        }
        .seasonal-card-link,
        .seasonal-card-link:hover,
        .seasonal-card-link:active {
            top: 0.95rem;
            right: 1rem;
            font-size: 0.82rem !important;
        }
        .seasonal-card-title {
            font-size: 2.35rem;
        }
        .seasonal-card-subtitle {
            max-width: 100%;
            font-size: 0.92rem;
        }
        .seasonal-page-hero,
        .seasonal-page-overlay {
            min-height: 320px;
        }
        .seasonal-page-overlay {
            padding: 1.2rem 1.2rem 1.28rem;
        }
        .seasonal-page-title {
            font-size: 2.38rem;
        }
        .seasonal-page-copy,
        .seasonal-page-meta {
            max-width: 100%;
            font-size: 0.92rem;
        }
        .st-key-prompt_actions {
            margin-top: -4.6rem !important;
        }
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
    .recipe-tag-stack {
        display: flex;
        flex-direction: column;
        gap: 0.42rem;
        margin: 0.18rem 0 0.8rem 0;
    }
    .recipe-tag-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
    }
    .recipe-tag-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.26rem 0.76rem;
        border-radius: 999px;
        border: 1px solid rgba(189, 122, 81, 0.18);
        font-size: 0.86rem;
        line-height: 1.2;
        white-space: nowrap;
    }
    .recipe-tag-chip-primary {
        background: rgba(255, 241, 225, 0.9);
        color: #9f552d;
    }
    .recipe-tag-chip-secondary {
        background: rgba(255, 241, 225, 0.48);
        color: #ac643a;
    }
    .recipe-tag-inline {
        color: rgba(116, 74, 52, 0.52);
        font-size: 0.82rem;
        line-height: 1.45;
        letter-spacing: 0.01em;
    }
    .recipe-card p,
    .recipe-card strong {
        color: #6a4330;
    }
    .recipe-card p {
        line-height: 1.72;
    }
    .recipe-card .recipe-description {
        color: rgba(106, 67, 48, 0.62) !important;
    }
    .metric-line {
        color: #744a34;
        margin: 0.2rem 0 0.4rem 0;
        font-weight: 600;
    }
    [class*="st-key-recipe_actions_"] [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.75rem !important;
    }
    @media (max-width: 700px) {
        [class*="st-key-recipe_actions_"] [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0.42rem !important;
        }
        [class*="st-key-recipe_actions_"] [data-testid="stColumn"] {
            width: 0 !important;
            min-width: 0 !important;
            flex: 1 1 0 !important;
        }
        [class*="st-key-recipe_actions_"] [data-testid="stButton"] > button {
            min-height: 2.75rem !important;
            padding: 0.3rem 0.32rem !important;
        }
        [class*="st-key-recipe_actions_"] [data-testid="stButton"] > button p {
            font-size: 0.76rem !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
        }
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
    .profile-shell {
        display: grid;
        gap: 1.35rem;
    }
    .profile-lead {
        padding: 1.35rem 1.4rem;
        border-radius: 28px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.78), rgba(255, 246, 238, 0.66));
        border: 1px solid rgba(255, 255, 255, 0.24);
        box-shadow:
            0 12px 28px rgba(154, 102, 72, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        color: #694330;
        margin-bottom: 0.8rem;
    }
    .profile-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.45rem;
        margin-top: 0.7rem;
    }
    .profile-card {
        padding: 1.15rem 1.1rem;
        border-radius: 24px;
        background: rgba(255, 251, 246, 0.74);
        border: 1px solid rgba(255, 255, 255, 0.24);
        box-shadow:
            0 10px 24px rgba(149, 97, 63, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.28);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 0.1rem;
    }
    .profile-card-title {
        font-size: 1.18rem;
        font-weight: 700;
        color: #7a311f;
        margin-bottom: 0.25rem;
    }
    .profile-card-copy {
        color: #7b5a47;
        line-height: 1.7;
        margin-bottom: 0.8rem;
    }
    .profile-item {
        margin-bottom: 0.9rem;
        padding-bottom: 0.85rem;
        border-bottom: 1px solid rgba(212, 182, 161, 0.28);
    }
    .profile-item:last-child {
        margin-bottom: 0;
        padding-bottom: 0;
        border-bottom: none;
    }
    .profile-item-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        color: #6d4531;
        font-weight: 600;
        margin-bottom: 0.42rem;
    }
    .profile-meter {
        width: 100%;
        height: 0.5rem;
        border-radius: 999px;
        background: rgba(226, 203, 188, 0.38);
        overflow: hidden;
        margin-bottom: 0.45rem;
    }
    .profile-meter-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(194, 111, 72, 0.9), rgba(236, 161, 102, 0.82));
    }
    .profile-item-note {
        color: #88604b;
        font-size: 0.86rem;
        line-height: 1.55;
    }
    .profile-feedback-row {
        margin: 0.58rem 0 1rem 0;
    }
    .profile-feedback-row div[data-testid="stButton"] > button {
        min-height: 2rem;
        height: 2rem;
        padding: 0 0.8rem !important;
        border-radius: 999px;
        font-size: 0.84rem;
        white-space: nowrap;
    }
    .profile-feedback-row div[data-testid="stButton"] > button p {
        white-space: nowrap;
        line-height: 1;
    }
    .profile-empty {
        padding: 1.05rem 1.1rem;
        border-radius: 18px;
        background: rgba(255, 249, 243, 0.72);
        color: #7c5a46;
        line-height: 1.7;
    }
    @media (max-width: 900px) {
        .profile-grid {
            grid-template-columns: 1fr;
        }
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
    .skill-group-meta {
        display: inline-block;
        margin-left: 0.4rem;
        color: rgba(162, 126, 104, 0.58);
        font-size: 0.72rem;
        letter-spacing: 0.02em;
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
        caret-color: #9f4f2e !important;
        border-radius: 22px !important;
        border: 1px solid rgba(225, 196, 173, 0.9) !important;
        box-shadow:
            0 10px 24px rgba(176, 128, 95, 0.08),
            0 0 0 1px rgba(255, 248, 241, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(14px) saturate(112%) !important;
        -webkit-backdrop-filter: blur(14px) saturate(112%) !important;
        outline: none !important;
        padding: 1rem 1.05rem 3.35rem 1.05rem !important;
        user-select: text !important;
        -webkit-user-select: text !important;
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
        caret-color: #cf6a42 !important;
        border: 1px solid rgba(214, 175, 145, 0.96) !important;
        box-shadow:
            0 12px 28px rgba(176, 128, 95, 0.11),
            0 0 0 2px rgba(245, 221, 202, 0.55),
            inset 0 1px 0 rgba(255, 255, 255, 0.82) !important;
    }
    .stTextArea textarea::placeholder {
        color: rgba(137, 84, 61, 0.62) !important;
    }
    input,
    textarea,
    select,
    option,
    button,
    [data-baseweb="input"],
    [data-baseweb="select"],
    [data-baseweb="popover"] {
        color-scheme: light !important;
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
    .skill-section div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(
            180deg,
            rgba(245, 225, 208, 0.96) 0%,
            rgba(232, 201, 177, 0.92) 100%
        ) !important;
        color: #7b4f39 !important;
        border: 1px solid rgba(177, 136, 109, 0.34) !important;
        box-shadow:
            0 7px 14px rgba(137, 102, 80, 0.09),
            inset 0 1px 0 rgba(255, 255, 255, 0.42) !important;
    }
    .skill-section div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: linear-gradient(
            180deg,
            rgba(247, 231, 217, 0.98) 0%,
            rgba(236, 208, 186, 0.94) 100%
        ) !important;
        color: #744934 !important;
        border: 1px solid rgba(177, 136, 109, 0.38) !important;
    }
    div[data-testid="stPopover"] > button,
    div[data-testid="stPopover"] button {
        min-height: 2.3rem;
        min-width: 2.3rem;
        border-radius: 999px;
        padding: 0 0.15rem !important;
        background: linear-gradient(
            180deg,
            rgba(255, 251, 246, 0.92) 0%,
            rgba(255, 244, 236, 0.84) 100%
        ) !important;
        color: #8c5538 !important;
        border: 1px solid rgba(226, 197, 175, 0.88) !important;
        box-shadow:
            0 8px 20px rgba(163, 118, 85, 0.08),
            0 0 0 1px rgba(255, 248, 241, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.58);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        font-size: 1.15rem;
        font-weight: 500;
    }
    div[data-testid="stPopover"] > button:hover,
    div[data-testid="stPopover"] button:hover {
        background: linear-gradient(180deg, rgba(255, 249, 242, 0.98) 0%, rgba(255, 241, 231, 0.9) 100%);
        color: #774229 !important;
        border-color: rgba(214, 178, 150, 0.95) !important;
    }
    div[data-testid="stPopover"] button svg,
    div[data-testid="stPopover"] button span,
    div[data-testid="stPopover"] button p {
        color: #8c5538 !important;
        fill: #8c5538 !important;
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
    div[data-testid="stPopoverContent"] div[data-testid="stButton"] > button,
    div[data-baseweb="popover"] div[data-testid="stButton"] > button,
    div[data-testid="stPopoverContent"] button[kind],
    div[data-baseweb="popover"] button[kind] {
        min-height: 2.55rem;
        border-radius: 16px !important;
        padding: 0.2rem 0.7rem !important;
        background: linear-gradient(
            180deg,
            rgba(255, 252, 248, 0.98) 0%,
            rgba(255, 246, 238, 0.92) 100%
        ) !important;
        color: #7a4c33 !important;
        border: 1px solid rgba(226, 195, 171, 0.58) !important;
        box-shadow:
            0 10px 20px rgba(151, 104, 71, 0.11),
            0 0 0 1px rgba(255, 248, 241, 0.52),
            inset 0 1px 0 rgba(255, 255, 255, 0.78) !important;
        backdrop-filter: blur(10px) saturate(110%) !important;
        -webkit-backdrop-filter: blur(10px) saturate(110%) !important;
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        white-space: normal !important;
        line-height: 1.3 !important;
    }
    div[data-testid="stPopoverContent"] div[data-testid="stButton"] > button:hover,
    div[data-baseweb="popover"] div[data-testid="stButton"] > button:hover,
    div[data-testid="stPopoverContent"] button[kind]:hover,
    div[data-baseweb="popover"] button[kind]:hover {
        background: linear-gradient(
            180deg,
            rgba(255, 255, 252, 1) 0%,
            rgba(255, 249, 242, 0.96) 100%
        ) !important;
        color: #6f4029 !important;
        border-color: rgba(216, 176, 145, 0.72) !important;
        box-shadow:
            0 12px 24px rgba(151, 104, 71, 0.14),
            0 0 0 1px rgba(255, 248, 241, 0.58),
            inset 0 1px 0 rgba(255, 255, 255, 0.82) !important;
    }
    div[data-testid="stPopoverContent"] div[data-testid="stButton"] > button p,
    div[data-baseweb="popover"] div[data-testid="stButton"] > button p,
    div[data-testid="stPopoverContent"] button[kind] p,
    div[data-baseweb="popover"] button[kind] p {
        color: #7a4c33 !important;
        line-height: 1.3 !important;
    }
    div[data-testid="stPopoverContent"] .skill-section div[data-testid="stButton"] > button[kind="primary"],
    div[data-baseweb="popover"] .skill-section div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(
            180deg,
            rgba(231, 193, 167, 0.98) 0%,
            rgba(214, 171, 141, 0.95) 100%
        ) !important;
        color: #693a25 !important;
        border: 1px solid rgba(171, 120, 89, 0.68) !important;
        box-shadow:
            0 12px 24px rgba(143, 91, 61, 0.16),
            0 0 0 1px rgba(255, 244, 234, 0.72),
            inset 0 1px 0 rgba(255, 255, 255, 0.56) !important;
    }
    div[data-testid="stPopoverContent"] .skill-section div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-baseweb="popover"] .skill-section div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: linear-gradient(
            180deg,
            rgba(236, 202, 178, 1) 0%,
            rgba(220, 179, 149, 0.98) 100%
        ) !important;
        color: #60311f !important;
        border-color: rgba(159, 107, 77, 0.76) !important;
    }
    div[data-testid="stPopoverContent"] .skill-section div[data-testid="stButton"] > button[kind="primary"] p,
    div[data-baseweb="popover"] .skill-section div[data-testid="stButton"] > button[kind="primary"] p {
        color: #693a25 !important;
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
        .hero-date {
            top: 1rem;
            right: 1rem;
            min-width: 96px;
            padding: 0.44rem 0.72rem 0.4rem;
        }
        .hero-visual {
            height: 180px;
        }
        .hero-title {
            font-size: 2.2rem;
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

SKILL_GROUP_META = {
    "此刻适合": "按时段精选",
    "偏好方向": "按偏好精选",
    "心情": "可多选",
}

SKILL_GROUP_DISPLAY_LIMITS = {
    "此刻适合": 3,
    "偏好方向": 4,
    "心情": 3,
}


def build_skill_to_groups() -> dict[str, set[str]]:
    skill_to_groups: dict[str, set[str]] = {}
    all_groups = list(TIME_BASED_SKILL_GROUPS.values()) + [[MOOD_SKILL_GROUP]]
    for group_list in all_groups:
        for group_name, group_skills in group_list:
            for skill_name, _ in group_skills:
                skill_to_groups.setdefault(skill_name, set()).add(group_name)
    return skill_to_groups


SKILL_TO_GROUPS = build_skill_to_groups()

SKILL_PREFERENCE_HINTS = {
    "咖啡搭子": {"main_types": {"饮品", "甜品"}, "diet_goals": {"夜宵安慰"}},
    "轻一点": {"favorite_flavors": {"清淡"}, "diet_goals": {"均衡饮食", "减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "快手": {"time_limits": {"15 分钟内", "30 分钟内"}},
    "下饭": {"diet_goals": {"下饭解馋"}, "main_types": {"正餐主食", "正餐菜品"}},
    "省钱": {"budget_levels": {"低预算"}},
    "下午茶": {"main_types": {"饮品", "甜品", "轻食早午餐"}},
    "甜一点": {"main_types": {"甜品", "饮品"}, "diet_goals": {"夜宵安慰"}},
    "治愈一点": {"diet_goals": {"夜宵安慰"}, "favorite_flavors": {"家常"}},
    "聚餐": {"diet_goals": {"朋友聚餐"}, "main_types": {"正餐主食", "正餐菜品"}},
    "夜宵": {"diet_goals": {"夜宵安慰"}},
    "高蛋白": {"diet_goals": {"高蛋白增肌"}, "favorite_flavors": {"鲜香"}},
    "奶香": {"main_types": {"甜品", "饮品"}, "favorite_flavors": {"酸甜"}},
    "一个人": {"budget_levels": {"低预算"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "暖胃": {"diet_goals": {"夜宵安慰"}, "main_types": {"正餐主食", "正餐菜品"}},
    "低糖": {"diet_goals": {"减脂清爽"}},
    "香辣": {"favorite_flavors": {"香辣", "重口"}, "diet_goals": {"下饭解馋"}},
    "解馋": {"diet_goals": {"下饭解馋"}, "favorite_flavors": {"重口", "鲜香"}},
    "汤面": {"main_types": {"正餐菜品"}},
    "果香": {"main_types": {"饮品", "甜品"}, "favorite_flavors": {"酸口", "酸甜"}},
    "茶点": {"main_types": {"甜品", "饮品"}},
    "清淡": {"favorite_flavors": {"清淡"}, "diet_goals": {"均衡饮食", "减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "汤锅": {"main_types": {"正餐菜品"}},
    "家常": {"favorite_flavors": {"家常", "酱香"}, "diet_goals": {"均衡饮食"}},
    "不油腻": {"diet_goals": {"减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "一人食": {"budget_levels": {"低预算"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "安慰系": {"diet_goals": {"夜宵安慰"}, "favorite_flavors": {"家常", "酸甜"}},
    "解压系": {"diet_goals": {"下饭解馋"}, "favorite_flavors": {"香辣", "重口"}},
    "暖胃系": {"diet_goals": {"夜宵安慰"}, "main_types": {"正餐主食", "正餐菜品"}},
    "提神系": {"main_types": {"饮品"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "犒赏系": {"diet_goals": {"朋友聚餐"}, "main_types": {"甜品", "饮品", "正餐主食", "正餐菜品"}},
}


MAIN_TYPE_ALL_OPTION = "全部"
MAIN_TYPE_OPTIONS = ["正餐主食", "正餐菜品", "轻食早午餐", "甜品", "饮品"]
MAIN_TYPE_PICKER_OPTIONS = [MAIN_TYPE_ALL_OPTION, *MAIN_TYPE_OPTIONS]
MAIN_TYPE_ALIASES = {
    "正餐": ["正餐主食", "正餐菜品"],
    "正餐主食": ["正餐主食"],
    "正餐菜品": ["正餐菜品"],
    "家常菜肴": ["正餐菜品"],
    "汤锅粥羹": ["正餐菜品"],
    "甜品点心": ["甜品"],
}
MAIN_TYPE_HELP = {
    "正餐主食": "饭、面、粉、饼这类更偏吃饱的主食",
    "正餐菜品": "热菜、汤锅、粥羹这类更偏配菜或菜品",
    "轻食早午餐": "沙拉、能量碗、早午餐、轻正餐",
    "甜品": "甜品、烘焙、茶点、小点心",
    "饮品": "咖啡、奶茶、果茶、茶饮和特调",
}
MAIN_TYPE_COURSE_TYPES = {
    "正餐主食": {"main", "savory"},
    "正餐菜品": {"main", "savory"},
    "轻食早午餐": {"light_meal"},
    "甜品": {"dessert", "snack", "sweet"},
    "饮品": {"drink"},
}
MAIN_TYPE_PRIMARY_BUCKET = {
    "正餐主食": "main",
    "正餐菜品": "main",
    "轻食早午餐": "light_meal",
    "甜品": "dessert",
    "饮品": "drink",
}
MAIN_TYPE_STAPLE_COMPATIBILITY = {
    "正餐主食": {"饭类", "面类", "粉类", "饼类"},
    "正餐菜品": {"菜肴", "菜肴类", "汤粥", "锅物", "锅汤类"},
    "轻食早午餐": {"轻食", "面包三明治", "饭类"},
    "甜品": {"甜品"},
    "饮品": {"饮品"},
}


def normalize_ui_main_types(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        for main_type in MAIN_TYPE_ALIASES.get(value, [value]):
            if main_type in MAIN_TYPE_OPTIONS:
                normalized.append(main_type)
    return list(dict.fromkeys(normalized))


def normalize_main_type_picker_values(values: list[str]) -> list[str]:
    normalized = normalize_ui_main_types(values)
    if not normalized:
        return [MAIN_TYPE_ALL_OPTION]
    return normalized

SEASONAL_PAGE_CONFIG = {
    "立春": {
        "start_md": (2, 4),
        "title": "立春时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": LICHUN_CARD_PATH,
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "立春更适合从鲜嫩、清爽、带一点生机的味道开始想。先看香椿、春笋、春饼这些更像春天开场的东西。",
        "intro": "立春之后，味觉适合先回到鲜嫩、清爽、带一点生机的方向。我们先把这段时节更应景的食材和菜，单独拎出来给你看。",
        "seasonal_tags": ["立春", "春季时令", "咬春"],
        "display_tags": ["鲜嫩", "清爽", "香椿", "春笋", "春饼"],
        "display_tag_groups": {
            "时令食材": ["香椿", "春笋", "荠菜"],
            "适合口感": ["鲜嫩", "清爽"],
        },
        "card_tags": ["香椿", "春笋", "春饼", "春蔬小炒"],
        "main_types": ["正餐", "轻食早午餐", "甜品", "饮品"],
        "scene_note": "更适合春天刚开场时那种想吃得轻一点、鲜一点的胃口。",
    },
    "雨水": {
        "start_md": (2, 19),
        "title": "雨水时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": YUSHUI_CARD_PATH,
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "雨水更适合从鲜嫩、清润、带一点暖意的味道开始想。荠菜、春笋和豆腐羹，把早春的湿润与新鲜慢慢端上桌。",
        "intro": "雨水之后，空气开始湿润，春菜也渐渐有了鲜味。我们从荠菜、春笋、豆腐和早春嫩蔬里，挑一批清润又不失温度的菜给你看。",
        "seasonal_tags": ["雨水", "春季时令", "早春清润"],
        "display_tags": ["清润", "鲜嫩", "荠菜", "春笋", "豆腐羹"],
        "display_tag_groups": {
            "时令食材": ["荠菜", "春笋", "嫩豆腐"],
            "适合口感": ["清润", "鲜嫩"],
        },
        "card_tags": ["荠菜", "春笋", "嫩豆腐", "清润鲜羹"],
        "main_types": ["正餐", "轻食早午餐"],
        "scene_note": "更适合早春水汽渐起时，那种想吃得清润、鲜嫩又带一点暖意的胃口。",
    },
    "惊蛰": {
        "start_md": (3, 5),
        "title": "惊蛰时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": JINGZHE_CARD_PATH,
        "background_position": "center 66%",
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "惊蛰更适合从清润、鲜活、带一点辛香的味道开始想。雪梨百合、春笋和嫩芽，把仲春刚醒来的胃口慢慢打开。",
        "intro": "惊蛰之后，春意开始真正活动起来，风燥也渐渐明显。我们从雪梨、百合、春笋和嫩芽里，挑一批清润鲜活、不过分厚重的菜。",
        "seasonal_tags": ["惊蛰", "春季时令", "仲春清润"],
        "display_tags": ["清润", "鲜活", "雪梨", "百合", "春笋"],
        "display_tag_groups": {
            "时令食材": ["雪梨", "百合", "春笋"],
            "适合口感": ["清润", "鲜活"],
        },
        "card_tags": ["雪梨百合", "春笋", "嫩芽", "清润甜羹"],
        "main_types": ["正餐", "轻食早午餐", "甜品", "饮品"],
        "scene_note": "更适合春雷初动、万物渐醒时，那种想吃得清润、鲜活又有一点暖意的胃口。",
    },
    "春分": {
        "start_md": (3, 20),
        "title": "春分时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": CHUNFEN_CARD_PATH,
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "春分更适合吃得鲜嫩、舒展、不过分偏重。香椿、春笋、豆苗和一盘春日煎蛋，正好接住昼夜均分的轻盈感。",
        "intro": "春分之后，鲜嫩春菜正慢慢铺开。我们从香椿、春笋和豆苗这些当令味道里，挑一批清鲜、平衡又有春意的菜给你看。",
        "seasonal_tags": ["春分", "春季时令", "仲春尝鲜"],
        "display_tags": ["平衡", "鲜嫩", "香椿", "春笋", "豆苗"],
        "display_tag_groups": {
            "时令食材": ["香椿", "春笋", "豆苗"],
            "适合口感": ["鲜嫩", "清鲜"],
        },
        "card_tags": ["香椿", "春笋", "豆苗", "春日煎蛋"],
        "main_types": ["正餐", "轻食早午餐"],
        "scene_note": "更适合昼夜渐暖、春菜正鲜时，那种想吃得平衡又轻快的胃口。",
    },
    "清明": {
        "start_md": (4, 4),
        "title": "清明时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": QINGMING_CARD_PATH,
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "清明更适合从草木清香、软糯与春鲜里找灵感。艾草青团、春笋和马兰头，把暮春刚好的青绿味道端上桌。",
        "intro": "清明前后，艾草、春笋和田野嫩蔬正鲜。我们从青团、马兰头、春笋和青梅里，挑一批带草木香、清鲜又不失软糯的暮春味道。",
        "seasonal_tags": ["清明", "春季时令", "暮春尝青"],
        "display_tags": ["草木香", "软糯", "艾草", "春笋", "青梅"],
        "display_tag_groups": {
            "时令食材": ["艾草", "春笋", "青梅"],
            "适合口感": ["清鲜", "软糯"],
        },
        "card_tags": ["艾草青团", "春笋", "马兰头", "青梅米饮"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合暮春草木正青时，那种想吃得清鲜、软糯又带一点新绿香气的胃口。",
    },
    "谷雨": {
        "start_md": (4, 20),
        "title": "谷雨时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": GUYU_CARD_PATH,
        "page_background_url": LICHUN_SCENIC_BG_URL,
        "card_subtitle": "谷雨更适合从春茶、嫩芽与清鲜河味里找灵感。龙井虾仁、香椿豆腐和春笋，把春天最后一段鲜味留在桌上。",
        "intro": "谷雨之后，春茶新采，香椿与嫩笋也正鲜。我们从龙井、虾仁、嫩豆腐和枇杷里，挑一批清鲜、带茶香又不过分厚重的暮春味道。",
        "seasonal_tags": ["谷雨", "春季时令", "雨生百谷"],
        "display_tags": ["清鲜", "茶香", "龙井", "香椿", "春笋"],
        "display_tag_groups": {
            "时令食材": ["龙井", "香椿", "春笋"],
            "适合口感": ["清鲜", "茶香"],
        },
        "card_tags": ["龙井虾仁", "香椿豆腐", "春茶饭", "枇杷饮"],
        "main_types": ["正餐主食", "正餐菜品", "轻食早午餐", "甜品", "饮品"],
        "scene_note": "更适合春天将尽、雨润百谷时，那种想吃得清鲜、轻盈又带一点新茶香的胃口。",
    },
    "立夏": {
        "start_md": (5, 5),
        "title": "立夏时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": LIXIA_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "立夏更适合从清爽、带汁水、不过分厚重的味道开始想。番茄、黄瓜、嫩豌豆和轻盈小菜，会更像夏天刚开场的胃口。",
        "intro": "立夏之后，适合先从清爽、带汁水、不过分厚重的味道开始想。我们先把这段时节更应景的食材和菜，单独拎出来给你看。",
        "seasonal_tags": ["立夏", "夏季时令", "入夏"],
        "display_tags": ["清爽", "脆嫩", "番茄", "黄瓜", "嫩豌豆"],
        "display_tag_groups": {
            "时令食材": ["番茄", "黄瓜", "嫩豌豆"],
            "适合口感": ["清爽", "脆嫩"],
        },
        "card_tags": ["番茄", "黄瓜", "嫩豌豆", "清爽时蔬"],
        "main_types": ["正餐", "轻食早午餐", "饮品"],
        "scene_note": "更适合天气开始热起来时那种想吃得轻一点、凉快一点的节奏。",
    },
    "小满": {
        "start_md": (5, 21),
        "title": "小满时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": XIAOMAN_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "小满更适合吃一点微苦、脆嫩、不过分厚重的味道。苦瓜、豆干、青梅和嫩豆，刚好是初夏未满的清爽。",
        "intro": "小满之后，天气渐热但还没有走到盛夏。我们从苦瓜、青梅、嫩豆和清爽豆制品里，挑一批微苦回甘、轻快利落的菜。",
        "seasonal_tags": ["小满", "夏季时令", "初夏清苦"],
        "display_tags": ["微苦", "脆嫩", "苦瓜", "青梅", "嫩豆"],
        "display_tag_groups": {
            "时令食材": ["苦瓜", "青梅", "嫩豆"],
            "适合口感": ["微苦", "脆嫩"],
        },
        "card_tags": ["苦瓜", "豆干", "青梅", "清爽嫩豆"],
        "main_types": ["正餐", "轻食早午餐", "饮品"],
        "scene_note": "更适合初夏渐热但尚未酷暑时，那种想吃得清爽、微苦又有回甘的胃口。",
    },
    "芒种": {
        "start_md": (6, 5),
        "title": "芒种时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": MANGZHONG_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "芒种更适合从酸香、开胃、利落的味道开始想。青梅、仔姜、麦仁和一盘梅香鸡，把忙热交织的初夏吃得更轻快。",
        "intro": "芒种之后，麦香与梅子的酸味都到了更鲜明的时候。我们从青梅、仔姜、麦仁和清爽时蔬里，挑一批开胃又有饱足感的菜。",
        "seasonal_tags": ["芒种", "夏季时令", "煮梅食新"],
        "display_tags": ["酸香", "开胃", "青梅", "仔姜", "麦仁"],
        "display_tag_groups": {
            "时令食材": ["青梅", "仔姜", "麦仁"],
            "适合口感": ["酸香", "开胃"],
        },
        "card_tags": ["青梅仔姜鸡", "麦仁", "黄瓜", "梅香轻食"],
        "main_types": ["正餐", "轻食早午餐", "甜品", "饮品"],
        "scene_note": "更适合农忙与暑气一起渐起时，那种想吃得酸香、开胃又不拖沓的节奏。",
    },
    "夏至": {
        "start_md": (6, 21),
        "title": "夏至时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": XIAZHI_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "夏至更适合从凉面、黄瓜、绿豆和冬瓜这些清爽味道开始想。白昼最长，也让这一餐吃得轻快一点。",
        "intro": "夏至之后，暑气渐盛，胃口更需要清爽和利落。我们先从凉面、绿豆、黄瓜和冬瓜这些应季方向里，挑一批适合长夏白昼的菜。",
        "seasonal_tags": ["夏至", "夏季时令", "消暑吃面"],
        "display_tags": ["清凉", "爽口", "凉面", "绿豆", "冬瓜"],
        "display_tag_groups": {
            "时令食材": ["黄瓜", "绿豆", "冬瓜"],
            "适合口感": ["清凉", "爽口"],
        },
        "card_tags": ["麻酱凉面", "黄瓜", "绿豆", "冬瓜"],
        "main_types": ["正餐", "饮品"],
        "scene_note": "更适合白昼最长、暑气渐盛时，那种想吃得清凉又有饱足感的节奏。",
    },
    "小暑": {
        "start_md": (7, 7),
        "title": "小暑时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": XIAOSHU_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "小暑更适合从清凉、淡甜和有水汽的味道开始想。绿豆莲子、冬瓜与薄荷，把刚起势的暑热吃得轻快一点。",
        "intro": "小暑之后，热意开始变得明确，胃口也更偏向清淡和消暑。我们从绿豆、莲子、冬瓜和薄荷里，挑一批清凉爽口又不过分冰冷的味道。",
        "seasonal_tags": ["小暑", "夏季时令", "初暑清凉"],
        "display_tags": ["清凉", "淡甜", "绿豆", "莲子", "冬瓜"],
        "display_tag_groups": {
            "时令食材": ["绿豆", "莲子", "冬瓜"],
            "适合口感": ["清凉", "爽口"],
        },
        "card_tags": ["绿豆莲子羹", "冬瓜", "荷叶", "薄荷饮"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合暑气刚起、身体还在适应热意时，那种想吃得清凉、轻盈又有一点甜润的胃口。",
    },
    "大暑": {
        "start_md": (7, 22),
        "title": "大暑时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": DASHU_CARD_PATH,
        "page_background_url": LIXIA_SCENIC_BG_URL,
        "card_subtitle": "大暑更适合从清汤、水润瓜果和酸甜里找灵感。冬瓜老鸭汤、西瓜冰粉与酸梅饮，把盛夏最热的一段吃得舒服些。",
        "intro": "大暑到了，热意走到一年里最盛的时候，胃口更需要清爽与补水。我们从冬瓜、鸭肉、西瓜和乌梅里，挑一批清凉却有饱足感的盛夏味道。",
        "seasonal_tags": ["大暑", "夏季时令", "盛夏消暑"],
        "display_tags": ["消暑", "水润", "冬瓜", "鸭肉", "西瓜"],
        "display_tag_groups": {
            "时令食材": ["冬瓜", "鸭肉", "西瓜"],
            "适合口感": ["清爽", "水润"],
        },
        "card_tags": ["冬瓜老鸭汤", "西瓜冰粉", "荷香糯米鸡", "酸梅饮"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合暑热最盛、胃口容易发懒时，那种想吃得水润、清爽又不失饱足感的节奏。",
    },
    "立秋": {
        "start_md": (8, 7),
        "title": "立秋时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": LIQIU_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "暑气未散，先吃一点清润、热乎、带秋意的东西。让“今天吃什么”，从这个时节开始想。",
        "intro": "立秋之后，适合先从清润、热乎、带一点收敛感的味道开始想。我们先把这段时节更应景的菜，单独拎出来给你看。",
        "seasonal_tags": ["立秋", "秋季时令", "咬秋"],
        "display_tags": ["清润", "热汤", "梨", "莲藕", "玉米"],
        "display_tag_groups": {
            "时令食材": ["梨", "莲藕", "玉米"],
            "适合口感": ["清润", "热汤"],
        },
        "card_tags": ["梨", "莲藕", "玉米", "清润热汤"],
        "main_types": ["正餐", "甜品", "饮品"],
        "scene_note": "更适合现在这段从盛夏转向初秋的胃口和节奏。",
    },
    "处暑": {
        "start_md": (8, 23),
        "title": "处暑时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": CHUSHU_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "处暑更适合从清补、润燥、带一点秋意的味道开始想。荷香鸭饭、莲藕和秋梨，把暑气慢慢送走。",
        "intro": "处暑之后，热意开始退场，饮食也适合从消暑转向清补。我们从鸭肉、荷叶、莲藕和秋梨里，挑一批温和润燥的过渡时节味道。",
        "seasonal_tags": ["处暑", "秋季时令", "出暑清补"],
        "display_tags": ["清补", "润燥", "鸭肉", "莲藕", "秋梨"],
        "display_tag_groups": {
            "时令食材": ["鸭肉", "莲藕", "秋梨"],
            "适合口感": ["清补", "润燥"],
        },
        "card_tags": ["荷香鸭饭", "莲藕", "秋梨", "清补鲜汤"],
        "main_types": ["正餐", "甜品", "饮品"],
        "scene_note": "更适合暑气渐退、早晚转凉时，那种想吃得温和、清补又不油腻的胃口。",
    },
    "白露": {
        "start_md": (9, 7),
        "title": "白露时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": BAILU_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "白露更适合从清甜、温润、不过分燥的味道开始想。龙眼银耳、秋梨和一杯淡茶，把初秋的凉意接得更柔和。",
        "intro": "白露之后，清晨与夜晚的凉意更明显，饮食也适合慢慢转向温润。我们从龙眼、银耳、秋梨和莲子里，挑一批清甜不腻的秋日味道。",
        "seasonal_tags": ["白露", "秋季时令", "温润润燥"],
        "display_tags": ["温润", "清甜", "龙眼", "银耳", "秋梨"],
        "display_tag_groups": {
            "时令食材": ["龙眼", "银耳", "秋梨"],
            "适合口感": ["温润", "清甜"],
        },
        "card_tags": ["龙眼银耳", "秋梨", "莲子", "白露茶"],
        "main_types": ["正餐", "甜品", "饮品"],
        "scene_note": "更适合早晚凉意渐浓时，那种想吃得温润、清甜又不显厚重的胃口。",
    },
    "秋分": {
        "start_md": (9, 22),
        "title": "秋分时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": QIUFEN_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "秋分更适合从清润、温和、带一点丰收感的味道开始想。梨、莲藕、板栗和桂花，都是刚刚好的秋意。",
        "intro": "秋分之后，昼夜重新均分，味觉也适合回到温润和平衡。我们先把梨、莲藕、板栗和桂花这些秋日线索，变成一批应景的菜。",
        "seasonal_tags": ["秋分", "秋季时令", "润燥尝秋"],
        "display_tags": ["温润", "清甜", "梨", "莲藕", "板栗"],
        "display_tag_groups": {
            "时令食材": ["梨", "莲藕", "板栗"],
            "适合口感": ["温润", "清甜"],
        },
        "card_tags": ["秋梨", "莲藕", "板栗", "桂花甜汤"],
        "main_types": ["正餐", "甜品", "饮品"],
        "scene_note": "更适合凉意渐稳、秋味正盛时，那种想吃得温润又不厚重的胃口。",
    },
    "寒露": {
        "start_md": (10, 8),
        "title": "寒露时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": HANLU_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "寒露更适合从温润、坚果香和热汤里找灵感。板栗山药鸡汤、黑芝麻与菊花茶，把深秋的凉意接得稳稳的。",
        "intro": "寒露之后，空气更凉也更干，饮食适合往温润与滋养转。我们从板栗、山药、黑芝麻和菊花里，挑一批香而不腻、暖而不燥的深秋味道。",
        "seasonal_tags": ["寒露", "秋季时令", "深秋温润"],
        "display_tags": ["温润", "坚果香", "板栗", "山药", "黑芝麻"],
        "display_tag_groups": {
            "时令食材": ["板栗", "山药", "黑芝麻"],
            "适合口感": ["温润", "醇香"],
        },
        "card_tags": ["板栗山药鸡汤", "黑芝麻", "菊花茶", "莲藕煲"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合深秋凉意变清晰时，那种想吃得温润、醇香又不过分厚重的胃口。",
    },
    "霜降": {
        "start_md": (10, 23),
        "title": "霜降时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": SHUANGJIANG_CARD_PATH,
        "page_background_url": LIQIU_SCENIC_BG_URL,
        "card_subtitle": "霜降更适合从柿子的甜、根茎与热煲里找灵感。牛腩萝卜煲、柿香糯米饼和板栗饭，把晚秋吃得更扎实。",
        "intro": "霜降之后，晚秋的凉意逐渐贴近冬天，饮食也适合更温暖扎实。我们从柿子、白萝卜、山药和板栗里，挑一批甜润又暖胃的味道。",
        "seasonal_tags": ["霜降", "秋季时令", "晚秋暖食"],
        "display_tags": ["甜润", "暖胃", "柿子", "白萝卜", "板栗"],
        "display_tag_groups": {
            "时令食材": ["柿子", "白萝卜", "板栗"],
            "适合口感": ["甜润", "暖胃"],
        },
        "card_tags": ["牛腩萝卜煲", "柿香糯米饼", "山药板栗饭", "秋梨饮"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合霜意渐重、秋冬交界时，那种想吃得温暖、甜润又更有饱足感的胃口。",
    },
    "立冬": {
        "start_md": (11, 7),
        "title": "立冬时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": LIDONG_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "立冬更适合从热乎、扎实、能暖起来的味道开始想。白萝卜、大白菜、板栗和热炖锅，会更像冬天刚开场的一口。",
        "intro": "立冬之后，适合先从热乎、扎实、能暖起来的味道开始想。我们先把这段时节更应景的食材和菜，单独拎出来给你看。",
        "seasonal_tags": ["立冬", "冬季时令", "入冬"],
        "display_tags": ["暖胃", "热炖", "白萝卜", "大白菜", "板栗"],
        "display_tag_groups": {
            "时令食材": ["白萝卜", "大白菜", "板栗"],
            "适合口感": ["暖胃", "热炖"],
        },
        "card_tags": ["白萝卜", "大白菜", "板栗", "暖身炖锅"],
        "main_types": ["正餐", "甜品"],
        "scene_note": "更适合天气开始冷下来之后，那种想吃热乎、厚实一点的胃口。",
    },
    "小雪": {
        "start_md": (11, 22),
        "title": "小雪时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": XIAOXUE_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "小雪更适合从软糯、热乎、带一点甜暖的味道开始想。红糖糍粑、白菜、白萝卜和板栗，让初冬慢慢暖起来。",
        "intro": "小雪之后，寒意更清楚了，但还没到最深的冬天。我们从糯米、红糖、白菜、萝卜和板栗里，挑一批软糯暖胃的初冬味道。",
        "seasonal_tags": ["小雪", "冬季时令", "初冬暖食"],
        "display_tags": ["软糯", "甜暖", "红糖糍粑", "白菜", "白萝卜"],
        "display_tag_groups": {
            "时令食材": ["糯米", "白菜", "白萝卜"],
            "适合口感": ["软糯", "热乎"],
        },
        "card_tags": ["红糖糍粑", "白菜", "白萝卜", "板栗暖汤"],
        "main_types": ["正餐", "甜品"],
        "scene_note": "更适合初冬寒意渐起时，那种想吃软糯、热乎、能慢慢暖起来的胃口。",
    },
    "大雪": {
        "start_md": (12, 7),
        "title": "大雪时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": DAXUE_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "大雪更适合从热汤、根茎和温补的味道开始想。当归萝卜羊肉汤、白菜与板栗，让深冬的一餐更踏实。",
        "intro": "大雪之后，寒意进入更深的一段，饮食也适合往热乎和温补走。我们从羊肉、白萝卜、白菜和板栗里，挑一批扎实却不过分油腻的冬日菜。",
        "seasonal_tags": ["大雪", "冬季时令", "深冬温补"],
        "display_tags": ["温补", "热汤", "羊肉", "白萝卜", "白菜"],
        "display_tag_groups": {
            "时令食材": ["羊肉", "白萝卜", "白菜"],
            "适合口感": ["温补", "热汤"],
        },
        "card_tags": ["当归羊肉汤", "白萝卜", "白菜", "板栗"],
        "main_types": ["正餐", "甜品"],
        "scene_note": "更适合寒意渐深、身体想要热量时，那种想吃热乎、温补又踏实的胃口。",
    },
    "冬至": {
        "start_md": (12, 21),
        "title": "冬至时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": DONGZHI_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "冬至更适合围着一桌热气慢慢吃。饺子、汤圆和一碗暖汤，把一年里最长的夜晚接得更踏实。",
        "intro": "冬至到了，适合把一餐吃得热乎、有团聚感。我们从饺子、汤圆和暖汤这些熟悉的冬至味道里，挑一批适合围桌分享的选择。",
        "seasonal_tags": ["冬至", "冬季时令", "团圆暖食"],
        "display_tags": ["团圆", "暖胃", "饺子", "汤圆", "热汤"],
        "display_tag_groups": {
            "时令食物": ["饺子", "汤圆", "热汤"],
            "适合口感": ["暖胃", "热乎"],
        },
        "card_tags": ["三鲜饺子", "黑芝麻汤圆", "热汤", "围桌暖食"],
        "main_types": ["正餐", "甜品"],
        "scene_note": "更适合一年里夜晚最长的时候，和家人朋友围桌吃一顿热乎的。",
    },
    "小寒": {
        "start_md": (1, 5),
        "title": "小寒时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": XIAOHAN_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "小寒更适合从杂粮粥、根茎和热炖里找灵感。腊八粥、牛肉萝卜锅与姜枣茶，让一年最冷的一段慢慢暖起来。",
        "intro": "小寒之后，寒意进入一年里最明显的一段，饮食也适合更扎实温暖。我们从杂粮、红枣、山药和白萝卜里，挑一批热乎、有饱足感又不显油重的味道。",
        "seasonal_tags": ["小寒", "冬季时令", "隆冬暖食"],
        "display_tags": ["热乎", "暖胃", "杂粮", "山药", "白萝卜"],
        "display_tag_groups": {
            "时令食材": ["杂粮", "山药", "白萝卜"],
            "适合口感": ["热乎", "暖胃"],
        },
        "card_tags": ["腊八粥", "牛肉萝卜锅", "山药", "姜枣茶"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合隆冬寒意正深时，那种想吃得热乎、扎实又能慢慢暖起来的胃口。",
    },
    "大寒": {
        "start_md": (1, 20),
        "title": "大寒时令推荐",
        "kicker": "Solar Term Selection",
        "image_path": DAHAN_CARD_PATH,
        "page_background_url": LIDONG_SCENIC_BG_URL,
        "card_subtitle": "大寒更适合从糯米、热锅和年味里找灵感。八宝饭、山药羊肉锅与煎年糕，为二十四节气收一个暖融融的尾。",
        "intro": "大寒到了，一年的节气也走到最后一站，饮食适合热乎、扎实又带一点团聚感。我们从糯米、红枣、年糕和羊肉里，挑一批暖身又有年味的选择。",
        "seasonal_tags": ["大寒", "冬季时令", "岁末暖食"],
        "display_tags": ["糯香", "温补", "八宝饭", "年糕", "羊肉"],
        "display_tag_groups": {
            "时令食物": ["八宝饭", "年糕", "羊肉锅"],
            "适合口感": ["糯香", "温补"],
        },
        "card_tags": ["八宝饭", "山药羊肉锅", "煎年糕", "红枣核桃露"],
        "main_types": ["正餐主食", "正餐菜品", "甜品", "饮品"],
        "scene_note": "更适合一年最冷、也最接近新岁的时候，吃一顿热乎、糯香又有团聚感的饭。",
    },
}

INSPIRATION_CARD_SCHEDULE = sorted(
    [
        {"name": term_name, "kind": "solar_term", "start_md": config["start_md"]}
        for term_name, config in SEASONAL_PAGE_CONFIG.items()
    ],
    key=lambda item: item["start_md"],
)


def get_current_seasonal_term_name(now: datetime | None = None) -> str:
    current_dt = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    month_day = (current_dt.month, current_dt.day)
    active_term = INSPIRATION_CARD_SCHEDULE[-1]["name"]
    for schedule_item in INSPIRATION_CARD_SCHEDULE:
        if month_day >= tuple(schedule_item["start_md"]):
            active_term = schedule_item["name"]
        else:
            break
    return active_term


def get_current_hidden_time_slot(now: datetime | None = None) -> str:
    current_dt = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    hour = current_dt.hour
    if 5 <= hour < 11:
        return "早餐"
    if 11 <= hour < 14:
        return "午餐"
    if 14 <= hour < 17:
        return "下午茶"
    if 17 <= hour < 22:
        return "晚餐"
    return "夜宵"


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
if "selected_main_types" not in st.session_state:
    st.session_state.selected_main_types = []
if "main_type_notice" not in st.session_state:
    st.session_state.main_type_notice = ""
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "last_query" not in st.session_state:
    st.session_state.last_query = {}
if "last_query_signature" not in st.session_state:
    st.session_state.last_query_signature = None
if "excluded_recipe_ids" not in st.session_state:
    st.session_state.excluded_recipe_ids = []
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "sync_prompt_input" not in st.session_state:
    st.session_state.sync_prompt_input = False
if "auth_session_token" not in st.session_state:
    st.session_state.auth_session_token = None
if "pending_login_cookie_token" not in st.session_state:
    st.session_state.pending_login_cookie_token = None
if "clear_login_cookie" not in st.session_state:
    st.session_state.clear_login_cookie = False
if "preference_notice" not in st.session_state:
    st.session_state.preference_notice = ""
if "reset_notice" not in st.session_state:
    st.session_state.reset_notice = ""
if "reset_debug_code" not in st.session_state:
    st.session_state.reset_debug_code = ""
if "auth_notice" not in st.session_state:
    st.session_state.auth_notice = ""
if "reset_email" not in st.session_state:
    st.session_state.reset_email = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "recommend"
if "profile_notice" not in st.session_state:
    st.session_state.profile_notice = ""
if "seasonal_term" not in st.session_state:
    st.session_state.seasonal_term = get_current_seasonal_term_name()
if "seasonal_recommendations" not in st.session_state:
    st.session_state.seasonal_recommendations = []
if "seasonal_excluded_recipe_ids" not in st.session_state:
    st.session_state.seasonal_excluded_recipe_ids = []
if "seasonal_main_type_filter" not in st.session_state:
    st.session_state.seasonal_main_type_filter = "全部"
if "seasonal_main_types" not in st.session_state:
    legacy_seasonal_main_type = st.session_state.get("seasonal_main_type_filter", MAIN_TYPE_ALL_OPTION)
    st.session_state.seasonal_main_types = (
        [legacy_seasonal_main_type]
        if legacy_seasonal_main_type in MAIN_TYPE_OPTIONS
        else [MAIN_TYPE_ALL_OPTION]
    )


def set_auth_mode(mode: str) -> None:
    st.session_state.auth_mode = mode
    if mode == "forgot_password":
        st.query_params["auth_mode"] = "forgot_password"
    else:
        st.query_params.pop("auth_mode", None)


def sync_auth_mode_from_query() -> None:
    query_mode = st.query_params.get("auth_mode")
    if query_mode == "forgot_password":
        st.session_state.auth_mode = "forgot_password"
    elif st.session_state.auth_mode == "forgot_password":
        st.session_state.auth_mode = "login"


def sync_page_from_query() -> None:
    page = st.query_params.get("page")
    if page in {"recommend", "profile", "seasonal", "seasonal_preview"}:
        st.session_state.current_page = page
    if page == "seasonal_preview":
        preview_term = st.query_params.get("term")
        if preview_term in SEASONAL_PAGE_CONFIG:
            if st.session_state.seasonal_term != preview_term:
                st.session_state.seasonal_recommendations = []
                st.session_state.seasonal_excluded_recipe_ids = []
            st.session_state.seasonal_term = preview_term


def set_page_query(page: str) -> None:
    st.query_params["page"] = page
    st.query_params.pop("term", None)
    st.query_params.pop("seasonal_debug", None)
    st.query_params.pop("preview_term", None)


def sync_login_cookie() -> None:
    pending_token = st.session_state.get("pending_login_cookie_token")
    if pending_token:
        components.html(
            f"""
            <script>
            const secure = window.location.protocol === "https:" ? "; Secure" : "";
            document.cookie = "{LOGIN_COOKIE_NAME}={pending_token}; path=/; max-age={LOGIN_COOKIE_MAX_AGE}; SameSite=Lax" + secure;
            </script>
            """,
            height=0,
        )
        st.session_state.pending_login_cookie_token = None

    if st.session_state.get("clear_login_cookie"):
        components.html(
            f"""
            <script>
            document.cookie = "{LOGIN_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
            </script>
            """,
            height=0,
        )
        st.session_state.clear_login_cookie = False


def render_page_scroll_bridge() -> None:
    page_key = st.session_state.get("current_page", "recommend")
    components.html(
        f"""
        <script>
        const parentWindow = window.parent;
        const parentDoc = parentWindow.document;
        const pageKey = {page_key!r};

        function scrollTastePilotToTop() {{
          const scrollTargets = [
            parentWindow,
            parentDoc.documentElement,
            parentDoc.body,
            parentDoc.querySelector('[data-testid="stAppViewContainer"]'),
            parentDoc.querySelector('section[data-testid="stMain"]'),
            parentDoc.querySelector('.stMain'),
            parentDoc.querySelector('.main'),
          ].filter(Boolean);

          scrollTargets.forEach((target) => {{
            try {{
              if (target === parentWindow) {{
                target.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
              }} else {{
                target.scrollTop = 0;
                target.scrollLeft = 0;
              }}
            }} catch (error) {{}}
          }});
        }}

        if (parentDoc.body.dataset.tastepilotPageKey !== pageKey) {{
          parentDoc.body.dataset.tastepilotPageKey = pageKey;
          scrollTastePilotToTop();
          parentWindow.requestAnimationFrame(scrollTastePilotToTop);
          parentWindow.setTimeout(scrollTastePilotToTop, 80);
          parentWindow.setTimeout(scrollTastePilotToTop, 220);
        }}
        </script>
        """,
        height=0,
    )


def render_sidebar_toggle_bridge() -> None:
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        const BUTTON_ID = "tastepilot-sidebar-toggle";

        function ensureButton() {
          let button = parentDoc.getElementById(BUTTON_ID);
          if (!button) {
            button = parentDoc.createElement("button");
            button.id = BUTTON_ID;
            button.type = "button";
            button.innerText = "☰";
            Object.assign(button.style, {
              position: "fixed",
              top: "16px",
              left: "14px",
              zIndex: "1002",
              width: "42px",
              height: "42px",
              borderRadius: "999px",
              border: "1px solid rgba(221, 186, 157, 0.92)",
              background: "linear-gradient(180deg, rgba(255, 251, 246, 0.98) 0%, rgba(255, 242, 231, 0.92) 100%)",
              color: "#8c5538",
              boxShadow: "0 10px 22px rgba(151, 104, 71, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.72)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              fontSize: "18px",
              fontWeight: "600",
              cursor: "pointer",
              display: "none",
              alignItems: "center",
              justifyContent: "center",
            });
            button.onclick = () => {
              const toggleButton =
                parentDoc.querySelector('[data-testid="collapsedControl"]') ||
                parentDoc.querySelector('[data-testid="stExpandSidebarButton"] button') ||
                parentDoc.querySelector('[data-testid="stExpandSidebarButton"]');
              if (toggleButton) {
                toggleButton.click();
              }
            };
            parentDoc.body.appendChild(button);
          }
          return button;
        }

        function syncButtonVisibility() {
          const button = ensureButton();
          const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
          const isCollapsed = sidebar && sidebar.getAttribute("aria-expanded") === "false";
          const nativeToggle =
            parentDoc.querySelector('[data-testid="collapsedControl"]') ||
            parentDoc.querySelector('[data-testid="stExpandSidebarButton"]');
          button.style.display = isCollapsed ? "flex" : "none";
          if (nativeToggle) {
            nativeToggle.style.display = isCollapsed ? "flex" : "";
          }
        }

        ensureButton();
        syncButtonVisibility();

        const observer = new MutationObserver(syncButtonVisibility);
        observer.observe(parentDoc.body, {
          subtree: true,
          attributes: true,
          childList: true,
          attributeFilter: ["aria-expanded", "style", "class"],
        });
        window.addEventListener("beforeunload", () => observer.disconnect(), { once: true });
        </script>
        """,
        height=0,
    )


def restore_login_session() -> None:
    if st.session_state.user is not None:
        return

    session_token = st.context.cookies.get(LOGIN_COOKIE_NAME)
    if not session_token:
        return

    user = get_user_by_session_token(session_token)
    if user is None:
        st.session_state.clear_login_cookie = True
        st.session_state.auth_session_token = None
        return

    st.session_state.user = user
    st.session_state.auth_session_token = session_token


def _read_smtp_setting(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def send_password_reset_email(recipient_email: str, code: str) -> tuple[bool, str]:
    smtp_host = _read_smtp_setting("SMTP_HOST")
    smtp_port = int(_read_smtp_setting("SMTP_PORT", "587"))
    smtp_username = _read_smtp_setting("SMTP_USERNAME")
    smtp_password = _read_smtp_setting("SMTP_PASSWORD")
    smtp_from_email = _read_smtp_setting("SMTP_FROM_EMAIL", smtp_username)
    smtp_from_name = _read_smtp_setting("SMTP_FROM_NAME", "TastePilot")
    smtp_use_tls = _read_smtp_setting("SMTP_USE_TLS", "true").lower() != "false"

    if not all([smtp_host, smtp_port, smtp_username, smtp_password, smtp_from_email]):
        return False, "当前还没有配置邮件服务，已切换到本地调试模式。"

    message = EmailMessage()
    message["Subject"] = "TastePilot 密码重置验证码"
    message["From"] = f"{smtp_from_name} <{smtp_from_email}>"
    message["To"] = recipient_email
    message.set_content(
        f"你的 TastePilot 密码重置验证码是：{code}\n\n"
        "验证码 10 分钟内有效。如果这不是你本人操作，请忽略这封邮件。"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    except Exception:
        return False, "邮件发送失败，已切换到本地调试模式。"

    return True, "验证码已经发送到你的邮箱。"


def send_reset_code(email: str) -> None:
    normalized_email = email.strip().lower()
    user = get_user_by_email(normalized_email)
    if user is None:
        st.session_state.reset_notice = "这个邮箱还没有注册。"
        st.session_state.reset_debug_code = ""
        st.session_state.reset_email = ""
        return

    code = f"{randint(0, 999999):06d}"
    create_password_reset_code(normalized_email, code)
    sent, message = send_password_reset_email(normalized_email, code)
    st.session_state.reset_email = normalized_email
    st.session_state.reset_notice = message
    st.session_state.reset_debug_code = "" if sent else code


def render_tag_pills(tags: list[str]) -> str:
    unique_tags = list(dict.fromkeys(tag for tag in tags if tag))
    return "".join(f'<span class="skill-chip">{tag}</span>' for tag in unique_tags)


def render_recipe_card_tags(recipe: dict) -> str:
    def _unique(items: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in items if item))

    primary_tags = _unique([
        recipe.get("main_type", ""),
        recipe.get("sub_type", ""),
    ])
    secondary_tags = _unique([
        recipe.get("food_origin", ""),
        recipe.get("regional_cuisine", ""),
    ])
    tertiary_tags = _unique(
        str(recipe.get("flavor_tags", "")).split("|")
        + str(recipe.get("scene_tags", "")).split("|")
    )

    first_row = "".join(f'<span class="recipe-tag-chip recipe-tag-chip-primary">{tag}</span>' for tag in primary_tags)
    first_row += "".join(f'<span class="recipe-tag-chip recipe-tag-chip-secondary">{tag}</span>' for tag in secondary_tags)
    second_row = " / ".join(tertiary_tags)

    parts = ['<div class="recipe-tag-stack">']
    if first_row:
        parts.append(f'<div class="recipe-tag-row">{first_row}</div>')
    if second_row:
        parts.append(f'<div class="recipe-tag-inline">{second_row}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_seasonal_tag_groups(tag_groups: dict[str, list[str]] | None, fallback_tags: list[str]) -> str:
    if not tag_groups:
        return render_tag_pills(fallback_tags)

    sections = []
    for group_title, tags in tag_groups.items():
        unique_tags = list(dict.fromkeys(tag for tag in tags if tag))
        if not unique_tags:
            continue
        sections.append(
            (
                '<div class="seasonal-tag-group">'
                f'<div class="seasonal-tag-group-title">{group_title}</div>'
                f'{render_tag_pills(unique_tags)}'
                "</div>"
            )
        )

    if not sections:
        return render_tag_pills(fallback_tags)

    return f'<div class="seasonal-tag-groups">{"".join(sections)}</div>'


def logout() -> None:
    session_token = st.session_state.get("auth_session_token")
    if session_token:
        delete_login_session(session_token)
    st.session_state.auth_session_token = None
    st.session_state.clear_login_cookie = True
    st.session_state.user = None
    st.session_state.prompt_text = ""
    st.session_state.prompt_text_input = ""
    st.session_state.selected_skills = []
    st.session_state.selected_main_types = []
    st.session_state.main_type_notice = ""
    st.session_state.recommendations = []
    st.session_state.last_query = {}
    st.session_state.last_query_signature = None
    st.session_state.excluded_recipe_ids = []
    st.session_state.preference_notice = ""
    st.session_state.profile_notice = ""
    st.session_state.current_page = "recommend"
    st.session_state.seasonal_term = get_current_seasonal_term_name()
    st.session_state.seasonal_recommendations = []
    st.session_state.seasonal_excluded_recipe_ids = []
    st.session_state.seasonal_main_type_filter = "全部"
    st.session_state.seasonal_main_types = [MAIN_TYPE_ALL_OPTION]


def apply_skill(skill_name: str) -> None:
    if skill_name in st.session_state.selected_skills:
        remove_skill(skill_name)
        return

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
    st.session_state.selected_main_types = []
    st.session_state.main_type_notice = ""
    st.session_state.recommendations = []
    st.session_state.last_query = {}
    st.session_state.last_query_signature = None
    st.session_state.excluded_recipe_ids = []
    st.session_state.sync_prompt_input = False


def open_profile_page() -> None:
    st.session_state.current_page = "profile"
    set_page_query("profile")


def open_recommend_page() -> None:
    st.session_state.current_page = "recommend"
    set_page_query("recommend")


def open_seasonal_page() -> None:
    st.session_state.current_page = "seasonal"
    next_term = get_current_seasonal_term_name()
    if st.session_state.seasonal_term != next_term:
        st.session_state.seasonal_recommendations = []
        st.session_state.seasonal_excluded_recipe_ids = []
    st.session_state.seasonal_term = next_term
    set_page_query("seasonal")


def select_seasonal_preview_term(term_name: str) -> None:
    if term_name not in SEASONAL_PAGE_CONFIG:
        return
    if st.session_state.seasonal_term != term_name:
        st.session_state.seasonal_recommendations = []
        st.session_state.seasonal_excluded_recipe_ids = []
    st.session_state.seasonal_term = term_name
    st.query_params["page"] = "seasonal_preview"
    st.query_params["term"] = term_name


def on_seasonal_main_type_change() -> None:
    st.session_state.seasonal_recommendations = []
    st.session_state.seasonal_excluded_recipe_ids = []


def on_main_type_change() -> None:
    st.session_state.main_type_notice = ""
    st.session_state.recommendations = []
    st.session_state.last_query = {}
    st.session_state.last_query_signature = None
    st.session_state.excluded_recipe_ids = []


def submit_profile_feedback(profile_type: str, profile_value: str, feedback_type: str) -> None:
    record_profile_feedback(st.session_state.user["id"], profile_type, profile_value, feedback_type)
    tone = "更像我" if feedback_type == "confirm" else "不太准"
    st.session_state.profile_notice = f"已记下这条画像“{profile_value}”对你来说是“{tone}”。"


def _profile_strength_width(score: float, items: list[dict]) -> float:
    if not items:
        return 0.0
    max_score = max(item["score"] for item in items) or 1
    return max(18.0, min(100.0, score / max_score * 100))


def render_profile_module(title: str, description: str, items: list[dict], profile_type: str) -> None:
    st.markdown(
        f"""
        <div class="profile-card">
            <div class="profile-card-title">{title}</div>
            <div class="profile-card-copy">{description}</div>
        """,
        unsafe_allow_html=True,
    )

    if not items:
        st.markdown('<div class="profile-empty">还在慢慢认识你，先多点几次推荐，我会更快看出你稳定的偏好。</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for item in items:
        width = _profile_strength_width(item["score"], items)
        st.markdown(
            f"""
            <div class="profile-item">
                <div class="profile-item-head">
                    <span>{item['label']}</span>
                    <span>{int(round(width))}%</span>
                </div>
                <div class="profile-meter">
                    <div class="profile-meter-fill" style="width: {width:.1f}%"></div>
                </div>
                <div class="profile-item-note">这个标签最近更常出现在你收藏、浏览和搜索过的菜里。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="profile-feedback-row">', unsafe_allow_html=True)
        feedback_cols = st.columns([1.25, 1.25], gap="medium")
        with feedback_cols[0]:
            if st.button("更像我", key=f"profile_confirm_{profile_type}_{item['label']}", use_container_width=True):
                submit_profile_feedback(profile_type, item["label"], "confirm")
                st.rerun()
        with feedback_cols[1]:
            if st.button("不太准", key=f"profile_downvote_{profile_type}_{item['label']}", use_container_width=True):
                submit_profile_feedback(profile_type, item["label"], "downvote")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_profile_page() -> None:
    profile = build_user_profile(st.session_state.user["id"])

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-shell">
                <div>
                    <div class="hero-kicker">Personal Taste Map</div>
                    <div class="hero-title">我的口味画像</div>
                    <div class="hero-subtitle">
                        这不是一张静态标签表，而是 TastePilot 根据你的偏好、浏览、收藏和跳过慢慢学出来的口味轮廓。
                    </div>
                </div>
                <div class="hero-visual">
                    <div class="hero-shape one"></div>
                    <div class="hero-shape two"></div>
                    <div class="hero-shape three"></div>
                    <div class="hero-dot a"></div>
                    <div class="hero-dot b"></div>
                    <div class="hero-mini-card top">
                        <div class="hero-mini-title">Profile</div>
                        <span class="hero-emoji">🫖</span> 越用越懂你
                    </div>
                    <div class="hero-mini-card bottom">
                        <div class="hero-mini-title">Signals</div>
                        <span class="hero-emoji">📌</span> 收藏 / 浏览 / 跳过
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="profile-shell">
            <div class="profile-lead">
                <div class="section-heading">这阵子我眼里的你</div>
                <div class="section-copy">{profile['confidence_summary']}</div>
                <div class="section-copy">{' '.join(profile['profile_explanations'])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.profile_notice:
        st.success(st.session_state.profile_notice)
        st.session_state.profile_notice = ""

    grid_cols = st.columns(3, gap="large")
    with grid_cols[0]:
        render_profile_module(
            "常见口味",
            "这里会沉淀你最近最常靠近的味型，用来帮推荐更快收窄方向。",
            profile.get("top_flavors", []),
            "flavor",
        )
    with grid_cols[1]:
        render_profile_module(
            "偏好菜系",
            "我会把你最近更常接受的料理风格慢慢总结成稳定偏好。",
            profile.get("top_cuisines", []),
            "cuisine",
        )
    with grid_cols[2]:
        render_profile_module(
            "活跃时段",
            "这会影响我在不同时间更倾向推荐什么节奏和氛围的食物。",
            profile.get("active_time_slots", []),
            "time_slot",
        )


def _get_skill_time_context() -> tuple[str, str]:
    current_hour = datetime.now(ZoneInfo("Asia/Shanghai")).hour
    if 5 <= current_hour < 11:
        return "早上", "morning"
    if 11 <= current_hour < 15:
        return "中午", "lunch"
    if 15 <= current_hour < 18:
        return "下午", "afternoon"
    if 18 <= current_hour < 22:
        return "晚上", "evening"
    return "深夜", "night"


def _score_skill_for_preferences(skill_name: str, preferences: dict) -> int:
    score = 0
    hints = SKILL_PREFERENCE_HINTS.get(skill_name, {})
    favorite_flavors = set(filter(None, str(preferences.get("favorite_flavors", "")).split("|")))
    selected_main_types = set(st.session_state.get("selected_main_types", []))
    budget_level = preferences.get("budget_level", "")
    time_limit = preferences.get("cooking_time_limit", "")
    diet_goal = preferences.get("diet_goal", "")
    vegetarian_preference = preferences.get("vegetarian_preference", "")

    if favorite_flavors.intersection(hints.get("favorite_flavors", set())):
        score += 4
    if selected_main_types.intersection(hints.get("main_types", set())):
        score += 3
    if budget_level and budget_level in hints.get("budget_levels", set()):
        score += 3
    if time_limit and time_limit in hints.get("time_limits", set()):
        score += 3
    if diet_goal and diet_goal in hints.get("diet_goals", set()):
        score += 4
    if vegetarian_preference and vegetarian_preference in hints.get("vegetarian_preferences", set()):
        score += 2
    if skill_name in st.session_state.get("selected_skills", []):
        score += 1
    return score


def _build_ranked_skill_group(
    group_name: str,
    skills: list[tuple[str, str]],
    preferences: dict,
) -> list[tuple[str, str]]:
    ranked: list[tuple[int, int, str, str]] = []
    for index, (skill_name, skill_desc) in enumerate(skills):
        ranked.append(
            (
                _score_skill_for_preferences(skill_name, preferences),
                -index,
                skill_name,
                skill_desc,
            )
        )
    ranked.sort(reverse=True)
    limit = SKILL_GROUP_DISPLAY_LIMITS.get(group_name, len(skills))
    return [(skill_name, skill_desc) for _, _, skill_name, skill_desc in ranked[:limit]]


def get_dynamic_skill_groups(preferences: dict) -> tuple[str, list[tuple[str, list[tuple[str, str]]]]]:
    time_label, time_key = _get_skill_time_context()
    base_groups = TIME_BASED_SKILL_GROUPS[time_key] + [MOOD_SKILL_GROUP]
    ranked_groups = [
        (group_name, _build_ranked_skill_group(group_name, group_skills, preferences))
        for group_name, group_skills in base_groups
    ]
    return time_label, ranked_groups


def render_selected_skills() -> None:
    if not st.session_state.selected_skills:
        return

    st.markdown('<div class="selected-tags-label">已选标签：</div>', unsafe_allow_html=True)
    row_size = 5
    skills = st.session_state.selected_skills[:]
    for start_index in range(0, len(skills), row_size):
        row_skills = skills[start_index : start_index + row_size]
        st.markdown('<div class="selected-skill-row">', unsafe_allow_html=True)
        pill_cols = st.columns(row_size, gap="small")
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


def render_prompt_tool_button_bridge() -> None:
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        let promptToolButtonFrame = null;

        function placePromptToolButton() {
          const textarea = parentDoc.querySelector('.stTextArea textarea');
          const plusButton = Array.from(parentDoc.querySelectorAll('[data-testid="stPopoverButton"]'))
            .find((button) => button.textContent && button.textContent.includes('＋'));
          if (!textarea || !plusButton) {
            return;
          }

          const rect = textarea.getBoundingClientRect();
          const popoverShell = plusButton.closest('[data-testid="stPopover"]');
          const buttonParent = plusButton.parentElement;
          const originalRow = plusButton.closest('[data-testid="stHorizontalBlock"]');
          const narrowStyles = {
            width: '40px',
            minWidth: '40px',
            maxWidth: '40px',
            height: '40px',
            minHeight: '40px',
            maxHeight: '40px',
          };
          [popoverShell, buttonParent].forEach((element) => {
            if (!element) {
              return;
            }
            Object.assign(element.style, {
              ...narrowStyles,
              display: 'block',
              flex: '0 0 40px',
              margin: '0',
            });
          });
          if (originalRow) {
            Object.assign(originalRow.style, {
              height: '0',
              minHeight: '0',
              margin: '0',
              overflow: 'visible',
            });
          }
          Object.assign(plusButton.style, {
            position: 'fixed',
            left: `${rect.left + 14}px`,
            top: `${rect.bottom - 50}px`,
            ...narrowStyles,
            zIndex: '1001',
            margin: '0',
            padding: '0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0',
          });
          plusButton.querySelectorAll('svg').forEach((icon) => {
            icon.style.display = 'none';
          });
        }

        function schedulePromptToolButtonPlacement() {
          if (promptToolButtonFrame) {
            window.parent.cancelAnimationFrame(promptToolButtonFrame);
          }
          promptToolButtonFrame = window.parent.requestAnimationFrame(() => {
            placePromptToolButton();
            window.parent.setTimeout(placePromptToolButton, 120);
            window.parent.setTimeout(placePromptToolButton, 280);
            window.parent.setTimeout(placePromptToolButton, 520);
          });
        }

        schedulePromptToolButtonPlacement();
        window.parent.addEventListener('resize', schedulePromptToolButtonPlacement);
        window.parent.addEventListener('scroll', schedulePromptToolButtonPlacement, true);

        const observer = new MutationObserver(schedulePromptToolButtonPlacement);
        observer.observe(parentDoc.body, { subtree: true, childList: true, attributes: true });
        window.addEventListener('beforeunload', () => {
          observer.disconnect();
          window.parent.removeEventListener('resize', schedulePromptToolButtonPlacement);
          window.parent.removeEventListener('scroll', schedulePromptToolButtonPlacement, true);
        }, { once: true });
        </script>
        """,
        height=0,
    )


def render_main_type_arrow_bridge() -> None:
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        const ARROW_BINDING_VERSION = "5";
        const selectorRoots = [
          { selector: '.st-key-selected_main_types div[data-baseweb="select"]', readOnly: true },
          { selector: '.st-key-seasonal_main_type_filter_shell div[data-baseweb="select"]', readOnly: true },
        ];

        function bindMainTypeArrowBehavior() {
          selectorRoots.forEach((config) => {
            const root = parentDoc.querySelector(config.selector);
            if (root) {
              bindSelectArrow(root, config.readOnly);
            }
          });
        }

        function bindSelectArrow(root, readOnly) {
          if (root.dataset.tastepilotArrowBound === ARROW_BINDING_VERSION) {
            return;
          }
          root.dataset.tastepilotArrowBound = ARROW_BINDING_VERSION;
          root.dataset.tastepilotMenuOpen = "0";

          const getCombobox = () => root.querySelector('input[role="combobox"]');
          const getExpanded = () => {
            return root.dataset.tastepilotMenuOpen === "1";
          };
          const getArrow = () => {
            const titledArrow = root.querySelector('svg[title="open"], svg[title="close"]');
            if (titledArrow) {
              return titledArrow;
            }
            const icons = Array.from(root.querySelectorAll("svg"));
            return icons[icons.length - 1] || null;
          };
          const isArrowClick = (event, arrow) => {
            const arrowShell = arrow?.parentElement;
            if (arrow && (arrow === event.target || arrow.contains(event.target))) {
              return true;
            }
            if (arrowShell && (arrowShell === event.target || arrowShell.contains(event.target))) {
              return true;
            }
            const rect = root.getBoundingClientRect();
            return event.clientX >= rect.right - 54 && event.clientX <= rect.right + 6;
          };

          const syncArrow = () => {
            const combobox = getCombobox();
            const arrow = getArrow();
            if (!combobox || !arrow) {
              return;
            }
            const nativeExpanded = (
              combobox.getAttribute("aria-expanded") === "true"
              || root.getAttribute("aria-expanded") === "true"
            );
            if (nativeExpanded && root.dataset.tastepilotForcedClosed !== "1") {
              root.dataset.tastepilotMenuOpen = "1";
            }
            const expanded = getExpanded();
            arrow.style.transition = "transform 160ms ease";
            arrow.style.transform = expanded ? "rotate(180deg)" : "rotate(0deg)";
            if (readOnly) {
              applyReadOnlySelect(root, combobox);
            }
          };

          const applyReadOnlySelect = (root, combobox) => {
            combobox.readOnly = true;
            combobox.setAttribute("readonly", "readonly");
            combobox.setAttribute("placeholder", "");
            combobox.style.cursor = "pointer";
            combobox.style.caretColor = "transparent";
            combobox.value = "";

            const hasSelectedTags = root.querySelectorAll('[data-baseweb="tag"], [class*="multiValue"]').length > 0;
            const inputShell = combobox.parentElement;
            if (hasSelectedTags && inputShell) {
              Object.assign(inputShell.style, {
                width: "0px",
                minWidth: "0px",
                maxWidth: "0px",
                flex: "0 0 0px",
                padding: "0",
                margin: "0",
                overflow: "hidden",
              });
              Object.assign(combobox.style, {
                width: "0px",
                minWidth: "0px",
                maxWidth: "0px",
                padding: "0",
              });
            }
          };

          if (readOnly) {
            const blockTyping = (event) => {
              const allowedKeys = new Set([
                "ArrowUp",
                "ArrowDown",
                "Enter",
                "Escape",
                "Tab",
                "Home",
                "End",
              ]);
              if (event.type === "keydown" && allowedKeys.has(event.key)) {
                return;
              }
              event.preventDefault();
            };
            root.addEventListener("keydown", blockTyping, true);
            root.addEventListener("keypress", blockTyping, true);
            root.addEventListener("beforeinput", blockTyping, true);
            root.addEventListener("paste", blockTyping, true);
            root.addEventListener(
              "input",
              (event) => {
                const combobox = getCombobox();
                if (combobox && event.target === combobox) {
                  combobox.value = "";
                  applyReadOnlySelect(root, combobox);
                }
              },
              true
            );
          }

          root.addEventListener(
            "mousedown",
            (event) => {
              const arrow = getArrow();
              const combobox = getCombobox();
              if (!arrow || !combobox) {
                return;
              }

              const clickedArrow = isArrowClick(event, arrow);
              if (!clickedArrow) {
                window.parent.setTimeout(syncArrow, 30);
                return;
              }

              const expanded = getExpanded();
              if (!expanded) {
                if (root.dataset.tastepilotForcedClosed === "1") {
                  clearForcedClosed(root);
                }
                root.dataset.tastepilotMenuOpen = "1";
                window.parent.setTimeout(syncArrow, 30);
                window.parent.setTimeout(syncArrow, 140);
                window.parent.setTimeout(syncArrow, 260);
                return;
              }

              event.preventDefault();
              event.stopPropagation();
              if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
              }
              closeSelectMenu(root, combobox, arrow);
            },
            true
          );

          root.addEventListener(
            "focusin",
            () => {
              if (root.dataset.tastepilotForcedClosed !== "1") {
                window.parent.setTimeout(syncArrow, 30);
              }
            },
            true
          );

          const closeSelectMenu = (root, combobox, arrow) => {
            root.dataset.tastepilotForcedClosed = "1";
            root.dataset.tastepilotMenuOpen = "0";
            combobox.setAttribute("aria-expanded", "false");
            root.setAttribute("aria-expanded", "false");
            const escapeEventInit = {
              key: "Escape",
              code: "Escape",
              keyCode: 27,
              which: 27,
              bubbles: true,
              cancelable: true,
            };
            [combobox, parentDoc.activeElement, parentDoc.body].filter(Boolean).forEach((target) => {
              target.dispatchEvent(new KeyboardEvent("keydown", escapeEventInit));
              target.dispatchEvent(new KeyboardEvent("keyup", escapeEventInit));
            });
            if (typeof combobox.blur === "function") {
              combobox.blur();
            }
            const outsideTarget = parentDoc.elementFromPoint(12, 12) || parentDoc.body;
            ["pointerdown", "mousedown", "mouseup", "click"].forEach((type) => {
              outsideTarget.dispatchEvent(
                new MouseEvent(type, {
                  bubbles: true,
                  cancelable: true,
                  composed: true,
                  view: window.parent,
                  clientX: 12,
                  clientY: 12,
                  button: 0,
                })
              );
            });
            parentDoc
              .querySelectorAll('div[data-baseweb="popover"], [role="listbox"]')
              .forEach((popover) => {
                popover.dataset.tastepilotHiddenByArrow = "1";
                popover.style.display = "none";
                popover.style.pointerEvents = "none";
              });
            if (arrow) {
              arrow.style.transform = "rotate(0deg)";
            }
            window.parent.setTimeout(syncArrow, 30);
            window.parent.setTimeout(syncArrow, 140);
          };

          const clearForcedClosed = (root) => {
            root.dataset.tastepilotForcedClosed = "0";
            parentDoc
              .querySelectorAll('[data-tastepilot-hidden-by-arrow="1"]')
              .forEach((popover) => {
                popover.style.display = "";
                popover.style.pointerEvents = "";
                popover.dataset.tastepilotHiddenByArrow = "0";
              });
            window.parent.setTimeout(syncArrow, 30);
          };

          root.addEventListener(
            "mousedown",
            (event) => {
              if (root.dataset.tastepilotForcedClosed === "1") {
                const arrow = getArrow();
                if (isArrowClick(event, arrow)) {
                  clearForcedClosed(root);
                  return;
                }
                clearForcedClosed(root);
              }
            },
            true
          );

          const observer = new MutationObserver(syncArrow);
          observer.observe(root, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ["aria-expanded", "style", "class"],
          });
          syncArrow();
        };

        bindMainTypeArrowBehavior();

        const pageObserver = new MutationObserver(bindMainTypeArrowBehavior);
        pageObserver.observe(parentDoc.body, { subtree: true, childList: true, attributes: true });
        window.addEventListener(
          "beforeunload",
          () => {
            pageObserver.disconnect();
          },
          { once: true }
        );
        </script>
        """,
        height=0,
    )


def render_seasonal_card_bridge() -> None:
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;

        function bindSeasonalCard() {
          const card = parentDoc.querySelector(".seasonal-card");
          const trigger = parentDoc.querySelector(".st-key-seasonal_card_trigger button");
          if (!card || !trigger) {
            return;
          }

          card.dataset.tastepilotSeasonalBound = "2";
          card.onclick = () => {
            trigger.click();
          };
        }

        bindSeasonalCard();

        const observer = new MutationObserver(bindSeasonalCard);
        observer.observe(parentDoc.body, { subtree: true, childList: true });
        window.addEventListener("beforeunload", () => observer.disconnect(), { once: true });
        </script>
        """,
        height=0,
    )


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
            background: rgba(255, 250, 245, 0.96);
            border-radius: 14px;
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
        .password-row-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.35rem;
        }
        .password-row-label {
            color: #2f3240;
            font-size: 1rem;
            font-weight: 600;
            margin: 0;
        }
        .reset-link-note {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            min-height: 100%;
            margin: 0;
        }
        .reset-link-note a,
        .auth-inline-link a {
            color: rgba(255, 239, 226, 0.84) !important;
            font-size: 0.76rem !important;
            font-weight: 500 !important;
            text-decoration: underline;
            white-space: nowrap;
        }
        .reset-link-note a:hover,
        .auth-inline-link a:hover {
            color: #fff7ee !important;
        }
        .password-row-label {
            color: #3b312a;
        }
        .reset-link-note a,
        .auth-inline-link a {
            color: rgba(118, 78, 55, 0.82) !important;
        }
        .reset-link-note a:hover,
        .auth-inline-link a:hover {
            color: #7a4930 !important;
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
    if st.session_state.auth_notice:
        st.success(st.session_state.auth_notice)
        st.session_state.auth_notice = ""
    st.markdown('<div class="auth-form-shell">', unsafe_allow_html=True)
    with st.container():
        if st.session_state.auth_mode == "login":
            st.subheader("登录")
            st.caption("已经有账号了，直接回来继续选菜。")
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("邮箱", placeholder="you@example.com")
                st.markdown(
                    """
                    <div class="password-row-head">
                        <div class="password-row-label">密码</div>
                        <div class="reset-link-note"><a href="?auth_mode=forgot_password" target="_self">忘记密码？</a></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                password = st.text_input("密码", type="password", label_visibility="collapsed")
                login_submitted = st.form_submit_button("登录并进入", use_container_width=True)
            if login_submitted:
                user = authenticate_user(email.strip(), password)
                if user is None:
                    st.error("邮箱或密码不正确。")
                else:
                    st.session_state.user = user
                    st.session_state.auth_session_token = create_login_session(user["id"])
                    st.session_state.pending_login_cookie_token = st.session_state.auth_session_token
                    st.rerun()

            st.write("新用户第一次来这里？")
            st.button(
                "去注册",
                on_click=set_auth_mode,
                args=("register",),
                use_container_width=True,
            )
        elif st.session_state.auth_mode == "register":
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
                    st.session_state.auth_session_token = create_login_session(user_id)
                    st.session_state.pending_login_cookie_token = st.session_state.auth_session_token
                    st.success("注册成功。现在可以开始选今晚吃什么了。")
                    st.rerun()

            st.write("已经注册过了？")
            st.button(
                "返回登录",
                on_click=set_auth_mode,
                args=("login",),
                use_container_width=True,
            )
        else:
            st.subheader("找回密码")
            st.caption("输入注册邮箱，我们会发一个验证码给你，用它来重新设置密码。")

            if st.session_state.reset_notice:
                st.info(st.session_state.reset_notice)
            if st.session_state.reset_debug_code:
                st.warning(f"当前未配置邮件服务，调试验证码：{st.session_state.reset_debug_code}")
            if st.session_state.reset_email:
                st.caption(f"当前验证码绑定邮箱：{st.session_state.reset_email}")

            with st.form("send_reset_code_form", clear_on_submit=False):
                reset_email = st.text_input("注册邮箱", placeholder="you@example.com")
                send_code_submitted = st.form_submit_button("发送验证码", use_container_width=True)
            if send_code_submitted:
                send_reset_code(reset_email)
                st.rerun()

            with st.form("reset_password_form", clear_on_submit=False):
                verify_code = st.text_input("邮箱验证码", placeholder="6 位数字")
                new_password = st.text_input("设置新密码", type="password")
                reset_submitted = st.form_submit_button("重置密码", use_container_width=True)
            if reset_submitted:
                if not st.session_state.reset_email:
                    st.error("请先输入注册邮箱并发送验证码。")
                    return
                success, message = reset_password_with_code(
                    st.session_state.reset_email.strip(),
                    verify_code.strip(),
                    new_password,
                )
                if success:
                    st.session_state.reset_notice = ""
                    st.session_state.reset_debug_code = ""
                    st.session_state.reset_email = ""
                    st.session_state.auth_notice = message
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error(message)

            st.markdown(
                '<div class="auth-inline-link"><a href="/" target="_self">返回登录</a></div>',
                unsafe_allow_html=True,
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
        st.markdown("## 进入哪里")
        if st.button("智能推荐主页", on_click=open_recommend_page, use_container_width=True):
            pass
        if st.button("节气时令推荐", on_click=open_seasonal_page, use_container_width=True):
            pass
        if st.button("我的口味画像", on_click=open_profile_page, use_container_width=True):
            pass
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
        if st.session_state.preference_notice:
            st.success(st.session_state.preference_notice)
            st.session_state.preference_notice = ""

        with st.expander("修改偏好", expanded=False):
            flavor_options = ["香辣", "酸口", "酸甜", "清淡", "蒜香", "鲜香", "重口", "家常", "酱香"]
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
                payload = {
                    "favorite_flavors": "|".join(favorite_flavors),
                    "disliked_ingredients": disliked_ingredients.strip(),
                    "diet_goal": diet_goal,
                    "budget_level": budget_level,
                    "cooking_time_limit": cooking_time_limit,
                    "vegetarian_preference": vegetarian_preference,
                }
                save_user_preferences(
                    st.session_state.user["id"],
                    payload,
                )
                preferences.update(payload)
                st.session_state.preference_notice = "偏好已更新。"
                st.rerun()

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
    selected_main_type_values = st.session_state.get("selected_main_types", [])
    selected_main_types = normalize_ui_main_types(selected_main_type_values)
    use_all_main_types = MAIN_TYPE_ALL_OPTION in selected_main_type_values or not selected_main_types
    parsed_main_types = normalize_ui_main_types(parsed.get("main_types", []))
    conflicting_main_types = [
        main_type for main_type in parsed_main_types if main_type not in selected_main_types
    ] if selected_main_types and not use_all_main_types else []
    has_main_type_conflict = bool(conflicting_main_types)
    selected_course_types = set()
    compatible_staple_categories = set()
    for main_type in selected_main_types:
        selected_course_types.update(MAIN_TYPE_COURSE_TYPES.get(main_type, set()))
        compatible_staple_categories.update(MAIN_TYPE_STAPLE_COMPATIBILITY.get(main_type, set()))

    if use_all_main_types:
        main_types = MAIN_TYPE_OPTIONS
        preferred_course_types = []
        avoid_course_types = parsed.get("avoid_course_types", [])
        staple_categories = parsed.get("staple_categories", [])
        beverage_categories = parsed.get("beverage_categories", [])
        primary_bucket = parsed.get("primary_bucket")
    elif selected_main_types:
        main_types = list(dict.fromkeys(selected_main_types))
        preferred_course_types = list(selected_course_types)
        avoid_course_types = [] if has_main_type_conflict else [
            course_type
            for course_type in parsed.get("avoid_course_types", [])
            if course_type not in selected_course_types
        ]
        staple_categories = [] if has_main_type_conflict else [
            category
            for category in parsed.get("staple_categories", [])
            if category in compatible_staple_categories
        ]
        beverage_categories = [] if has_main_type_conflict else (
            parsed.get("beverage_categories", []) if "饮品" in selected_main_types else []
        )
        selected_primary_buckets = [
            MAIN_TYPE_PRIMARY_BUCKET[main_type]
            for main_type in selected_main_types
            if main_type in MAIN_TYPE_PRIMARY_BUCKET
        ]
        primary_bucket = selected_primary_buckets[0] if len(selected_primary_buckets) == 1 else None
    else:
        main_types = parsed_main_types
        preferred_course_types = parsed.get("preferred_course_types", [])
        avoid_course_types = parsed.get("avoid_course_types", [])
        staple_categories = parsed.get("staple_categories", [])
        beverage_categories = parsed.get("beverage_categories", [])
        primary_bucket = parsed.get("primary_bucket")

    preferred_flavors = list(
        dict.fromkeys(
            [item for item in preferences.get("favorite_flavors", "").split("|") if item]
            + ([] if has_main_type_conflict else parsed.get("favorite_flavors", []))
        )
    )
    conflict_display_hints = []
    if has_main_type_conflict:
        conflict_display_hints = [
            f"大类冲突：已按{'、'.join(selected_main_types)}推荐",
            f"输入提到{'、'.join(conflicting_main_types)}",
            "本轮随机看同大类菜谱",
        ]
        parsed["display_hints"] = conflict_display_hints
        parsed["recognized_hints"] = conflict_display_hints

    query = {
        "scene": "" if has_main_type_conflict else parsed.get("scene", ""),
        "favorite_flavors": preferred_flavors,
        "current_input_flavors": [] if has_main_type_conflict else parsed.get("favorite_flavors", []),
        "required_flavors": [] if has_main_type_conflict else parsed.get("required_flavors", []),
        "diet_goal": "" if has_main_type_conflict else parsed.get("diet_goal", ""),
        "budget_level": parsed.get("budget_level", preferences.get("budget_level", "中等预算")),
        "cooking_time_limit": parsed.get("cooking_time_limit", preferences.get("cooking_time_limit", "30 分钟内")),
        "vegetarian_preference": parsed.get("vegetarian_preference", preferences.get("vegetarian_preference", "不限")),
        "disliked_ingredients": "、".join(
            filter(None, [preferences.get("disliked_ingredients", ""), parsed.get("disliked_ingredients", "")])
        ),
        "preferred_course_types": preferred_course_types,
        "avoid_course_types": avoid_course_types,
        "intent_tags": [] if has_main_type_conflict else parsed.get("intent_tags", []),
        "mood_search_tags": [] if has_main_type_conflict else parsed.get("mood_search_tags", []),
        "beverage_categories": beverage_categories,
        "main_types": main_types,
        "staple_categories": staple_categories,
        "solar_terms": [] if has_main_type_conflict else parsed.get("solar_terms", []),
        "cuisine_groups": [] if has_main_type_conflict else parsed.get("cuisine_groups", []),
        "primary_bucket": primary_bucket,
        "mood_bucket": None if has_main_type_conflict else parsed.get("mood_bucket"),
        "mood_detected": None if has_main_type_conflict else parsed.get("mood_detected"),
        "main_type_conflict": has_main_type_conflict,
        "conflicting_main_types": conflicting_main_types,
        "soften_seasonal_bias": True,
        "implicit_current_solar_term": get_current_seasonal_term_name(),
        "implicit_time_slot": get_current_hidden_time_slot(),
    }
    return query, parsed


def build_current_query_signature(prompt_override: str | None = None) -> tuple[str, tuple[str, ...]]:
    prompt_text = (
        prompt_override
        if prompt_override is not None
        else st.session_state.get("prompt_text_input", "")
    ).strip()
    selected_main_types = tuple(
        normalize_main_type_picker_values(st.session_state.get("selected_main_types", []))
    )
    return prompt_text, selected_main_types


def build_display_hints_for_current_input(parsed: dict) -> tuple[list[str], bool]:
    selected_main_type_values = st.session_state.get("selected_main_types", [])
    selected_main_types = normalize_ui_main_types(selected_main_type_values)
    use_all_main_types = MAIN_TYPE_ALL_OPTION in selected_main_type_values or not selected_main_types
    parsed_main_types = normalize_ui_main_types(parsed.get("main_types", []))
    conflicting_main_types = [
        main_type for main_type in parsed_main_types if main_type not in selected_main_types
    ] if selected_main_types and not use_all_main_types else []
    if conflicting_main_types:
        return (
            [
                f"大类冲突：已按{'、'.join(selected_main_types)}推荐",
                f"输入提到{'、'.join(conflicting_main_types)}",
                "本轮随机看同大类菜谱",
            ],
            True,
        )
    return parsed.get("display_hints") or parsed.get("recognized_hints", []), False


def recipe_matches_required_home_intent(recipe: dict, query: dict) -> bool:
    selected_main_types = normalize_ui_main_types(query.get("main_types", []))
    if selected_main_types and recipe.get("main_type") not in selected_main_types:
        return False

    required_flavors = query.get("current_input_flavors") or query.get("required_flavors") or []
    if not required_flavors:
        return True

    recipe_tags = set(recipe.get("display_tags", []))
    recipe_tags.update(recipe.get("feature_tags", "").split("|"))
    recipe_tags.update(recipe.get("flavor_profile", "").split("|"))
    recipe_tags.update(recipe.get("taste_tags", "").split("|"))
    recipe_tags = {tag for tag in recipe_tags if tag}

    flavor_aliases = {
        "香辣": {"香辣", "辣", "辣味", "重口", "川菜", "湘菜"},
        "清淡": {"清淡", "清爽", "轻负担"},
        "酸甜": {"酸甜", "酸口", "果香"},
        "甜香": {"甜香", "奶香", "酸甜", "甜口", "甜品"},
        "鲜香": {"鲜香", "鲜味"},
        "奶香": {"奶香"},
    }
    for flavor in required_flavors:
        if flavor == "香辣" and int(recipe.get("is_spicy") or 0) == 1:
            continue
        accepted_tags = flavor_aliases.get(flavor, {flavor})
        if recipe_tags.intersection(accepted_tags):
            continue
        return False
    return True


def run_recommendation(preferences: dict, append_skill: str | None = None, replace_mode: bool = False) -> None:
    st.session_state.main_type_notice = ""
    prompt_override = None
    if append_skill:
        apply_skill(append_skill)
        prompt_override = st.session_state.prompt_text

    query, parsed = build_query_from_prompt(preferences, prompt_override=prompt_override)
    if not replace_mode and (
        parsed.get("favorite_flavors") or parsed.get("cuisine_groups") or parsed.get("scene")
    ):
        persist_query_profile_signal(st.session_state.user["id"], parsed)
    excluded_ids = st.session_state.excluded_recipe_ids if replace_mode else []
    recommendations = recommend_recipes(
        query=query,
        preferences=preferences,
        user_id=st.session_state.user["id"],
        limit=3,
        exclude_recipe_ids=excluded_ids,
    )
    recommendations = [
        recipe for recipe in recommendations
        if recipe_matches_required_home_intent(recipe, query)
    ]
    st.session_state.last_query = query
    st.session_state.last_query_signature = build_current_query_signature(prompt_override=prompt_override)

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


def render_seasonal_inspiration_card() -> None:
    term_name = get_current_seasonal_term_name()
    config = SEASONAL_PAGE_CONFIG.get(term_name, SEASONAL_PAGE_CONFIG[get_current_seasonal_term_name()])
    background_image = resolve_image_source(config["image_path"])
    background_position = config.get("background_position", "center")
    background_style = (
        f"background-image: linear-gradient(180deg, rgba(255, 248, 239, 0.08), rgba(84, 54, 35, 0.14)), url('{background_image}'); background-position: {background_position};"
        if background_image
        else "background: linear-gradient(135deg, rgba(253, 239, 213, 0.96), rgba(201, 153, 104, 0.78));"
    )

    st.markdown(
        f"""
        <div class="seasonal-card-shell">
            <div class="seasonal-card" style="{background_style}">
                <div class="seasonal-card-overlay">
                    <div class="seasonal-card-link">点击灵感卡，前往当前节气专题页 &gt;&gt;</div>
                    <div class="seasonal-card-kicker">节气灵感 · Solar Term</div>
                    <div class="seasonal-card-title seasonal-card-title-songti">{term_name}</div>
                    <div class="seasonal-card-subtitle">
                        {config.get("card_subtitle", config["intro"])}
                    </div>
                    <div class="seasonal-card-tags">
                        {"".join(f'<span class="seasonal-card-tag">{tag}</span>' for tag in config.get("card_tags", config["display_tags"][:4]))}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="seasonal_card_trigger"):
        st.button("打开节气专题", key="open_seasonal_card_button", on_click=open_seasonal_page)
    render_seasonal_card_bridge()


def run_seasonal_recommendation(preferences: dict, term_name: str, replace_mode: bool = False) -> None:
    config = SEASONAL_PAGE_CONFIG.get(term_name)
    if not config:
        st.session_state.seasonal_recommendations = []
        return

    selected_main_types = normalize_main_type_picker_values(st.session_state.get("seasonal_main_types", []))
    use_all_main_types = MAIN_TYPE_ALL_OPTION in selected_main_types
    seasonal_available_main_types = config.get("main_types", [])
    requested_main_types = (
        seasonal_available_main_types
        if use_all_main_types
        else [main_type for main_type in selected_main_types if main_type in seasonal_available_main_types]
    )
    if not requested_main_types:
        st.session_state.seasonal_recommendations = []
        return
    excluded_ids = st.session_state.seasonal_excluded_recipe_ids if replace_mode else []
    query = {
        "scene": "",
        "favorite_flavors": [],
        "required_flavors": [],
        "diet_goal": "",
        "budget_level": preferences.get("budget_level", "中等预算"),
        "cooking_time_limit": preferences.get("cooking_time_limit", "30 分钟内"),
        "vegetarian_preference": preferences.get("vegetarian_preference", "不限"),
        "disliked_ingredients": preferences.get("disliked_ingredients", ""),
        "preferred_course_types": [],
        "avoid_course_types": [],
        "intent_tags": [],
        "mood_search_tags": [],
        "beverage_categories": [],
        "main_types": requested_main_types,
        "staple_categories": [],
        "solar_terms": config.get("seasonal_tags", [term_name]),
        "cuisine_groups": [],
        "primary_bucket": None,
        "mood_bucket": None,
        "mood_detected": None,
        "main_type_conflict": False,
        "conflicting_main_types": [],
        "soften_seasonal_bias": False,
        "implicit_current_solar_term": term_name,
        "implicit_time_slot": get_current_hidden_time_slot(),
    }
    recommendations = recommend_recipes(
        query=query,
        preferences=preferences,
        user_id=st.session_state.user["id"],
        limit=6,
        exclude_recipe_ids=excluded_ids,
    )
    if not use_all_main_types:
        recommendations = [
            item for item in recommendations
            if item.get("main_type") in selected_main_types
        ]
    if replace_mode and recommendations:
        st.session_state.seasonal_excluded_recipe_ids.extend([item["id"] for item in recommendations])
        st.session_state.seasonal_excluded_recipe_ids = list(dict.fromkeys(st.session_state.seasonal_excluded_recipe_ids))
    elif recommendations:
        st.session_state.seasonal_excluded_recipe_ids = [item["id"] for item in recommendations]
    st.session_state.seasonal_recommendations = recommendations


def render_recommendation_cards(
    recommendations: list[dict],
    title: str,
    key_prefix: str,
) -> None:
    if not recommendations:
        return

    user_id = st.session_state.user["id"]
    favorite_recipe_ids = set(get_favorite_recipes(user_id))
    st.markdown(f'<div class="followup-title">{title}</div>', unsafe_allow_html=True)
    for recipe in recommendations:
        is_favorite = recipe["id"] in favorite_recipe_ids
        st.markdown(
            f"""
            <div class="recipe-card">
                <div class="recipe-title">{recipe['name']}</div>
                <div>{render_recipe_card_tags(recipe)}</div>
                <p><strong>推荐理由：</strong>{recipe['reason']}</p>
                <p class="metric-line">
                    {recipe['cook_time_minutes']} 分钟 ｜ {recipe['budget_level']} ｜ {recipe['difficulty']}难度
                </p>
                <p><strong>主要食材：</strong>{recipe['ingredients']}</p>
                <p class="recipe-description">{recipe['description']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key=f"recipe_actions_{key_prefix}_{recipe['id']}"):
            col1, col2, col3 = st.columns([0.95, 0.95, 1.1])
            if col1.button("就吃这个", key=f"{key_prefix}_pick_{recipe['id']}", use_container_width=True):
                if not is_favorite:
                    record_action(user_id, recipe["id"], "favorite")
                st.success(f"已帮你记住你喜欢 {recipe['name']}。")
            favorite_label = "取消收藏" if is_favorite else "先收藏"
            if col2.button(favorite_label, key=f"{key_prefix}_favorite_{recipe['id']}", use_container_width=True):
                if is_favorite:
                    remove_favorite_recipe(user_id, recipe["id"])
                else:
                    record_action(user_id, recipe["id"], "favorite")
                st.rerun()
            if col3.button("不太像我想吃的", key=f"{key_prefix}_skip_{recipe['id']}", use_container_width=True):
                record_action(user_id, recipe["id"], "skip")
                st.info(f"已记下你这次不太想吃 {recipe['name']}。")


def render_empty_recipe_state() -> None:
    st.markdown(
        """
        <div class="followup-title">抱歉，暂无此类菜品</div>
        <div class="section-note">
            可以换一个大类，或放宽口味、场景、预算等条件再试试。
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_input_area(preferences: dict) -> None:
    time_label, active_skill_groups = get_dynamic_skill_groups(preferences)
    hero_date_label = format_hero_date_label()
    normalized_main_types = normalize_main_type_picker_values(st.session_state.get("selected_main_types", []))
    if st.session_state.get("selected_main_types", []) != normalized_main_types:
        st.session_state.selected_main_types = normalized_main_types
    if st.session_state.sync_prompt_input:
        st.session_state.prompt_text_input = st.session_state.prompt_text
        st.session_state.sync_prompt_input = False

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-date hero-date--{HERO_DATE_FONT_STYLE}">{hero_date_label}</div>
            <div class="hero-shell">
                <div>
                    <div class="hero-kicker">Smart Food Picks</div>
                    <div class="hero-title">TastePilot</div>
                    <div class="hero-subtitle">
                        把你现在想吃的感觉告诉我，我来帮你决定这顿吃什么。少一点筛选，多一点被理解，
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
                        <div class="hero-mini-title">Right Now</div>
                        <span class="hero-emoji">🍲</span> 快一点，也更对味一点
                    </div>
                    <div class="hero-mini-card bottom">
                        <div class="hero-mini-title">Mood Board</div>
                        <span class="hero-emoji">✨</span> 香辣 / 清爽 / 治愈
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_seasonal_inspiration_card()
    st.markdown(
        """
        <div class="prompt-card">
            <div class="section-heading">告诉我你现在想吃什么</div>
            <div class="section-copy">
                可以先选大类，也可以直接输入一句模糊需求，比如“想吃热乎一点、别太贵、一个人吃”。
                不选大类时会默认从全部推荐池里帮你找。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="main-type-card">
            <div class="main-type-title">选择大类</div>
            <div class="main-type-copy">可多选；不选或选择“全部”时，会从四个大类一起推荐。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.multiselect(
        "选择菜谱大类",
        options=MAIN_TYPE_PICKER_OPTIONS,
        key="selected_main_types",
        placeholder="全部",
        help="；".join(f"{name}：{MAIN_TYPE_HELP[name]}" for name in MAIN_TYPE_OPTIONS),
        label_visibility="collapsed",
        on_change=on_main_type_change,
    )
    render_main_type_arrow_bridge()
    st.text_area(
        "输入一句话",
        key="prompt_text_input",
        placeholder="比如：我今天想吃辣一点，一个人吃，最好 15 分钟内能搞定",
        height=110,
        label_visibility="collapsed",
    )
    if st.session_state.main_type_notice:
        notice = st.session_state.main_type_notice
        st.markdown(f'<div class="main-type-warning">{notice}</div>', unsafe_allow_html=True)

    with st.container(key="prompt_skill_shell"):
        picker_col, selected_col = st.columns([0.095, 0.905], gap="small")
        with picker_col:
            st.markdown('<div class="prompt-skill-toggle">', unsafe_allow_html=True)
            with st.popover("＋"):
                for group_name, group_skills in active_skill_groups:
                    st.markdown(
                        (
                            '<div class="skill-section">'
                            f'<div class="skill-group-label">{group_name}'
                            f'<span class="skill-group-meta">{SKILL_GROUP_META.get(group_name, "")}</span>'
                            "</div></div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    if group_name == "偏好方向":
                        st.markdown(
                            '<div class="skill-popover-note">结合你当前时段、已选大类和长期偏好，先给你更值得点的几个。</div>',
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
                                type="primary" if skill_name in st.session_state.selected_skills else "secondary",
                                use_container_width=True,
                            )
            st.markdown("</div>", unsafe_allow_html=True)

        with selected_col:
            st.markdown('<div class="prompt-skill-tags">', unsafe_allow_html=True)
            render_selected_skills()
            st.markdown("</div>", unsafe_allow_html=True)
    render_prompt_tool_button_bridge()

    has_recommendations = bool(st.session_state.recommendations)
    with st.container(key="prompt_actions"):
        if has_recommendations:
            action_col1, action_col2, action_col3 = st.columns([1.2, 1.1, 0.9])
            with action_col1:
                if st.button("立即推荐菜谱", type="primary", use_container_width=True):
                    run_recommendation(preferences)
                    st.rerun()
            with action_col2:
                if st.button("换一批候选菜", use_container_width=True):
                    run_recommendation(preferences, replace_mode=True)
                    st.rerun()
            with action_col3:
                st.button("清空", on_click=clear_prompt, use_container_width=True)
        else:
            action_col1, action_col2 = st.columns([1.3, 0.95])
            with action_col1:
                if st.button("立即推荐菜谱", type="primary", use_container_width=True):
                    run_recommendation(preferences)
                    st.rerun()
            with action_col2:
                st.button("清空", on_click=clear_prompt, use_container_width=True)

    parsed = (
        parse_free_text_request(st.session_state.prompt_text_input)
        if st.session_state.prompt_text_input.strip()
        else {}
    )
    display_hints, has_main_type_conflict = build_display_hints_for_current_input(parsed)
    if display_hints:
        st.info(f"我先帮你理解成：{'、'.join(display_hints)}")
        if not has_main_type_conflict:
            st.markdown(
                f"""
                <div class="section-note">
                    <strong>理解标签：</strong> {render_tag_pills(display_hints)}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_recipe_cards() -> None:
    if st.session_state.get("last_query_signature") != build_current_query_signature():
        return

    recommendations = st.session_state.recommendations
    if recommendations:
        render_recommendation_cards(recommendations, "今晚先看这 3 个", "home")
    elif st.session_state.get("last_query"):
        render_empty_recipe_state()


def render_follow_up_actions(preferences: dict) -> None:
    if not st.session_state.recommendations:
        return

    st.markdown(
        """
        <div class="followup-shell">
            <div class="followup-title">还想再收窄一点吗</div>
            <div class="followup-copy">如果这 3 个里还没有特别心动的，我们可以继续往前推一步。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    follow_up_actions = get_follow_up_actions()
    cols = st.columns(len(follow_up_actions))
    for index, (label, skill) in enumerate(follow_up_actions):
        with cols[index]:
            if st.button(label, key=f"followup_{skill}_{index}", use_container_width=True):
                run_recommendation(preferences, append_skill=skill)
                st.rerun()


def render_seasonal_page(preferences: dict, preview_mode: bool = False) -> None:
    current_term_name = get_current_seasonal_term_name()
    if not preview_mode:
        st.session_state.seasonal_term = current_term_name
    term_name = st.session_state.get("seasonal_term", current_term_name)
    config = SEASONAL_PAGE_CONFIG.get(term_name, SEASONAL_PAGE_CONFIG[current_term_name])
    if term_name not in SEASONAL_PAGE_CONFIG:
        st.session_state.seasonal_term = current_term_name
        term_name = current_term_name
        config = SEASONAL_PAGE_CONFIG[term_name]

    if preview_mode:
        st.markdown('<div class="seasonal-switch-label">节气测试预览 · Seasonal Preview</div>', unsafe_allow_html=True)
        preview_terms = list(SEASONAL_PAGE_CONFIG.keys())
        with st.container(key="seasonal_term_switcher"):
            for row_start in range(0, len(preview_terms), 6):
                row_terms = preview_terms[row_start : row_start + 6]
                switch_cols = st.columns(6, gap="small")
                for column_index, preview_term in enumerate(row_terms):
                    with switch_cols[column_index]:
                        st.button(
                            preview_term,
                            key=f"preview_term_{preview_term}",
                            type="primary" if preview_term == term_name else "secondary",
                            use_container_width=True,
                            on_click=select_seasonal_preview_term,
                            args=(preview_term,),
                        )

    if not st.session_state.seasonal_recommendations:
        run_seasonal_recommendation(preferences, term_name)

    scenic_background_url = config.get("page_background_url", "")
    if scenic_background_url:
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image:
                    linear-gradient(rgba(252, 248, 242, 0.78), rgba(248, 241, 232, 0.82)),
                    url("{scenic_background_url}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    background_image = resolve_image_source(config["image_path"])
    background_position = config.get("background_position", "center")
    background_style = (
        f"background-image: url('{background_image}'); background-position: {background_position};"
        if background_image
        else "background: linear-gradient(135deg, rgba(253, 239, 213, 0.96), rgba(201, 153, 104, 0.78));"
    )

    st.markdown(
        f"""
        <div class="seasonal-page-hero" style="{background_style}">
            <div class="seasonal-page-overlay">
                <div class="seasonal-page-route">Seasonal Editorial · {term_name}</div>
                <div class="seasonal-page-kicker">{config['kicker']}</div>
                <div class="seasonal-page-title">{config['title']}</div>
                <div class="seasonal-page-copy">{config['intro']}</div>
                <div>{render_seasonal_tag_groups(config.get('display_tag_groups'), config['display_tags'])}</div>
                <div class="seasonal-page-meta">{config['scene_note']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="seasonal_action_shell"):
        action_col1, action_col2 = st.columns([1.1, 0.9], gap="small")
        with action_col1:
            if st.button("换一批这个时节的菜", key=f"refresh_seasonal_{term_name}", use_container_width=True):
                run_seasonal_recommendation(preferences, term_name, replace_mode=True)
                st.rerun()
        with action_col2:
            if st.button("返回智能推荐主页", key=f"back_home_{term_name}", use_container_width=True):
                open_recommend_page()
                st.rerun()

    seasonal_filter_options = [MAIN_TYPE_ALL_OPTION, *MAIN_TYPE_OPTIONS]
    normalized_seasonal_main_types = normalize_main_type_picker_values(st.session_state.get("seasonal_main_types", []))
    if st.session_state.get("seasonal_main_types", []) != normalized_seasonal_main_types:
        st.session_state.seasonal_main_types = normalized_seasonal_main_types

    with st.container(key="seasonal_main_type_filter_shell"):
        st.multiselect(
            "想看哪一类",
            seasonal_filter_options,
            key="seasonal_main_types",
            placeholder="全部",
            on_change=on_seasonal_main_type_change,
            help="按照菜谱数据库中的一级分类筛选当前节气推荐。",
        )
        st.caption("可多选；不选或选择“全部”时，会从当前节气的全部分类一起推荐。")
    render_main_type_arrow_bridge()

    st.markdown(
        """
        <div class="seasonal-section-card">
            <div class="seasonal-section-title">这页会给你什么</div>
            <div class="seasonal-section-copy">
                这里先不走模糊输入，而是先把这段时节更应景的菜品单独拎出来。你可以把它理解成
                “最近值得吃什么”的轻专题页。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recommendations = st.session_state.seasonal_recommendations
    selected_main_types = normalize_main_type_picker_values(st.session_state.get("seasonal_main_types", []))
    use_all_main_types = MAIN_TYPE_ALL_OPTION in selected_main_types
    selected_main_type_label = " / ".join(selected_main_types)
    recommendation_title = (
        f"先看看这批 {term_name} {selected_main_type_label}"
        if not use_all_main_types
        else f"先看看这批 {term_name} 时令菜"
    )
    if recommendations:
        render_recommendation_cards(
            recommendations,
            recommendation_title,
            f"seasonal_{term_name}_{selected_main_type_label}",
        )
    else:
        render_empty_recipe_state()


def main() -> None:
    sync_auth_mode_from_query()
    sync_page_from_query()
    restore_login_session()
    sync_login_cookie()
    render_sidebar_toggle_bridge()

    if st.session_state.user is None:
        render_auth_screen()
        return

    preferences = get_user_preferences(st.session_state.user["id"])
    render_sidebar(preferences)
    if st.session_state.current_page == "profile":
        render_profile_page()
    elif st.session_state.current_page == "seasonal":
        render_seasonal_page(preferences)
    elif st.session_state.current_page == "seasonal_preview":
        render_seasonal_page(preferences, preview_mode=True)
    else:
        render_input_area(preferences)
        render_recipe_cards()
        render_follow_up_actions(preferences)
    render_page_scroll_bridge()


main()

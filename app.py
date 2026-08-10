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
LIXIA_CARD_PATH = ASSET_DIR / "lixia-card.png"
LIDONG_CARD_PATH = ASSET_DIR / "lidong-card.png"
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
        line-height: 1.4;
        text-decoration: none !important;
        text-shadow: 0 8px 18px rgba(68, 39, 22, 0.22);
        border-bottom: none !important;
        padding-bottom: 0;
        transition: opacity 160ms ease;
        -webkit-text-fill-color: rgba(255, 250, 244, 0.94) !important;
    }
    .seasonal-card-link:hover {
        opacity: 0.86;
    }
    .seasonal-card {
        cursor: pointer;
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
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
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
        padding: 1rem 1.12rem 0.78rem;
        border-radius: 24px;
        background: linear-gradient(180deg, rgba(255, 251, 246, 0.78), rgba(255, 245, 236, 0.58));
        border: 1px solid rgba(219, 176, 141, 0.34);
        box-shadow:
            0 12px 26px rgba(149, 97, 63, 0.055),
            inset 0 1px 0 rgba(255, 255, 255, 0.34);
        color: #6b4530;
        margin: 0.74rem 0 0.72rem;
    }
    .main-type-title {
        color: #8a3728;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .main-type-copy {
        color: rgba(107, 69, 48, 0.72);
        font-size: 0.88rem;
        line-height: 1.55;
        margin-bottom: 0.42rem;
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
    .st-key-main_type_picker div[data-baseweb="select"] > div > div {
        background: linear-gradient(180deg, rgba(255, 235, 214, 0.98), rgba(246, 203, 174, 0.9)) !important;
        border: 1px solid rgba(203, 133, 89, 0.48) !important;
        border-radius: 18px !important;
        box-shadow:
            0 10px 22px rgba(159, 95, 58, 0.105),
            inset 0 1px 0 rgba(255, 255, 255, 0.46) !important;
        color: #5e3b2a !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"],
    .st-key-main_type_picker [data-baseweb="tag"] {
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
    .st-key-main_type_picker [data-baseweb="tag"] > * {
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
    .st-key-main_type_picker [class*="multiValue"] {
        color: #7b4f39 !important;
        fill: #7b4f39 !important;
        background: transparent !important;
        -webkit-text-fill-color: #7b4f39 !important;
    }
    .st-key-selected_main_types [data-baseweb="tag"] [role="button"],
    .st-key-main_type_picker [data-baseweb="tag"] [role="button"] {
        background: transparent !important;
        color: #7b4f39 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] svg,
    .st-key-selected_main_types div[data-baseweb="select"] path,
    .st-key-main_type_picker div[data-baseweb="select"] svg,
    .st-key-main_type_picker div[data-baseweb="select"] path {
        color: #8a4d2b !important;
        fill: #8a4d2b !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] input::placeholder,
    .st-key-main_type_picker div[data-baseweb="select"] input::placeholder {
        color: #8a4d2b !important;
        opacity: 1 !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] [class*="placeholder"],
    .st-key-selected_main_types div[data-baseweb="select"] [class*="Placeholder"],
    .st-key-main_type_picker div[data-baseweb="select"] [class*="placeholder"],
    .st-key-main_type_picker div[data-baseweb="select"] [class*="Placeholder"] {
        color: #8a4d2b !important;
        -webkit-text-fill-color: #8a4d2b !important;
    }
    .st-key-selected_main_types div[data-baseweb="select"] .st-dg.st-cq,
    .st-key-main_type_picker div[data-baseweb="select"] .st-dg.st-cq,
    .st-key-selected_main_types div[data-baseweb="select"] .st-dg.st-cq *,
    .st-key-main_type_picker div[data-baseweb="select"] .st-dg.st-cq * {
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
        z-index: 2;
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
            padding: 0.86rem 0.92rem 0.68rem;
            margin: 0.58rem 0 0.54rem;
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
        .seasonal-card-link {
            top: 0.95rem;
            right: 1rem;
            font-size: 0.82rem;
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
    "咖啡搭子": {"main_types": {"饮品", "甜品点心"}, "diet_goals": {"夜宵安慰"}},
    "轻一点": {"favorite_flavors": {"清淡"}, "diet_goals": {"均衡饮食", "减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "快手": {"time_limits": {"15 分钟内", "30 分钟内"}},
    "下饭": {"diet_goals": {"下饭解馋"}, "main_types": {"正餐主食", "家常菜肴"}},
    "省钱": {"budget_levels": {"低预算"}},
    "下午茶": {"main_types": {"饮品", "甜品点心", "轻食早午餐"}},
    "甜一点": {"main_types": {"甜品点心", "饮品"}, "diet_goals": {"夜宵安慰"}},
    "治愈一点": {"diet_goals": {"夜宵安慰"}, "favorite_flavors": {"家常"}},
    "聚餐": {"diet_goals": {"朋友聚餐"}, "main_types": {"家常菜肴", "正餐主食"}},
    "夜宵": {"diet_goals": {"夜宵安慰"}},
    "高蛋白": {"diet_goals": {"高蛋白增肌"}, "favorite_flavors": {"鲜香"}},
    "奶香": {"main_types": {"甜品点心", "饮品"}, "favorite_flavors": {"酸甜"}},
    "一个人": {"budget_levels": {"低预算"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "暖胃": {"diet_goals": {"夜宵安慰"}, "main_types": {"汤锅粥羹"}},
    "低糖": {"diet_goals": {"减脂清爽"}},
    "香辣": {"favorite_flavors": {"香辣", "重口"}, "diet_goals": {"下饭解馋"}},
    "解馋": {"diet_goals": {"下饭解馋"}, "favorite_flavors": {"重口", "鲜香"}},
    "汤面": {"main_types": {"汤锅粥羹"}},
    "果香": {"main_types": {"饮品", "甜品点心"}, "favorite_flavors": {"酸口", "酸甜"}},
    "茶点": {"main_types": {"甜品点心", "饮品"}},
    "清淡": {"favorite_flavors": {"清淡"}, "diet_goals": {"均衡饮食", "减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "汤锅": {"main_types": {"汤锅粥羹"}},
    "家常": {"favorite_flavors": {"家常", "酱香"}, "diet_goals": {"均衡饮食"}},
    "不油腻": {"diet_goals": {"减脂清爽"}, "vegetarian_preferences": {"希望多素食", "严格素食"}},
    "一人食": {"budget_levels": {"低预算"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "安慰系": {"diet_goals": {"夜宵安慰"}, "favorite_flavors": {"家常", "酸甜"}},
    "解压系": {"diet_goals": {"下饭解馋"}, "favorite_flavors": {"香辣", "重口"}},
    "暖胃系": {"diet_goals": {"夜宵安慰"}, "main_types": {"汤锅粥羹"}},
    "提神系": {"main_types": {"饮品"}, "time_limits": {"15 分钟内", "30 分钟内"}},
    "犒赏系": {"diet_goals": {"朋友聚餐"}, "main_types": {"甜品点心", "饮品", "家常菜肴"}},
}


MAIN_TYPE_OPTIONS = ["正餐主食", "家常菜肴", "汤锅粥羹", "轻食早午餐", "甜品点心", "饮品"]
MAIN_TYPE_HELP = {
    "正餐主食": "饭、面、粉、饼、三明治等更顶饱的一餐",
    "家常菜肴": "炒菜、热菜、冷盘、下饭菜等菜肴本身",
    "汤锅粥羹": "汤、粥、锅物、汤面等热乎带汤的方向",
    "轻食早午餐": "沙拉、能量碗、早午餐、轻正餐",
    "甜品点心": "甜品、烘焙、茶点、小点心",
    "饮品": "咖啡、奶茶、果茶、茶饮和特调",
}
MAIN_TYPE_COURSE_TYPES = {
    "正餐主食": {"main", "savory"},
    "家常菜肴": {"main", "savory"},
    "汤锅粥羹": {"main", "savory"},
    "轻食早午餐": {"light_meal"},
    "甜品点心": {"dessert", "snack", "sweet"},
    "饮品": {"drink"},
}
MAIN_TYPE_PRIMARY_BUCKET = {
    "正餐主食": "staple",
    "家常菜肴": "dish",
    "汤锅粥羹": "soup_hotpot",
    "轻食早午餐": "light_meal",
    "甜品点心": "dessert",
    "饮品": "drink",
}
MAIN_TYPE_STAPLE_COMPATIBILITY = {
    "正餐主食": {"饭类", "面类", "粉类", "饼类", "面包三明治"},
    "家常菜肴": {"菜肴"},
    "汤锅粥羹": {"汤粥", "锅物", "面类"},
    "轻食早午餐": {"轻食", "面包三明治", "饭类"},
    "甜品点心": {"甜品"},
    "饮品": {"饮品"},
}

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
        "main_types": ["正餐主食", "家常菜肴", "轻食早午餐", "甜品点心", "饮品"],
        "scene_note": "更适合春天刚开场时那种想吃得轻一点、鲜一点的胃口。",
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
        "main_types": ["正餐主食", "家常菜肴", "轻食早午餐", "饮品"],
        "scene_note": "更适合天气开始热起来时那种想吃得轻一点、凉快一点的节奏。",
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
        "main_types": ["正餐主食", "家常菜肴", "汤锅粥羹", "甜品点心", "饮品"],
        "scene_note": "更适合现在这段从盛夏转向初秋的胃口和节奏。",
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
        "main_types": ["正餐主食", "家常菜肴", "汤锅粥羹", "甜品点心"],
        "scene_note": "更适合天气开始冷下来之后，那种想吃热乎、厚实一点的胃口。",
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
    if page in {"recommend", "profile", "seasonal"}:
        st.session_state.current_page = page


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
    st.session_state.excluded_recipe_ids = []
    st.session_state.preference_notice = ""
    st.session_state.profile_notice = ""
    st.session_state.current_page = "recommend"
    st.session_state.seasonal_term = get_current_seasonal_term_name()
    st.session_state.seasonal_recommendations = []
    st.session_state.seasonal_excluded_recipe_ids = []


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


def on_main_type_change() -> None:
    st.session_state.main_type_notice = ""
    st.session_state.recommendations = []
    st.session_state.last_query = {}
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

        function bindMainTypeArrowBehavior() {
          const root = parentDoc.querySelector('.st-key-selected_main_types div[data-baseweb="select"]');
          if (!root || root.dataset.tastepilotArrowBound === "1") {
            return;
          }
          root.dataset.tastepilotArrowBound = "1";

          const getCombobox = () => root.querySelector('input[role="combobox"]');
          const getArrow = () => root.querySelector('svg[title="open"]');

          const syncArrow = () => {
            const combobox = getCombobox();
            const arrow = getArrow();
            if (!combobox || !arrow) {
              return;
            }
            const expanded = combobox.getAttribute("aria-expanded") === "true";
            arrow.style.transition = "transform 160ms ease";
            arrow.style.transform = expanded ? "rotate(180deg)" : "rotate(0deg)";
          };

          root.addEventListener(
            "mousedown",
            (event) => {
              const arrow = getArrow();
              const combobox = getCombobox();
              if (!arrow || !combobox) {
                return;
              }

              const clickedArrow = arrow === event.target || arrow.contains(event.target);
              if (!clickedArrow) {
                window.parent.setTimeout(syncArrow, 30);
                return;
              }

              const expanded = combobox.getAttribute("aria-expanded") === "true";
              if (!expanded) {
                window.parent.setTimeout(syncArrow, 30);
                window.parent.setTimeout(syncArrow, 140);
                return;
              }

              event.preventDefault();
              event.stopPropagation();

              const bodyEventInit = {
                bubbles: true,
                cancelable: true,
                composed: true,
                view: window.parent,
                clientX: 8,
                clientY: 8,
                button: 0,
              };
              if (typeof combobox.focus === "function") {
                combobox.focus();
              }
              combobox.dispatchEvent(
                new KeyboardEvent("keydown", {
                  key: "Escape",
                  code: "Escape",
                  keyCode: 27,
                  which: 27,
                  bubbles: true,
                  cancelable: true,
                })
              );
              combobox.dispatchEvent(
                new KeyboardEvent("keyup", {
                  key: "Escape",
                  code: "Escape",
                  keyCode: 27,
                  which: 27,
                  bubbles: true,
                  cancelable: true,
                })
              );
              ["mousedown", "mouseup", "click"].forEach((type) => {
                parentDoc.body.dispatchEvent(new MouseEvent(type, bodyEventInit));
              });

              window.parent.setTimeout(syncArrow, 30);
              window.parent.setTimeout(syncArrow, 140);
              window.parent.setTimeout(syncArrow, 260);
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
        }

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
          if (!card || !trigger || card.dataset.tastepilotSeasonalBound === "1") {
            return;
          }

          card.dataset.tastepilotSeasonalBound = "1";
          card.addEventListener("click", (event) => {
            const clickedLink = event.target.closest(".seasonal-card-link");
            if (clickedLink) {
              event.preventDefault();
            }
            trigger.click();
          });
        }

        bindSeasonalCard();

        const observer = new MutationObserver(bindSeasonalCard);
        observer.observe(parentDoc.body, { subtree: true, childList: true, attributes: true });
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
        @media (prefers-color-scheme: light) {
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
        }
        @media (prefers-color-scheme: dark) {
            .password-row-label {
                color: #f3eee8;
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
    selected_main_types = st.session_state.get("selected_main_types", [])
    parsed_main_types = parsed.get("main_types", [])
    conflicting_main_types = [
        main_type for main_type in parsed_main_types if main_type not in selected_main_types
    ] if selected_main_types else []
    has_main_type_conflict = bool(conflicting_main_types)
    selected_course_types = set()
    compatible_staple_categories = set()
    for main_type in selected_main_types:
        selected_course_types.update(MAIN_TYPE_COURSE_TYPES.get(main_type, set()))
        compatible_staple_categories.update(MAIN_TYPE_STAPLE_COMPATIBILITY.get(main_type, set()))

    if selected_main_types:
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
        main_types = parsed.get("main_types", [])
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
    }
    return query, parsed


def build_display_hints_for_current_input(parsed: dict) -> tuple[list[str], bool]:
    selected_main_types = st.session_state.get("selected_main_types", [])
    parsed_main_types = parsed.get("main_types", [])
    conflicting_main_types = [
        main_type for main_type in parsed_main_types if main_type not in selected_main_types
    ] if selected_main_types else []
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


def run_recommendation(preferences: dict, append_skill: str | None = None, replace_mode: bool = False) -> None:
    if not st.session_state.get("selected_main_types"):
        st.session_state.main_type_notice = "先选择至少一个大类，我再帮你把范围收准。"
        st.session_state.recommendations = []
        st.session_state.last_query = {}
        st.session_state.excluded_recipe_ids = []
        return

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


def render_seasonal_inspiration_card() -> None:
    term_name = get_current_seasonal_term_name()
    config = SEASONAL_PAGE_CONFIG.get(term_name, SEASONAL_PAGE_CONFIG[get_current_seasonal_term_name()])
    background_image = resolve_image_source(config["image_path"])
    background_style = (
        f"background-image: linear-gradient(180deg, rgba(255, 248, 239, 0.08), rgba(84, 54, 35, 0.14)), url('{background_image}');"
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
        st.button("open seasonal card", key="open_seasonal_card_button", on_click=open_seasonal_page)
    render_seasonal_card_bridge()


def run_seasonal_recommendation(preferences: dict, term_name: str, replace_mode: bool = False) -> None:
    config = SEASONAL_PAGE_CONFIG.get(term_name)
    if not config:
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
        "main_types": config.get("main_types", []),
        "staple_categories": [],
        "solar_terms": config.get("seasonal_tags", [term_name]),
        "cuisine_groups": [],
        "primary_bucket": None,
        "mood_bucket": None,
        "mood_detected": None,
        "main_type_conflict": False,
        "conflicting_main_types": [],
    }
    recommendations = recommend_recipes(
        query=query,
        preferences=preferences,
        user_id=st.session_state.user["id"],
        limit=6,
        exclude_recipe_ids=excluded_ids,
    )
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

    st.markdown(f'<div class="followup-title">{title}</div>', unsafe_allow_html=True)
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
        if col1.button(f"就吃这个", key=f"{key_prefix}_pick_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "favorite")
            st.success(f"已帮你记住你喜欢 {recipe['name']}。")
        if col2.button(f"先收藏", key=f"{key_prefix}_favorite_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "favorite")
            st.success(f"已收藏 {recipe['name']}。")
        if col3.button(f"不太像我想吃的", key=f"{key_prefix}_skip_{recipe['id']}", use_container_width=True):
            record_action(st.session_state.user["id"], recipe["id"], "skip")
            st.info(f"已记下你这次不太想吃 {recipe['name']}。")


def render_input_area(preferences: dict) -> None:
    time_label, active_skill_groups = get_dynamic_skill_groups(preferences)
    hero_date_label = format_hero_date_label()
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
                先选一个或多个大类，再输入一句模糊需求，比如“想吃热乎一点、别太贵、一个人吃”，
                也可以点下面的 skill，让我们更快接近那道对的菜。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="main-type-card">
            <div class="main-type-title">先选你想看的大类</div>
            <div class="main-type-copy">可以多选。大类负责确定推荐池，口味、菜系、场景会作为标签继续精细排序。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.multiselect(
        "选择菜谱大类",
        options=MAIN_TYPE_OPTIONS,
        key="selected_main_types",
        placeholder="例如：正餐主食、家常菜肴、饮品",
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
    if st.session_state.main_type_notice or (
        st.session_state.prompt_text_input.strip() and not st.session_state.selected_main_types
    ):
        notice = st.session_state.main_type_notice or "先选择至少一个大类，再告诉我具体想吃什么。"
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
    recommendations = st.session_state.recommendations
    render_recommendation_cards(recommendations, "今晚先看这 3 个", "home")


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


def render_seasonal_page(preferences: dict) -> None:
    current_term_name = get_current_seasonal_term_name()
    st.session_state.seasonal_term = current_term_name
    term_name = st.session_state.get("seasonal_term", current_term_name)
    config = SEASONAL_PAGE_CONFIG.get(term_name, SEASONAL_PAGE_CONFIG[current_term_name])
    if term_name not in SEASONAL_PAGE_CONFIG:
        st.session_state.seasonal_term = current_term_name
        term_name = current_term_name
        config = SEASONAL_PAGE_CONFIG[term_name]

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
    background_style = (
        f"background-image: url('{background_image}');"
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
    if recommendations:
        render_recommendation_cards(recommendations, f"先看看这批 {term_name} 时令菜", f"seasonal_{term_name}")
    else:
        st.info("这一页暂时还没筛出合适的时令菜，我们可以继续补更丰富的节气内容。")


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
    else:
        render_input_area(preferences)
        render_recipe_cards()
        render_follow_up_actions(preferences)


main()

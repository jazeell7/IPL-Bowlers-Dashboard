from __future__ import annotations

import base64
import hashlib
import html
import mimetypes
import re
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import mannwhitneyu

# ============================================================
# IPL 360 — Bowling Performance Intelligence
# Keep Dashboard.py and ipl.db in the same project folder.
# Portraits: images/ and assets/bowlers/
# ============================================================

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "ipl.db"
IMAGE_DIR = ROOT / "images"
PORTRAIT_DIR = ROOT / "assets" / "bowlers"

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)

PLAYER_IMAGES = {
    "A Ashish Reddy": r"images\A Ashish Reddy.png",
    "YS Chahal": r"images\Ys chahal.png",
    "B Kumar": r"images\B Kumar.avif",
    "SP Narine": r"images\SP Narine.avif",
    "PP Chawla": r"images\Piyush-Chawla.png",
    "R Ashwin": r"images\R Ashwin.avif",
}
DEFAULT_PLAYER_IMAGE = IMAGE_DIR / "unknown_player_image.png"

BLUE = "#E5252A"
CYAN = "#F56D75"
GREEN = "#F56D75"
PALE = "#F3F3F5"
MUTED = "#A5A8B0"
GRID = "rgba(243,243,245,.085)"
PHASES = ["Powerplay", "Middle", "Death"]
CREDITED = {
    "caught", "bowled", "lbw", "caught and bowled",
    "stumped", "hit wicket",
}
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".avif")

st.set_page_config(
    page_title="IPL 360 | Bowling Intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- DESIGN ----------------------------

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg:#1C1111; --panel:#302120; --panel2:#3E2A29;
  --blue:#E5252A; --text:#f2f5fb; --muted:#98a4b9;
  --line:rgba(220,230,248,.09);
}
.stApp {
  color:var(--text);
  font-family:'DM Sans',sans-serif;
  background:
    radial-gradient(ellipse at 76% -8%,rgba(223,61,74,.21),transparent 34%),
    radial-gradient(ellipse at 8% 45%,rgba(141,54,61,.09),transparent 38%),
    linear-gradient(135deg,#1B1010,#261817 53%,#1A1010);
}
header[data-testid="stHeader"] {background:transparent}
#MainMenu,footer {visibility:hidden}
.block-container {max-width:1600px;padding:1.1rem 1.35rem 2.5rem}
h1,h2,h3 {font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.04em;color:#f2f5fb}
h1 {font-size:clamp(1.7rem,3vw,2.8rem)!important;line-height:1.05!important}
h2 {font-size:1.4rem!important}
[data-testid="stCaptionContainer"] p {color:var(--muted)!important;font-size:.78rem}
section[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#241515,#1E1212);
  border-right:1px solid rgba(219,230,255,.08);
}
.brand {
  padding:15px;margin-bottom:16px;border:1px solid rgba(255,112,124,.24);
  border-radius:13px;background:linear-gradient(135deg,rgba(177,42,53,.48),#321A19);
}
.brand-name {font:700 21px 'Space Grotesk',sans-serif;letter-spacing:-.05em}
.brand-sub {color:#E8A9AE;font:9px 'DM Mono',monospace;letter-spacing:.12em;margin-top:4px}
.sidebar-heading {
  font:500 9px 'DM Mono',monospace;letter-spacing:.16em;color:#88696C;
  margin:18px 8px 7px;text-transform:uppercase
}
.sidebar-team {display:flex;justify-content:space-between;padding:5px 8px;color:#bec6d4;font-size:11px}
.sidebar-bullet {display:inline-block;width:7px;height:7px;border-radius:3px;margin-right:8px}
.topline {
  display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  padding:0 2px 11px;border-bottom:1px solid var(--line);margin-bottom:14px;
  color:#8994a8;font-size:11px
}
.topline strong {color:#e8edf7}
.hero {
  position:relative;isolation:isolate;overflow:hidden;
  display:flex;align-items:center;justify-content:space-between;gap:20px;
  min-height:160px;margin:7px 0 18px;padding:22px 27px;
  border:1px solid rgba(240,132,141,.25);border-radius:16px;
  background:
    radial-gradient(ellipse at 78% 45%,rgba(183,28,41,.20),transparent 32%),
    radial-gradient(ellipse at 14% 115%,rgba(214,64,76,.24),transparent 48%),
    linear-gradient(115deg,#311110,#441917 44%,#2A1110);
  box-shadow:0 20px 48px rgba(0,0,0,.3);
  animation:heroDrift 16s ease-in-out infinite alternate;
}
.hero:before {
  content:'';position:absolute;inset:-40%;z-index:0;pointer-events:none;
  background:repeating-linear-gradient(132deg,transparent 0 34px,rgba(255,121,132,.045) 34px 36px,transparent 36px 70px);
  animation:gridDrift 30s linear infinite
}
.hero > div {position:relative;z-index:1}
.hero-atmosphere {position:absolute!important;inset:0;pointer-events:none;overflow:hidden;z-index:0!important}
.hero-beam {
  position:absolute;top:-80%;height:260%;width:2px;
  background:linear-gradient(180deg,transparent,rgba(255,104,117,.6),rgba(255,91,105,.08),transparent);
  opacity:0;transform:rotate(28deg);animation:beamTravel 9s linear infinite
}
.hero-beam.b1 {left:18%;animation-delay:-2s}
.hero-beam.b2 {left:56%;animation-delay:-6s;animation-duration:13s}
.hero-beam.b3 {left:83%;animation-delay:-9s;animation-duration:11s}
.hero-particle {
  position:absolute;width:3px;height:3px;border-radius:50%;background:#FFB9BF;
  box-shadow:0 0 8px 2px rgba(255,81,95,.7);
  animation:particleFloat 7s ease-in-out infinite
}
.hero-particle.p1 {left:38%;top:28%}
.hero-particle.p2 {left:49%;top:76%;animation-delay:-2s}
.hero-particle.p3 {left:68%;top:19%;animation-delay:-3s}
.hero-particle.p4 {left:91%;top:68%;animation-delay:-4s}
.hero-particle.p5 {left:76%;top:84%;animation-delay:-5s}
.hero-eyebrow {color:#FF9AA2;font:500 9px 'DM Mono',monospace;letter-spacing:.21em}
.hero-title {
  color:#f3f6ff;font:700 clamp(23px,3vw,36px) 'Space Grotesk',sans-serif;
  line-height:1.08;margin-top:7px;letter-spacing:-.055em
}
.hero-title span {color:#F56D75}
.hero-copy {font-size:11px;color:#a4afc3;line-height:1.6;max-width:650px;margin-top:9px}
.hero-stats {display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}
.hero-pill {
  border:1px solid rgba(247,170,176,.17);border-radius:99px;padding:6px 9px;
  background:rgba(29,9,8,.23);color:#c0cce1;font:9px 'DM Mono',monospace
}
.hero-pill b {color:#FF9DA5;font-weight:500}
.field-stage {
  position:relative;flex:0 0 clamp(220px,28%,340px);height:145px;
  perspective:900px;isolation:isolate;overflow:visible
}
.field-aura {
  position:absolute;inset:10px 8px 18px;
  background:radial-gradient(ellipse,rgba(255,65,81,.19),transparent 68%);
  filter:blur(9px);animation:aura 5s ease-in-out infinite alternate
}
.field-map {
  position:absolute;left:7%;top:4%;width:86%;height:85%;
  border-radius:48% / 43%;transform:rotateX(56deg) rotateZ(-19deg);
  transform-style:preserve-3d;background:linear-gradient(145deg,#1c4c48,#12312f 55%,#290E0D);
  border:1px solid rgba(255,105,117,.68);
  box-shadow:0 8px 0 #250B0A,0 16px 25px rgba(0,0,0,.45);
  animation:fieldHover 7s ease-in-out infinite
}
.field-map:before {
  content:'';position:absolute;inset:5%;border:1px solid rgba(255,151,160,.42);
  border-radius:48% / 43%;box-shadow:inset 0 0 20px rgba(255,69,84,.11)
}
.field-map:after {
  content:'';position:absolute;inset:14% 24%;border:1px solid rgba(255,109,121,.5);
  border-radius:48% / 43%;background:rgba(255,68,84,.08)
}
.field-lines {position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.field-zone {position:absolute;z-index:2;border-radius:50%;filter:blur(.2px)}
.field-zone.power {
  left:12%;top:24%;width:26%;height:35%;
  background:radial-gradient(ellipse,rgba(255,76,91,.4),transparent 70%);
  animation:zonePulse 3s ease-in-out infinite
}
.field-zone.death {
  right:11%;bottom:15%;width:27%;height:33%;
  background:radial-gradient(ellipse,rgba(255,91,105,.3),transparent 70%);
  animation:zonePulse 4s ease-in-out infinite reverse
}
.delivery {
  position:absolute;z-index:5;width:7px;height:7px;border-radius:50%;
  background:#d8f5ff;border:1px solid white;box-shadow:0 0 12px #E5252A;
  animation:zonePulse 2s ease-in-out infinite
}
.delivery.d1 {left:27%;top:39%}
.delivery.d2 {left:48%;top:55%;animation-delay:.4s}
.delivery.d3 {left:70%;top:34%;animation-delay:.8s}
.delivery.d4 {left:61%;top:69%;width:5px;height:5px}
.delivery-trail {
  position:absolute;z-index:4;left:29%;top:42%;width:43%;height:2px;
  transform:rotate(18deg);background:linear-gradient(90deg,transparent,#FF737F,transparent);
  animation:trail 3s ease-in-out infinite
}
.field-label {position:absolute;right:0;bottom:0;color:#D57E85;font:8px 'DM Mono',monospace;letter-spacing:.1em;text-align:right}
.field-coord {position:absolute;left:0;top:0;color:#FF99A1;font:7px 'DM Mono',monospace}
.section-head {display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin:19px 0 10px}
.section-title {font:600 15px 'Space Grotesk',sans-serif;color:#f0f4fb}
.section-sub {font-size:10px;color:#8f99ab;margin-top:3px}
.section-tag {font:9px 'DM Mono',monospace;color:#FF7883;letter-spacing:.12em;white-space:nowrap}
.kpi {
  min-height:86px;padding:12px 14px;border-radius:11px;
  border:1px solid rgba(223,233,250,.08);
  background:linear-gradient(140deg,#3A2B2A,#2C2020);
  animation:cardIn .4s both
}
.kpi-label {font:9px 'DM Mono',monospace;letter-spacing:.09em;color:#96a1b3;text-transform:uppercase}
.kpi-value {font:600 clamp(1.15rem,1.6vw,1.55rem) 'Space Grotesk',sans-serif;color:#f2f5fb;margin-top:6px}
.kpi-value.blue {color:#F56D75}
.kpi-value.green {color:#65d9ab}
.kpi-detail {font-size:9px;color:#7f8b9e;margin-top:4px}
.profile-card {
  border:1px solid rgba(241,112,123,.24);border-radius:15px;padding:14px;
  background:linear-gradient(132deg,#3E2120,#4B1E1C 47%,#2D1817);
  box-shadow:0 18px 40px rgba(0,0,0,.25)
}
.profile-image {
  width:100%;height:205px;object-fit:contain;object-position:center bottom;
  border-radius:10px;display:block;background:linear-gradient(180deg,#4A2120,#291716)
}
.profile-name {color:#f4f6fb;font:600 clamp(1.25rem,1.8vw,1.75rem) 'Space Grotesk',sans-serif}
.profile-sub {font-size:11px;color:#bac9e7;margin-top:4px}
.chip {
  display:inline-block;border:1px solid rgba(255,137,147,.26);border-radius:99px;
  padding:4px 8px;color:#FFB8BE;background:rgba(216,74,86,.12);
  font:9px 'DM Mono',monospace;margin-top:8px
}
.fact-label {font:9px 'DM Mono',monospace;color:#C58F93;letter-spacing:.1em;margin-top:10px}
.fact {font-size:11px;color:#e2e9f8;margin-top:3px}
.profile-stats {
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  margin-top:13px;background:rgba(29,11,10,.32);
  border:1px solid rgba(255,165,172,.13);border-radius:10px;overflow:hidden
}
.profile-stat {padding:8px;border-right:1px solid rgba(255,165,172,.12)}
.profile-stat:last-child {border-right:0}
.profile-stat-label {font-size:9px;color:#D2A5A9}
.profile-stat-value {font:600 16px 'Space Grotesk',sans-serif;color:#f5f7fc;margin-top:3px}
.chart-panel {
  border:1px solid rgba(225,234,249,.075);border-radius:12px;
  background:linear-gradient(145deg,rgba(55,42,42,.95),rgba(42,31,31,.98));
  padding:4px;box-shadow:0 12px 26px rgba(0,0,0,.14)
}
[data-testid="stPlotlyChart"] {border-radius:9px}
.player-tile {
  border:1px solid rgba(223,233,250,.09);border-radius:13px;
  background:linear-gradient(145deg,#3B2625,#2B1B1A);padding:10px;
  transition:transform .2s,border-color .2s
}
.player-tile:hover {transform:translateY(-3px);border-color:rgba(255,104,117,.5)}
.tile-image {
  width:100%;height:132px;object-fit:contain;object-position:center bottom;
  border-radius:9px;background:linear-gradient(180deg,#4A2120,#291716);display:block
}
.tile-name {font:600 13px 'Space Grotesk',sans-serif;color:#f2f5fb;margin:9px 0 3px}
.tile-meta {font:9px 'DM Mono',monospace;color:#D89A9F}
.tile-stats {font-size:10px;color:#b6c1d3;margin:8px 0}
.stButton button {
  background:#E5252A;color:white;border:1px solid rgba(255,159,167,.20);
  border-radius:8px;font-weight:600;transition:transform .18s,box-shadow .18s
}
.stButton button:hover {background:#F56D75;color:white;transform:translateY(-1px)}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div {
  background:#332525;border-color:#4E3C3B;border-radius:8px;min-height:37px
}
label {color:#b6c0d0!important;font-size:10px!important}
.insight {
  border:1px solid rgba(255,96,109,.21);border-radius:11px;
  background:linear-gradient(110deg,rgba(211,63,75,.13),rgba(51,36,35,.7));
  padding:11px 14px;color:#c2cad7;font-size:11px;line-height:1.55;margin:5px 0 13px
}
.insight strong {color:#FF9FA7}
hr {border-color:rgba(220,230,248,.09)!important}
@keyframes heroDrift {from{background-position:0 0}to{background-position:100% 50%}}
@keyframes gridDrift {from{transform:translateX(0)}to{transform:translateX(70px)}}
@keyframes beamTravel {0%{transform:translateX(-80px) rotate(28deg);opacity:0}20%{opacity:.7}100%{transform:translateX(180px) rotate(28deg);opacity:0}}
@keyframes particleFloat {0%,100%{transform:translateY(10px);opacity:0}50%{transform:translateY(-12px);opacity:.9}}
@keyframes fieldHover {0%,100%{transform:rotateX(56deg) rotateZ(-19deg) translateY(-3px)}50%{transform:rotateX(53deg) rotateZ(-16deg) translateY(-8px)}}
@keyframes aura {from{opacity:.55;transform:scale(.94)}to{opacity:1;transform:scale(1.06)}}
@keyframes zonePulse {0%,100%{opacity:.5;transform:scale(.92)}50%{opacity:1;transform:scale(1.1)}}
@keyframes trail {0%,100%{opacity:.2;transform:rotate(18deg) scaleX(.6)}50%{opacity:1;transform:rotate(18deg) scaleX(1)}}
@keyframes cardIn {from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
@media(max-width:1000px){.hero{padding:17px}.profile-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.block-container{padding:1rem .8rem 2rem}}
@media(max-width:760px){.field-stage{flex-basis:210px;height:125px}.hero{align-items:flex-start}.profile-image{height:210px}}
@media(max-width:520px){.field-stage{flex-basis:100%;height:130px;max-width:300px;margin:0 auto}.hero{flex-direction:column}}
</style>
""", unsafe_allow_html=True)


# ------------------------- DATABASE -------------------------

@st.cache_data(show_spinner="Loading IPL delivery data…")
def load_data(db_path: str, modified_time: float) -> pd.DataFrame:
    del modified_time

    with sqlite3.connect(db_path) as conn:
        deliveries = pd.read_sql_query("""
            SELECT season_id, match_id, innings, over_number, batter, bowler,
                   batter_runs, extras, total_runs, is_wicket, wicket_kind,
                   is_wide_ball, is_no_ball, is_leg_bye, is_bye, is_penalty,
                   leg_bye_runs, bye_runs, penalty_runs, is_super_over,
                   batting_team, bowling_team, bowler_type, batsman_type
            FROM deliveries
            WHERE COALESCE(is_super_over, 0) = 0
        """, conn)

        matches = pd.read_sql_query(
            "SELECT match_id, season, venue FROM matches", conn
        )
        player_table = pd.read_sql_query(
            "SELECT player_name, bowl_style, bat_style FROM players", conn
        )

    if deliveries.empty:
        raise ValueError("No non-super-over delivery rows found.")

    matches = matches.drop_duplicates("match_id").set_index("match_id")
    player_table = player_table.drop_duplicates("player_name").set_index("player_name")

    deliveries["season"] = (
        deliveries["match_id"].map(matches["season"])
        .fillna(deliveries["season_id"].astype(str)).astype(str)
    )
    deliveries["venue"] = (
        deliveries["match_id"].map(matches["venue"]).fillna("Unknown").astype(str)
    )
    deliveries["bowler_style"] = (
        deliveries["bowler"].map(player_table["bowl_style"])
        .fillna(deliveries["bowler_type"]).fillna("Unknown").astype(str).str.strip()
    )
    deliveries["batter_hand"] = (
        deliveries["batter"].map(player_table["bat_style"])
        .fillna(deliveries["batsman_type"]).fillna("Unknown").astype(str).str.strip()
    )

    numeric_columns = [
        "season_id", "innings", "over_number", "batter_runs", "extras",
        "total_runs", "is_wicket", "is_wide_ball", "is_no_ball",
        "leg_bye_runs", "bye_runs", "penalty_runs", "is_super_over",
    ]
    for col in numeric_columns:
        deliveries[col] = pd.to_numeric(
            deliveries[col], errors="coerce"
        ).fillna(0)

    text_columns = [
        "season", "bowler", "batter", "wicket_kind", "bowler_style",
        "batter_hand", "venue", "batting_team", "bowling_team",
    ]
    for col in text_columns:
        deliveries[col] = (
            deliveries[col].fillna("Unknown").astype(str).str.strip()
            .replace("", "Unknown")
        )

    deliveries["legal_ball"] = (
        (deliveries["is_wide_ball"] == 0)
        & (deliveries["is_no_ball"] == 0)
    ).astype(int)

    deliveries["bowler_runs"] = (
        deliveries["total_runs"] - deliveries["leg_bye_runs"]
        - deliveries["bye_runs"] - deliveries["penalty_runs"]
    ).clip(lower=0)

    wicket_kind = deliveries["wicket_kind"].str.lower().str.strip()
    deliveries["credited_wicket"] = (
        (deliveries["is_wicket"] == 1) & wicket_kind.isin(CREDITED)
    ).astype(int)

    deliveries["dot_ball"] = (
        (deliveries["batter_runs"] == 0)
        & (deliveries["legal_ball"] == 1)
        & (deliveries["bowler_runs"] == 0)
    ).astype(int)

    style = deliveries["bowler_style"].str.lower()

    deliveries["style_group"] = np.select(
        [
            style.str.contains(
                r"spin|orthodox|legbreak|leg break|offbreak|off break|wrist|googly|chinaman",
                regex=True, na=False,
            ),
            style.str.contains(r"fast|medium|seam|pace", regex=True, na=False),
        ],
        ["Spin", "Pace"],
        default="Unclassified",
    )

    deliveries["arm_group"] = np.select(
        [
            style.str.contains(r"left arm|slow left", regex=True, na=False),
            style.str.contains(r"right arm", regex=True, na=False),
        ],
        ["Left-arm", "Right-arm"],
        default="Unknown",
    )

    hand = deliveries["batter_hand"].str.lower()
    deliveries["hand_group"] = np.select(
        [
            hand.str.contains("left hand", na=False),
            hand.str.contains("right hand", na=False),
        ],
        ["Left-handed", "Right-handed"],
        default="Unknown",
    )

    deliveries["phase"] = np.select(
        [
            deliveries["over_number"].between(0, 5),
            deliveries["over_number"].between(6, 14),
            deliveries["over_number"] >= 15,
        ],
        PHASES,
        default="Unknown",
    )
    return deliveries


# ------------------------- HELPERS --------------------------

def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "player"


def player_image(name: str):
    """Find a real player portrait first, then use the shared fallback."""

    configured = PLAYER_IMAGES.get(name)
    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = ROOT / configured_path
        if configured_path.is_file():
            return configured_path

    def normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    target = normalize(name)

    for folder in (IMAGE_DIR, PORTRAIT_DIR):
        if folder.is_dir():
            try:
                candidates = [
                    item for item in folder.iterdir()
                    if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
                ]
                for candidate in candidates:
                    if normalize(candidate.stem) == target:
                        return candidate
            except OSError:
                pass

    slug = slugify(name)
    for folder in (IMAGE_DIR, PORTRAIT_DIR):
        for extension in IMAGE_EXTENSIONS:
            candidate = folder / f"{slug}{extension}"
            if candidate.is_file():
                return candidate

    if DEFAULT_PLAYER_IMAGE.is_file():
        return DEFAULT_PLAYER_IMAGE

    return None


@st.cache_data(show_spinner=False)
def season_list(d: pd.DataFrame) -> list[str]:
    return (
        d[["season_id", "season"]].drop_duplicates()
        .sort_values("season_id", ascending=False)["season"]
        .astype(str).drop_duplicates().tolist()
    )


def economy(d: pd.DataFrame) -> float:
    balls = int(d["legal_ball"].sum()) if not d.empty else 0
    return float(d["bowler_runs"].sum() * 6 / balls) if balls else 0.0


def qualified(d: pd.DataFrame, minimum_balls: int) -> set[str]:
    if d.empty:
        return set()
    counts = d.groupby("bowler")["legal_ball"].sum()
    return set(counts[counts >= minimum_balls].index.astype(str))


def aggregate(
    d: pd.DataFrame, keys: list[str], min_balls: int = 1
) -> pd.DataFrame:
    expected = keys + ["Runs", "Balls", "Wickets", "Deliveries", "Economy"]
    if d.empty or any(key not in d.columns for key in keys):
        return pd.DataFrame(columns=expected)

    result = (
        d.groupby(keys, observed=True, dropna=False)
        .agg(
            Runs=("bowler_runs", "sum"),
            Balls=("legal_ball", "sum"),
            Wickets=("credited_wicket", "sum"),
            Deliveries=("match_id", "size"),
        )
        .reset_index()
    )

    result = result[result["Balls"] >= min_balls].copy()
    if result.empty:
        return pd.DataFrame(columns=expected)

    result["Economy"] = result["Runs"] * 6 / result["Balls"]
    return result


def safe_spells(d: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "match_id", "bowler", "phase", "style_group", "Runs", "Balls", "Economy"
    ]
    if d.empty or "style_group" not in d.columns:
        return pd.DataFrame(columns=columns)

    d = d[
        d["style_group"].isin(["Pace", "Spin"])
        & d["phase"].isin(PHASES)
    ].copy()
    if d.empty:
        return pd.DataFrame(columns=columns)

    spells = (
        d.groupby(
            ["match_id", "bowler", "phase", "style_group"], observed=True
        )
        .agg(Runs=("bowler_runs", "sum"), Balls=("legal_ball", "sum"))
        .reset_index()
    )
    spells = spells[spells["Balls"] >= 6].copy()
    if spells.empty:
        return pd.DataFrame(columns=columns)

    spells["Economy"] = spells["Runs"] * 6 / spells["Balls"]
    return spells[columns]


def spin_pace_test(d: pd.DataFrame):
    eligible = qualified(d, 500)
    if not eligible:
        return None

    spells = safe_spells(d[d["bowler"].isin(eligible)])
    if spells.empty:
        return None

    spin = spells.loc[spells["style_group"] == "Spin", "Economy"].to_numpy()
    pace = spells.loc[spells["style_group"] == "Pace", "Economy"].to_numpy()

    if len(spin) < 2 or len(pace) < 2:
        return None

    u_stat, p_value = mannwhitneyu(spin, pace, alternative="two-sided")
    difference = float(np.median(spin) - np.median(pace))

    direction = (
        "Spin spells had higher median economy" if difference > 0
        else "Spin spells had lower median economy" if difference < 0
        else "Median economies were equal"
    )
    significance = (
        "statistically distinguishable" if p_value < 0.05
        else "not statistically distinguishable"
    )

    return {
        "p": float(p_value),
        "delta": float(2 * u_stat / (len(spin) * len(pace)) - 1),
        "diff": difference,
        "n_spin": len(spin),
        "n_pace": len(pace),
        "text": f"{direction}; distributions were {significance} (p={p_value:.3g}).",
    }


def player_traits(d: pd.DataFrame, name: str) -> list[float]:
    stats = aggregate(d, ["bowler"], 1)
    if stats.empty or name not in set(stats["bowler"]):
        return [0, 0, 0, 0, 0]

    dots = (
        d.groupby("bowler")["dot_ball"].sum()
        .reindex(stats["bowler"]).fillna(0).to_numpy()
    )
    stats["Dot %"] = dots / stats["Balls"].replace(0, np.nan).to_numpy() * 100
    stats["Wickets/100"] = (
        stats["Wickets"] / stats["Balls"].replace(0, np.nan).to_numpy() * 100
    )
    stats = stats.set_index("bowler")

    def percentile(column: str, inverse: bool = False) -> float:
        ranks = stats[column].rank(pct=True, method="average")
        value = ranks.loc[name]
        return float((1 - value if inverse else value) * 100)

    powerplay = aggregate(d[d["phase"] == "Powerplay"], ["bowler"], 1).set_index("bowler")
    death = aggregate(d[d["phase"] == "Death"], ["bowler"], 1).set_index("bowler")

    pp_score = (
        float((1 - powerplay["Economy"].rank(pct=True).loc[name]) * 100)
        if name in powerplay.index else 50
    )
    death_score = (
        float((1 - death["Economy"].rank(pct=True).loc[name]) * 100)
        if name in death.index else 50
    )

    return [
        percentile("Economy", True),
        percentile("Wickets/100"),
        percentile("Dot %"),
        pp_score,
        death_score,
    ]


def style_chart(fig: go.Figure, height: int = 300, legend: bool = True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans,sans-serif", color="#DDE4EE", size=10),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
            font=dict(size=9, color="#AFBACB"),
        ),
        hoverlabel=dict(
            bgcolor="#2C2020", bordercolor=BLUE,
            font=dict(color="#F2F5FA"),
        ),
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        linecolor="rgba(220,230,248,.12)", tickfont=dict(color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID,
        zeroline=False, tickfont=dict(color=MUTED),
    )
    return fig


def blank_chart(message: str, height: int = 250):
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=.5, y=.5, xref="paper", yref="paper",
        showarrow=False, font=dict(color=MUTED, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_chart(fig, height, False)


def show_chart(
    fig: go.Figure, key: str, height: int = 300, legend: bool = True
):
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.plotly_chart(
        style_chart(fig, height, legend),
        width="stretch",
        key=key,
        config={"displayModeBar": False, "displaylogo": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)


def section(num: str, title: str, subtitle: str):
    st.markdown(
        f'<div class="section-head"><div>'
        f'<div class="section-title">{html.escape(title)}</div>'
        f'<div class="section-sub">{html.escape(subtitle)}</div></div>'
        f'<div class="section-tag">{html.escape(num)} / ANALYTICS</div></div>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, detail: str, color: str = "blue"):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value {color}">{value}</div>'
        f'<div class="kpi-detail">{html.escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def encoded_image(path_text: str, modified_time: float) -> tuple[str, str]:
    """Cache image encoding to prevent repeatedly reading the same portrait."""
    del modified_time
    path = Path(path_text)
    mime = mimetypes.guess_type(path.name)[0]
    if path.suffix.lower() == ".avif":
        mime = "image/avif"
    mime = mime or "image/jpeg"
    return mime, base64.b64encode(path.read_bytes()).decode("ascii")


def tile_image_html(name: str) -> str:
    path = player_image(name)

    if not path:
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        return (
            '<div class="tile-image" style="display:flex;align-items:center;'
            'justify-content:center;font:600 36px Space Grotesk,sans-serif;'
            f'color:#FFB9BF">{html.escape(initials)}</div>'
        )

    mime, encoded = encoded_image(str(path), path.stat().st_mtime)
    return (
        f'<img class="tile-image" src="data:{mime};base64,{encoded}" '
        f'alt="{html.escape(name)}">'
    )


def profile_image_html(name: str) -> str:
    return tile_image_html(name).replace(
        'class="tile-image"', 'class="profile-image"'
    )

    # ------------------------- LOAD DATABASE --------------------

if not DB_PATH.is_file():
    st.error(f"Database not found: {DB_PATH}. Keep ipl.db beside Dashboard.py.")
    st.stop()

try:
    data = load_data(str(DB_PATH), DB_PATH.stat().st_mtime)
except Exception as exc:
    st.error(f"Could not load IPL database: {exc}")
    st.info(
        "Expected deliveries, matches, and players tables from your IPL database."
    )
    st.stop()

seasons = season_list(data)
players = sorted(
    player for player in data["bowler"].unique()
    if player and player != "Unknown"
)
styles = sorted(
    style for style in data["bowler_style"].unique()
    if style and style != "Unknown"
)
style_options = ["All styles", "Spin", "Pace"] + [
    style for style in styles if style not in ("Spin", "Pace")
]
teams = (
    data.groupby("bowling_team").size()
    .sort_values(ascending=False).index.astype(str).tolist()
)

# ------------------------- NAVIGATION FIX -------------------

def open_bowler_profile(name: str) -> None:
    """Set the player state before Streamlit reruns the script."""
    st.session_state["selected_bowler"] = str(name)
    st.session_state["show_profile"] = True
    st.session_state["nav_page"] = "Players"


def close_bowler_profile() -> None:
    st.session_state["show_profile"] = False


def set_directory_page(page: int) -> None:
    st.session_state["directory_page"] = max(0, int(page))


def reset_directory_page() -> None:
    st.session_state["directory_page"] = 0


if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Players"
if "selected_bowler" not in st.session_state:
    st.session_state["selected_bowler"] = players[0] if players else "Unknown"
if "show_profile" not in st.session_state:
    st.session_state["show_profile"] = False
if "directory_page" not in st.session_state:
    st.session_state["directory_page"] = 0

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-name">◉ IPL 360</div>'
        '<div class="brand-sub">BOWLING PERFORMANCE INTELLIGENCE</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sidebar-heading">Navigation</div>',
        unsafe_allow_html=True,
    )
    current_page = st.radio(
        "Navigation",
        ["Players", "League overview"],
        key="nav_page",
        label_visibility="collapsed",
    )
    st.markdown(
        '<div class="sidebar-heading">Popular teams</div>',
        unsafe_allow_html=True,
    )
    team_colors = [BLUE, "#FF7984", GREEN, CYAN, "#E0B568"]
    for index, team in enumerate(teams[:7]):
        st.markdown(
            f'<div class="sidebar-team"><span>'
            f'<i class="sidebar-bullet" style="background:{team_colors[index % len(team_colors)]}"></i>'
            f'{html.escape(team)}</span><span>{index + 1:02}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="sidebar-heading">Database</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="padding:5px 8px;color:#A17F82;font-size:10px;line-height:1.7">'
        f'<b style="color:#c6d0e1">ipl.db</b><br>{len(data):,} deliveries'
        f'<br>{len(seasons)} seasons</div>',
        unsafe_allow_html=True,
    )

current_data = data.copy()
header_left, header_season = st.columns([2.2, 1.0])

with header_left:
    st.markdown(
        f'<div class="topline"><span>Home '
        f'<span style="color:#785255;padding:0 8px">›</span>'
        f'<strong>{html.escape(current_page)}</strong></span>'
        f'<span>LOCAL DATABASE · IPL BOWLING INTELLIGENCE</span></div>',
        unsafe_allow_html=True,
    )

with header_season:
    selected_season = st.selectbox(
        "Season", ["All seasons"] + seasons, key="global_season"
    )

if selected_season != "All seasons":
    current_data = current_data[
        current_data["season"] == selected_season
    ].copy()

# ------------------------- HERO -----------------------------

st.markdown(
    f'''<div class="hero">
    <div class="hero-atmosphere" aria-hidden="true">
      <span class="hero-beam b1"></span><span class="hero-beam b2"></span><span class="hero-beam b3"></span>
      <i class="hero-particle p1"></i><i class="hero-particle p2"></i><i class="hero-particle p3"></i>
      <i class="hero-particle p4"></i><i class="hero-particle p5"></i>
    </div>
    <div>
      <div class="hero-eyebrow">IPL 360 / PERFORMANCE LAB</div>
      <div class="hero-title">Read the game.<br><span>Own the innings.</span></div>
      <div class="hero-copy">Explore every bowler, compare their spells, and find where each delivery changes the match. Built around real IPL records.</div>
      <div class="hero-stats">
        <span class="hero-pill"><b>{len(seasons)}</b> SEASONS</span>
        <span class="hero-pill"><b>{data["bowler"].nunique():,}</b> BOWLERS</span>
        <span class="hero-pill"><b>{len(data):,}</b> DELIVERIES</span>
      </div>
    </div>
    <div class="field-stage" aria-label="Animated 3D cricket field map">
      <div class="field-aura"></div>
      <div class="field-coord">FIELD INTELLIGENCE / LIVE MODEL</div>
      <div class="field-map">
        <div class="field-zone power"></div><div class="field-zone death"></div>
        <div class="delivery-trail"></div>
        <span class="delivery d1"></span><span class="delivery d2"></span>
        <span class="delivery d3"></span><span class="delivery d4"></span>
        <svg class="field-lines" viewBox="0 0 320 180" preserveAspectRatio="none">
          <ellipse cx="160" cy="90" rx="145" ry="80" fill="none" stroke="rgba(255,174,181,.62)" stroke-width="1.3"/>
          <ellipse cx="160" cy="90" rx="105" ry="58" fill="none" stroke="rgba(255,125,136,.42)" stroke-width="1"/>
          <path d="M160 26 L160 154 M52 90 L268 90" stroke="rgba(255,154,162,.28)" stroke-width="1" stroke-dasharray="3 5"/>
          <rect x="143" y="67" width="34" height="46" rx="2" fill="rgba(204,220,180,.2)" stroke="rgba(212,237,255,.8)" stroke-width="1.3"/>
          <path d="M145 73 H175 M145 107 H175 M151 67 V113 M169 67 V113" stroke="rgba(225,239,255,.52)" stroke-width="1"/>
          <circle cx="160" cy="90" r="5" fill="rgba(255,114,126,.28)" stroke="#FF9DA5" stroke-width="1.4"/>
          <circle cx="160" cy="90" r="12" fill="none" stroke="rgba(255,115,127,.25)" stroke-width="1" stroke-dasharray="2 3"/>
        </svg>
      </div>
      <div class="field-label">FIELD ZONES · DELIVERY TRACKING<br>POWERPLAY / MIDDLE / DEATH</div>
    </div>
    </div>''',
    unsafe_allow_html=True,
)


# ============================================================
# PLAYERS PAGE
# ============================================================

if current_page == "Players":

    # ----- Individual player dashboard -----

    if st.session_state.get("show_profile", False):
        selected = str(st.session_state.get("selected_bowler", "Unknown"))

        st.button(
            "← All bowlers",
            key="back_to_players",
            on_click=close_bowler_profile,
        )

        profile_scope = current_data[
            current_data["bowler"] == selected
        ].copy()

        if profile_scope.empty and selected_season != "All seasons":
            st.info(
                f"{selected} has no delivery records in {selected_season}. "
                "Showing career totals instead."
            )
            profile_scope = data[data["bowler"] == selected].copy()

        if profile_scope.empty:
            st.warning("No records found for this player. Return to the directory.")
        else:
            image_html = profile_image_html(selected)

            style_values = (
                profile_scope["bowler_style"].replace("Unknown", np.nan).dropna()
            )
            style_name = (
                str(style_values.iloc[0])
                if not style_values.empty else "Bowling style unavailable"
            )
            team_name = (
                profile_scope["bowling_team"].value_counts().index[0]
                if not profile_scope.empty else "Team not recorded"
            )

            total_balls = int(profile_scope["legal_ball"].sum())
            total_wickets = int(profile_scope["credited_wicket"].sum())
            total_runs = int(profile_scope["bowler_runs"].sum())
            econ = economy(profile_scope)
            dot_count = int(profile_scope["dot_ball"].sum())
            dot_pct = dot_count / total_balls * 100 if total_balls else 0
            matches_played = int(profile_scope["match_id"].nunique())

            season_names = sorted(
                profile_scope["season"].astype(str).unique().tolist()
            )
            coverage = (
                f"{season_names[0]} — {season_names[-1]}"
                if season_names else "Unavailable"
            )

            c_profile, c_radar = st.columns([1.55, 1.0], gap="medium")

            with c_profile:
                st.markdown(
                    f'''<div class="profile-card">
                    <div style="display:grid;grid-template-columns:minmax(140px,.68fr) minmax(0,1.5fr);gap:16px;align-items:stretch">
                      <div>{image_html}
                        <div style="font:9px 'DM Mono',monospace;color:#EB9BA2;letter-spacing:.12em;margin-top:8px">PLAYER PROFILE</div>
                      </div>
                      <div>
                        <div class="profile-name">{html.escape(selected)}</div>
                        <div class="profile-sub">{html.escape(team_name)} · IPL Bowler</div>
                        <div class="chip">{html.escape(style_name.upper())}</div>
                        <div class="fact-label">SEASON SCOPE</div><div class="fact">{html.escape(selected_season)}</div>
                        <div class="fact-label">CAREER COVERAGE</div><div class="fact">{html.escape(coverage)}</div>
                        <div class="fact-label">BOWLING SNAPSHOT</div>
                        <div class="profile-stats">
                          <div class="profile-stat"><div class="profile-stat-label">Matches</div><div class="profile-stat-value">{matches_played:,}</div></div>
                          <div class="profile-stat"><div class="profile-stat-label">Wickets</div><div class="profile-stat-value">{total_wickets:,}</div></div>
                          <div class="profile-stat"><div class="profile-stat-label">Runs</div><div class="profile-stat-value">{total_runs:,}</div></div>
                          <div class="profile-stat"><div class="profile-stat-label">Economy</div><div class="profile-stat-value">{econ:.2f}</div></div>
                        </div>
                      </div>
                    </div>
                    </div>''',
                    unsafe_allow_html=True,
                )
                photo_path = player_image(selected)
                if photo_path:
                    st.caption(f"Image path: {photo_path}")

            with c_radar:
                st.markdown(
                    '<div class="section-title">Bowler traits</div>'
                    '<div class="section-sub">Relative performance index · cohort percentile</div>',
                    unsafe_allow_html=True,
                )
                values = player_traits(data, selected)
                labels = [
                    "Economy control", "Wicket rate", "Dot pressure",
                    "Powerplay", "Death overs",
                ]

                radar = go.Figure(
                    go.Scatterpolar(
                        r=values + [values[0]],
                        theta=labels + [labels[0]],
                        fill="toself",
                        fillcolor="rgba(255,79,94,.22)",
                        line=dict(color=BLUE, width=2),
                        marker=dict(color=CYAN, size=5),
                        hovertemplate="%{theta}<br>Index %{r:.0f}/100<extra></extra>",
                    )
                )
                radar.update_layout(
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(
                            visible=True, range=[0, 100],
                            tickvals=[25, 50, 75, 100],
                            tickfont=dict(size=7, color="#A88588"),
                            gridcolor=GRID, linecolor=GRID,
                        ),
                        angularaxis=dict(
                            tickfont=dict(size=8, color="#CDD6E5"),
                            gridcolor=GRID, linecolor=GRID,
                        ),
                    ),
                    showlegend=False,
                )
                show_chart(radar, "profile_radar", 285, False)

            metric_a, metric_b, metric_c, metric_d = st.columns(4, gap="small")
            with metric_a:

                kpi("Legal balls", f"{total_balls:,}", selected_season, "blue")
            with metric_b:
                kpi("Economy", f"{econ:.2f}", "Runs per six legal balls", "blue")
            with metric_c:
                kpi("Dot-ball share", f"{dot_pct:.1f}%", f"{dot_count:,} legal dot balls", "green")
            with metric_d:
                strike_rate = f"{total_balls / total_wickets:.1f}" if total_wickets else "—"
                kpi("Strike rate", strike_rate, "Legal balls per credited wicket", "blue")

            # Player chart 1: seasonal economy against league average
            left, right = st.columns([1.35, 1.0], gap="medium")

            with left:
                st.markdown(
                    '<div class="section-title">Bowling economy · year by year</div>'
                    '<div class="section-sub">Selected bowler against league economy</div>',
                    unsafe_allow_html=True,
                )
                rows = []
                ordered_seasons = season_list(data)

                for season_name in ordered_seasons:
                    season_data = data[data["season"] == season_name]
                    bowler_data = season_data[season_data["bowler"] == selected]

                    if int(bowler_data["legal_ball"].sum()):
                        rows.append({
                            "Season": season_name,
                            "Economy": economy(bowler_data),
                            "Series": selected,
                        })
                    if int(season_data["legal_ball"].sum()):
                        rows.append({
                            "Season": season_name,
                            "Economy": economy(season_data),
                            "Series": "League average",
                        })

                trend = pd.DataFrame(rows)
                if not trend.empty:
                    trend["Season"] = pd.Categorical(
                        trend["Season"], ordered_seasons, ordered=True
                    )
                    trend = trend.sort_values("Season")
                    fig = px.line(
                        trend, x="Season", y="Economy",
                        color="Series", markers=True,
                        color_discrete_map={
                            selected: BLUE, "League average": "#B7C0CF"
                        },
                    )
                    fig.update_traces(line_width=2.4, marker_size=6)
                    fig.update_layout(xaxis_title="", yaxis_title="Economy")
                    show_chart(fig, "profile_season_trend", 285)
                else:
                    st.plotly_chart(
                        blank_chart("No seasonal spells for this bowler."),
                        width="stretch", key="profile_season_empty",
                    )

            with right:
                st.markdown(
                    '<div class="section-title">Phase analysis</div>'
                    '<div class="section-sub">Economy and wickets by innings phase</div>',
                    unsafe_allow_html=True,
                )
                phase_stats = aggregate(
                    profile_scope[profile_scope["phase"].isin(PHASES)], ["phase"], 1
                )

                if not phase_stats.empty:
                    phase_stats["phase"] = pd.Categorical(
                        phase_stats["phase"], PHASES, ordered=True
                    )
                    phase_stats = phase_stats.sort_values("phase")

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=phase_stats["phase"],
                        y=phase_stats["Economy"],
                        name="Economy",
                        marker_color=BLUE,
                        customdata=phase_stats[["Balls", "Wickets"]],
                        hovertemplate=(
                            "%{x}<br>Economy %{y:.2f}<br>"
                            "Balls %{customdata[0]}<br>Wickets %{customdata[1]}<extra></extra>"
                        ),
                    ))
                    fig.add_trace(go.Scatter(
                        x=phase_stats["phase"],
                        y=phase_stats["Wickets"],
                        name="Wickets",
                        mode="lines+markers",
                        yaxis="y2",
                        line=dict(color=GREEN, width=2),
                        marker=dict(size=6),
                    ))
                    fig.update_layout(
                        xaxis_title="",
                        yaxis=dict(title="Economy"),
                        yaxis2=dict(
                            title="Wickets", overlaying="y", side="right",
                            showgrid=False, color=GREEN,
                        ),
                    )
                    show_chart(fig, "profile_phase", 285)
                else:
                    st.plotly_chart(
                        blank_chart("No phase data for this bowler."),
                        width="stretch", key="profile_phase_empty",
                    )

            # Player chart 3: opponents
            left, right = st.columns(2, gap="medium")

            with left:
                section("03", "Economy by opponent", "Compare the bowler against batting teams.")
                opponents = aggregate(
                    profile_scope[profile_scope["batting_team"] != "Unknown"],
                    ["batting_team"], 6,
                )
                if not opponents.empty:
                    opponents = opponents.sort_values("Economy").head(10)
                    fig = px.bar(
                        opponents, x="Economy", y="batting_team",
                        orientation="h", color="Economy",
                        color_continuous_scale=[
                            [0, BLUE], [.55, "#8D6266"], [1, "#463534"]
                        ],
                        custom_data=["Balls", "Wickets"],
                    )
                    fig.update_layout(
                        coloraxis_showscale=False, xaxis_title="Economy",
                        yaxis_title="", yaxis=dict(autorange="reversed"),
                    )
                    fig.update_traces(
                        marker_line_width=0,
                        hovertemplate=(
                            "%{y}<br>Economy %{x:.2f}<br>Balls %{customdata[0]}"
                            "<br>Wickets %{customdata[1]}<extra></extra>"
                        ),
                    )
                    show_chart(fig, "profile_opponents", max(270, len(opponents) * 25), False)
                else:
                    st.plotly_chart(
                        blank_chart("No opponent data."),
                        width="stretch", key="profile_opp_empty",
                    )

            with right:
                section("04", "Against batter handedness", "Compare economy versus left- and right-handed batters.")
                handed = profile_scope[
                    profile_scope["hand_group"].isin(["Left-handed", "Right-handed"])
                    & profile_scope["phase"].isin(PHASES)
                ]
                hand_stats = aggregate(handed, ["phase", "hand_group"], 1)

                if not hand_stats.empty:
                    hand_stats["phase"] = pd.Categorical(
                        hand_stats["phase"], PHASES, ordered=True
                    )
                    hand_stats = hand_stats.sort_values("phase")
                    fig = px.bar(
                        hand_stats, x="phase", y="Economy",
                        color="hand_group", barmode="group",
                        color_discrete_map={"Left-handed": BLUE, "Right-handed": PALE},
                        custom_data=["Balls", "Wickets"],
                        category_orders={"phase": PHASES},
                    )
                    fig.update_layout(xaxis_title="", yaxis_title="Economy")
                    fig.update_traces(
                        marker_line_width=0,
                        hovertemplate=(
                            "%{x}<br>%{fullData.name}<br>Economy %{y:.2f}"
                            "<br>Balls %{customdata[0]}<br>Wickets %{customdata[1]}<extra></extra>"
                        ),
                    )
                    show_chart(fig, "profile_handedness", 290)
                else:
                    st.plotly_chart(
                        blank_chart("Handedness metadata unavailable."),
                        width="stretch", key="profile_hand_empty",
                    )

            section("05", "Economy by ground", "Compare performance across venues; minimum six legal balls.")
            venues = aggregate(
                profile_scope[profile_scope["venue"] != "Unknown"], ["venue"], 6
            )

            if not venues.empty:
                venues = venues.sort_values("Economy").head(12)
                fig = px.bar(
                    venues, x="Economy", y="venue", orientation="h",
                    color="Economy",
                    color_continuous_scale=[
                        [0, BLUE], [.55, "#8D6266"], [1, "#463534"]
                    ],
                    custom_data=["Balls", "Wickets"],
                )
                fig.update_layout(
                    coloraxis_showscale=False, xaxis_title="Economy",
                    yaxis_title="", yaxis=dict(autorange="reversed"),
                )
                fig.update_traces(
                    marker_line_width=0,
                    hovertemplate=(
                        "%{y}<br>Economy %{x:.2f}<br>Balls %{customdata[0]}"
                        "<br>Wickets %{customdata[1]}<extra></extra>"
                    ),
                )
                show_chart(fig, "profile_venues", max(280, len(venues) * 25), False)
            else:
                st.plotly_chart(
                    blank_chart("Ground metadata unavailable."),
                    width="stretch", key="profile_venues_empty",
                )

    # ----- Bowler directory -----

    else:
        st.markdown(
            '<div class="section-head"><div>'
            '<div class="section-title">Choose your bowler</div>'
            '<div class="section-sub">Search all bowlers, then open a player for their profile, stats and five player-specific charts.</div>'
            '</div><div class="section-tag">PLAYERS / DIRECTORY</div></div>',
            unsafe_allow_html=True,
        )

        search = st.text_input(
            "Search bowlers",
            placeholder="Type a name…",
            key="player_gallery_search",
            on_change=reset_directory_page,
        )

        gallery_data = current_data
        if search.strip():
            gallery_data = gallery_data[
                gallery_data["bowler"].str.contains(
                    search.strip(), case=False, na=False
                )
            ]

        summary = (
            gallery_data.groupby("bowler", observed=True)
            .agg(
                Balls=("legal_ball", "sum"),
                Wickets=("credited_wicket", "sum"),
                Runs=("bowler_runs", "sum"),
                Matches=("match_id", "nunique"),
            )
            .reset_index()
        )
        summary = summary[summary["bowler"] != "Unknown"].copy()
        summary["Economy"] = np.where(
            summary["Balls"] > 0,
            summary["Runs"] * 6 / summary["Balls"],
            0,
        )
        summary = summary.sort_values(
            ["Wickets", "Balls"], ascending=False
        ).reset_index(drop=True)

        if summary.empty:
            st.info("No bowlers match that search/filter.")
        else:
            # FIX 1: render only 32 cards, rather than all 568 at once.
            page_size = 32
            total_players = len(summary)
            total_pages = max(
                1, (total_players + page_size - 1) // page_size
            )
            page = min(
                int(st.session_state.get("directory_page", 0)),
                total_pages - 1,
            )
            st.session_state["directory_page"] = page

            start = page * page_size
            end = min(start + page_size, total_players)
            visible_players = summary.iloc[start:end]

            previous_col, info_col, next_col = st.columns([1, 2, 1])

            with previous_col:
                st.button(
                    "← Previous",
                    key="directory_previous",
                    disabled=(page == 0),
                    on_click=set_directory_page,
                    args=(page - 1,),
                    width="stretch",
                )

            with info_col:
                st.markdown(
                    f"<div style='text-align:center;padding:8px;"
                    f"color:#aab8d4;font-size:12px'>"
                    f"Showing {start + 1}–{end} of {total_players} bowlers "
                    f"· Page {page + 1}/{total_pages}</div>",
                    unsafe_allow_html=True,
                )

            with next_col:
                st.button(
                    "Next →",
                    key="directory_next",
                    disabled=(page >= total_pages - 1),
                    on_click=set_directory_page,
                    args=(page + 1,),
                    width="stretch",
                )

            for batch_start in range(0, len(visible_players), 4):
                batch = visible_players.iloc[batch_start:batch_start + 4]
                columns = st.columns(4, gap="medium")

                for col, (_, row) in zip(columns, batch.iterrows()):
                    name = str(row["bowler"])


                    with col:
                        player_styles = (
                            gallery_data.loc[
                                gallery_data["bowler"] == name, "bowler_style"
                            ]
                            .replace("Unknown", np.nan)
                            .dropna()
                        )
                        style_name = (
                            str(player_styles.iloc[0])
                            if not player_styles.empty else "Style unavailable"
                        )

                        card_html = (
                            f'<div class="player-tile">{tile_image_html(name)}'
                            f'<div class="tile-name">{html.escape(name)}</div>'
                            f'<div class="tile-meta">{html.escape(style_name.upper())}</div>'
                            f'<div class="tile-stats">{int(row["Wickets"])} wickets · '
                            f'{int(row["Balls"]):,} balls<br>Economy '
                            f'{float(row["Economy"]):.2f} · '
                            f'{int(row["Matches"])} matches</div></div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

                        # FIX 2: hashed keys avoid collisions between player names.
                        button_id = hashlib.sha256(
                            name.encode("utf-8")
                        ).hexdigest()[:20]

                        # FIX 3: Streamlit handles reruns after this callback.
                        st.button(
                            "Open player dashboard ↗",
                            key=f"open_player_{button_id}",
                            width="stretch",
                            on_click=open_bowler_profile,
                            args=(name,),
                        )


# ============================================================
# LEAGUE OVERVIEW — FIVE CHARTS
# ============================================================

else:
    st.markdown(
        '<div class="section-head"><div>'
        '<div class="section-title">League overview</div>'
        '<div class="section-sub">Economy, wickets, seasons and bowling matchups from your SQLite database.</div>'
        '</div><div class="section-tag">LEAGUE / OVERVIEW</div></div>',
        unsafe_allow_html=True,
    )

    filter_a, filter_b = st.columns([1.4, 1])
    with filter_a:
        selected_style = st.selectbox(
            "Bowling style", style_options, key="overview_style"
        )
    with filter_b:
        minimum = st.select_slider(
            "Minimum legal balls per bowler",
            [0, 30, 60, 120, 300, 500],
            value=500,
            key="overview_minimum",
        )

    if selected_style == "All styles":
        scoped = current_data.copy()
    elif selected_style in ("Spin", "Pace"):
        scoped = current_data[
            current_data["style_group"] == selected_style
        ].copy()
    else:
        scoped = current_data[
            current_data["bowler_style"] == selected_style
        ].copy()

    eligible = qualified(scoped, minimum) if minimum else set(scoped["bowler"].unique())
    chart_data = scoped[scoped["bowler"].isin(eligible)].copy()
    qualified_500 = qualified(scoped, 500)
    test = spin_pace_test(current_data)

    kpi_a, kpi_b, kpi_c = st.columns(3, gap="small")

    with kpi_a:
        kpi(
            "Bowlers / qualified ≥ 500 balls",
            f'{scoped["bowler"].nunique():,} / {len(qualified_500):,}',
            f"{selected_season} · {selected_style}",
            "blue",
        )
    with kpi_b:
        kpi(
            "Credited wickets",
            f'{int(data["credited_wicket"].sum()):,}',
            "League total before filters",
            "green",
        )
    with kpi_c:
        kpi(
            "Spin vs pace",
            (
                "Spin higher" if test["diff"] > 0
                else "Spin lower" if test["diff"] < 0
                else "Same median"
            ) if test else "Small sample",
            (
                f'Median Δ {test["diff"]:+.2f} · p={test["p"]:.3g}'
                if test else "Need enough qualifying spells"
            ),
            "blue",
        )

    # League chart 1: economy by phase
    section(
        "01", "Economy by innings phase",
        "Spin vs pace · dashed line indicates overall league economy.",
    )
    phase_data = chart_data[
        chart_data["style_group"].isin(["Spin", "Pace"])
        & chart_data["phase"].isin(PHASES)
    ]
    phase_stats = aggregate(phase_data, ["phase", "style_group"], 1)

    if not phase_stats.empty:
        phase_stats["phase"] = pd.Categorical(
            phase_stats["phase"], PHASES, ordered=True
        )
        phase_stats = phase_stats.sort_values("phase")
        fig = px.bar(
            phase_stats, x="phase", y="Economy", color="style_group",
            barmode="group",
            color_discrete_map={"Spin": BLUE, "Pace": PALE},
            custom_data=["Balls", "Wickets"],
            category_orders={"phase": PHASES},
        )
        fig.update_traces(
            marker_line_width=0,
            hovertemplate=(
                "%{x}<br>%{fullData.name}<br>Economy %{y:.2f}"
                "<br>Balls %{customdata[0]}<br>Wickets %{customdata[1]}<extra></extra>"
            ),
        )
        league_economy = economy(current_data)
        fig.add_hline(
            y=league_economy, line_dash="dash", line_color="#D5DCE7",
            annotation_text=f"League {league_economy:.2f}",
            annotation_font_color="#D5DCE7", annotation_font_size=9,
        )
        fig.update_layout(xaxis_title="", yaxis_title="Runs / 6 legal balls")
        show_chart(fig, "league_phase_economy", 325)
    else:
        st.plotly_chart(
            blank_chart("No pace/spin sample. Change style or lower the ball threshold."),
            width="stretch", key="league_phase_empty",
        )

    left, right = st.columns(2, gap="medium")

    # League chart 2: bowling styles ranked by economy
    with left:
        section(
            "02", "Bowling styles ranked by economy",
            "Qualified bowlers · lowest economy first.",
        )
        style_stats = aggregate(
            scoped[scoped["bowler"].isin(qualified_500)], ["bowler_style"], 1
        )
        if not style_stats.empty:
            style_stats = (
                style_stats[style_stats["bowler_style"] != "Unknown"]
                .sort_values("Economy").head(12)
            )
            fig = px.bar(
                style_stats, x="Economy", y="bowler_style", orientation="h",
                color="Economy",
                color_continuous_scale=[
                    [0, BLUE], [.55, "#B77177"], [1, "#4D3A39"]
                ],
                custom_data=["Balls", "Wickets"],
            )
            fig.update_traces(
                marker_line_width=0,
                hovertemplate=(
                    "%{y}<br>Economy %{x:.2f}<br>Balls %{customdata[0]}"
                    "<br>Wickets %{customdata[1]}<extra></extra>"
                ),
            )
            fig.update_layout(
                coloraxis_showscale=False, xaxis_title="Economy",
                yaxis_title="", yaxis=dict(autorange="reversed"),
            )
            show_chart(fig, "league_style_rank", max(270, len(style_stats) * 25), False)
        else:
            st.plotly_chart(
                blank_chart("No styles qualify for 500 legal balls."),
                width="stretch", key="league_style_empty",
            )

    # League chart 3: wickets by phase
    with right:
        section(
            "03", "Wickets by innings phase",
            "Where do 500-ball-qualified bowlers take wickets?",
        )
        qualified_phase = scoped[
            scoped["bowler"].isin(qualified_500)
            & scoped["phase"].isin(PHASES)
        ]
        phase_wickets = (
            qualified_phase.groupby("phase", observed=True)
            .agg(
                Wickets=("credited_wicket", "sum"),
                Balls=("legal_ball", "sum"),
            )
            .reindex(PHASES).fillna(0).reset_index()
        )
        phase_wickets["phase"] = PHASES
        fig = px.bar(
            phase_wickets, x="phase", y="Wickets", color="phase",
            color_discrete_map={
                "Powerplay": BLUE, "Middle": "#C58288", "Death": "#F3F3F5"
            },
            custom_data=["Balls"], category_orders={"phase": PHASES},
        )
        fig.update_traces(
            marker_line_width=0,
            hovertemplate="%{x}<br>Wickets %{y:.0f}<br>Balls %{customdata[0]:.0f}<extra></extra>",
        )
        fig.update_layout(
            showlegend=False, xaxis_title="", yaxis_title="Credited wickets"
        )
        show_chart(fig, "league_phase_wickets", 300, False)

    left, right = st.columns(2, gap="medium")

    # League chart 4: economy by season
    with left:
        section(
            "04", "Economy by season",
            "All bowlers vs bowlers with at least 500 legal balls in that season.",
        )
        season_rows = []

        for season_name in seasons:
            part = current_data[current_data["season"] == season_name].copy()

            if selected_style == "Spin" or selected_style == "Pace":
                part = part[part["style_group"] == selected_style].copy()
            elif selected_style != "All styles":
                part = part[part["bowler_style"] == selected_style].copy()

            if int(part["legal_ball"].sum()):
                season_rows.append({
                    "Season": season_name,
                    "Economy": economy(part),
                    "Series": "All bowlers",
                })

            qualified_part = part[
                part["bowler"].isin(qualified(part, 500))
            ]
            if int(qualified_part["legal_ball"].sum()):
                season_rows.append({
                    "Season": season_name,
                    "Economy": economy(qualified_part),
                    "Series": "Qualified 500+",
                })

        season_trend = pd.DataFrame(season_rows)

        if not season_trend.empty:
            order = season_list(data)
            season_trend["Season"] = pd.Categorical(
                season_trend["Season"], order, ordered=True
            )
            season_trend = season_trend.sort_values("Season")
            fig = px.line(
                season_trend, x="Season", y="Economy", color="Series",
                line_dash="Series", markers=True,
                color_discrete_map={
                    "All bowlers": BLUE, "Qualified 500+": "#F3F3F5"
                },
                line_dash_map={
                    "All bowlers": "solid", "Qualified 500+": "dot"
                },
            )
            fig.update_traces(line_width=2.2, marker_size=5)
            fig.update_layout(xaxis_title="", yaxis_title="Economy")
            show_chart(fig, "league_season_trend", 300)
        else:
            st.plotly_chart(
                blank_chart("No seasonal data."),
                width="stretch", key="league_season_empty",
            )

    # League chart 5: left-arm vs right-arm
    with right:
        section("05", "Left-arm vs right-arm", "Compare economy by phase.")
        arms = chart_data[
            chart_data["arm_group"].isin(["Left-arm", "Right-arm"])
            & chart_data["phase"].isin(PHASES)
        ]
        arm_stats = aggregate(arms, ["phase", "arm_group"], 1)

        if not arm_stats.empty:
            arm_stats["phase"] = pd.Categorical(
                arm_stats["phase"], PHASES, ordered=True
            )
            arm_stats = arm_stats.sort_values("phase")
            fig = px.bar(
                arm_stats, x="phase", y="Economy", color="arm_group",
                barmode="group",
                color_discrete_map={"Left-arm": BLUE, "Right-arm": PALE},
                custom_data=["Balls", "Wickets"],
                category_orders={"phase": PHASES},
            )
            fig.update_traces(
                marker_line_width=0,
                hovertemplate=(
                    "%{x}<br>%{fullData.name}<br>Economy %{y:.2f}"
                    "<br>Balls %{customdata[0]}<br>Wickets %{customdata[1]}<extra></extra>"
                ),
            )
            fig.update_layout(xaxis_title="", yaxis_title="Economy")
            show_chart(fig, "league_arm_compare", 300)
        else:
            st.plotly_chart(
                blank_chart("No arm metadata in this filtered sample."),
                width="stretch", key="league_arm_empty",
            )

    if test:
        st.markdown(
            f'<div class="insight"><strong>SPIN VS PACE</strong> &nbsp; '
            f'{html.escape(test["text"])}<br>'
            f'<span style="color:#AD898C;font:9px DM Mono,monospace">'
            f'Cliff’s δ {test["delta"]:+.3f} · spin n={test["n_spin"]:,} · '
            f'pace n={test["n_pace"]:,}. Exploratory comparison, not causal evidence.'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    st.caption(
        "Economy = bowler-charged runs × 6 / legal balls. Credited wickets exclude "
        "run-outs, retired hurt/out and obstructing the field. Powerplay = overs 0–5, "
        "middle = 6–14, death = 15+. Super overs excluded."
    )

st.divider()
st.markdown(
    f'<div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;'
    f'color:#916F72;font:9px DM Mono,monospace;letter-spacing:.09em">'
    f'<span>IPL 360 · BOWLING INTELLIGENCE</span>'
    f'<span>{len(data):,} DELIVERIES · LOCAL SQLITE</span></div>',
    unsafe_allow_html=True,
)


# app.py
import math
import pandas as pd
import streamlit as st
from pathlib import Path
import base64
from datetime import datetime

# ==========================================================
# Rental Affordability Checker (DWIBAHASA UI)
# + Google Sheets logging (OWNER ONLY access via Service Account)
# ----------------------------------------------------------
# Condition A (Logistic model):
#   z = SUM(COEF * INPUT)
#   p = 1 / (1 + exp(-z))
#   Pass if p >= P_THRESHOLD
#
# Condition B (Rent-to-Income rule):
#   Pass if Rent <= ratio * Income
#
# Overall:
#   Pass only if BOTH conditions pass
# ==========================================================

APP_DIR = Path(__file__).resolve().parent

# ====== Condition A threshold (as requested) ======
P_THRESHOLD = 0.05  # pass if p >= 0.05

# Optional (Google Sheets). If not installed/configured, app still runs.
try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


# ===================== SECURITY NOTE =====================
# IMPORTANT: DO NOT put your service account JSON / private_key in this file or GitHub.
# Put it in Streamlit Secrets only (local: .streamlit/secrets.toml, cloud: App -> Settings -> Secrets).
# If you already pasted a private key anywhere public, revoke/rotate the key in Google Cloud immediately.
# =========================================================


# -------------------- LOGO HELPERS --------------------
def img_to_base64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def logo_strip_html(paths, height_px=42, gap_px=10):
    imgs = []
    for p in paths:
        if not p.exists():
            continue
        b64 = img_to_base64(p)
        ext = p.suffix.lower().replace(".", "")
        mime = "png" if ext in ("png",) else "jpeg"
        imgs.append(
            f'<img class="logo-img" src="data:image/{mime};base64,{b64}" '
            f'style="height:{height_px}px; width:auto; object-fit:contain;" />'
        )
    return f"""
    <div class="logo-wrap">
      <div class="logo-strip" style="gap:{gap_px}px;">
        {''.join(imgs)}
      </div>
    </div>
    """


# -------------------- MODEL MATH --------------------
def logistic(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _arc_path(cx, cy, r, a0_deg, a1_deg):
    a0 = math.radians(a0_deg)
    a1 = math.radians(a1_deg)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    large = 1 if abs(a1_deg - a0_deg) > 180 else 0
    sweep = 1
    return f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {large} {sweep} {x1:.2f} {y1:.2f}"


def svg_gauge_html(
    title: str,
    value_0_1: float,
    threshold_0_1: float,
    subtitle_left: str,
    subtitle_right: str,
    text_color: str,
    border_color: str,
) -> str:
    v = clamp(value_0_1, 0.0, 1.0)
    t = clamp(threshold_0_1, 0.0, 1.0)

    W, H = 300, 190
    cx, cy = W / 2, 150
    r = 95

    def p_to_deg(p):
        return -180 + (p * 180.0)

    segs = [
        (0.00, 0.10, "rgba(239,68,68,0.85)"),
        (0.10, 0.40, "rgba(245,158,11,0.85)"),
        (0.40, 1.00, "rgba(34,197,94,0.85)"),
    ]

    td = p_to_deg(t)
    tx1 = cx + (r - 2) * math.cos(math.radians(td))
    ty1 = cy + (r - 2) * math.sin(math.radians(td))
    tx2 = cx + (r - 24) * math.cos(math.radians(td))
    ty2 = cy + (r - 24) * math.sin(math.radians(td))

    nd = p_to_deg(v)
    nx = cx + (r - 10) * math.cos(math.radians(nd))
    ny = cy + (r - 10) * math.sin(math.radians(nd))

    paths = []
    for a0, a1, col in segs:
        paths.append(
            f'<path d="{_arc_path(cx, cy, r, p_to_deg(a0), p_to_deg(a1))}" '
            f'stroke="{col}" stroke-width="16" fill="none" stroke-linecap="round" />'
        )

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0;
    padding: 0;
    background: transparent;
    color: {text_color};
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    overflow: hidden;
  }}
  .gauge-card {{
    border: 1px solid {border_color};
    background: rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 12px 12px 14px 12px;
    box-sizing: border-box;
  }}
  .gauge-title {{
    font-weight: 800;
    margin-bottom: 6px;
    opacity: .95;
    color: {text_color};
  }}
  .gauge-value {{
    font-weight: 900;
    font-size: 20px;
    margin-top: -4px;
    color: {text_color};
  }}
  .gauge-sub {{
    display:flex;
    justify-content: space-between;
    font-size: 12px;
    opacity: .82;
    margin-top: 2px;
    color: {text_color};
  }}
</style>
</head>
<body>
  <div class="gauge-card">
    <div class="gauge-title">{title}</div>

    <div style="display:flex; justify-content:center;">
      <svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">
        {''.join(paths)}
        <line x1="{tx1:.2f}" y1="{ty1:.2f}" x2="{tx2:.2f}" y2="{ty2:.2f}"
              stroke="rgba(255,255,255,0.85)" stroke-width="3" stroke-linecap="round" />
        <line x1="{cx:.2f}" y1="{cy:.2f}" x2="{nx:.2f}" y2="{ny:.2f}"
              stroke="rgba(17,24,39,0.95)" stroke-width="4" stroke-linecap="round" />
        <circle cx="{cx:.2f}" cy="{cy:.2f}" r="7"
                fill="rgba(17,24,39,0.95)" stroke="rgba(255,255,255,0.35)" stroke-width="2" />
      </svg>
    </div>

    <div class="gauge-value">{(v*100):.2f}%</div>
    <div class="gauge-sub">
      <span>{subtitle_left}</span>
      <span>{subtitle_right}</span>
    </div>
  </div>
</body>
</html>
"""


# ===================== COEFFICIENTS (SIGNIFICANT ONLY: GREEN) =====================
# Based on your SPSS "Variables in the Equation" (green Sig. values).
# Keep Constant for the logistic equation.
COEF = {
    "Tahap Pendidikan=Undergraduate(1)": -0.537,
    "Pekerjaan=Pekerja Kerajaan(1)": 0.803,
    "Pekerjaan=Pekerja Swasta(1)": 0.912,
    "Jenis Penyewaan=Bilik(1)": 1.121,
    "Jenis rumah sewa=Kondominium(1)": -1.007,
    "Jenis rumah sewa=Pangsapuri(1)": -0.604,
    "Jenis rumah sewa=Rumah 1 unit(1)": -0.711,
    "Jenis rumah sewa=Rumah Teres(1)": 0.526,
    "Jenis kelengkapan perabot=Berperabot separa(1)": -0.370,
    "deposit_2_1(1)": 0.556,
    "Berapa lama anda telah menyewa rumah=3-5 tahun(1)": 0.413,
    "Berapa lama anda telah menyewa rumah=6+ tahun(1)": -0.584,
    "Constant": 0.310,
}


# ===================== OPTIONS (FOLLOW YOUR “LIST OF VARIABLES & CATEGORIES” PIC) =====================
# (Internal values remain the same; we only display bilingual label.)
OPTIONS = {
    "Jantina": ["Lelaki", "Perempuan"],
    "Warganegara": ["Malaysian", "Non-Malaysian"],
    "Bangsa": ["Bumiputera", "Cina", "India", "Lain-lain"],
    "Agama": ["Islam", "Buddha", "Hindu", "Lain-lain"],
    "Status Perkahwinan": ["Single", "Bercerai", "Berkahwin"],
    "Tahap Pendidikan": ["SPM dan ke bawah", "Undergraduate", "Postgraduate"],
    "Pekerjaan": ["Tidak bekerja", "Bekerja sendiri", "Lain-lain", "Pekerja Kerajaan", "Pekerja Swasta", "Pesara"],
    "Bilangan Isi Rumah": ["Kurang dari 2 orang", "3 - 4 orang", "Lebih 5 orang"],
    "Bilangan Tanggungan": ["Kurang dari 2 orang", "3 - 4 orang", "Lebih 5 orang"],
    "Jenis Penyewaan": ["Rumah", "Bilik"],
    "Jenis Rumah Sewa": ["Flat", "Condominium", "Lain-lain", "Pangsapuri", "Rumah 1 unit", "Rumah Teres"],
    "Jenis Kelengkapan Perabot": ["Tiada perabot", "Perabot penuh", "Perabot separa"],
    "Deposit": ["Tiada deposit", "1 + 1", "2 + 1", "3 + 1"],
    "Tempoh Menyewa": ["Kurang 2 tahun", "3 - 5 tahun", "Lebih 6 tahun"],
    "Skim": ["Ya", "Tidak"],
}

# --- Display (bilingual) for dropdown options (English first) ---
DISPLAY = {
    "Jantina": {"Lelaki": "Male (Lelaki)", "Perempuan": "Female (Perempuan)"},
    "Warganegara": {
        "Malaysian": "Malaysian (Warganegara Malaysia)",
        "Non-Malaysian": "Non-Malaysian (Bukan warganegara)",
    },
    "Bangsa": {
        "Bumiputera": "Bumiputera (Bumiputera)",
        "Cina": "Chinese (Cina)",
        "India": "Indian (India)",
        "Lain-lain": "Other (Lain-lain)",
    },
    "Agama": {
        "Islam": "Islam (Islam)",
        "Buddha": "Buddhism (Buddha)",
        "Hindu": "Hinduism (Hindu)",
        "Lain-lain": "Other (Lain-lain)",
    },
    "Status Perkahwinan": {
        "Single": "Single (Bujang)",
        "Bercerai": "Divorced (Bercerai)",
        "Berkahwin": "Married (Berkahwin)",
    },
    "Tahap Pendidikan": {
        "SPM dan ke bawah": "SPM & below (SPM dan ke bawah)",
        "Undergraduate": "Undergraduate (Ijazah Sarjana Muda)",
        "Postgraduate": "Postgraduate (Pascasiswazah)",
    },
    "Pekerjaan": {
        "Tidak bekerja": "Unemployed (Tidak bekerja)",
        "Bekerja sendiri": "Self-employed (Bekerja sendiri)",
        "Lain-lain": "Other (Lain-lain)",
        "Pekerja Kerajaan": "Government employee (Pekerja Kerajaan)",
        "Pekerja Swasta": "Private employee (Pekerja Swasta)",
        "Pesara": "Retired (Pesara)",
    },
    "Bilangan Isi Rumah": {
        "Kurang dari 2 orang": "1–2 people (Kurang dari 2 orang)",
        "3 - 4 orang": "3–4 people (3–4 orang)",
        "Lebih 5 orang": "5+ people (Lebih 5 orang)",
    },
    "Bilangan Tanggungan": {
        "Kurang dari 2 orang": "Less than 2 (Kurang dari 2)",
        "3 - 4 orang": "3–4 (3–4 orang)",
        "Lebih 5 orang": "More than 5 (Lebih 5)",
    },
    "Jenis Penyewaan": {"Rumah": "Whole unit/house (Rumah)", "Bilik": "Room (Bilik)"},
    "Jenis Rumah Sewa": {
        "Flat": "Flat (Flat)",
        "Condominium": "Condominium (Kondominium)",
        "Pangsapuri": "Apartment (Pangsapuri)",
        "Rumah Teres": "Terrace house (Rumah Teres)",
        "Rumah 1 unit": "Detached / single unit (Rumah 1 unit)",
        "Lain-lain": "Other (Lain-lain)",
    },
    "Jenis Kelengkapan Perabot": {
        "Tiada perabot": "Unfurnished (Tiada perabot)",
        "Perabot penuh": "Fully furnished (Perabot penuh)",
        "Perabot separa": "Partly furnished (Perabot separa)",
    },
    "Deposit": {
        "Tiada deposit": "No deposit (Tiada deposit)",
        "1 + 1": "1+1 deposit (1+1)",
        "2 + 1": "2+1 deposit (2+1)",
        "3 + 1": "3+1 deposit (3+1)",
    },
    "Tempoh Menyewa": {
        "Kurang 2 tahun": "Less than 2 years (Kurang 2 tahun)",
        "3 - 5 tahun": "3–5 years (3–5 tahun)",
        "Lebih 6 tahun": "More than 6 years (Lebih 6 tahun)",
    },
    "Skim": {"Ya": "Yes (Ya)", "Tidak": "No (Tidak)"},
}


# -------------------- BILINGUAL LABEL + HELP --------------------
def label_html(en: str, ms: str) -> str:
    return f"""
<div class="lbl">
  <div class="en">{en}</div>
  <div class="ms">{ms}</div>
</div>
""".strip()


def help_text(en: str, ms: str) -> str:
    return f"EN: {en}\nBM: {ms}"


def fmt(field: str):
    m = DISPLAY.get(field, {})
    return lambda x: m.get(x, str(x))


# -------------------- MODEL INPUTS (SIGNIFICANT ONLY) --------------------
def build_inputs(
    edu_label: str,
    job_label: str,
    jenis_penyewaan_label: str,
    jenis_rumah_sewa_label: str,
    perabot_label: str,
    deposit_label: str,
    tempoh_label: str,
) -> dict:
    # Only significant variables + constant
    inp = {k: 0.0 for k in COEF.keys()}
    inp["Constant"] = 1.0

    # Education
    if edu_label == "Undergraduate":
        inp["Tahap Pendidikan=Undergraduate(1)"] = 1.0

    # Occupation (only significant ones)
    if job_label == "Pekerja Kerajaan":
        inp["Pekerjaan=Pekerja Kerajaan(1)"] = 1.0
    elif job_label == "Pekerja Swasta":
        inp["Pekerjaan=Pekerja Swasta(1)"] = 1.0

    # Type of rental (Rumah/Bilik)
    if jenis_penyewaan_label == "Bilik":
        inp["Jenis Penyewaan=Bilik(1)"] = 1.0

    # House type (only significant ones)
    if jenis_rumah_sewa_label == "Condominium":
        inp["Jenis rumah sewa=Kondominium(1)"] = 1.0
    elif jenis_rumah_sewa_label == "Pangsapuri":
        inp["Jenis rumah sewa=Pangsapuri(1)"] = 1.0
    elif jenis_rumah_sewa_label == "Rumah 1 unit":
        inp["Jenis rumah sewa=Rumah 1 unit(1)"] = 1.0
    elif jenis_rumah_sewa_label == "Rumah Teres":
        inp["Jenis rumah sewa=Rumah Teres(1)"] = 1.0

    # Furnish type (only separa significant)
    if perabot_label == "Perabot separa":
        inp["Jenis kelengkapan perabot=Berperabot separa(1)"] = 1.0

    # Deposit (only 2+1 significant)
    if deposit_label == "2 + 1":
        inp["deposit_2_1(1)"] = 1.0

    # Renting duration (only 3-5 and 6+ significant)
    if tempoh_label == "3 - 5 tahun":
        inp["Berapa lama anda telah menyewa rumah=3-5 tahun(1)"] = 1.0
    elif tempoh_label == "Lebih 6 tahun":
        inp["Berapa lama anda telah menyewa rumah=6+ tahun(1)"] = 1.0

    return inp


def compute_table(inputs: dict):
    rows = []
    for var, coef in COEF.items():
        x = float(inputs.get(var, 0.0))
        rows.append({"Variable": var, "COEF": float(coef), "INPUT": x, "COEF×INPUT": float(coef) * x})
    df = pd.DataFrame(rows)
    z = float(df["COEF×INPUT"].sum())
    p = float(logistic(z))
    return df, z, p


# ===================== GOOGLE SHEETS (APPEND ROW) =====================
SHEET_ID_DEFAULT = "1sv9VlXO07K-wcmNCRVO5fvZcrzGcI4gncxfFVR73wxc"  # your sheet id

SHEET_COLS = [
    "timestamp",
    "jantina",
    "warganegara",
    "bangsa",
    "agama",
    "status_perkahwinan",
    "tahap_pendidikan",
    "pekerjaan",
    "bil_isi_rumah",
    "bil_tanggungan",
    "jenis_penyewaan",
    "jenis_rumah_sewa",
    "jenis_perabot",
    "deposit",
    "tempoh_menyewa",
    "skim",
    "income_rm",
    "rent_rm",
    "ratio_threshold",
    "z",
    "p",
    "condition_a_ok",
    "condition_b_ok",
    "overall_ok",
]


def sheets_status():
    """
    Returns (ok: bool, msg: str)
    """
    if gspread is None or Credentials is None:
        return False, "Missing libraries. Install: pip install gspread google-auth"

    try:
        _ = st.secrets["gcp_service_account"]
    except Exception:
        return False, "Missing Streamlit secret: [gcp_service_account]."

    return True, "Google Sheets is ready."


def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    client = gspread.authorize(creds)

    sheet_id = st.secrets.get("SHEET_ID", SHEET_ID_DEFAULT)
    tab_name = st.secrets.get("SHEET_TAB", "Sheet1")
    return client.open_by_key(sheet_id).worksheet(tab_name)


def ensure_header(ws):
    try:
        first_row = ws.row_values(1)
        if first_row != SHEET_COLS:
            if not first_row:
                ws.insert_row(SHEET_COLS, 1)
            else:
                ws.insert_row(SHEET_COLS, 1)
    except Exception:
        pass


def append_to_sheet(payload: dict) -> None:
    ws = get_sheet()
    ensure_header(ws)
    row = [payload.get(c, "") for c in SHEET_COLS]
    ws.append_row(row, value_input_option="USER_ENTERED")


# ===================== STREAMLIT CONFIG =====================
st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# ======================== TOP BAR ========================
logo_paths = [
    APP_DIR / "logo_kpkt.png",
    APP_DIR / "logo_kementerian_ekonomi.jpg",
    APP_DIR / "logo_uitm.png",
    APP_DIR / "logo_ukm.png",
]

top_l, top_r = st.columns([0.68, 0.32], vertical_alignment="center")

with top_l:
    st.markdown("## Rental Affordability Checker")
    st.caption(
        "Two checks are applied: Condition A (Logistic model) and Condition B (Rent ≤ ratio×Income). "
        "Overall = Afford only if both are satisfied."
    )

with top_r:
    st.markdown(logo_strip_html(logo_paths, height_px=40, gap_px=10), unsafe_allow_html=True)
    dark_mode = st.toggle("Dark mode", value=True)

# ======================== THEME ========================
if dark_mode:
    PAGE_BG = "linear-gradient(180deg, #0b0b14 0%, #0b0b14 45%, #1a102b 100%)"
    CARD_BG = "rgba(17, 24, 39, 0.68)"
    BORDER = "rgba(167, 139, 250, 0.22)"
    TXT = "#f8fafc"

    INPUT_BG = "rgba(17, 24, 39, 0.92)"
    INPUT_BORDER = "rgba(167, 139, 250, 0.22)"
    INPUT_TEXT = "#f8fafc"

    MENU_BG = "#ffffff"
    MENU_TEXT = "#111827"
    MENU_HOVER = "rgba(139, 92, 246, 0.10)"
else:
    PAGE_BG = "linear-gradient(180deg, #f7f2ff 0%, #f7f2ff 45%, #efe6ff 100%)"
    CARD_BG = "rgba(255,255,255,0.84)"
    BORDER = "rgba(139, 92, 246, 0.20)"
    TXT = "#111827"

    INPUT_BG = "rgba(255,255,255,0.98)"
    INPUT_BORDER = "rgba(139, 92, 246, 0.22)"
    INPUT_TEXT = "#111827"

    MENU_BG = "#ffffff"
    MENU_TEXT = "#111827"
    MENU_HOVER = "rgba(139, 92, 246, 0.12)"

st.markdown(
    f"""
<style>
  header[data-testid="stHeader"] {{ display: none !important; }}
  div[data-testid="stToolbar"] {{ display: none !important; }}
  #MainMenu {{ visibility: hidden; }}
  footer {{ visibility: hidden; }}

  .stApp {{
    background: {PAGE_BG} !important;
    color: {TXT} !important;
  }}
  .block-container {{
    padding-top: .75rem;
    max-width: 100% !important;
  }}

  .purple-card {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 16px 16px;
    box-shadow: 0 12px 30px rgba(76, 29, 149, 0.10);
  }}

  h1,h2,h3,h4,h5,h6, p, div, span, label, small {{
    color: {TXT} !important;
  }}

  /* Bilingual label */
  .lbl {{
    margin: 0 0 .25rem 0;
    line-height: 1.1;
  }}
  .lbl .en {{
    font-weight: 800;
    font-size: 14px;
    color: {TXT};
  }}
  .lbl .ms {{
    font-size: 12px;
    opacity: .80;
    color: {TXT};
  }}

  /* ========= INPUTS ========= */
  .stNumberInput input, .stTextInput input, .stTextArea textarea {{
    background: {INPUT_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
    color: {INPUT_TEXT} !important;
    -webkit-text-fill-color: {INPUT_TEXT} !important;
    caret-color: {INPUT_TEXT} !important;
    border-radius: 12px !important;
  }}

  /* ========= SELECT (closed control) ========= */
  [data-baseweb="select"] > div {{
    background: {INPUT_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
    border-radius: 12px !important;
  }}
  [data-baseweb="select"] * {{
    color: {INPUT_TEXT} !important;
    -webkit-text-fill-color: {INPUT_TEXT} !important;
  }}

  /* ========= DROPDOWN LIST ========= */
  div[role="dialog"] {{
    background: {MENU_BG} !important;
  }}

  div[role="dialog"] [data-baseweb="menu"],
  div[role="dialog"] ul[role="listbox"],
  [data-baseweb="menu"],
  ul[role="listbox"],
  [data-baseweb="popover"] > div,
  div[role="listbox"],
  div[role="dialog"] div[role="listbox"] {{
    background: {MENU_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
  }}

  div[role="dialog"] [data-baseweb="menu"] *,
  div[role="dialog"] ul[role="listbox"] *,
  [data-baseweb="menu"] *,
  ul[role="listbox"] *,
  div[role="listbox"] *,
  div[role="dialog"] div[role="listbox"] * {{
    color: {MENU_TEXT} !important;
    -webkit-text-fill-color: {MENU_TEXT} !important;
    opacity: 1 !important;
  }}

  div[role="dialog"] li[role="option"],
  li[role="option"] {{
    background: transparent !important;
    color: {MENU_TEXT} !important;
    -webkit-text-fill-color: {MENU_TEXT} !important;
    opacity: 1 !important;
  }}

  div[role="dialog"] li[role="option"]:hover,
  li[role="option"]:hover {{
    background: {MENU_HOVER} !important;
  }}
  div[role="dialog"] [aria-selected="true"],
  [aria-selected="true"] {{
    background: {MENU_HOVER} !important;
  }}

  /* ========= TOOLTIP ========= */
  div[role="tooltip"] {{
    background: {MENU_BG} !important;
    color: {MENU_TEXT} !important;
    border: 1px solid {INPUT_BORDER} !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25) !important;
  }}
  div[role="tooltip"] * {{
    color: {MENU_TEXT} !important;
    -webkit-text-fill-color: {MENU_TEXT} !important;
    opacity: 1 !important;
  }}

  /* Buttons */
  div.stButton > button,
  div.stDownloadButton > button {{
    color: #ffffff !important;
    background: rgba(17, 24, 39, 0.92) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
  }}
  div.stButton > button * ,
  div.stDownloadButton > button * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
  }}

  /* Chips */
  .chip {{
    display:inline-flex;
    align-items:center;
    padding: 6px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 12px;
    border: 1px solid {BORDER};
    background: rgba(255,255,255,0.10);
  }}
  .chip.ok {{
    background: rgba(34,197,94,0.18);
    border-color: rgba(34,197,94,0.35);
  }}
  .chip.no {{
    background: rgba(239,68,68,0.16);
    border-color: rgba(239,68,68,0.35);
  }}

  /* Metrics size */
  [data-testid="stMetricValue"] > div {{
    font-size: 2rem !important;
    line-height: 1.15 !important;
  }}

  /* ===== LOGO ===== */
  .logo-wrap {{ display:flex; justify-content:flex-end; }}
  .logo-strip {{
    display:inline-flex;
    align-items:center;
    flex-wrap: nowrap;
    padding: 2px 6px;
    border-radius: 12px;
    border: 1px solid {BORDER};
    background: rgba(255,255,255,0.55);
    line-height: 0;
    width: fit-content;
    max-width: 100%;
  }}
  .logo-img {{ display:block; }}
</style>
""",
    unsafe_allow_html=True,
)


def chip(label: str, ok: bool) -> str:
    return f'<span class="chip {"ok" if ok else "no"}">{label}</span>'


# ======================== LAYOUT ========================
left, right = st.columns([1, 1.35], gap="large")

with left:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("User Inputs")

    colA, colB = st.columns(2)

    with colA:
        st.markdown(label_html("Gender", "Jantina"), unsafe_allow_html=True)
        jantina = st.selectbox(
            "jantina_hidden",
            OPTIONS["Jantina"],
            index=0,
            format_func=fmt("Jantina"),
            label_visibility="collapsed",
            help=help_text(
                "Select the respondent's gender.",
                "Pilih jantina responden.",
            ),
        )

        st.markdown(label_html("Nationality", "Warganegara"), unsafe_allow_html=True)
        warganegara = st.selectbox(
            "warganegara_hidden",
            OPTIONS["Warganegara"],
            index=0,
            format_func=fmt("Warganegara"),
            label_visibility="collapsed",
            help=help_text(
                "Select whether the respondent is Malaysian or non-Malaysian.",
                "Pilih sama ada responden warganegara Malaysia atau bukan warganegara.",
            ),
        )

        st.markdown(label_html("Ethnicity", "Bangsa"), unsafe_allow_html=True)
        bangsa = st.selectbox(
            "bangsa_hidden",
            OPTIONS["Bangsa"],
            index=0,
            format_func=fmt("Bangsa"),
            label_visibility="collapsed",
            help=help_text(
                "Choose the ethnicity category.",
                "Pilih kategori bangsa.",
            ),
        )

        st.markdown(label_html("Religion", "Agama"), unsafe_allow_html=True)
        agama = st.selectbox(
            "agama_hidden",
            OPTIONS["Agama"],
            index=0,
            format_func=fmt("Agama"),
            label_visibility="collapsed",
            help=help_text(
                "Choose the religion category.",
                "Pilih kategori agama.",
            ),
        )

        st.markdown(label_html("Marital status", "Status perkahwinan"), unsafe_allow_html=True)
        status_kahwin = st.selectbox(
            "status_hidden",
            OPTIONS["Status Perkahwinan"],
            index=0,
            format_func=fmt("Status Perkahwinan"),
            label_visibility="collapsed",
            help=help_text(
                "Select marital status.",
                "Pilih status perkahwinan.",
            ),
        )

        st.markdown(label_html("Education level", "Tahap pendidikan"), unsafe_allow_html=True)
        tahap_pendidikan = st.selectbox(
            "edu_hidden",
            OPTIONS["Tahap Pendidikan"],
            index=0,
            format_func=fmt("Tahap Pendidikan"),
            label_visibility="collapsed",
            help=help_text(
                "Select the highest education level.",
                "Pilih tahap pendidikan tertinggi.",
            ),
        )

    with colB:
        st.markdown(label_html("Occupation", "Pekerjaan"), unsafe_allow_html=True)
        pekerjaan = st.selectbox(
            "job_hidden",
            OPTIONS["Pekerjaan"],
            index=0,
            format_func=fmt("Pekerjaan"),
            label_visibility="collapsed",
            help=help_text(
                "Select the occupation category.",
                "Pilih kategori pekerjaan.",
            ),
        )

        st.markdown(label_html("Household size", "Bilangan isi rumah"), unsafe_allow_html=True)
        bil_isi_rumah = st.selectbox(
            "hh_hidden",
            OPTIONS["Bilangan Isi Rumah"],
            index=0,
            format_func=fmt("Bilangan Isi Rumah"),
            label_visibility="collapsed",
            help=help_text(
                "Total number of people living in the household.",
                "Jumlah orang yang tinggal dalam isi rumah.",
            ),
        )

        st.markdown(label_html("Number of dependents", "Bilangan tanggungan"), unsafe_allow_html=True)
        bil_tanggungan = st.selectbox(
            "dep_hidden",
            OPTIONS["Bilangan Tanggungan"],
            index=0,
            format_func=fmt("Bilangan Tanggungan"),
            label_visibility="collapsed",
            help=help_text(
                "Number of dependents supported financially.",
                "Bilangan tanggungan yang ditanggung dari segi kewangan.",
            ),
        )

        st.markdown(label_html("Rental type", "Jenis penyewaan"), unsafe_allow_html=True)
        jenis_penyewaan = st.selectbox(
            "jenis_penyewaan_hidden",
            OPTIONS["Jenis Penyewaan"],
            index=0,
            format_func=fmt("Jenis Penyewaan"),
            label_visibility="collapsed",
            help=help_text(
                "Choose whether renting a whole unit/house or just a room.",
                "Pilih sama ada menyewa rumah/unit atau bilik sahaja.",
            ),
        )

        st.markdown(label_html("Type of rental housing", "Jenis rumah sewa"), unsafe_allow_html=True)
        jenis_rumah_sewa = st.selectbox(
            "jenis_rumah_hidden",
            OPTIONS["Jenis Rumah Sewa"],
            index=0,
            format_func=fmt("Jenis Rumah Sewa"),
            label_visibility="collapsed",
            help=help_text(
                "Select the rental housing type (e.g., flat/condo/apartment/terrace).",
                "Pilih jenis rumah sewa (cth: flat/kondo/pangsapuri/teres).",
            ),
        )

        st.markdown(label_html("Furnished type", "Jenis kelengkapan perabot"), unsafe_allow_html=True)
        jenis_perabot = st.selectbox(
            "perabot_hidden",
            OPTIONS["Jenis Kelengkapan Perabot"],
            index=0,
            format_func=fmt("Jenis Kelengkapan Perabot"),
            label_visibility="collapsed",
            help=help_text(
                "Indicate the furnishing level of the rental unit.",
                "Nyatakan tahap perabot bagi rumah sewa.",
            ),
        )

        st.markdown(label_html("Deposit", "Deposit"), unsafe_allow_html=True)
        deposit = st.selectbox(
            "deposit_hidden",
            OPTIONS["Deposit"],
            index=0,
            format_func=fmt("Deposit"),
            label_visibility="collapsed",
            help=help_text(
                "Choose the deposit arrangement (example: 2+1 = 2 months deposit + 1 month utility).",
                "Pilih jenis deposit (cth: 2+1 = 2 bulan deposit + 1 bulan utiliti).",
            ),
        )

        st.markdown(label_html("Years renting", "Tempoh menyewa"), unsafe_allow_html=True)
        tempoh_menyewa = st.selectbox(
            "tempoh_hidden",
            OPTIONS["Tempoh Menyewa"],
            index=0,
            format_func=fmt("Tempoh Menyewa"),
            label_visibility="collapsed",
            help=help_text(
                "How long the respondent has been renting.",
                "Tempoh responden telah menyewa.",
            ),
        )

        st.markdown(label_html("Know affordable rental scheme?", "Tahu skim mampu sewa?"), unsafe_allow_html=True)
        skim = st.selectbox(
            "skim_hidden",
            OPTIONS["Skim"],
            index=0,
            format_func=fmt("Skim"),
            label_visibility="collapsed",
            help=help_text(
                "Whether the respondent is aware of affordable rental schemes.",
                "Sama ada responden tahu skim mampu sewa.",
            ),
        )

    st.divider()
    st.subheader("Income & Rent Inputs")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(label_html("Monthly income (RM)", "Pendapatan bulanan (RM)"), unsafe_allow_html=True)
        income = st.number_input(
            "income_hidden",
            min_value=0.0,
            value=6000.0,
            step=100.0,
            label_visibility="collapsed",
            help=help_text(
                "Enter total monthly household income in RM.",
                "Masukkan jumlah pendapatan isi rumah bulanan (RM).",
            ),
        )
    with c2:
        st.markdown(label_html("Monthly rent (RM)", "Sewa bulanan (RM)"), unsafe_allow_html=True)
        rent = st.number_input(
            "rent_hidden",
            min_value=0.0,
            value=2000.0,
            step=50.0,
            label_visibility="collapsed",
            help=help_text(
                "Enter the monthly rent amount in RM.",
                "Masukkan jumlah sewa bulanan (RM).",
            ),
        )
    with c3:
        st.markdown(label_html("Rent ratio threshold", "Had nisbah sewa"), unsafe_allow_html=True)
        ratio = st.number_input(
            "ratio_hidden",
            min_value=0.0,
            max_value=1.0,
            value=0.38,
            step=0.01,
            label_visibility="collapsed",
            help=help_text(
                "Maximum recommended rent share of income (example: 0.38 = 38%).",
                "Had maksimum sewa berbanding pendapatan (cth: 0.38 = 38%).",
            ),
        )

    st.divider()
    st.subheader("Spreadsheet Logging (Google Sheets)")
    st.caption("EN: Optional logging to your private Google Sheet.  •  BM: Simpan rekod ke Google Sheet peribadi (pilihan).")

    save_to_sheet = st.toggle("Save submission to spreadsheet", value=False)

    ok_sheet, msg_sheet = sheets_status()
    if save_to_sheet:
        if ok_sheet:
            st.success(msg_sheet)
            st.caption(
                "EN: Users will NOT see your spreadsheet. Only the Service Account writes to it.\n"
                "BM: Pengguna TIDAK akan nampak spreadsheet. Hanya Service Account yang menulis data."
            )
        else:
            st.warning(
                f"Google Sheets is NOT ready. {msg_sheet}\n\n"
                "Checklist:\n"
                "1) Install libs: `pip install gspread google-auth`\n"
                "2) Put Service Account JSON into Streamlit Secrets as `[gcp_service_account]`\n"
                "3) Share the Google Sheet to the service account email (Editor)\n"
                "4) (Optional) Put `SHEET_ID` and `SHEET_TAB` in Secrets"
            )

    run = st.button("✅ Run Check", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================== RESULTS (ONLY AFTER RUN) ========================
if "result" not in st.session_state:
    st.session_state["result"] = None

if run:
    inputs = build_inputs(
        edu_label=tahap_pendidikan,
        job_label=pekerjaan,
        jenis_penyewaan_label=jenis_penyewaan,
        jenis_rumah_sewa_label=jenis_rumah_sewa,
        perabot_label=jenis_perabot,
        deposit_label=deposit,
        tempoh_label=tempoh_menyewa,
    )

    _df, z, p = compute_table(inputs)

    ok_a = p >= P_THRESHOLD
    threshold = ratio * income
    ok_b = rent <= threshold
    ok_all = ok_a and ok_b

    rent_share = (rent / income) if income > 0 else 0.0
    rent_share = clamp(rent_share, 0.0, 1.0)

    st.session_state["result"] = {
        "z": z,
        "p": p,
        "threshold": threshold,
        "ratio": ratio,
        "income": income,
        "rent": rent,
        "rent_share": rent_share,
        "ok_a": ok_a,
        "ok_b": ok_b,
        "ok_all": ok_all,
    }

    # ===== Append to Google Sheet if enabled =====
    if save_to_sheet:
        ok_sheet, _ = sheets_status()
        if ok_sheet:
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "jantina": jantina,
                "warganegara": warganegara,
                "bangsa": bangsa,
                "agama": agama,
                "status_perkahwinan": status_kahwin,
                "tahap_pendidikan": tahap_pendidikan,
                "pekerjaan": pekerjaan,
                "bil_isi_rumah": bil_isi_rumah,
                "bil_tanggungan": bil_tanggungan,
                "jenis_penyewaan": jenis_penyewaan,
                "jenis_rumah_sewa": jenis_rumah_sewa,
                "jenis_perabot": jenis_perabot,
                "deposit": deposit,
                "tempoh_menyewa": tempoh_menyewa,
                "skim": skim,
                "income_rm": float(income),
                "rent_rm": float(rent),
                "ratio_threshold": float(ratio),
                "z": float(z),
                "p": float(p),
                "condition_a_ok": int(ok_a),
                "condition_b_ok": int(ok_b),
                "overall_ok": int(ok_all),
            }
            try:
                append_to_sheet(payload)
                st.toast("Saved to Google Sheets ✅", icon="✅")
            except Exception as e:
                st.error(
                    "Failed to save to Google Sheets.\n\n"
                    f"Error: {e}\n\n"
                    "Most common fix: share the sheet to the Service Account email as Editor."
                )
        else:
            st.error("Google Sheets is not configured yet (missing secrets or libraries).")

res = st.session_state["result"]

with right:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("Results")

    if res is None:
        st.info("Click **Run Check** to show results.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:10px;">
  <div><b>Condition A (p ≥ {P_THRESHOLD:.2f})</b>: {chip("Afford" if res["ok_a"] else "Not Afford", res["ok_a"])}</div>
  <div><b>Condition B (Rent ≤ {res["ratio"]:.2f}×Income)</b>: {chip("Afford" if res["ok_b"] else "Not Afford", res["ok_b"])}</div>
  <div><b>Overall</b>: {chip("Afford" if res["ok_all"] else "Not Afford", res["ok_all"])}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        g1, g2 = st.columns(2)

        with g1:
            st.components.v1.html(
                svg_gauge_html(
                    title="Condition A Meter (Probability p)",
                    value_0_1=float(res["p"]),
                    threshold_0_1=float(P_THRESHOLD),
                    subtitle_left="Low",
                    subtitle_right=f"Pass at {P_THRESHOLD:.2f}",
                    text_color=("#f8fafc" if dark_mode else "#111827"),
                    border_color=BORDER,
                ),
                height=310,
                scrolling=False,
            )

        with g2:
            ratio_v = float(res["ratio"])
            share = float(res["rent_share"])
            closeness = clamp(share / ratio_v, 0.0, 1.0) if ratio_v > 0 else 0.0
            st.components.v1.html(
                svg_gauge_html(
                    title="Condition B Meter (Rent vs Threshold)",
                    value_0_1=float(closeness),
                    threshold_0_1=1.0,
                    subtitle_left=f"Rent/Income: {share:.2f}",
                    subtitle_right=f"Threshold: {ratio_v:.2f}",
                    text_color=("#f8fafc" if dark_mode else "#111827"),
                    border_color=BORDER,
                ),
                height=310,
                scrolling=False,
            )

        m1, m2, m3 = st.columns(3)
        m1.metric("Score (z)", f"{res['z']:.6f}")
        m2.metric("Estimated probability (p)", f"{res['p']:.9f}")
        m3.metric("Rent threshold (RM)", f"{res['threshold']:.2f}")

        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================================
# IMPORTANT SETUP NOTES (DO THIS ONCE)
# ----------------------------------------------------------
# 1) Install packages (local):
#    pip install gspread google-auth
#
# 2) Create Service Account + enable Google Sheets API, then download JSON key.
#
# 3) Share your Google Sheet to service account email (Editor).
#    Example email: xxx@xxx.iam.gserviceaccount.com
#
# 4) Put secrets in Streamlit:
#    - Local: .streamlit/secrets.toml
#    - Streamlit Cloud: App settings -> Secrets
#
#    Example secrets.toml:
#    SHEET_ID="1sv9VlXO07K-wcmNCRVO5fvZcrzGcI4gncxfFVR73wxc"
#    SHEET_TAB="Sheet1"
#
#    [gcp_service_account]
#    type="service_account"
#    project_id="..."
#    private_key_id="..."
#    private_key="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
#    client_email="...@...iam.gserviceaccount.com"
#    client_id="..."
#    token_uri="https://oauth2.googleapis.com/token"
# ==========================================================

# app.py
import math
import pandas as pd
import streamlit as st
from pathlib import Path
import base64

# ==========================================================
# Rental Affordability Checker (English UI)
# ==========================================================
APP_DIR = Path(__file__).resolve().parent

# ====== Condition A threshold (as requested) ======
P_THRESHOLD = 0.05  # pass if p >= 0.05


def img_to_base64(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")


def logo_strip_html(paths, height_px=42, gap_px=10):
    imgs = []
    for p in paths:
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


st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# -------------------- COEFFICIENTS (UPDATED: COLUMN B) --------------------
COEF = {
    "Umur": 0.002,
    "Jantina ketua keluarga(1)": 0.007,  # Woman(1)
    "Warganegara(1)": -0.818,            # Non-Malaysian(1)

    "Bangsa=Cina(1)": -0.411,
    "Bangsa=India(1)": 0.463,
    "Bangsa=Lain-lain(1)": 0.849,

    "Agama=Buddha(1)": 0.131,
    "Agama=Hindu(1)": -0.525,
    "Agama=Lain-lain(1)": -0.158,

    "Status Perkahwinan=Berkahwin(1)": -0.007,
    "Status Perkahwinan=Cerai/BaluDuda/Pisah(1)": 0.313,

    "Tahap Pendidikan=Undergraduate(1)": -0.537,
    "Tahap Pendidikan=Postgraduate(1)": -0.808,

    "Pekerjaan=Bekerja sendiri(1)": 0.198,
    "Pekerjaan=Lain-lain(1)": -0.801,
    "Pekerjaan=Pekerja Kerajaan(1)": 0.803,
    "Pekerjaan=Pekerja Swasta(1)": 0.912,
    "Pekerjaan=Pesara(1)": 0.018,

    "Bilangan isi rumah=3-4 orang(1)": 0.096,
    "Bilangan isi rumah=5+ orang(1)": -0.403,

    "Bilangan tanggungan=3-4 orang(1)": -0.028,
    "Bilangan tanggungan=5+ orang(1)": -0.134,

    "Jenis Penyewaan=Bilik(1)": 1.121,

    "Jenis rumah sewa=Kondominium(1)": -1.007,
    "Jenis rumah sewa=Lain-lain(1)": -0.598,
    "Jenis rumah sewa=Pangsapuri(1)": -0.604,
    "Jenis rumah sewa=Rumah 1 unit(1)": -0.711,
    "Jenis rumah sewa=Rumah Teres(1)": 0.526,

    "Jenis kelengkapan perabot=Berperabot penuh(1)": -0.053,
    "Jenis kelengkapan perabot=Berperabot separa(1)": -0.370,

    "deposit_1_1(1)": 0.339,
    "deposit_2_1(1)": 0.556,
    "deposit_3_1(1)": 0.686,

    "Berapa lama anda telah menyewa rumah=3-5 tahun(1)": 0.413,
    "Berapa lama anda telah menyewa rumah=6+ tahun(1)": -0.584,

    "Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)": 0.200,

    "Constant": 0.310,
}

# -------------------- ENGLISH OPTIONS --------------------
OPTIONS = {
    "Gender": ["Man", "Woman"],
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],
    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],
    "Religion": ["Islam", "Buddhism", "Hinduism", "Others"],
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],
    "Education Level": [
        "No certificate",
        "UPSR",
        "PT3",
        "SPM",
        "STPM",
        "Certificate/TVET",
        "Certificate (Polytechnic/University)",
        "Diploma",
        "Bachelor's Degree",
    ],
    "Occupation": [
        "Unemployed",
        "Government employee",
        "Private employee",
        "Self-employed",
        "Homemaker",
        "Student",
        "Government retiree",
    ],
    "Household Size": ["1 person", "2 people", "3–4 people", "5–6 people", "7 people or more"],
    "Number of Dependents": ["None", "1–2 people", "3–4 people", "5–6 people", "7 people or more"],
    "Type of Rental Housing (labels)": [
        "Flat",
        "Apartment",
        "Condominium",
        "Terrace House (Single storey)",
        "Terrace House (Double storey)",
        "One-unit house",
    ],
    "Type of Rental Housing (codes)": [2, 3, 4, 5, 6, 7],
    "Furnished Type": ["None", "Furnished"],
    "Deposit": [
        "No deposit",
        "1 + 1",
        "2 + 1",
        "3 + 1",
        "1 + 1 + utility",
        "2 + 1 + utility",
        "3 + 1 + utility",
    ],
    "Total years renting": ["Less than 6 months", "Less than 1 year", "1–2 years", "3–5 years", "6–10 years"],
    "Known SMART SEWA": ["Yes", "No"],
}


def logistic(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def gauge_html(title: str, value_0_1: float, threshold_0_1: float, subtitle_left: str, subtitle_right: str) -> str:
    """
    Semicircle gauge (like your screenshot).
    - value_0_1 in [0,1]
    - threshold marker shown as a thin tick.
    """
    v = clamp(value_0_1, 0.0, 1.0)
    t = clamp(threshold_0_1, 0.0, 1.0)

    # Needle rotation: -90deg (left) to +90deg (right)
    needle_deg = -90 + (v * 180.0)
    tick_deg = -90 + (t * 180.0)

    # For nicer banding when threshold is small, we keep a sensible zone split:
    # red: 0-0.10, yellow: 0.10-0.40, green: 0.40-1.00 (visual only)
    # (Threshold marker still shows exact pass line.)
    red_end = 0.10
    yellow_end = 0.40
    red_pct = red_end * 100
    yel_pct = yellow_end * 100

    return f"""
<div class="gauge-card">
  <div class="gauge-title">{title}</div>

  <div class="gauge-wrap">
    <div class="gauge-arc"
      style="background:
        conic-gradient(
          rgba(239,68,68,0.85) 0% {red_pct}%,
          rgba(245,158,11,0.85) {red_pct}% {yel_pct}%,
          rgba(34,197,94,0.85) {yel_pct}% 100%
        );">
      <div class="gauge-cutout"></div>

      <!-- threshold tick -->
      <div class="gauge-tick" style="transform: rotate({tick_deg}deg);"></div>

      <!-- needle -->
      <div class="gauge-needle" style="transform: rotate({needle_deg}deg);"></div>
      <div class="gauge-dot"></div>
    </div>

    <div class="gauge-value">{(v*100):.2f}%</div>
    <div class="gauge-sub">
      <span>{subtitle_left}</span>
      <span>{subtitle_right}</span>
    </div>
  </div>
</div>
"""


def build_inputs(
    age: int,
    gender_idx: int,
    nationality_idx: int,
    ethnicity_idx: int,
    religion_idx: int,
    marital_idx: int,
    edu_idx: int,
    job_idx: int,
    household_idx: int,
    dep_idx: int,
    rental_code: int,
    furnish_idx: int,
    deposit_idx: int,
    years_idx: int,
    smart_idx: int,
) -> dict:
    inp = {k: 0.0 for k in COEF.keys()}
    inp["Constant"] = 1.0
    inp["Umur"] = float(age)

    inp["Jantina ketua keluarga(1)"] = 1.0 if gender_idx == 1 else 0.0
    inp["Warganegara(1)"] = 1.0 if nationality_idx == 1 else 0.0

    eth_label = OPTIONS["Ethnicity"][ethnicity_idx]
    if eth_label == "Chinese":
        inp["Bangsa=Cina(1)"] = 1.0
    elif eth_label == "Indian":
        inp["Bangsa=India(1)"] = 1.0
    elif eth_label != "Malay":
        inp["Bangsa=Lain-lain(1)"] = 1.0

    rel_label = OPTIONS["Religion"][religion_idx]
    if rel_label == "Buddhism":
        inp["Agama=Buddha(1)"] = 1.0
    elif rel_label == "Hinduism":
        inp["Agama=Hindu(1)"] = 1.0
    elif rel_label != "Islam":
        inp["Agama=Lain-lain(1)"] = 1.0

    mar_label = OPTIONS["Marital Status"][marital_idx]
    if mar_label == "Married":
        inp["Status Perkahwinan=Berkahwin(1)"] = 1.0
    elif mar_label in ("Widowed", "Divorced", "Separated"):
        inp["Status Perkahwinan=Cerai/BaluDuda/Pisah(1)"] = 1.0

    edu_label = OPTIONS["Education Level"][edu_idx]
    if edu_label in ("Diploma", "Bachelor's Degree"):
        inp["Tahap Pendidikan=Undergraduate(1)"] = 1.0

    job_label = OPTIONS["Occupation"][job_idx]
    if job_label == "Self-employed":
        inp["Pekerjaan=Bekerja sendiri(1)"] = 1.0
    elif job_label == "Government employee":
        inp["Pekerjaan=Pekerja Kerajaan(1)"] = 1.0
    elif job_label == "Private employee":
        inp["Pekerjaan=Pekerja Swasta(1)"] = 1.0
    elif job_label == "Government retiree":
        inp["Pekerjaan=Pesara(1)"] = 1.0
    elif job_label in ("Homemaker", "Student"):
        inp["Pekerjaan=Lain-lain(1)"] = 1.0

    if household_idx == 2:
        inp["Bilangan isi rumah=3-4 orang(1)"] = 1.0
    elif household_idx in (3, 4):
        inp["Bilangan isi rumah=5+ orang(1)"] = 1.0

    if dep_idx == 2:
        inp["Bilangan tanggungan=3-4 orang(1)"] = 1.0
    elif dep_idx in (3, 4):
        inp["Bilangan tanggungan=5+ orang(1)"] = 1.0

    if rental_code == 4:
        inp["Jenis rumah sewa=Kondominium(1)"] = 1.0
    elif rental_code in (2, 3):
        inp["Jenis rumah sewa=Pangsapuri(1)"] = 1.0
    elif rental_code in (5, 6):
        inp["Jenis rumah sewa=Rumah Teres(1)"] = 1.0
    elif rental_code == 7:
        inp["Jenis rumah sewa=Rumah 1 unit(1)"] = 1.0

    if furnish_idx == 1:
        inp["Jenis kelengkapan perabot=Berperabot penuh(1)"] = 1.0

    dep_label = OPTIONS["Deposit"][deposit_idx]
    if dep_label == "1 + 1":
        inp["deposit_1_1(1)"] = 1.0
    elif dep_label == "2 + 1":
        inp["deposit_2_1(1)"] = 1.0
    elif dep_label == "3 + 1":
        inp["deposit_3_1(1)"] = 1.0

    if years_idx == 3:
        inp["Berapa lama anda telah menyewa rumah=3-5 tahun(1)"] = 1.0
    elif years_idx == 4:
        inp["Berapa lama anda telah menyewa rumah=6+ tahun(1)"] = 1.0

    inp["Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)"] = 1.0 if smart_idx == 1 else 0.0

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
    MUTED = "rgba(248,250,252,.75)"
else:
    PAGE_BG = "linear-gradient(180deg, #f7f2ff 0%, #f7f2ff 45%, #efe6ff 100%)"
    CARD_BG = "rgba(255,255,255,0.84)"
    BORDER = "rgba(139, 92, 246, 0.20)"
    TXT = "#111827"
    MUTED = "rgba(17,24,39,.70)"

WIDGET_TEXT = "#f8fafc"
DROPDOWN_BG = "rgba(17, 24, 39, 0.98)"

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
  .block-container {{ padding-top: .75rem; }}

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

  /* ===== LOGO: ngam ngam, no long grey bar ===== */
  .logo-wrap {{
    display:flex;
    justify-content:flex-end;
  }}
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

  /* Widget text always white */
  .stNumberInput input, .stTextInput input, .stTextArea textarea {{
    color: {WIDGET_TEXT} !important;
    -webkit-text-fill-color: {WIDGET_TEXT} !important;
  }}
  [data-baseweb="select"] * {{
    color: {WIDGET_TEXT} !important;
    -webkit-text-fill-color: {WIDGET_TEXT} !important;
  }}

  /* Dropdown menu open */
  [data-baseweb="menu"], ul[role="listbox"] {{
    background: {DROPDOWN_BG} !important;
  }}
  [data-baseweb="popover"] * {{
    color: {WIDGET_TEXT} !important;
    -webkit-text-fill-color: {WIDGET_TEXT} !important;
  }}
  li[role="option"]:hover {{
    background: rgba(167, 139, 250, 0.14) !important;
  }}

  /* DataFrame text white */
  div[data-testid="stDataFrame"] * {{
    color: {WIDGET_TEXT} !important;
  }}

  /* Buttons text white */
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

  /* Gauge (semicircle) */
  .gauge-card {{
    border: 1px solid {BORDER};
    background: rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 12px 12px;
    margin: 10px 0;
  }}
  .gauge-title {{
    font-weight: 800;
    margin-bottom: 8px;
    opacity: .95;
  }}
  .gauge-wrap {{
    display:flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }}
  .gauge-arc {{
    width: 240px;
    height: 120px;
    border-radius: 240px 240px 0 0;
    position: relative;
    overflow: hidden;
    border: 1px solid {BORDER};
  }}
  .gauge-cutout {{
    position:absolute;
    left: 16px;
    right: 16px;
    bottom: -1px;
    height: 96px;
    border-radius: 180px 180px 0 0;
    background: {CARD_BG};
    border-top: 1px solid rgba(255,255,255,0.10);
  }}

  .gauge-needle {{
    position:absolute;
    width: 4px;
    height: 98px;
    left: 50%;
    bottom: 0px;
    transform-origin: 50% 100%;
    background: rgba(17,24,39,0.98);
    box-shadow: 0 6px 18px rgba(0,0,0,0.35);
    border-radius: 8px;
  }}
  .gauge-dot {{
    position:absolute;
    width: 14px;
    height: 14px;
    border-radius: 999px;
    background: rgba(17,24,39,0.98);
    left: calc(50% - 7px);
    bottom: 4px;
    border: 2px solid rgba(255,255,255,0.35);
  }}

  /* thin tick marker for threshold */
  .gauge-tick {{
    position:absolute;
    width: 2px;
    height: 108px;
    left: 50%;
    bottom: 0px;
    transform-origin: 50% 100%;
    background: rgba(255,255,255,0.75);
    opacity: .9;
  }}

  .gauge-value {{
    font-weight: 900;
    font-size: 20px;
  }}
  .gauge-sub {{
    width: 100%;
    max-width: 260px;
    display:flex;
    justify-content: space-between;
    font-size: 12px;
    opacity: .82;
  }}

  /* Simple helper text under inputs */
  .mini-help {{
    font-size: 12px;
    opacity: .80;
    margin-top: -6px;
  }}
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
        age = st.number_input("Age (years)", min_value=15, max_value=100, value=38, step=1)
        st.markdown('<div class="mini-help">Your age (years).</div>', unsafe_allow_html=True)

        gender = st.selectbox("Gender", OPTIONS["Gender"], index=0)
        st.markdown('<div class="mini-help">Your gender.</div>', unsafe_allow_html=True)

        nationality = st.selectbox("Nationality", OPTIONS["Nationality"], index=0)
        st.markdown('<div class="mini-help">Your nationality status.</div>', unsafe_allow_html=True)

        ethnicity = st.selectbox("Ethnicity", OPTIONS["Ethnicity"], index=0)
        st.markdown('<div class="mini-help">Your ethnic background.</div>', unsafe_allow_html=True)

        religion = st.selectbox("Religion", OPTIONS["Religion"], index=0)
        st.markdown('<div class="mini-help">Your religion.</div>', unsafe_allow_html=True)

        marital = st.selectbox("Marital Status", OPTIONS["Marital Status"], index=0)
        st.markdown('<div class="mini-help">Your current marital status.</div>', unsafe_allow_html=True)

        edu = st.selectbox("Education Level", OPTIONS["Education Level"], index=0)
        st.markdown('<div class="mini-help">Your highest education level.</div>', unsafe_allow_html=True)

    with colB:
        job = st.selectbox("Occupation", OPTIONS["Occupation"], index=0)
        st.markdown('<div class="mini-help">Your current jobs.</div>', unsafe_allow_html=True)

        household = st.selectbox("Household Size", OPTIONS["Household Size"], index=0)
        st.markdown('<div class="mini-help">Number of people living together.</div>', unsafe_allow_html=True)

        dependents = st.selectbox("Number of Dependents", OPTIONS["Number of Dependents"], index=0)
        st.markdown('<div class="mini-help">Number of dependents you support.</div>', unsafe_allow_html=True)

        rental_label = st.selectbox("Type of Rental Housing", OPTIONS["Type of Rental Housing (labels)"], index=0)
        st.markdown('<div class="mini-help">Type of house you rent.</div>', unsafe_allow_html=True)
        rental_code = OPTIONS["Type of Rental Housing (codes)"][OPTIONS["Type of Rental Housing (labels)"].index(rental_label)]

        furnished = st.selectbox("Furnished Type", OPTIONS["Furnished Type"], index=0)
        st.markdown('<div class="mini-help">Whether the house is furnished.</div>', unsafe_allow_html=True)

        deposit = st.selectbox("Deposit", OPTIONS["Deposit"], index=0)
        st.markdown('<div class="mini-help">Your deposit arrangement.</div>', unsafe_allow_html=True)

        years = st.selectbox("Total years renting", OPTIONS["Total years renting"], index=0)
        st.markdown('<div class="mini-help">How long you have been renting.</div>', unsafe_allow_html=True)

        smart = st.selectbox("Known SMART SEWA", OPTIONS["Known SMART SEWA"], index=0)
        st.markdown('<div class="mini-help">Whether you know SMART SEWA scheme.</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Income & Rent Inputs")

    c1, c2, c3 = st.columns(3)
    with c1:
        income = st.number_input("Monthly Income (RM)", min_value=0.0, value=6000.0, step=100.0)
    with c2:
        rent = st.number_input("Monthly Rent (RM)", min_value=0.0, value=2000.0, step=50.0)
    with c3:
        ratio = st.number_input("Rent ratio threshold", min_value=0.0, max_value=1.0, value=0.38, step=0.01)

    run = st.button("✅ Run Check", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================== RESULTS (ONLY AFTER RUN) ========================
if "result" not in st.session_state:
    st.session_state["result"] = None

if run:
    inputs = build_inputs(
        age=int(age),
        gender_idx=OPTIONS["Gender"].index(gender),
        nationality_idx=OPTIONS["Nationality"].index(nationality),
        ethnicity_idx=OPTIONS["Ethnicity"].index(ethnicity),
        religion_idx=OPTIONS["Religion"].index(religion),
        marital_idx=OPTIONS["Marital Status"].index(marital),
        edu_idx=OPTIONS["Education Level"].index(edu),
        job_idx=OPTIONS["Occupation"].index(job),
        household_idx=OPTIONS["Household Size"].index(household),
        dep_idx=OPTIONS["Number of Dependents"].index(dependents),
        rental_code=int(rental_code),
        furnish_idx=OPTIONS["Furnished Type"].index(furnished),
        deposit_idx=OPTIONS["Deposit"].index(deposit),
        years_idx=OPTIONS["Total years renting"].index(years),
        smart_idx=OPTIONS["Known SMART SEWA"].index(smart),
    )

    df, z, p = compute_table(inputs)

    # ---- Condition A threshold changed to 0.05 ----
    ok_a = p >= P_THRESHOLD
    cond_a = "Afford" if ok_a else "Not Afford"

    threshold = ratio * income
    ok_b = rent <= threshold
    cond_b = "Afford" if ok_b else "Not Afford"

    ok_all = ok_a and ok_b
    overall = "Afford" if ok_all else "Not Afford"

    rent_share = (rent / income) if income > 0 else 0.0
    rent_share = clamp(rent_share, 0.0, 1.0)

    st.session_state["result"] = {
        "df": df,
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
        "cond_a": cond_a,
        "cond_b": cond_b,
        "overall": overall,
    }

res = st.session_state["result"]

with right:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("Results")

    if res is None:
        st.info("Click **Run Check** to show results and the calculation table.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # ===== keep the highlight summary like before =====
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

        # ===== meters (like your screenshot) =====
        g1, g2 = st.columns(2)

        with g1:
            st.markdown(
                gauge_html(
                    title="Condition A Meter (Probability p)",
                    value_0_1=float(res["p"]),
                    threshold_0_1=float(P_THRESHOLD),
                    subtitle_left="Low",
                    subtitle_right=f"Pass at {P_THRESHOLD:.2f}",
                ),
                unsafe_allow_html=True,
            )

        with g2:
            # show how close rent share is to threshold ratio
            ratio_v = float(res["ratio"])
            share = float(res["rent_share"])
            closeness = clamp(share / ratio_v, 0.0, 1.0) if ratio_v > 0 else 0.0

            st.markdown(
                gauge_html(
                    title="Condition B Meter (Rent vs Threshold)",
                    value_0_1=float(closeness),
                    threshold_0_1=1.0,  # pass line is at the end (<= threshold)
                    subtitle_left=f"Rent/Income: {share:.2f}",
                    subtitle_right=f"Threshold: {ratio_v:.2f}",
                ),
                unsafe_allow_html=True,
            )

        # ===== metrics =====
        m1, m2, m3 = st.columns(3)
        m1.metric("SUM(COEF×INPUT)  (z)", f"{res['z']:.6f}")
        m2.metric("Probability p = 1/(1+exp(-z))", f"{res['p']:.9f}")
        m3.metric(f"{res['ratio']:.2f} × Income (RM)", f"{res['threshold']:.2f}")

        st.caption("Calculation table (COEF, INPUT, COEF×INPUT). z is exactly the sum of the COEF×INPUT column.")
        st.dataframe(res["df"], use_container_width=True, height=520)

        csv = res["df"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Calculation Table (CSV)",
            data=csv,
            file_name="affordability_calculation.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown(
            f"""
**Rules used**
- Condition A: `IF( p >= {P_THRESHOLD:.2f} , "Afford" , "Not Afford")`
- Condition B: `IF( Rent <= ratio×Income , "Afford" , "Not Afford")`
- Overall: `IF( AND(ConditionA, ConditionB) , "Afford" , "Not Afford")`
"""
        )
        st.markdown("</div>", unsafe_allow_html=True)

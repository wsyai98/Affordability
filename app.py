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

# -------------------- COEFFICIENTS --------------------
COEF = {
    "Umur": 0.002,
    "Jantina ketua keluarga(1)": 0.007,
    "Warganegara(1)": -0.818,
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

# -------------------- OPTIONS --------------------
OPTIONS = {
    "Gender": ["Man", "Woman"],
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],
    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],
    "Religion": ["Islam", "Buddhism", "Hinduism", "Others"],
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],
    "Education Level": [
        "No certificate", "UPSR", "PT3", "SPM", "STPM",
        "Certificate/TVET", "Certificate (Polytechnic/University)",
        "Diploma", "Bachelor's Degree",
    ],
    "Occupation": [
        "Unemployed", "Government employee", "Private employee",
        "Self-employed", "Homemaker", "Student", "Government retiree",
    ],
    "Household Size": ["1 person", "2 people", "3–4 people", "5–6 people", "7 people or more"],
    "Number of Dependents": ["None", "1–2 people", "3–4 people", "5–6 people", "7 people or more"],
    "Type of Rental Housing (labels)": [
        "Flat", "Apartment", "Condominium",
        "Terrace House (Single storey)",
        "Terrace House (Double storey)",
        "One-unit house",
    ],
    "Type of Rental Housing (codes)": [2, 3, 4, 5, 6, 7],
    "Furnished Type": ["None", "Furnished"],
    "Deposit": [
        "No deposit", "1 + 1", "2 + 1", "3 + 1",
        "1 + 1 + utility", "2 + 1 + utility", "3 + 1 + utility",
    ],
    "Total years renting": ["Less than 6 months", "Less than 1 year", "1–2 years", "3–5 years", "6–10 years"],
    "Known SMART SEWA": ["Yes", "No"],
}

# ======================== THEME ========================
dark_mode = True  # default

PAGE_BG = "linear-gradient(180deg, #0b0b14 0%, #0b0b14 45%, #1a102b 100%)"
CARD_BG = "rgba(17, 24, 39, 0.68)"
BORDER = "rgba(167, 139, 250, 0.22)"
TXT = "#f8fafc"

INPUT_BG = "rgba(17, 24, 39, 0.92)"
INPUT_BORDER = "rgba(167, 139, 250, 0.22)"
INPUT_TEXT = "#f8fafc"

# DARK MODE dropdown + tooltip colors
DROPDOWN_BG = "#0b0b14"
DROPDOWN_TEXT = "#f8fafc"
DROPDOWN_OPTION_HOVER = "rgba(167, 139, 250, 0.14)"

st.markdown(
f"""
<style>
/* ================= GLOBAL ================= */
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
}}

/* ================= INPUT ================= */
.stNumberInput input,
.stTextInput input,
.stTextArea textarea {{
    background: {INPUT_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
    color: {INPUT_TEXT} !important;
    -webkit-text-fill-color: {INPUT_TEXT} !important;
    border-radius: 12px !important;
}}

/* ================= SELECT ================= */
[data-baseweb="select"] > div {{
    background: {INPUT_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
    border-radius: 12px !important;
}}

[data-baseweb="select"] * {{
    color: {INPUT_TEXT} !important;
    -webkit-text-fill-color: {INPUT_TEXT} !important;
}}

/* ================= DROPDOWN LIST (DARK) ================= */
[data-baseweb="popover"] > div,
div[role="listbox"],
div[role="dialog"] div[role="listbox"] {{
    background: {DROPDOWN_BG} !important;
    border: 1px solid {INPUT_BORDER} !important;
}}

div[role="listbox"] * ,
div[role="dialog"] div[role="listbox"] * {{
    color: {DROPDOWN_TEXT} !important;
    -webkit-text-fill-color: {DROPDOWN_TEXT} !important;
    opacity: 1 !important;
}}

div[role="listbox"] [aria-selected="true"],
div[role="listbox"] [role="option"]:hover {{
    background: {DROPDOWN_OPTION_HOVER} !important;
}}

/* ================= TOOLTIP / HELP ================= */
div[role="tooltip"] {{
    background: {DROPDOWN_BG} !important;
    color: {DROPDOWN_TEXT} !important;
    border: 1px solid {INPUT_BORDER} !important;
    border-radius: 10px !important;
}}

div[role="tooltip"] * {{
    color: {DROPDOWN_TEXT} !important;
    -webkit-text-fill-color: {DROPDOWN_TEXT} !important;
}}
</style>
""",
unsafe_allow_html=True
)

# ======================== UI ========================
left, right = st.columns([1, 1.35], gap="large")

with left:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("User Inputs")

    colA, colB = st.columns(2)
    with colA:
        age = st.number_input("Age (years)", 15, 100, 38, help="Your age (years).")
        gender = st.selectbox("Gender", OPTIONS["Gender"], help="Your gender.")
        nationality = st.selectbox("Nationality", OPTIONS["Nationality"], help="Your nationality status.")
        ethnicity = st.selectbox("Ethnicity", OPTIONS["Ethnicity"], help="Your ethnic background.")
        religion = st.selectbox("Religion", OPTIONS["Religion"], help="Your religion.")
        marital = st.selectbox("Marital Status", OPTIONS["Marital Status"], help="Your current marital status.")
        edu = st.selectbox("Education Level", OPTIONS["Education Level"], help="Your highest education level.")

    with colB:
        job = st.selectbox("Occupation", OPTIONS["Occupation"], help="Your current jobs.")
        household = st.selectbox("Household Size", OPTIONS["Household Size"], help="Number of people living together.")
        dependents = st.selectbox("Number of Dependents", OPTIONS["Number of Dependents"], help="Number of dependents you support.")
        rental_label = st.selectbox("Type of Rental Housing", OPTIONS["Type of Rental Housing (labels)"], help="Type of house you rent.")
        furnished = st.selectbox("Furnished Type", OPTIONS["Furnished Type"], help="Whether the house is furnished.")
        deposit = st.selectbox("Deposit", OPTIONS["Deposit"], help="Your deposit arrangement.")
        years = st.selectbox("Total years renting", OPTIONS["Total years renting"], help="How long you have been renting.")
        smart = st.selectbox("Known SMART SEWA", OPTIONS["Known SMART SEWA"], help="Whether you know SMART SEWA scheme.")

    st.subheader("Income & Rent Inputs")
    income = st.number_input("Monthly Income (RM)", 0.0, 6000.0, step=100.0, help="Your total monthly income.")
    rent = st.number_input("Monthly Rent (RM)", 0.0, 2000.0, step=50.0, help="Your monthly rent payment.")
    ratio = st.number_input("Rent ratio threshold", 0.0, 1.0, 0.38, step=0.01)

    run = st.button("✅ Run Check", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("Results")
    st.info("Click **Run Check** to show results.")
    st.markdown("</div>", unsafe_allow_html=True)

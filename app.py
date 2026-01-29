# app.py
import math
import pandas as pd
import streamlit as st

# ==========================================================
# Rental Affordability Checker (English UI)
# ----------------------------------------------------------
# Condition A (Logistic model):
#   z = SUM(COEF * INPUT)   <-- EXACTLY sum of COEF×INPUT column
#   p = 1 / (1 + exp(-z))
#   Afford if p >= 0.5
#
# Condition B (Rent-to-Income rule):
#   Afford if Rent <= ratio * Income   (default ratio = 0.38)
#
# Overall:
#   Afford only if BOTH conditions are Afford
# ==========================================================

st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# -------------------- COEFFICIENTS (from your Excel) --------------------
COEF = {
    "Umur": -0.006,
    "Jantina ketua keluarga(1)": 0.04,
    "Warganegara(1)": -2.49,

    "Bangsa(1)": -1.222,
    "Bangsa(2)": -1.693,
    "Bangsa(3)": 17.641,
    "Bangsa(4)": 1.828,

    "Agama(1)": -0.291,
    "Agama(2)": -15.98,
    "Agama(3)": 0.175,

    "Status Perkahwinan(1)": -25.465,
    "Status Perkahwinan(2)": 1.468,
    "Status Perkahwinan(3)": -0.114,
    "Status Perkahwinan(4)": 20.673,

    "Tahap Pendidikan(1)": -0.292,
    "Tahap Pendidikan(2)": -0.27,
    "Tahap Pendidikan(3)": -0.371,
    "Tahap Pendidikan(4)": -22.714,
    "Tahap Pendidikan(5)": 20.045,
    "Tahap Pendidikan(6)": -1.436,
    "Tahap Pendidikan(7)": 18.556,
    "Tahap Pendidikan(8)": 30.823,

    "Pekerjaan(1)": -19.721,
    "Pekerjaan(2)": -20.39,
    "Pekerjaan(3)": -18.736,
    "Pekerjaan(4)": -20.434,
    "Pekerjaan(5)": -35.097,
    "Pekerjaan(6)": 0.085,

    "Bilangan isi rumah(1)": -0.392,
    "Bilangan isi rumah(2)": -0.398,
    "Bilangan isi rumah(3)": -0.012,
    "Bilangan isi rumah(4)": 0.158,

    "Bilangan tanggungan(1)": 0.729,
    "Bilangan tanggungan(2)": -1.316,
    "Bilangan tanggungan(3)": 20.145,
    "Bilangan tanggungan(4)": 17.796,

    "Jenis rumah sewa(1)": 0.307,
    "Jenis rumah sewa(2)": -0.493,
    "Jenis rumah sewa(3)": 0.579,
    "Jenis rumah sewa(4)": -0.331,
    "Jenis rumah sewa(5)": 18.194,

    "Jenis kelengkapan perabot(1)": -0.46,

    "Bayaran deposit(1)": 1.511,
    "Bayaran deposit(2)": 0.841,
    "Bayaran deposit(3)": 1.496,
    "Bayaran deposit(4)": 1.975,
    "Bayaran deposit(5)": -0.487,
    "Bayaran deposit(6)": 18.336,

    "Berapa lama anda telah menyewa rumah(1)": -17.564,
    "Berapa lama anda telah menyewa rumah(2)": -18.419,
    "Berapa lama anda telah menyewa rumah(3)": -17.135,
    "Berapa lama anda telah menyewa rumah(4)": -18.69,

    "Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)": 0.531,

    "Constant": 38.956,
}

# -------------------- ENGLISH OPTIONS (coded by index like your sheet) --------------------
OPTIONS = {
    "Gender": ["Man", "Woman"],  # dummy(1)=1 if Woman
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],  # dummy(1)=1 if Non-Malaysian

    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],  # 0..4 -> dummies (1..4)
    "Religion": ["Islam", "Buddhism", "Hinduism", "Others"],          # 0..3 -> dummies (1..3)
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],  # 0..4 -> dummies (1..4)

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
    ],  # 0..8 -> dummies (1..8)

    "Occupation": [
        "Unemployed",
        "Government employee",
        "Private employee",
        "Self-employed",
        "Homemaker",
        "Student",
        "Government retiree",
    ],  # 0..6 -> dummies (1..6)

    "Household Size": ["1 person", "2 people", "3–4 people", "5–6 people", "7 people or more"],  # 0..4 -> dummies (1..4)
    "Number of Dependents": ["None", "1–2 people", "3–4 people", "5–6 people", "7 people or more"],  # 0..4 -> dummies (1..4)

    "Type of Rental Housing": [
        "House",
        "Room",
        "Flat",
        "Apartment",
        "Condominium",
        "Terrace House (Single storey)",
        "Terrace House (Double storey)",
        "One-unit house",
    ],  # 0..7 -> model has dummies (1..5) only; others treated as base

    "Furnished Type": ["None", "Furnished"],  # dummy(1)=1 if Furnished

    "Deposit": [
        "No deposit",
        "1 + 1",
        "2 + 1",
        "3 + 1",
        "1 + 1 + utility",
        "2 + 1 + utility",
        "3 + 1 + utility",
    ],  # 0..6 -> dummies (1..6)

    "Total years renting": ["Less than 6 months", "Less than 1 year", "1–2 years", "3–5 years", "6–10 years"],  # 0..4 -> dummies (1..4)

    "Known SMART SEWA": ["Yes", "No"],  # dummy(1)=1 if No
}

# -------------------- logistic (stable) --------------------
def logistic(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)

# -------------------- Build INPUTs (age + dummies + constant=1) --------------------
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
    rental_idx: int,
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

    for k in range(1, 5):
        inp[f"Bangsa({k})"] = 1.0 if ethnicity_idx == k else 0.0

    for k in range(1, 4):
        inp[f"Agama({k})"] = 1.0 if religion_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Status Perkahwinan({k})"] = 1.0 if marital_idx == k else 0.0

    for k in range(1, 9):
        inp[f"Tahap Pendidikan({k})"] = 1.0 if edu_idx == k else 0.0

    for k in range(1, 7):
        inp[f"Pekerjaan({k})"] = 1.0 if job_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Bilangan isi rumah({k})"] = 1.0 if household_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Bilangan tanggungan({k})"] = 1.0 if dep_idx == k else 0.0

    # Model has Jenis rumah sewa(1..5). If user picks idx 6/7 => treated as base (all zeros)
    for k in range(1, 6):
        inp[f"Jenis rumah sewa({k})"] = 1.0 if rental_idx == k else 0.0

    inp["Jenis kelengkapan perabot(1)"] = 1.0 if furnish_idx == 1 else 0.0

    for k in range(1, 7):
        inp[f"Bayaran deposit({k})"] = 1.0 if deposit_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Berapa lama anda telah menyewa rumah({k})"] = 1.0 if years_idx == k else 0.0

    # (1) means "No" per your dummy
    inp["Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)"] = 1.0 if smart_idx == 1 else 0.0

    return inp

# -------------------- Compute table + z + p --------------------
def compute_table(inputs: dict):
    rows = []
    for var, coef in COEF.items():
        x = float(inputs.get(var, 0.0))
        rows.append(
            {
                "Variable": var,
                "COEF": float(coef),
                "INPUT": x,
                "COEF×INPUT": float(coef) * x,
            }
        )
    df = pd.DataFrame(rows)
    z = float(df["COEF×INPUT"].sum())  # IMPORTANT: EXACT SUM OF COLUMN
    p = float(logistic(z))
    return df, z, p

# ======================== TOP BAR (HEADER REMOVED TO AVOID OVERLAP) ========================
# keep ONLY the toggle at top-right (no title/caption)
_, top_r = st.columns([0.78, 0.22], vertical_alignment="center")
with top_r:
    dark_mode = st.toggle("Dark mode", value=True)

# ======================== THEME ========================
if dark_mode:
    PAGE_BG = "linear-gradient(180deg, #0b0b14 0%, #0b0b14 45%, #1a102b 100%)"
    CARD_BG = "rgba(17, 24, 39, 0.68)"
    BORDER = "rgba(167, 139, 250, 0.22)"
    TXT = "#f8fafc"     # white
    DF_TXT = "#e5e7eb"  # dataframe text
    MUTED = "rgba(248,250,252,.75)"
else:
    PAGE_BG = "linear-gradient(180deg, #f7f2ff 0%, #f7f2ff 45%, #efe6ff 100%)"
    CARD_BG = "rgba(255,255,255,0.84)"
    BORDER = "rgba(139, 92, 246, 0.20)"
    TXT = "#111827"     # black
    DF_TXT = "#111827"
    MUTED = "rgba(17,24,39,.70)"

st.markdown(
    f"""
<style>
  .stApp {{
    background: {PAGE_BG} !important;
    color: {TXT} !important;
  }}
  .block-container {{ padding-top: .35rem; }}

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
  .muted {{ color: {MUTED} !important; }}

  .chip {{
    display:inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 800;
    font-size: 12px;
    border: 1px solid rgba(17,24,39,.12);
    background: rgba(255,255,255,.78);
    color: #111827 !important;
  }}
  .chip.ok {{
    border-color: rgba(16,185,129,.35);
    color: #065f46 !important;
    background: rgba(209,250,229,.90);
  }}
  .chip.no {{
    border-color: rgba(239,68,68,.35);
    color: #7f1d1d !important;
    background: rgba(254,226,226,.92);
  }}

  /* DataFrame text color */
  div[data-testid="stDataFrame"] * {{
    color: {DF_TXT} !important;
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
        gender = st.selectbox("Gender", OPTIONS["Gender"], index=0)
        nationality = st.selectbox("Nationality", OPTIONS["Nationality"], index=0)
        ethnicity = st.selectbox("Ethnicity", OPTIONS["Ethnicity"], index=0)
        religion = st.selectbox("Religion", OPTIONS["Religion"], index=0)
        marital = st.selectbox("Marital Status", OPTIONS["Marital Status"], index=0)
        edu = st.selectbox("Education Level", OPTIONS["Education Level"], index=0)

    with colB:
        job = st.selectbox("Occupation", OPTIONS["Occupation"], index=0)
        household = st.selectbox("Household Size", OPTIONS["Household Size"], index=0)
        dependents = st.selectbox("Number of Dependents", OPTIONS["Number of Dependents"], index=0)
        rental = st.selectbox("Type of Rental Housing", OPTIONS["Type of Rental Housing"], index=0)
        furnished = st.selectbox("Furnished Type", OPTIONS["Furnished Type"], index=0)
        deposit = st.selectbox("Deposit", OPTIONS["Deposit"], index=0)
        years = st.selectbox("Total years renting", OPTIONS["Total years renting"], index=0)
        smart = st.selectbox("Known SMART SEWA", OPTIONS["Known SMART SEWA"], index=0)

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
        rental_idx=OPTIONS["Type of Rental Housing"].index(rental),
        furnish_idx=OPTIONS["Furnished Type"].index(furnished),
        deposit_idx=OPTIONS["Deposit"].index(deposit),
        years_idx=OPTIONS["Total years renting"].index(years),
        smart_idx=OPTIONS["Known SMART SEWA"].index(smart),
    )

    df, z, p = compute_table(inputs)

    ok_a = p >= 0.5
    cond_a = "Afford" if ok_a else "Not Afford"

    threshold = ratio * income
    ok_b = rent <= threshold
    cond_b = "Afford" if ok_b else "Not Afford"

    ok_all = ok_a and ok_b
    overall = "Afford" if ok_all else "Not Afford"

    st.session_state["result"] = {
        "df": df,
        "z": z,
        "p": p,
        "threshold": threshold,
        "ratio": ratio,
        "income": income,
        "rent": rent,
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
        st.markdown(
            f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:10px;">
  <div><b>Condition A (p ≥ 0.5)</b>: {chip(res["cond_a"], res["ok_a"])}</div>
  <div><b>Condition B (Rent ≤ {res["ratio"]:.2f}×Income)</b>: {chip(res["cond_b"], res["ok_b"])}</div>
  <div><b>Overall</b>: {chip(res["overall"], res["ok_all"])}</div>
</div>
""",
            unsafe_allow_html=True,
        )

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
            """
**Rules used**
- Condition A: `IF( p >= 0.5 , "Afford" , "Not Afford")`
- Condition B: `IF( Rent <= ratio×Income , "Afford" , "Not Afford")`
- Overall: `IF( AND(ConditionA, ConditionB) , "Afford" , "Not Afford")`
"""
        )
        st.markdown("</div>", unsafe_allow_html=True)

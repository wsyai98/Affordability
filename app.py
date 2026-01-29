# app.py
import math
import pandas as pd
import streamlit as st

# ==========================================================
# Rental Affordability Checker (Logit + Rent-to-Income rule)
# - Condition A: p = 1/(1+exp(-z)) >= 0.5
# - Condition B: Rent <= ratio * Income  (default ratio = 0.38)
# - Overall: Afford only if BOTH A and B are satisfied
# ==========================================================

st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# ---------- Model coefficients (as provided) ----------
COEF = {
    "Age": -0.006,
    "Gender (Female=1)": 0.04,
    "Nationality (Non-Malaysian=1)": -2.49,

    "Ethnicity(1)": -1.222,
    "Ethnicity(2)": -1.693,
    "Ethnicity(3)": 17.641,
    "Ethnicity(4)": 1.828,

    "Religion(1)": -0.291,
    "Religion(2)": -15.98,
    "Religion(3)": 0.175,

    "Marital Status(1)": -25.465,
    "Marital Status(2)": 1.468,
    "Marital Status(3)": -0.114,
    "Marital Status(4)": 20.673,

    "Education Level(1)": -0.292,
    "Education Level(2)": -0.27,
    "Education Level(3)": -0.371,
    "Education Level(4)": -22.714,
    "Education Level(5)": 20.045,
    "Education Level(6)": -1.436,
    "Education Level(7)": 18.556,
    "Education Level(8)": 30.823,

    "Occupation(1)": -19.721,
    "Occupation(2)": -20.39,
    "Occupation(3)": -18.736,
    "Occupation(4)": -20.434,
    "Occupation(5)": -35.097,
    "Occupation(6)": 0.085,

    "Household Size(1)": -0.392,
    "Household Size(2)": -0.398,
    "Household Size(3)": -0.012,
    "Household Size(4)": 0.158,

    "Dependents(1)": 0.729,
    "Dependents(2)": -1.316,
    "Dependents(3)": 20.145,
    "Dependents(4)": 17.796,

    "Rental Type(1)": 0.307,
    "Rental Type(2)": -0.493,
    "Rental Type(3)": 0.579,
    "Rental Type(4)": -0.331,
    "Rental Type(5)": 18.194,

    "Furnishing (Furnished=1)": -0.46,

    "Deposit(1)": 1.511,
    "Deposit(2)": 0.841,
    "Deposit(3)": 1.496,
    "Deposit(4)": 1.975,
    "Deposit(5)": -0.487,
    "Deposit(6)": 18.336,

    "Years Renting(1)": -17.564,
    "Years Renting(2)": -18.419,
    "Years Renting(3)": -17.135,
    "Years Renting(4)": -18.69,

    "Knows SMART SEWA (No=1)": 0.531,

    "Constant": 38.956,
}

# ---------- UI options (English) ----------
OPTIONS = {
    "Gender": ["Male", "Female"],  # Female -> (1)
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],  # Non-Malaysian -> (1)

    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],  # dummies (1..4) for indices 1..4
    "Religion": ["Islam", "Buddhism", "Hinduism", "Others"],          # dummies (1..3) for indices 1..3
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],  # dummies (1..4)
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
    ],  # dummies (1..8)

    "Occupation": [
        "Unemployed",
        "Government employee",
        "Private employee",
        "Self-employed",
        "Homemaker",
        "Student",
        "Government retiree",
    ],  # dummies (1..6)

    "Household Size": ["1 person", "2 people", "3–4 people", "5–6 people", "7 people or more"],  # dummies (1..4)
    "Dependents": ["None", "1–2 people", "3–4 people", "5–6 people", "7 people or more"],       # dummies (1..4)

    "Rental Type": [
        "House",
        "Room",
        "Flat",
        "Apartment",
        "Condominium",
        "Terrace House (Single storey)",
        "Terrace House (Double storey)",
        "One-unit house",
    ],  # model has (1..5). indices 1..5 map to those; others treated as base.

    "Furnishing": ["Not furnished", "Furnished"],  # Furnished -> (1)

    "Deposit": [
        "No deposit",
        "1 + 1",
        "2 + 1",
        "3 + 1",
        "1 + 1 + utility",
        "2 + 1 + utility",
        "3 + 1 + utility",
    ],  # dummies (1..6)

    "Years Renting": ["Less than 6 months", "Less than 1 year", "1–2 years", "3–5 years", "6–10 years"],  # dummies (1..4)

    "Knows SMART SEWA": ["Yes", "No"],  # No -> (1) (assumption)
}

# ---------- Theme (Light/Dark) ----------
with st.sidebar:
    st.markdown("### Theme")
    dark_mode = st.toggle("Dark mode", value=False)
    st.markdown("---")
    st.caption("Tip: In dark mode, text becomes white for readability.")

if dark_mode:
    PAGE_BG = "linear-gradient(180deg, #0b0b14 0%, #0b0b14 40%, #1a102b 100%)"
    SIDEBAR_BG = "rgba(167, 139, 250, 0.10)"
    CARD_BG = "rgba(17, 24, 39, 0.62)"
    BORDER = "rgba(167, 139, 250, 0.22)"
    TXT = "#f8fafc"
    SUB = "rgba(248,250,252,.72)"
else:
    PAGE_BG = "linear-gradient(180deg, #f7f2ff 0%, #f7f2ff 40%, #efe6ff 100%)"
    SIDEBAR_BG = "rgba(139, 92, 246, 0.07)"
    CARD_BG = "rgba(255,255,255,0.78)"
    BORDER = "rgba(139, 92, 246, 0.20)"
    TXT = "#2e1065"
    SUB = "rgba(46,16,101,.72)"

st.markdown(
    f"""
<style>
  .stApp{{ background: {PAGE_BG} !important; color: {TXT}; }}
  [data-testid="stSidebar"]{{
    background: {SIDEBAR_BG} !important;
    border-right: 1px solid {BORDER} !important;
  }}
  .block-container{{ padding-top: 1.2rem; }}
  h1,h2,h3,h4,h5,h6, label, p, div, span, small {{ color: {TXT}; }}

  .purple-card{{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 16px 16px;
    box-shadow: 0 12px 30px rgba(76, 29, 149, 0.10);
  }}
  .purple-title{{ font-weight: 900; letter-spacing: .2px; color: {TXT}; font-size: 28px; margin: 0 0 6px 0; }}
  .purple-sub{{ color: {SUB}; margin: 0; }}

  .chip{{ display:inline-block; padding: 6px 12px; border-radius: 999px; font-weight: 800; font-size: 12px;
          border: 1px solid rgba(17,24,39,.12); background: rgba(255,255,255,.75); color: #111827; }}
  .chip.ok{{ border-color: rgba(16,185,129,.35); color: #065f46; background: rgba(209,250,229,.85); }}
  .chip.no{{ border-color: rgba(239,68,68,.35); color: #7f1d1d; background: rgba(254,226,226,.90); }}

  /* Make dataframe text readable in dark mode too */
  div[data-testid="stDataFrame"] * {{
    color: {"#e5e7eb" if dark_mode else "#111827"} !important;
  }}
</style>
""",
    unsafe_allow_html=True,
)

def chip(label: str, ok: bool) -> str:
    cls = "ok" if ok else "no"
    return f'<span class="chip {cls}">{label}</span>'

def logistic(z: float) -> float:
    # stable logistic
    if z >= 0:
        ez = math.exp(-z)
        return 1 / (1 + ez)
    ez = math.exp(z)
    return ez / (1 + ez)

def build_inputs(
    *,
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
    """
    Build INPUTs:
    - base level index 0 => all zeros
    - if user selects level k (k>=1), then corresponding (k)=1 when available in model
    """
    inp = {k: 0.0 for k in COEF.keys()}
    inp["Constant"] = 1.0
    inp["Age"] = float(age)

    inp["Gender (Female=1)"] = 1.0 if gender_idx == 1 else 0.0
    inp["Nationality (Non-Malaysian=1)"] = 1.0 if nationality_idx == 1 else 0.0

    for k in range(1, 5):
        inp[f"Ethnicity({k})"] = 1.0 if ethnicity_idx == k else 0.0

    for k in range(1, 4):
        inp[f"Religion({k})"] = 1.0 if religion_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Marital Status({k})"] = 1.0 if marital_idx == k else 0.0

    for k in range(1, 9):
        inp[f"Education Level({k})"] = 1.0 if edu_idx == k else 0.0

    for k in range(1, 7):
        inp[f"Occupation({k})"] = 1.0 if job_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Household Size({k})"] = 1.0 if household_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Dependents({k})"] = 1.0 if dep_idx == k else 0.0

    # Rental Type: only (1..5) exist in coefficients
    for k in range(1, 6):
        inp[f"Rental Type({k})"] = 1.0 if rental_idx == k else 0.0

    inp["Furnishing (Furnished=1)"] = 1.0 if furnish_idx == 1 else 0.0

    for k in range(1, 7):
        inp[f"Deposit({k})"] = 1.0 if deposit_idx == k else 0.0

    for k in range(1, 5):
        inp[f"Years Renting({k})"] = 1.0 if years_idx == k else 0.0

    inp["Knows SMART SEWA (No=1)"] = 1.0 if smart_idx == 1 else 0.0

    return inp

def compute_all(user_inputs: dict) -> tuple[pd.DataFrame, float, float]:
    rows = []
    z = 0.0
    for var, coef in COEF.items():
        x = float(user_inputs.get(var, 0.0))
        prod = float(coef) * x
        z += prod
        rows.append({"Variable": var, "COEF": float(coef), "INPUT": x, "COEF*INPUT": prod})
    p = logistic(z)
    return pd.DataFrame(rows), z, p

# ---------- Header ----------
st.markdown(
    """
<div class="purple-card">
  <div class="purple-title">Rental Affordability Checker</div>
  <p class="purple-sub">
    Two checks are applied: <b>Condition A</b> (Logistic model) and <b>Condition B</b> (Rent-to-Income rule).
    <b>Overall</b> = Afford only if both conditions are satisfied.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")

# ---------- Layout ----------
left, right = st.columns([1, 1.35], gap="large")

with left:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("User Inputs")

    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("Age (years)", min_value=15, max_value=100, value=38, step=1)
        gender = st.selectbox("Gender", OPTIONS["Gender"], index=0)
        nationality = st.selectbox("Nationality", OPTIONS["Nationality"], index=0)
        ethnicity = st.selectbox("Ethnicity", OPTIONS["Ethnicity"], index=0)
        religion = st.selectbox("Religion", OPTIONS["Religion"], index=0)
        marital = st.selectbox("Marital Status", OPTIONS["Marital Status"], index=0)
        education = st.selectbox("Education Level", OPTIONS["Education Level"], index=0)

    with c2:
        occupation = st.selectbox("Occupation", OPTIONS["Occupation"], index=0)
        household = st.selectbox("Household Size", OPTIONS["Household Size"], index=0)
        dependents = st.selectbox("Number of Dependents", OPTIONS["Dependents"], index=0)
        rental_type = st.selectbox("Rental Type", OPTIONS["Rental Type"], index=0)
        furnishing = st.selectbox("Furnishing", OPTIONS["Furnishing"], index=0)
        deposit = st.selectbox("Deposit", OPTIONS["Deposit"], index=0)
        years = st.selectbox("Years Renting", OPTIONS["Years Renting"], index=0)
        smart = st.selectbox("Knows SMART SEWA?", OPTIONS["Knows SMART SEWA"], index=0)

    st.divider()
    st.subheader("Income & Rent Inputs")
    c3, c4, c5 = st.columns(3)
    with c3:
        income = st.number_input("Monthly Income (RM)", min_value=0.0, value=6000.0, step=100.0)
    with c4:
        rent = st.number_input("Monthly Rent (RM)", min_value=0.0, value=2000.0, step=50.0)
    with c5:
        ratio = st.number_input("Rent ratio threshold", min_value=0.0, max_value=1.0, value=0.38, step=0.01)

    run = st.button("✅ Run Check", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Only show results AFTER clicking Run ----------
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if run:
    user_inputs = build_inputs(
        age=int(age),
        gender_idx=OPTIONS["Gender"].index(gender),
        nationality_idx=OPTIONS["Nationality"].index(nationality),
        ethnicity_idx=OPTIONS["Ethnicity"].index(ethnicity),
        religion_idx=OPTIONS["Religion"].index(religion),
        marital_idx=OPTIONS["Marital Status"].index(marital),
        edu_idx=OPTIONS["Education Level"].index(education),
        job_idx=OPTIONS["Occupation"].index(occupation),
        household_idx=OPTIONS["Household Size"].index(household),
        dep_idx=OPTIONS["Dependents"].index(dependents),
        rental_idx=OPTIONS["Rental Type"].index(rental_type),
        furnish_idx=OPTIONS["Furnishing"].index(furnishing),
        deposit_idx=OPTIONS["Deposit"].index(deposit),
        years_idx=OPTIONS["Years Renting"].index(years),
        smart_idx=OPTIONS["Knows SMART SEWA"].index(smart),
    )

    df, z, p = compute_all(user_inputs)

    # Condition A
    ok_a = p >= 0.5
    cond_a = "Afford" if ok_a else "Not Afford"

    # Condition B
    threshold = ratio * income
    ok_b = rent <= threshold
    cond_b = "Afford" if ok_b else "Not Afford"

    # Overall
    ok_all = ok_a and ok_b
    overall = "Afford" if ok_all else "Not Afford"

    st.session_state["last_result"] = {
        "df": df,
        "z": z,
        "p": p,
        "threshold": threshold,
        "ratio": ratio,
        "income": income,
        "rent": rent,
        "cond_a": cond_a,
        "cond_b": cond_b,
        "overall": overall,
        "ok_a": ok_a,
        "ok_b": ok_b,
        "ok_all": ok_all,
    }

res = st.session_state["last_result"]

with right:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("Results")

    if res is None:
        st.info("Click **Run Check** to generate results and the calculation table.")
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

        c1, c2, c3 = st.columns(3)
        c1.metric("SUM COEF*INPUT (z)", f'{res["z"]:.6f}')
        c2.metric("Probability p = 1/(1+exp(-z))", f'{res["p"]:.9f}')
        c3.metric(f"{res['ratio']:.2f} × Income (RM)", f'{res["threshold"]:.2f}')

        st.write("")
        st.caption("Calculation table (COEF, INPUT, COEF×INPUT):")
        st.dataframe(res["df"], use_container_width=True, height=520)

        csv = res["df"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Calculation Table (CSV)",
            data=csv,
            file_name="affordability_calculation.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.write("")
        st.markdown(
            """
**Rules used**
- Condition A: `IF( p >= 0.5 , "Afford" , "Not Afford")`
- Condition B: `IF( Rent <= ratio×Income , "Afford" , "Not Afford")`
- Overall: `IF( AND(ConditionA, ConditionB) , "Afford" , "Not Afford")`
"""
        )
        st.markdown("</div>", unsafe_allow_html=True)

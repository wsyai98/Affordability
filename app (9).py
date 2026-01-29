# app.py
import math
import pandas as pd
import streamlit as st

# ==========================================================
# Soft Purple Rental Affordability Checker (Logit + 0.38 rule)
# ==========================================================

st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# ---------- Soft purple styling ----------
st.markdown(
    """
<style>
  .stApp{
    background: linear-gradient(180deg, #f7f2ff 0%, #f7f2ff 40%, #efe6ff 100%) !important;
  }
  [data-testid="stSidebar"]{
    background: rgba(139, 92, 246, 0.07) !important;
    border-right: 1px solid rgba(139, 92, 246, 0.18) !important;
  }
  .block-container{ padding-top: 1.2rem; }

  /* cards */
  .purple-card{
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(139, 92, 246, 0.20);
    border-radius: 18px;
    padding: 16px 16px;
    box-shadow: 0 12px 30px rgba(76, 29, 149, 0.08);
  }
  .purple-title{
    font-weight: 900;
    letter-spacing: .2px;
    color: #2e1065;
    font-size: 28px;
    margin: 0 0 6px 0;
  }
  .purple-sub{
    color: rgba(46,16,101,.72);
    margin: 0 0 0 0;
  }

  /* result chips */
  .chip{
    display:inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 12px;
    border: 1px solid rgba(17,24,39,.12);
    background: rgba(255,255,255,.75);
  }
  .chip.ok{ border-color: rgba(16,185,129,.35); color: #065f46; background: rgba(209,250,229,.8); }
  .chip.no{ border-color: rgba(239,68,68,.35); color: #7f1d1d; background: rgba(254,226,226,.85); }

  /* tidy tables */
  .stDataFrame, div[data-testid="stTable"] { border-radius: 14px; overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Model coefficients (as provided) ----------
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

# ---------- Category options (based on your coding table) ----------
OPTIONS = {
    "Gender": ["Man", "Woman"],  # dummy: Woman -> (1)
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],  # dummy: Non-Malaysian -> (1)

    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],  # dummies 1..4
    "Religion": ["Islam", "Buddha", "Hindu", "Others"],  # dummies 1..3
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],  # dummies 1..4
    "Level of Education": [
        "No certificate",
        "UPSR",
        "PT3",
        "SPM",
        "STPM",
        "SIJIL/TVET",
        "Sijil Politeknik/Universiti",
        "Diploma",
        "Bachelor's Degree",
    ],  # dummies 1..8

    "Occupation": [
        "tidak bekerja",
        "pekerja kerajaan",
        "pekerja swasta",
        "bekerja sendiri",
        "suri rumah",
        "pelajar",
        "pesara kerajaan",
    ],  # dummies 1..6

    "No household": ["1 org", "2 people", "3 - 4 people", "5 - 6 people", "7 people or more"],  # dummies 1..4
    "Number of dependent": ["None", "1 - 2 people", "3 - 4 people", "5 - 6 people", "7 people or more"],  # dummies 1..4

    "Type of rental Housing": [
        "House",
        "Room",
        "Flat",
        "Apartment",
        "Condominium",
        "Terrace House - Single storey",
        "Terrace House - Double storey",
        "1 unit House",
    ],  # model has (1..5). We'll map first 6 levels to (base + 1..5) and keep last 2 as base by default.

    "Furnished type": [
        "None",
        "furnished",
        "1 + 1",
        "2 + 1",
        "3 + 1",
        "1 + 1 + utility",
        "2 + 1 + utility",
        "3 + 1 + utility",
    ],  # model has only (1). We'll map "furnished" -> (1), others -> base by default.

    "deposit": [
        "tiada",
        "1 + 1",
        "2 + 1",
        "3 + 1",
        "1 + 1 + utility",
        "2 + 1 + utility",
        "3 + 1 + utility",
    ],  # dummies 1..6

    "Total year of rental": ["Less than 6 months", "Less than 1 year", "1 - 2 years", "3 - 5 years", "6 - 10 years"],  # dummies 1..4

    "known SMART SEWA": ["Yes", "No"],  # dummy: No -> (1) (assumption)
}


def one_hot_inputs(
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
    furnished_idx: int,
    deposit_idx: int,
    years_idx: int,
    smart_idx: int,
) -> dict:
    """
    Build the INPUT column exactly like your Excel:
    - Continuous: Umur uses the numeric age.
    - Categorical: base level (index 0) => all zeros; other levels => corresponding (k) = 1.
    Notes:
    - Some variables in your coefficient list exist only for certain levels (e.g., furnished has only (1)).
      We keep the rest as 0, matching your provided coefficients.
    """
    inp = {k: 0.0 for k in COEF.keys()}
    inp["Constant"] = 1.0
    inp["Umur"] = float(age)

    # Gender: Woman -> (1)
    inp["Jantina ketua keluarga(1)"] = 1.0 if gender_idx == 1 else 0.0

    # Nationality: Non-Malaysian -> (1)
    inp["Warganegara(1)"] = 1.0 if nationality_idx == 1 else 0.0

    # Ethnicity dummies (1..4) for indices 1..4
    for k in range(1, 5):
        inp[f"Bangsa({k})"] = 1.0 if ethnicity_idx == k else 0.0

    # Religion dummies (1..3) for indices 1..3
    for k in range(1, 4):
        inp[f"Agama({k})"] = 1.0 if religion_idx == k else 0.0

    # Marital dummies (1..4) for indices 1..4
    for k in range(1, 5):
        inp[f"Status Perkahwinan({k})"] = 1.0 if marital_idx == k else 0.0

    # Education dummies (1..8) for indices 1..8
    for k in range(1, 9):
        inp[f"Tahap Pendidikan({k})"] = 1.0 if edu_idx == k else 0.0

    # Occupation dummies (1..6) for indices 1..6
    for k in range(1, 7):
        inp[f"Pekerjaan({k})"] = 1.0 if job_idx == k else 0.0

    # Household size dummies (1..4) for indices 1..4
    for k in range(1, 5):
        inp[f"Bilangan isi rumah({k})"] = 1.0 if household_idx == k else 0.0

    # Dependents dummies (1..4) for indices 1..4
    for k in range(1, 5):
        inp[f"Bilangan tanggungan({k})"] = 1.0 if dep_idx == k else 0.0

    # Rental type: your coefficients exist only for (1..5).
    # We'll map:
    #   idx 0 -> base (all 0)
    #   idx 1..5 -> Jenis rumah sewa(1..5)
    #   idx 6..7 -> treat as base (all 0) unless you later provide extra coefficients.
    for k in range(1, 6):
        inp[f"Jenis rumah sewa({k})"] = 1.0 if rental_idx == k else 0.0

    # Furnished: only (1) exists in coefficient list.
    # We'll map "furnished" (idx=1) -> (1), others -> 0.
    inp["Jenis kelengkapan perabot(1)"] = 1.0 if furnished_idx == 1 else 0.0

    # Deposit dummies (1..6) for indices 1..6
    for k in range(1, 7):
        inp[f"Bayaran deposit({k})"] = 1.0 if deposit_idx == k else 0.0

    # Years renting dummies (1..4) for indices 1..4
    for k in range(1, 5):
        inp[f"Berapa lama anda telah menyewa rumah({k})"] = 1.0 if years_idx == k else 0.0

    # SMART SEWA known: assume "No" -> (1)
    inp["Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)"] = (
        1.0 if smart_idx == 1 else 0.0
    )

    return inp


def logistic(z: float) -> float:
    # stable logistic
    if z >= 0:
        ez = math.exp(-z)
        return 1 / (1 + ez)
    else:
        ez = math.exp(z)
        return ez / (1 + ez)


def chip(label: str, ok: bool) -> str:
    cls = "ok" if ok else "no"
    return f'<span class="chip {cls}">{label}</span>'


# ---------- Header ----------
st.markdown(
    """
<div class="purple-card">
  <div class="purple-title">Rental Affordability Checker</div>
  <p class="purple-sub">
    Two checks are applied:
    <b>Condition A</b> (Logistic model) and <b>Condition B</b> (Rent ≤ 0.38×Income).  
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
        age = st.number_input("Umur (Age)", min_value=15, max_value=100, value=38, step=1)
        gender = st.selectbox("Gender", OPTIONS["Gender"], index=0)
        nationality = st.selectbox("Nationality", OPTIONS["Nationality"], index=0)
        ethnicity = st.selectbox("Ethnicity", OPTIONS["Ethnicity"], index=0)
        religion = st.selectbox("Religion", OPTIONS["Religion"], index=0)
        marital = st.selectbox("Marital Status", OPTIONS["Marital Status"], index=0)
        education = st.selectbox("Level of Education", OPTIONS["Level of Education"], index=0)

    with c2:
        occupation = st.selectbox("Occupation", OPTIONS["Occupation"], index=0)
        household = st.selectbox("No household", OPTIONS["No household"], index=0)
        dependents = st.selectbox("Number of dependent", OPTIONS["Number of dependent"], index=0)
        rental_type = st.selectbox("Type of rental Housing", OPTIONS["Type of rental Housing"], index=0)
        furnished = st.selectbox("Furnished type", OPTIONS["Furnished type"], index=0)
        deposit = st.selectbox("deposit", OPTIONS["deposit"], index=0)
        years = st.selectbox("Total year of rental", OPTIONS["Total year of rental"], index=0)
        smart = st.selectbox("known SMART SEWA", OPTIONS["known SMART SEWA"], index=0)

    st.divider()
    st.subheader("Income & Rent Inputs")
    c3, c4, c5 = st.columns(3)
    with c3:
        income = st.number_input("Income (RM)", min_value=0.0, value=6000.0, step=100.0)
    with c4:
        rent = st.number_input("House Rent (RM)", min_value=0.0, value=2000.0, step=50.0)
    with c5:
        ratio = st.number_input("Rent ratio (default 0.38)", min_value=0.0, max_value=1.0, value=0.38, step=0.01)

    run = st.button("✅ Check Affordability", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Compute ----------
def compute_all():
    inp = one_hot_inputs(
        age=int(age),
        gender_idx=OPTIONS["Gender"].index(gender),
        nationality_idx=OPTIONS["Nationality"].index(nationality),
        ethnicity_idx=OPTIONS["Ethnicity"].index(ethnicity),
        religion_idx=OPTIONS["Religion"].index(religion),
        marital_idx=OPTIONS["Marital Status"].index(marital),
        edu_idx=OPTIONS["Level of Education"].index(education),
        job_idx=OPTIONS["Occupation"].index(occupation),
        household_idx=OPTIONS["No household"].index(household),
        dep_idx=OPTIONS["Number of dependent"].index(dependents),
        rental_idx=OPTIONS["Type of rental Housing"].index(rental_type),
        furnished_idx=OPTIONS["Furnished type"].index(furnished),
        deposit_idx=OPTIONS["deposit"].index(deposit),
        years_idx=OPTIONS["Total year of rental"].index(years),
        smart_idx=OPTIONS["known SMART SEWA"].index(smart),
    )

    rows = []
    z = 0.0
    for k, coef in COEF.items():
        x = float(inp.get(k, 0.0))
        prod = float(coef) * x
        z += prod
        rows.append({"Variable": k, "COEF": float(coef), "INPUT": x, "COEF*INPUT": prod})

    p = logistic(z)

    # Condition A
    cond_a_ok = p >= 0.5
    cond_a = "Afford" if cond_a_ok else "Not Afford"

    # Condition B
    threshold = ratio * income
    cond_b_ok = rent <= threshold
    cond_b = "Afford" if cond_b_ok else "Not Afford"

    # Overall
    overall_ok = cond_a_ok and cond_b_ok
    overall = "Afford" if overall_ok else "Not Afford"

    df = pd.DataFrame(rows)
    return df, z, p, threshold, cond_a, cond_b, overall, cond_a_ok, cond_b_ok, overall_ok

df, z, p, thr, cond_a, cond_b, overall, ok_a, ok_b, ok_all = compute_all()

with right:
    st.markdown('<div class="purple-card">', unsafe_allow_html=True)
    st.subheader("Results")

    st.markdown(
        f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:6px;">
  <div><b>Condition A (Logit ≥ 0.5)</b>: {chip(cond_a, ok_a)}</div>
  <div><b>Condition B (Rent ≤ {ratio:.2f}×Income)</b>: {chip(cond_b, ok_b)}</div>
  <div><b>Overall</b>: {chip(overall, ok_all)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("SUM COEF*INPUT (z)", f"{z:.6f}")
    c2.metric("Probability p = 1/(1+exp(-z))", f"{p:.9f}")
    c3.metric(f"{ratio:.2f} × Income (RM)", f"{thr:.2f}")

    st.write("")
    st.caption("Breakdown table (matches your Excel structure):")
    st.dataframe(df, use_container_width=True, height=520)

    # download
    csv = df.to_csv(index=False).encode("utf-8")
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
- Condition B: `IF( Rent <= 0.38×Income , "Afford" , "Not Afford")` (ratio adjustable)
- Overall: `IF( AND(ConditionA, ConditionB) , "Afford" , "Not Afford")`
""")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Auto-run hint ----------
if not run:
    st.info("Edit inputs on the left — results update automatically. Click **Check Affordability** if you want a clear action button for users.")


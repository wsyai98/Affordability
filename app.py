# app.py
import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rental Affordability Checker", layout="wide")

# ==========================================================
# MODEL DEFINITIONS
# ==========================================================

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

OPTIONS = {
    "Gender": ["Man", "Woman"],
    "Nationality": ["Malaysian citizen", "Non-Malaysian citizen"],
    "Ethnicity": ["Malay", "Chinese", "Indian", "Sabah", "Sarawak"],
    "Religion": ["Islam", "Buddhism", "Hinduism", "Others"],
    "Marital Status": ["Single", "Married", "Widowed", "Divorced", "Separated"],
    "Education Level": [
        "No certificate","UPSR","PT3","SPM","STPM",
        "Certificate/TVET","Certificate (Poly/Uni)","Diploma","Bachelor Degree"
    ],
    "Occupation": [
        "Unemployed","Government employee","Private employee",
        "Self-employed","Homemaker","Student","Government retiree"
    ],
    "Household Size": ["1 person","2 people","3–4 people","5–6 people","7+ people"],
    "Number of Dependents": ["None","1–2","3–4","5–6","7+"],
    "Type of Rental Housing": [
        "House","Room","Flat","Apartment","Condominium",
        "Terrace (1 storey)","Terrace (2 storey)","Single unit"
    ],
    "Furnished Type": ["None","Furnished"],
    "Deposit": [
        "No deposit","1+1","2+1","3+1",
        "1+1+utility","2+1+utility","3+1+utility"
    ],
    "Total years renting": ["<6 months","<1 year","1–2 years","3–5 years","6–10 years"],
    "Known SMART SEWA": ["Yes","No"],
}

# ==========================================================
# FUNCTIONS
# ==========================================================

def logistic(z):
    if z >= 0:
        ez = math.exp(-z)
        return 1/(1+ez)
    ez = math.exp(z)
    return ez/(1+ez)

def build_inputs(age, idx):
    inp = {k:0.0 for k in COEF}
    inp["Constant"] = 1
    inp["Umur"] = age

    inp["Jantina ketua keluarga(1)"] = 1 if idx["gender"]==1 else 0
    inp["Warganegara(1)"] = 1 if idx["nationality"]==1 else 0

    for k in range(1,5): inp[f"Bangsa({k})"] = 1 if idx["ethnicity"]==k else 0
    for k in range(1,4): inp[f"Agama({k})"] = 1 if idx["religion"]==k else 0
    for k in range(1,5): inp[f"Status Perkahwinan({k})"] = 1 if idx["marital"]==k else 0
    for k in range(1,9): inp[f"Tahap Pendidikan({k})"] = 1 if idx["edu"]==k else 0
    for k in range(1,7): inp[f"Pekerjaan({k})"] = 1 if idx["job"]==k else 0
    for k in range(1,5): inp[f"Bilangan isi rumah({k})"] = 1 if idx["household"]==k else 0
    for k in range(1,5): inp[f"Bilangan tanggungan({k})"] = 1 if idx["dependents"]==k else 0
    for k in range(1,6): inp[f"Jenis rumah sewa({k})"] = 1 if idx["rental"]==k else 0
    inp["Jenis kelengkapan perabot(1)"] = 1 if idx["furnished"]==1 else 0
    for k in range(1,7): inp[f"Bayaran deposit({k})"] = 1 if idx["deposit"]==k else 0
    for k in range(1,5): inp[f"Berapa lama anda telah menyewa rumah({k})"] = 1 if idx["years"]==k else 0
    inp["Adakah anda mengetahui terdapat skim mampu sewa di Malaysia? (contoh: SMART sewa)(1)"] = 1 if idx["smart"]==1 else 0
    return inp

def compute_table(inputs):
    rows=[]
    for v,c in COEF.items():
        x = inputs.get(v,0)
        rows.append({
            "Variable":v,
            "COEF":c,
            "INPUT":x,
            "COEF×INPUT":c*x
        })
    df = pd.DataFrame(rows)
    z = df["COEF×INPUT"].sum()     # EXACT
    p = logistic(z)
    return df,z,p

# ==========================================================
# TOP RIGHT DARK MODE BUTTON
# ==========================================================

_, col_toggle = st.columns([0.85,0.15])
with col_toggle:
    dark_mode = st.toggle("Dark mode", value=True)

# ==========================================================
# THEME
# ==========================================================

if dark_mode:
    bg = "#0b0b14"; card="#111827"; text="#f8fafc"
else:
    bg="#f6f2ff"; card="#ffffff"; text="#111827"

st.markdown(f"""
<style>
.stApp{{background:{bg}; color:{text};}}
.card{{background:{card}; padding:18px; border-radius:16px;}}
h1,h2,h3,h4,h5,h6,p,span,label,div{{color:{text}!important;}}
</style>
""",unsafe_allow_html=True)

# ==========================================================
# UI
# ==========================================================

left,right = st.columns([1,1.4], gap="large")

with left:
    st.markdown('<div class="card">',unsafe_allow_html=True)
    st.subheader("User Inputs")

    age = st.number_input("Age",15,100,38)
    gender = st.selectbox("Gender",OPTIONS["Gender"])
    nationality = st.selectbox("Nationality",OPTIONS["Nationality"])
    ethnicity = st.selectbox("Ethnicity",OPTIONS["Ethnicity"])
    religion = st.selectbox("Religion",OPTIONS["Religion"])
    marital = st.selectbox("Marital Status",OPTIONS["Marital Status"])
    edu = st.selectbox("Education Level",OPTIONS["Education Level"])
    job = st.selectbox("Occupation",OPTIONS["Occupation"])
    household = st.selectbox("Household Size",OPTIONS["Household Size"])
    dependents = st.selectbox("Number of Dependents",OPTIONS["Number of Dependents"])
    rental = st.selectbox("Type of Rental Housing",OPTIONS["Type of Rental Housing"])
    furnished = st.selectbox("Furnished Type",OPTIONS["Furnished Type"])
    deposit = st.selectbox("Deposit",OPTIONS["Deposit"])
    years = st.selectbox("Total years renting",OPTIONS["Total years renting"])
    smart = st.selectbox("Known SMART SEWA",OPTIONS["Known SMART SEWA"])

    st.subheader("Income & Rent")
    income = st.number_input("Monthly Income (RM)",0.0, value=6000.0, step=100.0)
    rent = st.number_input("Monthly Rent (RM)",0.0, value=2000.0, step=50.0)
    ratio = st.number_input("Rent ratio threshold",0.0,1.0,0.38,0.01)

    run = st.button("Run Check", use_container_width=True)
    st.markdown('</div>',unsafe_allow_html=True)

if "res" not in st.session_state:
    st.session_state.res=None

if run:
    idx={
        "gender":OPTIONS["Gender"].index(gender),
        "nationality":OPTIONS["Nationality"].index(nationality),
        "ethnicity":OPTIONS["Ethnicity"].index(ethnicity),
        "religion":OPTIONS["Religion"].index(religion),
        "marital":OPTIONS["Marital Status"].index(marital),
        "edu":OPTIONS["Education Level"].index(edu),
        "job":OPTIONS["Occupation"].index(job),
        "household":OPTIONS["Household Size"].index(household),
        "dependents":OPTIONS["Number of Dependents"].index(dependents),
        "rental":OPTIONS["Type of Rental Housing"].index(rental),
        "furnished":OPTIONS["Furnished Type"].index(furnished),
        "deposit":OPTIONS["Deposit"].index(deposit),
        "years":OPTIONS["Total years renting"].index(years),
        "smart":OPTIONS["Known SMART SEWA"].index(smart),
    }

    inputs = build_inputs(age,idx)
    df,z,p = compute_table(inputs)

    condA = p>=0.5
    condB = rent <= ratio*income
    overall = condA and condB

    st.session_state.res = {
        "df":df,"z":z,"p":p,
        "condA":condA,"condB":condB,"overall":overall,
        "threshold":ratio*income
    }

with right:
    st.markdown('<div class="card">',unsafe_allow_html=True)
    st.subheader("Results")

    if st.session_state.res is None:
        st.info("Click **Run Check** to view results.")
    else:
        r = st.session_state.res

        st.metric("SUM(COEF×INPUT)  (z)", f"{r['z']:.6f}")
        st.metric("Probability p", f"{r['p']:.9f}")
        st.metric("Rent Threshold (RM)", f"{r['threshold']:.2f}")

        st.write("Condition A (Logistic):", "Afford" if r["condA"] else "Not Afford")
        st.write("Condition B (Income Rule):", "Afford" if r["condB"] else "Not Afford")
        st.write("Overall:", "Afford" if r["overall"] else "Not Afford")

        st.dataframe(r["df"], use_container_width=True, height=520)

        st.download_button(
            "Download Calculation Table (CSV)",
            r["df"].to_csv(index=False),
            file_name="affordability_calc.csv"
        )

    st.markdown('</div>',unsafe_allow_html=True)

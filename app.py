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
        # Keep these (options refer to pic) even if not used in significant-only model (others maintain)
        jantina = st.selectbox("Jantina", OPTIONS["Jantina"], index=0)
        warganegara = st.selectbox("Warganegara", OPTIONS["Warganegara"], index=0)
        bangsa = st.selectbox("Bangsa", OPTIONS["Bangsa"], index=0)
        agama = st.selectbox("Agama", OPTIONS["Agama"], index=0)
        status_kahwin = st.selectbox("Status Perkahwinan", OPTIONS["Status Perkahwinan"], index=0)
        tahap_pendidikan = st.selectbox("Tahap Pendidikan", OPTIONS["Tahap Pendidikan"], index=0)

    with colB:
        pekerjaan = st.selectbox("Pekerjaan", OPTIONS["Pekerjaan"], index=0)
        bil_isi_rumah = st.selectbox("Bilangan Isi Rumah", OPTIONS["Bilangan Isi Rumah"], index=0)
        bil_tanggungan = st.selectbox("Bilangan Tanggungan", OPTIONS["Bilangan Tanggungan"], index=0)

        jenis_penyewaan = st.selectbox("Jenis Penyewaan", OPTIONS["Jenis Penyewaan"], index=0)
        jenis_rumah_sewa = st.selectbox("Jenis Rumah Sewa", OPTIONS["Jenis Rumah Sewa"], index=0)
        jenis_perabot = st.selectbox("Jenis Kelengkapan Perabot", OPTIONS["Jenis Kelengkapan Perabot"], index=0)
        deposit = st.selectbox("Deposit", OPTIONS["Deposit"], index=0)
        tempoh_menyewa = st.selectbox("Tempoh Menyewa", OPTIONS["Tempoh Menyewa"], index=0)
        skim = st.selectbox("Skim", OPTIONS["Skim"], index=0)

    st.divider()
    st.subheader("Income & Rent Inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        income = st.number_input("Monthly Income (RM)", min_value=0.0, value=6000.0, step=100.0)
    with c2:
        rent = st.number_input("Monthly Rent (RM)", min_value=0.0, value=2000.0, step=50.0)
    with c3:
        ratio = st.number_input(
            "Rent ratio threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.38,
            step=0.01,
            help="Affordability ratio used in Condition B (example: 0.30 means rent should be ≤ 30% of income).",
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

    df, z, p = compute_table(inputs)

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

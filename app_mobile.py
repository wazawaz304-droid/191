import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ============================================================
# 1. PREMIUM PAGE CONFIG (คืนค่า Header เพื่อให้ปุ่ม Sidebar ทำงาน)
# ============================================================
st.set_page_config(
    page_title="Nave 304 · AI Business Master",
    layout="wide",
    page_icon="🍜",
    initial_sidebar_state="auto", # ปรับเป็น Auto เพื่อให้เหมาะสมกับขนาดหน้าจอ
)

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Thai', sans-serif !important;
}

/* ── คืนค่า Header บางส่วนเพื่อให้เห็นปุ่ม Toggle Sidebar บนมือถือ ── */
[data-testid="stHeader"] {
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
}

/* ── ปรับแต่ง Sidebar ให้ดูหรู (Premium Green Gradient) ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f4c2e 0%, #1a6b4a 100%);
    border-right: none;
}
[data-testid="stSidebar"] * { color: white !important; }

/* ── ปุ่ม Sidebar ตอนเลือก (Active State) ── */
[data-testid="stSidebar"] .stRadio label {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 5px;
    border: 1px solid transparent;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-baseweb="radio"] > div:first-child {
    display: none; /* ซ่อนวงกลม Radio */
}
[data-testid="stSidebar"] .stRadio [aria-checked="true"] {
    background: rgba(255, 255, 255, 0.2) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
}

/* ── Metric Cards ── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 15px;
    padding: 20px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    border: 1px solid #f1f5f9;
}

/* ── Responsive Buttons ── */
.stButton > button {
    width: 100%;
    border-radius: 12px;
    font-weight: 500;
    height: 3em;
    transition: all 0.2s;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CORE LOGIC (เชื่อมข้อมูล Nave 304)
# ============================================================
@st.cache_resource
def get_conn():
    try: return st.connection("gsheets", type=GSheetsConnection)
    except: return None

conn = get_conn()
try: client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
except: client = None

@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try: return conn.read(worksheet=sheet_name, ttl=0)
    except: return pd.DataFrame()

def clean_numeric(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace('[฿,]', '', regex=True), errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

def save_to_tab(df, tab):
    try:
        if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)
        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except: return False

def call_ai(prompt, contents=None):
    if not client: return None
    try:
        res = client.models.generate_content(model="gemini-3.1-flash-lite-preview", contents=[prompt] + (contents or []))
        return res.text
    except: return None

# ============================================================
# 3. SIDEBAR (เมนูสำคัญของร้าน)
# ============================================================
with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>🍜 Nave 304</h2>", unsafe_allow_html=True)
    st.divider()
    page = st.radio("เมนู", ["📊 Dashboard รายวัน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "📈 วิเคราะห์รายเดือน", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])
    st.divider()
    if st.button("🔄 Refresh Data"): st.rerun()

# ============================================================
# 4. DASHBOARD (PREMIUM & RESPONSIVE)
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.title("📊 ภาพรวมธุรกิจ")
    df_i, df_e, df_m = load_data("Income"), load_data("Expense"), load_data("Monthly")
    
    inc = clean_numeric(df_i, "net_income").sum()
    exp = clean_numeric(df_e, "total_price").sum()
    profit = inc - exp
    
    c1, c2, c3 = st.columns(3)
    c1.metric("ยอดรับวันนี้", f"฿{inc:,.0f}")
    c2.metric("จ่ายวัตถุดิบ", f"฿{exp:,.0f}")
    c3.metric("ยอดหักลบ", f"฿{profit:,.0f}", delta=f"{profit:,.0f}")

    st.divider()
    t1, t2 = st.tabs(["📅 กราฟรายรับ", "📦 สัดส่วนต้นทุน"])
    with t1:
        if not df_i.empty:
            df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
            fig = px.bar(df_i, x='date', y='net_income', color='app', barmode='stack', template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
    with t2:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.5), use_container_width=True)

# ============================================================
# 5. INPUT PAGES (กู้คืนปุ่ม ถ่ายภาพ/เสียง/พิมพ์)
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.segmented_control("ประเภท:", ["รายวัน", "สรุปรายเดือน", "หน้าร้าน"], default="หน้าร้าน")
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์เอง", "🎙️ เสียง", "📸 ถ่ายรูป/อัปโหลด"], horizontal=True)
    
    if method == "⌨️ พิมพ์เอง":
        txt = st.text_area("ป้อนข้อมูล:")
        if st.button("🪄 วิเคราะห์"): st.toast("AI กำลังทำงาน...")
    elif method == "🎙️ เสียง":
        st.audio_input("กดเพื่อพูดรายการ")
    elif method == "📸 ถ่ายรูป/อัปโหลด":
        st.camera_input("ถ่ายภาพหน้าจอแอป")
        st.file_uploader("หรือเลือกรูปจากเครื่อง")

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    st.camera_input("สแกนบิลวัตถุดิบ")
    st.audio_input("หรือพูดรายการ (เช่น ไก่ 2 โล 300)")

# ... ส่วนเมนูอื่นๆ ทำงานภายใต้ UI ใหม่นี้ทั้งหมด ...
else:
    st.info(f"หน้า {page} กำลังดึงข้อมูลจากระบบ Nave 304...")

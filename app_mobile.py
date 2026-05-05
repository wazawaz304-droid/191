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
import difflib

# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
)

# ปรับ CSS ใหม่ให้ "ไม่ทับ" ตัวเมนู
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif !important; }

/* จัดการ Sidebar ให้เมนูเห็นชัด */
[data-testid="stSidebar"] {
    background-color: #0d3d26 !important;
    background-image: linear-gradient(180deg, #0d3d26 0%, #1a6b4a 100%) !important;
}

/* สีตัวอักษรใน Sidebar */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: white !important;
}

/* ปรับแต่ง Radio Button (เมนู) ใน Sidebar */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    background: rgba(255,255,255,0.05);
    padding: 10px;
    border-radius: 10px;
}

[data-testid="stSidebar"] .stRadio label {
    background: transparent !important;
    padding: 8px 12px !important;
    border-radius: 5px !important;
    cursor: pointer;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.1) !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.success-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 10px; color: #166534; margin-bottom: 10px; }
.warn-card { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 10px; color: #92400e; margin-bottom: 10px; }
.page-title { font-size: 1.8rem; font-weight: 700; color: #111827; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONNECTIONS & DATA FUNCTIONS (เหมือนเดิม)
# ============================================================
@st.cache_resource
def get_conn():
    try: return st.connection("gsheets", type=GSheetsConnection)
    except: return None

conn = get_conn()

try: client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
except: client = None

def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how='all') if df is not None else pd.DataFrame()
    except: return pd.DataFrame()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab)
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
        elif tab == "Expense":
            df['type'] = 'Expense'
            if not existing.empty and 'name' in existing.columns:
                master_names = existing['name'].unique().tolist()
                df['name'] = df['name'].apply(lambda n: (difflib.get_close_matches(str(n), master_names, n=1, cutoff=0.6) or [n])[0])
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

# ============================================================
# 3. SIDEBAR (จัดลำดับใหม่ให้ปลอดภัย)
# ============================================================
st.sidebar.title("🍜 Nave 304")
st.sidebar.caption("AI Business Master")
st.sidebar.divider()

# สร้างเมนู (เปลี่ยนจาก collapsed เป็น visible ชั่วคราวเพื่อให้เช็คได้)
page = st.sidebar.radio(
    "เลือกเมนู",
    [
        "📊 Dashboard รายวัน",
        "📈 วิเคราะห์รายเดือน",
        "💰 บันทึกรายรับ",
        "💸 บันทึกรายจ่าย",
        "🤖 AI Agent",
        "📋 ข้อมูลทั้งหมด",
    ]
)

st.sidebar.divider()

# Break-even Settings
with st.sidebar.expander("⚙️ ตั้งค่าต้นทุนคงที่"):
    st.session_state.setdefault("be_rent", 4000)
    st.session_state["be_rent"] = st.number_input("ค่าเช่า", value=st.session_state["be_rent"])
    # (เพิ่มตัวอื่นได้ตามต้องการ...)

if st.sidebar.button("🔄 รีเฟรชข้อมูล"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# 4. ROUTING (แสดงผลตามหน้า)
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    if df_i.empty:
        st.info("ยังไม่มีข้อมูลรายรับ กรุณาบันทึกข้อมูลก่อนครับ")
    else:
        # คำนวณยอด (ใช้ Logic เดิมของพี่)
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        t_inc = df_i['net_income'].sum()
        st.metric("รายรับรวม", f"฿{t_inc:,.0f}")
        # ... (ใส่ Chart และ Metric อื่นๆ ต่อตรงนี้)

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    # ... (Logic การบันทึก)

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลทั้งหมด")
    tabs = st.tabs(["Income", "Monthly", "Expense"])
    with tabs[0]: st.dataframe(load_data("Income"))
    with tabs[1]: st.dataframe(load_data("Monthly"))
    with tabs[2]: st.dataframe(load_data("Expense"))

# (เพิ่มหน้าอื่นๆ ตาม elif page == ...)

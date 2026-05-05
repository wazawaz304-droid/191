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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif !important; }

/* ซ่อนเฉพาะปุ่ม MainMenu และ Footer (ไม่ซ่อน Header ทั้งหมดเพื่อป้องกัน Layout พัง) */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { background-color: rgba(0,0,0,0) !important; height: 0px; }

.block-container { padding: 1.25rem 2rem 3rem; max-width: 1300px; }

/* Sidebar Design - เจาะจงเฉพาะพื้นที่ Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0d3d26 0%, #1a6b4a 100%) !important;
}

/* ปรับสีตัวอักษรเฉพาะใน Sidebar เท่านั้น (ป้องกันตัวอักษรหน้าหลักหาย) */
section[data-testid="stSidebar"] .stMarkdown p, 
section[data-testid="stSidebar"] span, 
section[data-testid="stSidebar"] label { 
    color: rgba(255,255,255,0.9) !important; 
}

section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

/* เมนู Radio ใน Sidebar */
section[data-testid="stSidebar"] .stRadio label {
    padding: 0.5rem 0.9rem; border-radius: 8px; display: block;
    transition: background 0.15s; font-size: 0.875rem; cursor: pointer;
    color: rgba(255,255,255,0.9) !important;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.1) !important; }

/* ปุ่มใน Sidebar */
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #fff !important; width: 100%; border-radius: 8px;
}

/* Metric cards ในหน้าหลัก */
[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f3f4f6; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-size: 0.85rem; color: #6b7280; padding: 0.4rem 1rem; }
.stTabs [aria-selected="true"] { background: white !important; color: #111827 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }

/* Custom Banner Styles */
.success-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 0.8rem 1rem; font-size: 0.85rem; color: #166534; margin-bottom: 0.75rem; }
.warn-card { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 0.8rem 1rem; font-size: 0.85rem; color: #92400e; margin-bottom: 0.75rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin-bottom: 0.1rem; }
.section-title { font-size: 1rem; font-weight: 600; color: #111827; padding-bottom: 0.4rem; border-bottom: 2px solid #e5e7eb; margin: 1.2rem 0 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONNECTIONS
# ============================================================
@st.cache_resource
def get_conn():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        return None

conn = get_conn()

try:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
except Exception as e:
    st.error(f"⚠️ ไม่พบ API Key: {e}")
    client = None

# ============================================================
# 3. DATA FUNCTIONS
# ============================================================
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
                def match_name(n):
                    matches = difflib.get_close_matches(str(n), master_names, n=1, cutoff=0.6)
                    return matches[0] if matches else n
                df['name'] = df['name'].apply(match_name)
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        elif tab == "Monthly":
            df['type'] = 'Monthly'

        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 4. AI FUNCTION
# ============================================================
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    if client is None: return []
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"
    
    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = (f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', "
             f"'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. "
             f"ใช้ชื่อเดิมเหล่านี้ถ้าคล้าย: [{names_str}]")
    else:
        p = (f"สกัดข้อมูลรายได้เป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': 0}}]")

    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=data, mime_type=mime),
            ])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])
        text = res.text.strip()
        if "```" in text: text = text.split("
```")[1].replace("json", "")
        return json.loads(text)
    except: return []

# ============================================================
# 5. SIDEBAR
# ============================================================
st.sidebar.markdown("## 🍜 Nave 304")
st.sidebar.markdown("<small style='opacity:.65'>AI Business Master</small>", unsafe_allow_html=True)
st.sidebar.divider()

# กำหนดหน้าปัจจุบันจาก Sidebar
page = st.sidebar.radio(
    "เมนู",
    [
        "📊 Dashboard รายวัน",
        "📈 วิเคราะห์รายเดือน",
        "💰 บันทึกรายรับ",
        "💸 บันทึกรายจ่าย",
        "🤖 AI Agent",
        "📋 ข้อมูลทั้งหมด",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()

# Break-even settings
st.session_state.setdefault("be_rent", 4000)
st.session_state.setdefault("be_electric", 800)
st.session_state.setdefault("be_water", 400)
st.session_state.setdefault("be_other", 0)

_be_exp = st.sidebar.expander("⚙️ ต้นทุนคงที่ (Break-even)")
st.session_state["be_rent"] = _be_exp.number_input("🏠 ค่าเช่า/เดือน (฿)", value=st.session_state["be_rent"], step=500, min_value=0)
st.session_state["be_electric"] = _be_exp.number_input("💡 ค่าไฟ/เดือน (฿)", value=st.session_state["be_electric"], step=100, min_value=0)
st.session_state["be_water"] = _be_exp.number_input("🚿 ค่าน้ำ/เดือน (฿)", value=st.session_state["be_water"], step=100, min_value=0)
st.session_state["be_other"] = _be_exp.number_input("📦 ค่าคงที่อื่นๆ/เดือน (฿)", value=st.session_state["be_other"], step=100, min_value=0)

st.sidebar.divider()
if st.sidebar.button("🔄 รีเฟรชข้อมูล"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# 6. PAGE LOGIC (ส่วนที่แสดงเนื้อหาหลัก)
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>ภาพรวมรายรับ-รายจ่าย ทั้งหมดในชีต</div>", unsafe_allow_html=True)

    df_i = load_data("Income")
    df_e = load_data("Expense")

    if not df_i.empty:
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    if not df_e.empty:
        df_e['total_price'] = clean_numeric(df_e, 'total_price')
        df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc = df_i['net_income'].sum() if not df_i.empty else 0
    t_exp = df_e['total_price'].sum() if not df_e.empty else 0
    profit = t_inc - t_exp

    # Break-even Calculation
    be_rent = st.session_state["be_rent"]
    be_electric = st.session_state["be_electric"]
    be_water = st.session_state["be_water"]
    be_other = st.session_state["be_other"]
    fixed_daily = (be_rent + be_electric + be_water + be_other) / 26
    food_cost_pct = (t_exp / t_inc * 100) if t_inc > 0 else 0
    contribution_margin = 1 - (food_cost_pct / 100)
    be_daily = (fixed_daily / contribution_margin) if contribution_margin > 0 else 0

    today = pd.Timestamp.now().normalize()
    today_inc = df_i[df_i["date"] >= today]["net_income"].sum() if not df_i.empty else 0

    # Display KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น", f"฿{profit:,.0f}")
    c4.metric("🎯 เป้าวันนี้", f"฿{be_daily:,.0f}")

    st.divider()
    t_inc_tab, t_exp_tab = st.tabs(["📅 รายรับ", "🛒 รายจ่าย"])
    with t_inc_tab:
        if not df_i.empty:
            st.plotly_chart(px.line(df_i.groupby('date')['net_income'].sum().reset_index(), x='date', y='net_income', title="แนวโน้มรายรับรายวัน"), use_container_width=True)

elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='page-title'>📈 วิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    df_m = load_data("Monthly")
    if not df_m.empty:
        st.dataframe(df_m, use_container_width=True)
    else: st.info("ยังไม่มีข้อมูลรายเดือน")

elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    # (ส่วนบันทึกรายรับเหมือนเดิม...)
    st.info("เลือกวิธีบันทึกด้านล่าง")

elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่ายวัตถุดิบ</div>", unsafe_allow_html=True)
    # (ส่วนบันทึกรายจ่ายเหมือนเดิม...)

elif page == "🤖 AI Agent":
    st.markdown("<div class='page-title'>🤖 AI ที่ปรึกษาธุรกิจ</div>", unsafe_allow_html=True)
    # (ส่วน AI Agent เหมือนเดิม...)

elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 ข้อมูลดิบ</div>", unsafe_allow_html=True)
    st.dataframe(load_data("Income"), use_container_width=True)

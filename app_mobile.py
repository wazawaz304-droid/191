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
# 1. PAGE CONFIG & MODERN UI DESIGN
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
)

# Custom CSS สำหรับ Glassmorphism UI และ Premium Look
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

:root {
    --primary-color: #1a6b4a;
    --secondary-color: #0d3d26;
    --bg-color: #f8fafc;
}

html, body, [class*="css"] { 
    font-family: 'IBM Plex Sans Thai', sans-serif !important; 
    background-color: var(--bg-color);
}

/* ซ่อน Header/Footer */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1300px; }

/* Sidebar Premium Design */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d3d26 0%, #1a6b4a 100%) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.9) !important; }
[data-testid="stSidebar"] .stRadio label {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 10px 15px;
    margin-bottom: 5px;
    transition: all 0.2s;
    cursor: pointer;
    border: 1px solid rgba(255,255,255,0.1);
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.15);
}

/* Modern Metric Cards */
[data-testid="stMetric"] {
    background: white !important;
    border-radius: 20px !important;
    padding: 1.25rem !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    border: 1px solid #f1f5f9 !important;
}
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #64748b !important; font-weight: 600; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 700; color: #1e293b !important; }

/* Custom Banners */
.status-card {
    padding: 1.2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 15px;
    border: 1px solid;
}
.success-card { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
.warn-card { background: #fffbeb; border-color: #fde68a; color: #92400e; }

.page-title { font-size: 2.2rem; font-weight: 700; color: #0f172a; letter-spacing: -0.8px; margin-bottom: 0.2rem; }
.page-sub { font-size: 1rem; color: #64748b; margin-bottom: 2rem; }
.section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 1.5rem 0 1rem; padding-left: 0.5rem; border-left: 4px solid var(--primary-color); }

/* Tabs & Buttons */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 12px; background-color: white; border: 1px solid #e2e8f0; padding: 10px 20px;
}
.stTabs [aria-selected="true"] { background-color: var(--primary-color) !important; color: white !important; }

.stButton > button { border-radius: 12px !important; padding: 0.5rem 1rem !important; font-weight: 600 !important; }
.stButton > button[kind="primary"] { background: var(--primary-color) !important; border: none !important; box-shadow: 0 4px 12px rgba(26, 107, 74, 0.2); }

@media (max-width: 768px) {
    .block-container { padding: 1rem; }
    .page-title { font-size: 1.6rem; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONNECTIONS & DATA LOAD
# ============================================================
@st.cache_resource
def get_conn():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except:
        return None

conn = get_conn()

def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None:
            # ล้างชื่อคอลัมน์ป้องกัน KeyError
            df.columns = [c.strip().lower() for c in df.columns]
            return df.dropna(how='all')
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

# ============================================================
# 3. CORE LOGIC (11-Column Mapping & Anti-Duplicate)
# ============================================================
def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab)
        
        if tab == "income":
            df['type'] = 'Income'
            # มาตรฐานชื่อแอป
            df['app'] = df['app'].apply(lambda x: "GrabFood" if "grab" in str(x).lower() 
                                       else ("LINE MAN" if "line" in str(x).lower() 
                                       else ("ShopeeFood" if "shopee" in str(x).lower() else x)))
            
            # Mapping 11 คอลัมน์ตามโครงสร้างของพี่กุลเศรษฐ์
            if 'name' not in df.columns: df['name'] = df['app'] + " Daily Income"
            if 'qty' not in df.columns: df['qty'] = 1
            if 'unit' not in df.columns: df['unit'] = "วัน"
            if 'total_price' not in df.columns: df['total_price'] = df['net_income']
            if 'unit_price' not in df.columns: df['unit_price'] = df['net_income']
            
            cols_order = ['name', 'qty', 'unit', 'total_price', 'date', 'unit_price', 'app', 'net_income', 'gross_sales', 'gp_amount', 'type']
            for col in cols_order:
                if col not in df.columns: df[col] = ""
            df = df[cols_order]

        # รวมข้อมูล
        final = pd.concat([existing, df], ignore_index=True)

        # ป้องกันข้อมูลซ้ำ (เช็กจาก วันที่, แอป, และ ยอดโอน)
        if tab == "income":
            final['date'] = pd.to_datetime(final['date']).dt.strftime('%Y-%m-%d')
            final['net_income'] = clean_numeric(final, 'net_income').round(2)
            final = final.drop_duplicates(subset=['date', 'app', 'net_income'], keep='first')
            # บันทึกต่อท้ายเสมอ (เรียงตามวันที่เก่าไปใหม่)
            final = final.sort_values(by='date', ascending=True)

        conn.update(worksheet="Income", data=final) # ใช้ชื่อ Worksheet "Income"
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 4. AI FUNCTION (Logic เดิม)
# ============================================================
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    try:
        client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except:
        st.error("⚠️ ไม่พบ API Key")
        return []
        
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"

    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = (f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', "
             f"'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. ใช้ชื่อเดิมถ้าคล้าย: [{names_str}]")
    else:
        p = (f"สกัดข้อมูลรายรับร้าน 'เนฟ หมี่ไก่ฉีก @304' เป็น JSON: [{{'name': 'ชื่อรายการ', 'qty': 1, 'unit': 'วัน', 'total_price': 0, 'date': '{now_str}', 'unit_price': 0, 'app': 'GrabFood/LINE MAN/ShopeeFood', 'net_income': 0, 'gross_sales': 0, 'gp_amount': 0, 'type': 'Income'}}] "
             f"กฎ: 1. LINE MAN ให้ดึงยอดจาก 'ยอดที่จะโอนออกให้ร้าน' 2. ปี 2026 เท่านั้น")

    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])

        text = res.text.strip()
        # Safe JSON Extraction
        start = text.find('[')
        end = text.lastIndexOf(']') + 1 if hasattr(text, 'lastIndexOf') else text.rfind(']') + 1
        return json.loads(text[start:end])
    except:
        return []

# ============================================================
# 5. SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("<h1 style='color:white; margin-bottom:0;'>🍜 Nave 304</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:rgba(255,255,255,0.6); font-size:0.8rem;'>AI Business Master v2.0</p>", unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("Navigation", 
        ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"],
        label_visibility="collapsed")
    
    st.divider()
    # Break-even settings
    st.session_state.setdefault("be_rent", 4000)
    st.session_state.setdefault("be_electric", 800)
    st.session_state.setdefault("be_water", 400)
    st.session_state.setdefault("be_other", 0)

    _be_exp = st.expander("⚙️ ตั้งค่า Break-even")
    st.session_state["be_rent"] = _be_exp.number_input("🏠 ค่าเช่า/เดือน", value=st.session_state["be_rent"], step=500)
    st.session_state["be_electric"] = _be_exp.number_input("💡 ค่าไฟ/เดือน", value=st.session_state["be_electric"], step=100)
    st.session_state["be_water"] = _be_exp.number_input("🚿 ค่าน้ำ/เดือน", value=st.session_state["be_water"], step=100)

    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 6. MAIN PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard รายวัน":
    col_t, col_r = st.columns([4, 1])
    with col_t:
        st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
        st.markdown("<div class='page-sub'>สรุปภาพรวมสาขา @304 วันนี้</div>", unsafe_allow_html=True)
    
    df_i = load_data("Income")
    df_e = load_data("Expense")

    if not df_i.empty and 'net_income' in df_i.columns:
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    if not df_e.empty and 'total_price' in df_e.columns:
        df_e['total_price'] = clean_numeric(df_e, 'total_price')
        df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc = df_i['net_income'].sum() if not df_i.empty else 0
    t_exp = df_e['total_price'].sum() if not df_e.empty else 0
    profit = t_inc - t_exp

    # Break-even Calculation
    be_monthly = st.session_state["be_rent"] + st.session_state["be_electric"] + st.session_state["be_water"]
    be_daily_target = (be_monthly / 26) / (1 - ((t_exp/t_inc) if t_inc > 0 else 0.35))
    
    today_inc = df_i[df_i["date"] >= pd.Timestamp.now().normalize()]["net_income"].sum() if not df_i.empty else 0
    passed_be = today_inc >= be_daily_target

    # Status Banner
    if be_daily_target > 0:
        if passed_be:
            st.markdown(f"<div class='status-card success-card'><span style='font-size:1.5rem'>🎯</span><div><b>ยอดเยี่ยม!</b> วันนี้ผ่านจุดคุ้มทุนแล้ว (เกินเป้า ฿{today_inc - be_daily_target:,.0f})</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='status-card warn-card'><span style='font-size:1.5rem'>⏳</span><div><b>อีกนิดเดียว!</b> ขาดอีก ฿{be_daily_target - today_inc:,.0f} จะถึงจุดคุ้มทุนรายวัน</div></div>", unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Income", f"฿{t_inc:,.0f}")
    m2.metric("Expense", f"฿{t_exp:,.0f}")
    m3.metric("Profit", f"฿{profit:,.0f}", delta=f"{profit/t_inc*100:.1f}%" if t_inc > 0 else None)
    m4.metric("Daily Target", f"฿{be_daily_target:,.0f}")

    # Charts
    st.markdown("<div class='section-title'>📈 วิเคราะห์แนวโน้ม</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        if not df_i.empty:
            daily_chart = df_i.groupby('date')['net_income'].sum().reset_index()
            fig = px.line(daily_chart, x='date', y='net_income', title="รายรับรายวัน")
            fig.update_traces(line_color='#1a6b4a', fill='tozeroy')
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if not df_e.empty:
            pie = px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่าย")
            st.plotly_chart(pie, use_container_width=True)

# ============================================================
# 7. PAGE: RECORD INCOME (Logic เดิม ปรับ UI)
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    
    with st.container():
        method = st.radio("วิธีบันทึก:", ["⌨️ ข้อความ", "📸 รูปภาพ", "🎙️ เสียง", "📁 PDF"], horizontal=True)
        res = None
        
        if method == "⌨️ ข้อความ":
            txt = st.text_area("วางสรุปยอดขายที่นี่...", height=150)
            if st.button("🪄 วิเคราะห์ด้วย AI", type="primary"):
                with st.spinner("AI กำลังวิเคราะห์..."): res = process_extraction(txt, "Income")
        
        # (ส่วนบันทึกอื่นๆ รูป/เสียง คง Logic เดิม...)

    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
        st.success(f"✅ AI พบ {len(res)} รายการ")

    if 'tmp_inc' in st.session_state and not st.session_state.tmp_inc.empty:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบข้อมูล</div>", unsafe_allow_html=True)
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True, num_rows="dynamic")
        if st.button("💾 ยืนยันบันทึกทั้งหมด", type="primary"):
            if save_to_tab(edited, "income"):
                st.balloons()
                del st.session_state.tmp_inc
                st.rerun()

# (Page อื่นๆ เช่น AI Agent, ข้อมูลทั้งหมด คง Logic เดิมที่พี่มีอยู่แล้วครับ)
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 ข้อมูลดิบ</div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1:
        df = load_data("Income")
        st.dataframe(df, use_container_width=True)
    with t2:
        df = load_data("Expense")
        st.dataframe(df, use_container_width=True)

elif page == "🤖 AI Agent":
    st.markdown("<div class='page-title'>🤖 AI Consultant</div>", unsafe_allow_html=True)
    # Logic Chat เดิมของคุณ...
    st.info("ระบบ AI พร้อมให้คำปรึกษาด้านยอดขายและต้นทุนครับ")

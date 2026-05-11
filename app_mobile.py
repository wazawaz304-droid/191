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
import logging

# ============================================================
# 0. LOGGING SETUP
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 1. PAGE CONFIG & MODERN UI DESIGN
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
)

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

#MainMenu, footer { visibility: hidden; }
header { background-color: transparent !important; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1300px; }

/* Sidebar Premium Design */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0d3d26 0%, #1a6b4a 100%) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.95) !important; }
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
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

/* Metric Cards */
[data-testid="stMetric"] {
    background: white !important;
    border-radius: 16px !important;
    padding: 1.25rem !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    border: 1px solid #e2e8f0 !important;
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important; }
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #64748b !important; font-weight: 600; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; color: #1e293b !important; }

/* Custom Banners */
.status-card {
    padding: 1.2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 15px;
}
.success-card { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.warn-card { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.info-card { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 0.75rem;}

.page-title { font-size: 2rem; font-weight: 700; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
.page-sub { font-size: 1rem; color: #64748b; margin-bottom: 2rem; }
.section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 1.5rem 0 1rem; padding-left: 0.5rem; border-left: 4px solid var(--primary-color); }

/* Tabs & Buttons */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
.stTabs [data-baseweb="tab"] { border-radius: 12px; background-color: white; border: 1px solid #e2e8f0; padding: 8px 16px; font-weight: 500;}
.stTabs [aria-selected="true"] { background-color: var(--primary-color) !important; color: white !important; border: none; }

.stButton > button { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.2s; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg,#1a6b4a,#2e8b62) !important; color: white !important; border: none !important; box-shadow: 0 4px 12px rgba(26, 107, 74, 0.2); }
.stButton > button:hover { transform: translateY(-1px); }

/* แก้ไขสีพื้นหลัง Expander, Input, Button ใน Sidebar */
[data-testid="stSidebar"] [data-testid="stExpander"] details, 
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background-color: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: rgba(0, 0, 0, 0.15) !important;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.15);
}
[data-testid="stSidebar"] div[data-baseweb="input"] {
    background-color: rgba(0, 0, 0, 0.25) !important; 
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] div[data-baseweb="input"] > div {
    background-color: transparent !important; 
}
[data-testid="stSidebar"] input {
    color: #ffffff !important; 
    background-color: transparent !important; 
    -webkit-text-fill-color: #ffffff !important; 
}
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255, 255, 255, 0.15) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255, 255, 255, 0.25) !important;
}

@media (max-width: 768px) {
    .block-container { padding: 1rem; }
    .page-title { font-size: 1.5rem; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONNECTIONS & DATA LOAD (WITH CACHING)
# ============================================================

@st.cache_resource
def get_conn():
    """✅ @st.cache_resource - Cache Connection Object"""
    try:
        logger.info("🔌 สร้าง Google Sheets Connection...")
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        logger.error(f"❌ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        return None

@st.cache_resource
def get_gemini_client():
    """✅ @st.cache_resource - Cache Gemini Client"""
    try:
        logger.info("🤖 สร้าง Gemini Client...")
        return genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except Exception as e:
        logger.error(f"❌ ไม่พบ API Key: {e}")
        st.error(f"⚠️ ไม่พบ API Key: {e}")
        return None

conn = get_conn()
client = get_gemini_client()

# ============================================================
# 3. DATA LOADING FUNCTIONS (WITH CACHING)
# ============================================================

@st.cache_data(ttl=3600)
def load_income_data():
    """✅ @st.cache_data - Cache Income Data (1 ชั่วโมง)"""
    logger.info("📥 โหลด Income Data...")
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet="Income", ttl=0)
        if df is not None:
            df.columns = [str(c).strip().lower() for c in df.columns]
            result = df.dropna(how='all')
            logger.info(f"✅ โหลด Income Data สำเร็จ ({len(result)} แถว)")
            return result
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ โหลด Income Data ล้มเหลว: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_expense_data():
    """✅ @st.cache_data - Cache Expense Data (1 ชั่วโมง)"""
    logger.info("📥 โหลด Expense Data...")
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet="Expense", ttl=0)
        if df is not None:
            df.columns = [str(c).strip().lower() for c in df.columns]
            result = df.dropna(how='all')
            logger.info(f"✅ โหลด Expense Data สำเร็จ ({len(result)} แถว)")
            return result
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ โหลด Expense Data ล้มเหลว: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_monthly_data():
    """✅ @st.cache_data - Cache Monthly Data (1 ชั่วโมง)"""
    logger.info("📥 โหลด Monthly Data...")
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet="Monthly", ttl=0)
        if df is not None:
            df.columns = [str(c).strip().lower() for c in df.columns]
            result = df.dropna(how='all')
            logger.info(f"✅ โหลด Monthly Data สำเร็จ ({len(result)} แถว)")
            return result
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ โหลด Monthly Data ล้มเหลว: {e}")
        return pd.DataFrame()

def load_data(sheet_name):
    """⚠️ ฟังก์ชันนี้ไม่มี Cache - ใช้สำหรับ Dynamic Sheets"""
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df.dropna(how='all')
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ โหลด {sheet_name} ล้มเหลว: {e}")
        return pd.DataFrame()

def clean_numeric(df, col_name):
    """✅ Clean numeric values"""
    if col_name in df.columns:
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

# ============================================================
# 4. CORE LOGIC (Mapping 11 Columns & Anti-Duplicate)
# ============================================================

def save_to_tab(df, tab):
    """⚠️ ฟังก์ชันนี้ไม่มี Cache - Write Operation"""
    if conn is None or df.empty:
        return False
    try:
        logger.info(f"💾 บันทึก {tab}...")
        existing = load_data(tab)
        
        if tab.lower() == "income":
            df['type'] = 'Income'
            df['app'] = df['app'].apply(lambda x: "GrabFood" if "grab" in str(x).lower() 
                                       else ("LINE MAN" if "line" in str(x).lower() 
                                       else ("ShopeeFood" if "shopee" in str(x).lower() else x)))
            
            if 'name' not in df.columns: df['name'] = df['app'] + " Daily Income"
            if 'qty' not in df.columns: df['qty'] = 1
            if 'unit' not in df.columns: df['unit'] = "วัน"
            if 'total_price' not in df.columns: df['total_price'] = df['net_income']
            if 'unit_price' not in df.columns: df['unit_price'] = df['net_income']
            
            cols_order = ['name', 'qty', 'unit', 'total_price', 'date', 'unit_price', 'app', 'net_income', 'gross_sales', 'gp_amount', 'type']
            for col in cols_order:
                if col not in df.columns: df[col] = ""
            df = df[cols_order]

        elif tab.lower() == "expense":
            df['type'] = 'Expense'
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)

        final = pd.concat([existing, df], ignore_index=True)

        if tab.lower() == "income":
            final['date'] = pd.to_datetime(final['date']).dt.strftime('%Y-%m-%d')
            final['net_income'] = pd.to_numeric(final['net_income']).round(2)
            final = final.drop_duplicates(subset=['date', 'app', 'net_income'], keep='first')
            final = final.sort_values(by='date', ascending=True) 
        elif tab.lower() == "expense":
            final = final.drop_duplicates(subset=['date', 'name', 'total_price'], keep='first')
            final = final.sort_values(by='date', ascending=True)

        target_sheet = "Income" if tab.lower() == "income" else ("Expense" if tab.lower() == "expense" else tab)
        conn.update(worksheet=target_sheet, data=final)
        
        # ✅ ล้าง Cache หลังจากบันทึก
        st.cache_data.clear()
        logger.info(f"✅ บันทึก {tab} สำเร็จ และล้าง Cache")
        
        return True
    except Exception as e:
        logger.error(f"❌ บันทึก {tab} ล้มเหลว: {e}")
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 5. AI FUNCTION
# ============================================================

def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    """AI Extraction Function"""
    if client is None:
        st.error("ไม่พบ Gemini API Key")
        return []
    
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"

    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = (f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', "
             f"'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. ใช้ชื่อเดิมถ้าคล้าย: [{names_str}]")
    else:
        p = (f"สกัดข้อมูลรายรับร้าน 'เนฟ หมี่ไก่ฉีก @304' เป็น JSON: [{{'name': 'ชื่อรายการ', 'qty': 1, 'unit': 'วัน', 'total_price': 0, 'date': '{now_str}', 'unit_price': 0, 'app': 'GrabFood/LINE MAN/ShopeeFood/หน้าร้าน', 'net_income': 0, 'gross_sales': 0, 'gp_amount': 0, 'type': 'Income'}}] "
             f"กฎ: 1. LINE MAN ให้ดึงยอดจาก 'ยอดที่จะโอนออกให้ร้าน' 2. ปี 2026 เท่านั้น")

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
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
        return []
    except Exception as e:
        logger.error(f"❌ process_extraction ล้มเหลว: {e}")
        st.error(f"AI Error: {e}")
        return []

# ============================================================
# 6. SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("<h1 style='color:white; margin-bottom:0;'>🍜 Nave 304</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:rgba(255,255,255,0.6); font-size:0.85rem; margin-top:0;'>AI Business Master</p>", unsafe_allow_html=True)
    st.divider()

    page = st.radio("เมนูหลัก", 
        ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"],
        label_visibility="collapsed")

    st.divider()
    
    # ✅ ปุ่มรีเฟรช - ล้าง Cache และ Rerun
    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        logger.info("🔄 ล้าง Cache และ Rerun...")
        st.cache_data.clear()
        st.rerun()
    
    # ✅ Cache Status
    with st.expander("📊 Cache Status"):
        st.write("**Cache Information:**")
        st.write(f"- Income Data: Cache 1 ชั่วโมง")
        st.write(f"- Expense Data: Cache 1 ชั่วโมง")
        st.write(f"- Monthly Data: Cache 1 ชั่วโมง")
        st.write(f"- Connection: Cache ตลอดเซสชัน")
        if st.button("ล้าง Cache ทั้งหมด"):
            logger.info("🗑️ ล้าง Cache ทั้งหมด...")
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ ล้าง Cache สำเร็จ")
            st.rerun()

# ============================================================
# 7. PAGE — DASHBOARD รายวัน
# ============================================================
if page == "📊 Dashboard รายวัน":
    col_t, col_r = st.columns([4, 1])
    with col_t:
        st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
        st.markdown("<div class='page-sub'>ภาพรวมรายรับ-รายจ่าย ทั้งหมดในชีต</div>", unsafe_allow_html=True)

    # ✅ ใช้ฟังก์ชันที่มี Cache
    df_i = load_income_data()
    df_e = load_expense_data()

    if not df_i.empty and 'net_income' in df_i.columns:
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        if 'date' in df_i.columns:
            df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
            
    if not df_e.empty and 'total_price' in df_e.columns:
        df_e['total_price'] = clean_numeric(df_e, 'total_price')
        if 'date' in df_e.columns:
            df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc = df_i['net_income'].sum() if not df_i.empty and 'net_income' in df_i.columns else 0
    t_exp = df_e['total_price'].sum() if not df_e.empty and 'total_price' in df_e.columns else 0
    profit = t_inc - t_exp

    # คำนวณรายรับเฉพาะวันนี้
    today = pd.Timestamp.now().normalize()
    today_inc = 0
    if not df_i.empty and "date" in df_i.columns:
        today_inc = df_i[df_i["date"] >= today]["net_income"].sum()

    # KPI 4 ช่อง
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น (รวม)", f"฿{profit:,.0f}", delta=f"{profit/t_inc*100:.1f}% margin" if t_inc > 0 else None)
    c4.metric("🔥 รายรับวันนี้", f"฿{today_inc:,.0f}")

    st.divider()

    # Tabs สำหรับกราฟ
    days = st.select_slider("ดูย้อนหลัง:", options=[7, 14, 30, 60, 90, 180, 365], value=30, format_func=lambda x: f"{x} วัน" if x < 365 else "1 ปี")
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)

    tab_inc, tab_exp, tab_price = st.tabs(["📅 รายรับรายวัน", "🛒 รายจ่ายวัตถุดิบ", "📈 ราคาวัตถุดิบ"])

    with tab_inc:
        if not df_i.empty and 'date' in df_i.columns:
            df_fi = df_i[df_i['date'] >= cutoff].copy()
            if not df_fi.empty:
                daily = df_fi.groupby('date')['net_income'].sum().reset_index()
                daily['rolling'] = daily['net_income'].rolling(7, min_periods=1).mean()

                fig = go.Figure()
                colors = {'GrabFood': '#00b14f', 'LINE MAN': '#0094ff', 'ShopeeFood': '#f97316', 'หน้าร้าน': '#8b5cf6'}
                fallback = ['#06b6d4','#f43f5e','#eab308','#14b8a6','#64748b']
                fb_idx = 0
                for app in df_fi.get('app', pd.Series()).unique():
                    d = df_fi[df_fi['app'] == app]
                    if app not in colors:
                        colors[app] = fallback[fb_idx % len(fallback)]
                        fb_idx += 1
                    fig.add_trace(go.Bar(x=d['date'], y=d['net_income'], name=app, marker_color=colors[app], opacity=0.9))
                fig.add_trace(go.Scatter(x=daily['date'], y=daily['rolling'], name='เฉลี่ย 7 วัน', mode='lines', line=dict(color='#fbbf24', dash='dot', width=2.5)))
                fig.update_layout(barmode='stack', hovermode='x unified', title=f"รายรับย้อนหลัง {days} วัน", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"ไม่มีข้อมูลรายรับในช่วง {days} วันที่ผ่านมา")
        else:
            st.info("ยังไม่มีข้อมูลรายรับ")

    with tab_exp:
        if not df_e.empty and 'name' in df_e.columns:
            col_l, col_r = st.columns(2)
            with col_l:
                fig_pie = px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่ายทั้งหมด")
                fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_r:
                top = df_e.groupby('name')['total_price'].sum().nlargest(8).reset_index()
                fig_bar = px.bar(top, x='total_price', y='name', orientation='h', color='total_price', color_continuous_scale='Greens', title="Top 8 รายจ่ายวัตถุดิบ")
                fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            item = st.selectbox("เลือกวัตถุดิบ:", sorted(df_e['name'].dropna().unique()))
            df_it = df_e[df_e['name'] == item].sort_values('date').copy()
            qty = clean_numeric(df_it, 'qty').replace(0, 1)
            df_it['unit_price'] = df_it['total_price'] / qty

            if len(df_it) >= 2:
                last, prev = df_it['unit_price'].iloc[-1], df_it['unit_price'].iloc[-2]
                chg = (last - prev) / prev * 100 if prev > 0 else 0
                ca, cb = st.columns(2)
                ca.metric("ราคาล่าสุด/หน่วย", f"฿{last:.2f}", delta=f"{chg:+.1f}% vs ครั้งก่อน", delta_color="inverse")
                cb.metric("ซื้อทั้งหมด", f"{len(df_it)} ครั้ง", delta=f"รวม ฿{df_it['total_price'].sum():,.0f}")
            
            fig_l = px.line(df_it, x='date', y='unit_price', markers=True, title=f"แนวโน้มราคา {item} ต่อหน่วย")
            fig_l.update_traces(line_color='#1a6b4a', marker_color='#1a6b4a')
            fig_l.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_l, use_container_width=True)

# ============================================================
# 8. PAGE — วิเคราะห์รายเดือน
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='page-title'>📈 วิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>เปรียบเทียบ Gross vs Net · ค่า GP · แนวโน้ม</div>", unsafe_allow_html=True)

    # ✅ ใช้ฟังก์ชันที่มี Cache
    df_m = load_monthly_data()

    if not df_m.empty:
        for c in ['net_income', 'gross', 'fees', 'ads', 'discounts']:
            if c in df_m.columns: df_m[c] = clean_numeric(df_m, c)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 ยอดโอนสุทธิรวม", f"฿{df_m['net_income'].sum() if 'net_income' in df_m.columns else 0:,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{df_m['gross'].sum() if 'gross' in df_m.columns else 0:,.0f}")
        m3.metric("📉 ค่า GP รวม", f"฿{df_m['fees'].sum() if 'fees' in df_m.columns else 0:,.0f}")
        m4.metric("📣 ค่าโฆษณารวม", f"฿{df_m['ads'].sum() if 'ads' in df_m.columns else 0:,.0f}")

        st.divider()
        cl, cr = st.columns([2, 1])
        with cl:
            if 'month_year' in df_m.columns and 'gross' in df_m.columns and 'net_income' in df_m.columns:
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='Gross', marker_color='#93c5fd'))
                fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='Net', marker_color='#1a6b4a'))
                fig_m.update_layout(barmode='group', title='Gross vs Net รายเดือน', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_m, use_container_width=True)

        with cr:
            if 'fees' in df_m.columns and 'platform' in df_m.columns and df_m['fees'].sum() > 0:
                fig_p = px.pie(df_m, values='fees', names='platform', hole=0.4, title='ค่า GP แยกแอป')
                fig_p.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("<div class='section-title'>📋 ตารางละเอียดรายเดือน</div>", unsafe_allow_html=True)
        if 'gross' in df_m.columns and 'fees' in df_m.columns and 'ads' in df_m.columns and 'net_income' in df_m.columns:
            df_m['cost_%'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'].replace(0, pd.NA) * 100).round(1)
            df_m['net_%'] = (df_m['net_income'] / df_m['gross'].replace(0, pd.NA) * 100).round(1)
            show_cols = [c for c in ['month_year','platform','gross','fees','ads','discounts','net_income','cost_%','net_%'] if c in df_m.columns]
            st.dataframe(
                df_m[show_cols].sort_values('month_year', ascending=False) if 'month_year' in df_m.columns else df_m[show_cols],
                use_container_width=True,
                column_config={
                    'month_year': 'เดือน', 'platform': 'แอป',
                    'gross': st.column_config.NumberColumn('Gross (฿)', format='฿%.0f'),
                    'fees': st.column_config.NumberColumn('GP (฿)', format='฿%.0f'),
                    'ads': st.column_config.NumberColumn('โฆษณา (฿)', format='฿%.0f'),
                    'discounts': st.column_config.NumberColumn('ส่วนลด (฿)', format='฿%.0f'),
                    'net_income': st.column_config.NumberColumn('Net (฿)', format='฿%.0f'),
                    'cost_%': st.column_config.NumberColumn('% ต้นทุน', format='%.1f%%'),
                    'net_%': st.column_config.NumberColumn('% Net Margin', format='%.1f%%'),
                },
            )
    else:
        st.info("ยังไม่มีข้อมูลรายเดือน — บันทึกสรุปรายเดือนก่อนครับ")

# ============================================================
# 9. PAGE — บันทึกรายรับ
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>รองรับข้อความ · ไฟล์ PDF · รูปภาพ · เสียง</div>", unsafe_allow_html=True)

    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "📷 ถ่ายรูป/อัปโหลด", "🎙️ บันทึกเสียง", "📁 ไฟล์ PDF"], horizontal=True)

    res = None

    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("วางข้อความรายงานยอดขายที่นี่:", placeholder="เช่น: Grab ยอดโอน 1,250 บาท วันที่ 1 พฤษภาคม")
        if txt:
            res = process_extraction(txt, rtype)

    elif method == "📷 ถ่ายรูป/อัปโหลด":
        img = st.file_uploader("อัปโหลดรูปภาพ:", type=["jpg", "jpeg", "png", "webp"])
        if img:
            img_bytes = img.read()
            mime = f"image/{img.name.split('.')[-1].lower()}"
            res = process_extraction(img_bytes, rtype, is_bytes=True, mime=mime)

    elif method == "🎙️ บันทึกเสียง":
        audio = st.file_uploader("อัปโหลดไฟล์เสียง:", type=["mp3", "wav", "ogg", "flac"])
        if audio:
            st.info("🎙️ บันทึกเสียง - ยังไม่รองรับในเวอร์ชันนี้")

    elif method == "📁 ไฟล์ PDF":
        pdf = st.file_uploader("อัปโหลด PDF:", type=["pdf"])
        if pdf:
            st.info("📄 ไฟล์ PDF - ยังไม่รองรับในเวอร์ชันนี้")

    if res:
        st.markdown("<div class='section-title'>📋 ข้อมูลที่สกัดได้</div>", unsafe_allow_html=True)
        st.json(res)

        if st.button("✅ บันทึกข้อมูล", key="save_income"):
            df_new = pd.DataFrame(res)
            if save_to_tab(df_new, "Income"):
                st.success("✅ บันทึกสำเร็จ!")
                st.rerun()

# ============================================================
# 10. PAGE — บันทึกรายจ่าย (แก้ไขส่วนกล้องและเสียงให้ใช้งานได้จริง)
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่าย</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>สแกนบิล · อัดเสียงพูด · พิมพ์รายการ</div>", unsafe_allow_html=True)

    method = st.radio("เลือกวิธีบันทึก:", ["📷 ถ่ายรูปใบเสร็จ", "🎙️ พูดบันทึกเสียง", "⌨️ พิมพ์เอง", "🖼️ อัปโหลดรูป"], horizontal=True)

    # ดึงชื่อสินค้าเดิมที่มีในชีตมาให้ AI ช่วยจำ
    df_exp = load_expense_data()
    existing_names = df_exp['name'].unique().tolist() if not df_exp.empty else []
    res_ex = None

    # --- ส่วนที่ 1: ถ่ายรูปสดจากกล้อง ---
    if method == "📷 ถ่ายรูปใบเสร็จ":
        img_cam = st.camera_input("📸 เล็งไปที่ใบเสร็จหรือบิลวัตถุดิบ")
        if img_cam and st.button("🪄 สกัดข้อมูลจากรูป", type="primary"):
            with st.spinner("AI กำลังอ่านบิล..."):
                res_ex = process_extraction(img_cam.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=existing_names)

    # --- ส่วนที่ 2: อัดเสียงสด ---
    elif method == "🎙️ พูดบันทึกเสียง":
        audio_rec = st.audio_input("🎙️ กดปุ่มแล้วพูดรายการ (เช่น: ซื้อไก่ 500 บาท)")
        if audio_rec and st.button("🚀 แปลงเสียงเป็นรายการ", type="primary"):
            with st.spinner("AI กำลังฟังเสียง..."):
                res_ex = process_extraction(audio_rec.read(), "Expense", is_bytes=True, mime="audio/wav", existing_names=existing_names)

    # --- ส่วนที่ 3: พิมพ์ข้อความเอง ---
    elif method == "⌨️ พิมพ์เอง":
        txt = st.text_area("วางข้อความรายจ่ายที่นี่:", placeholder="เช่น: ซื้อไข่ไก่ 3 แผง 420 บาท")
        if txt and st.button("🪄 วิเคราะห์ข้อความ", type="primary"):
            res_ex = process_extraction(txt, "Expense", existing_names=existing_names)

    # --- ส่วนที่ 4: อัปโหลดไฟล์รูป ---
    elif method == "🖼️ อัปโหลดรูป":
        img_file = st.file_uploader("เลือกรูปภาพใบเสร็จ", type=["jpg", "jpeg", "png"])
        if img_file and st.button("🪄 วิเคราะห์จากไฟล์", type="primary"):
            res_ex = process_extraction(img_file.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=existing_names)

    # --- ส่วนการตรวจสอบและบันทึกลง Sheets ---
    if res_ex:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบข้อมูลก่อนบันทึก</div>", unsafe_allow_html=True)
        edited_ex = st.data_editor(pd.DataFrame(res_ex), use_container_width=True, num_rows="dynamic")
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 บันทึกทันที", type="primary"):
                if save_to_tab(edited_ex, "Expense"):
                    st.success("✅ บันทึกรายจ่ายร้าน @304 สำเร็จ!")
                    st.rerun()
        with c2:
            if st.button("🗑️ ล้างรายการ"):
                st.rerun()

# ============================================================
# 11. PAGE — AI AGENT
# ============================================================
elif page == "🤖 AI Agent":
    st.markdown("<div class='page-title'>🤖 AI Agent</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>ตัวช่วย AI สำหรับวิเคราะห์ข้อมูล</div>", unsafe_allow_html=True)

    # ✅ ใช้ฟังก์ชันที่มี Cache
    df_i = load_income_data()
    df_e = load_expense_data()

    if not df_i.empty or not df_e.empty:
        st.info("🤖 AI Agent - ยังไม่พร้อมใช้งานในเวอร์ชันนี้")
        st.write("ฟีเจอร์นี้จะช่วยให้คุณสามารถสอบถาม AI เกี่ยวกับข้อมูลของคุณได้")
    else:
        st.warning("⚠️ ยังไม่มีข้อมูล - บันทึกข้อมูลรายรับ/รายจ่ายก่อนครับ")

# ============================================================
# 12. PAGE — ข้อมูลทั้งหมด
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 ข้อมูลทั้งหมด</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>ดูข้อมูลทั้งหมดจากทุก Sheet</div>", unsafe_allow_html=True)

    # ✅ ใช้ฟังก์ชันที่มี Cache
    df_i = load_income_data()
    df_e = load_expense_data()
    df_m = load_monthly_data()

    tab1, tab2, tab3 = st.tabs(["📊 Income", "📦 Expense", "📅 Monthly"])

    with tab1:
        st.markdown("<div class='section-title'>📊 ข้อมูลรายรับ</div>", unsafe_allow_html=True)
        if not df_i.empty:
            st.dataframe(df_i, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายรับ")

    with tab2:
        st.markdown("<div class='section-title'>📦 ข้อมูลรายจ่าย</div>", unsafe_allow_html=True)
        if not df_e.empty:
            st.dataframe(df_e, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab3:
        st.markdown("<div class='section-title'>📅 ข้อมูลรายเดือน</div>", unsafe_allow_html=True)
        if not df_m.empty:
            st.dataframe(df_m, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายเดือน")

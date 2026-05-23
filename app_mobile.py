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
import sqlalchemy
from sqlalchemy import text

# ============================================================
# 0. LOGGING SETUP
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 1. PAGE CONFIG & MODERN PASTEL DESIGN
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
    --primary-color: #A8E6CF; /* Mint Pastel */
    --secondary-color: #FFD3B6; /* Peach Pastel */
    --bg-color: #FFFAFA; /* Snow White Background */
    --accent-color: #DCEDC1; /* Light Sage */
}

html, body, [class*="css"] { 
    font-family: 'IBM Plex Sans Thai', sans-serif !important; 
    background-color: var(--bg-color);
}

#MainMenu, footer { visibility: hidden; }
header { background-color: transparent !important; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1300px; }

/* Sidebar Premium Pastel Design */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #A8E6CF 0%, #DCEDC1 100%) !important;
}
[data-testid="stSidebar"] * { color: #555 !important; }
[data-testid="stSidebar"] .stRadio label {
    background: rgba(255,255,255,0.4);
    border-radius: 12px;
    padding: 10px 15px;
    margin-bottom: 5px;
    transition: all 0.2s;
    cursor: pointer;
    border: 1px solid rgba(255,255,255,0.3);
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.6);
}
[data-testid="stSidebar"] hr { border-color: rgba(0,0,0,0.05) !important; }

/* Metric Cards พาสเทลขอบมน */
[data-testid="stMetric"] {
    background: white !important;
    border-radius: 20px !important;
    padding: 1.25rem !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.03) !important;
    border: none !important;
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important; }
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #888 !important; font-weight: 600; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 500; color: #555 !important; }

/* Status Cards แถบแจ้งเตือนสถานะ */
.status-card {
    padding: 1.2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 15px;
    font-size: 1rem;
    font-weight: 500;
}
.success-card { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.warn-card { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }

.page-title { font-size: 2rem; font-weight: 700; color: #555; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
.page-sub { font-size: 1rem; color: #888; margin-bottom: 2rem; }
.section-title { font-size: 1.1rem; font-weight: 600; color: #555; margin: 1.5rem 0 1rem; padding-left: 0.5rem; border-left: 4px solid var(--primary-color); }

/* Tabs & Buttons โทนพาสเทล */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
.stTabs [data-baseweb="tab"] { border-radius: 12px; background-color: white; border: 1px solid #e2e8f0; padding: 8px 16px; font-weight: 500;}
.stTabs [aria-selected="true"] { background-color: var(--primary-color) !important; color: #555 !important; border: none; }

.stButton > button { border-radius: 25px !important; font-weight: 600 !important; transition: all 0.2s; padding: 0.5rem 1rem !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #A8E6CF, #DCEDC1) !important; color: #555 !important; border: none !important; box-shadow: 0 4px 12px rgba(168, 230, 207, 0.3); }
.stButton > button:hover { background-color: #FFD3B6 !important; transform: scale(1.02); color: #555 !important; }

/* Sidebar Expanders */
[data-testid="stSidebar"] [data-testid="stExpander"] details, 
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background-color: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.4);
}
</style>
""", unsafe_allow_html=True)

pastel_colors = ['#A8E6CF', '#DCEDC1', '#FFD3B6', '#FFAAA5', '#FF8B94']

# ============================================================
# 2. CONNECTIONS
# ============================================================

@st.cache_resource
def get_supabase_conn():
    try:
        return st.connection("supabase", type="sql")
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Supabase ไม่ได้: {e}")
        return None

@st.cache_resource
def get_gsheets_conn():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except:
        return None

@st.cache_resource
def get_gemini_client():
    try:
        return genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except:
        return None

conn_sb = get_supabase_conn()
conn_gs = get_gsheets_conn()
client = get_gemini_client()

# ============================================================
# 2.5 GLOBAL STATUS NOTIFICATION SYSTEM
# ============================================================
def display_status_notification():
    """ระบบแบนเนอร์แจ้งเตือนสถานะความสำเร็จหรือข้อผิดพลาดหลังจากการ Rerun หน้าจอ"""
    if "status_msg" in st.session_state:
        msg_type = st.session_state.get("status_type", "success")
        if msg_type == "success":
            st.markdown(f"<div class='status-card success-card'>🎉 {st.session_state.status_msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='status-card warn-card'>🚨 {st.session_state.status_msg}</div>", unsafe_allow_html=True)
        del st.session_state.status_msg
        if "status_type" in st.session_state: 
            del st.session_state.status_type

# ============================================================
# 3. DATA LOADING & UPDATE FUNCTIONS
# ============================================================

@st.cache_data(ttl=60)
def load_data_sql(table_name):
    if conn_sb is None: return pd.DataFrame()
    try:
        date_col = "data" if table_name == "lineman_insight" else ("month_year" if table_name == "monthly" else "date")
        query = f"SELECT * FROM {table_name} ORDER BY {date_col} DESC"
        df = conn_sb.query(query, ttl=0)
        if df is not None and not df.empty and date_col in df.columns and table_name != "monthly":
            df[date_col] = pd.to_datetime(df[date_col])
        return df
    except Exception as e:
        logger.error(f"❌ โหลดข้อมูลตาราง {table_name} ล้มเหลว: {e}")
        return pd.DataFrame()

def load_income_data(): return load_data_sql("income")
def load_expense_data(): return load_data_sql("expense")
def load_monthly_data(): return load_data_sql("monthly")
def load_insight_data(): return load_data_sql("lineman_insight")

def clean_numeric(df, col_name):
    if df is None or df.empty or col_name not in df.columns:
        return pd.Series([0.0] * (len(df) if df is not None else 1))
    cleaned = df[col_name].astype(str).str.replace(r'[^\d.-]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0)

def update_full_table(df, table_name):
    if conn_sb is None or df.empty: return False
    try:
        save_df = df.copy()
        if table_name == "expense" and "unit_price" in save_df.columns:
            save_df = save_df.drop(columns=["unit_price"])
        save_df = save_df.where(pd.notnull(save_df), None)
        with conn_sb.engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {table_name}"))
            save_df.to_sql(table_name, connection, if_exists='append', index=False, method='multi')
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

# ============================================================
# 4. CORE SAVE LOGIC (ปรับปรุงประสิทธิภาพการแมปประเภทข้อมูลตัวเลข)
# ============================================================

def save_to_tab(df, tab):
    if conn_sb is None or df.empty: 
        st.session_state.status_msg = "ไม่สามารถเชื่อมต่อฐานข้อมูล Cloud หรือข้อมูลว่างเปล่า"
        st.session_state.status_type = "error"
        return False
    try:
        table_map = {"Income": "income", "Expense": "expense", "Monthly": "monthly", "LM_Insight": "lineman_insight"}
        table_name = table_map.get(tab, tab.lower())
        save_df = df.copy()
        save_df.columns = [str(c).strip().lower() for c in save_df.columns]
        
        if table_name == "income":
            save_df['type'] = 'Income'
            save_df['app'] = save_df['app'].apply(lambda x: "GrabFood" if "grab" in str(x).lower() 
                                       else ("LINE MAN" if "line" in str(x).lower() 
                                       else ("ShopeeFood" if "shopee" in str(x).lower() else x)))
            if 'name' not in save_df.columns: save_df['name'] = save_df['app'] + " Daily Income"
            if 'qty' not in save_df.columns: save_df['qty'] = 1
            if 'unit' not in save_df.columns: save_df['unit'] = "วัน"
            
            # บังคับประเภทข้อมูลตัวเลข เพื่อไม่ให้เพี้ยนเป็น Object Text ตอนแปลง Null
            for num_col in ['net_income', 'gross_sales', 'gp_amount', 'qty', 'total_price', 'unit_price']:
                if num_col in save_df.columns:
                    save_df[num_col] = pd.to_numeric(save_df[num_col], errors='coerce').fillna(0.0)
            
            if 'total_price' not in save_df.columns and 'net_income' in save_df.columns: 
                save_df['total_price'] = save_df['net_income']
            if 'unit_price' not in save_df.columns and 'net_income' in save_df.columns: 
                save_df['unit_price'] = save_df['net_income']
            if 'date' in save_df.columns: 
                save_df['date'] = pd.to_datetime(save_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
                
        elif table_name == "expense":
            save_df['type'] = 'Expense'
            if "unit_price" in save_df.columns: 
                save_df = save_df.drop(columns=["unit_price"])
            
            for num_col in ['qty', 'total_price']:
                if num_col in save_df.columns:
                    save_df[num_col] = pd.to_numeric(save_df[num_col], errors='coerce').fillna(0.0)
                    
            if 'date' in save_df.columns: 
                save_df['date'] = pd.to_datetime(save_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
        save_df = save_df.where(pd.notnull(save_df), None)
        save_df.to_sql(table_name, conn_sb.engine, if_exists='append', index=False, method='multi')
        st.cache_data.clear()
        return True
    except Exception as e:
        logger.error(f"❌ Database Constraint Fail: {e}")
        st.session_state.status_msg = f"บันทึกลงฐานข้อมูลไม่สำเร็จเนื่องจากโครงสร้างขัดข้อง: {str(e)}"
        st.session_state.status_type = "error"
        return False

# ============================================================
# 5. AI FUNCTION
# ============================================================

def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    if client is None: return []
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"

    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = (f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', "
             f"'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. ใช้ชื่อเดิมถ้าคล้าย: [{names_str}]")
    elif p_type == "Insight":
        p = ("สกัดข้อมูลจากรูปภาพแอป LINE MAN Merchant เป็น JSON array: "
             "1. หากเป็นรูป 'อันดับสินค้าขายดี': [{'type': 'Menu', 'name': 'ชื่อเมนู', 'qty': จำนวน, 'amount': ยอดเงิน}] "
             "2. หากเป็นรูป 'สรุปยอดขาย/การตลาด': [{'type': 'Marketing', 'name': 'ชื่อรายการ', 'qty': จำนวนครั้ง, 'amount': 0}] "
             "ตอบเฉพาะ PURE JSON เท่านั้น ห้ามมีคำอธิบายเพิ่มเติม")
    else:
        p = (f"สกัดข้อมูลรายรับร้าน 'เนฟ หมี่ไก่ฉีก @304' เป็น JSON: [{{'name': 'ชื่อรายการ', 'qty': 1, 'unit': 'วัน', 'total_price': 0, 'date': '{now_str}', 'unit_price': 0, 'app': 'GrabFood/LINE MAN/ShopeeFood/หน้าร้าน', 'net_income': 0, 'gross_sales': 0, 'gp_amount': 0, 'type': 'Income'}}] "
             f"กฎ: 1. LINE MAN ให้ดึงยอดจาก 'ยอดที่จะโอนออกให้ร้าน' 2. ปี 2026 เท่านั้น")

    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])
        text = res.text.strip()
        start, end = text.find('['), text.rfind(']') + 1
        return json.loads(text[start:end]) if start != -1 else []
    except Exception as e:
        return []

# ============================================================
# 6. SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("<h1 style='color:#555; margin-bottom:0;'>🍜 Nave 304</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#888; font-size:0.85rem; margin-top:0;'>AI Business Master</p>", unsafe_allow_html=True)
    st.divider()

    page = st.radio("เมนูหลัก", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "📧 Sync ยอดจาก Email", "🎯 LINE MAN Insight", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด", "🛠️ Admin Migration"], label_visibility="collapsed")
    st.divider()
    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 7. PAGE — DASHBOARD รายวัน
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    display_status_notification()
    df_i, df_e = load_income_data(), load_expense_data()

    if not df_i.empty: df_i['net_income'] = clean_numeric(df_i, 'net_income')
    if not df_e.empty: df_e['total_price'] = clean_numeric(df_e, 'total_price')

    t_inc = df_i['net_income'].sum() if not df_i.empty else 0
    t_exp = df_e['total_price'].sum() if not df_e.empty else 0
    profit = t_inc - t_exp

    today = pd.Timestamp.now().normalize()
    today_inc = df_i[df_i["date"] >= today]["net_income"].sum() if not df_i.empty and "date" in df_i.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น (รวม)", f"฿{profit:,.0f}", delta=f"{profit/t_inc*100:.1f}% margin" if t_inc > 0 else None)
    c4.metric("🔥 รายรับวันนี้", f"฿{today_inc:,.0f}")

    st.divider()
    days = st.select_slider("ดูย้อนหลัง:", options=[7, 14, 30, 60, 90, 180, 365], value=30)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    tab_inc, tab_exp, tab_price = st.tabs(["📅 รายรับรายแพลตฟอร์ม", "🛒 รายจ่ายวัตถุดิบ", "📈 ราคาวัตถุดิบ"])

    with tab_inc:
        if not df_i.empty and 'date' in df_i.columns:
            df_fi = df_i[df_i['date'] >= cutoff].copy()
            if not df_fi.empty:
                daily = df_fi.groupby('date')['net_income'].sum().reset_index()
                daily['rolling'] = daily['net_income'].rolling(7, min_periods=1).mean()
                fig = go.Figure()
                app_colors = {'LINE MAN': '#2ecc71', 'GrabFood': '#064e3b', 'ShopeeFood': '#f97316', 'หน้าร้าน': '#8b5cf6'}
                for app in df_fi['app'].unique():
                    d = df_fi[df_fi['app'] == app]
                    fig.add_trace(go.Bar(x=d['date'], y=d['net_income'], name=app, marker_color=app_colors.get(app, '#64748b'), opacity=0.9))
                fig.add_trace(go.Scatter(x=daily['date'], y=daily['rolling'], name='เฉลี่ย 7 วัน', mode='lines', line=dict(color='#fbbf24', dash='dot', width=2.5)))
                fig.update_layout(barmode='stack', hovermode='x unified', title=f"รายรับย้อนหลัง {days} วัน", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

    with tab_exp:
        if not df_e.empty:
            col_l, col_r = st.columns(2)
            with col_l:
                # 🛠️ ตรรกะคำนวณรวบรวมกลุ่มวัตถุดิบที่ยอดรวมต่ำกว่า 3% ให้กลายเป็น "อื่นๆ"
                df_pie_data = df_e.groupby('name')['total_price'].sum().reset_index()
                grand_total = df_pie_data['total_price'].sum()
                
                if grand_total > 0:
                    df_pie_data['percentage'] = (df_pie_data['total_price'] / grand_total) * 100
                    
                    # คัดแยกรายการหลัก (>= 3%) และรายการย่อย (< 3%)
                    main_items = df_pie_data[df_pie_data['percentage'] >= 3.0].copy()
                    other_items = df_pie_data[df_pie_data['percentage'] < 3.0]
                    
                    if not other_items.empty:
                        other_row = pd.DataFrame([{
                            'name': 'วัตถุดิบอื่นๆ (ย่อย)',
                            'total_price': other_items['total_price'].sum(),
                            'percentage': other_items['percentage'].sum()
                        }])
                        final_pie_df = pd.concat([main_items, other_row], ignore_index=True)
                    else:
                        final_pie_df = main_items
                else:
                    final_pie_df = df_pie_data

                # สร้างกราฟวงกลมพาสเทลที่สะอาดตาขึ้น
                fig_pie = px.pie(
                    final_pie_df, 
                    values='total_price', 
                    names='name', 
                    hole=0.4, 
                    title="สัดส่วนรายจ่ายวัตถุดิบหลัก (รวมกลุ่มชิ้นเล็ก)", 
                    color_discrete_sequence=pastel_colors
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_r:
                top = df_e.groupby('name')['total_price'].sum().nlargest(8).reset_index()
                fig_bar = px.bar(top, x='total_price', y='name', orientation='h', color='total_price', color_continuous_scale='Greens', title="Top 8 รายจ่ายสูงสุด")
                st.plotly_chart(fig_bar, use_container_width=True)

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            item = st.selectbox("เลือกวัตถุดิบ:", sorted(df_e['name'].dropna().unique()))
            df_it = df_e[df_e['name'] == item].sort_values('date').copy()
            if 'unit_price' not in df_it.columns:
                df_it['unit_price'] = df_it['total_price'] / clean_numeric(df_it, 'qty').replace(0, 1)
            fig_l = px.line(df_it, x='date', y='unit_price', markers=True, title=f"แนวโน้มราคา {item} ต่อหน่วย", color_discrete_sequence=[pastel_colors[0]])
            st.plotly_chart(fig_l, use_container_width=True)

# ============================================================
# 8. PAGE — วิเคราะห์รายเดือน
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='page-title'>📈 วิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    display_status_notification()
    st.markdown("<div class='page-sub'>เปรียบเทียบ Gross vs Net · ค่า GP · แนวโน้มแบบครบถ้วน</div>", unsafe_allow_html=True)
    df_m = load_monthly_data()

    if not df_m.empty:
        for c in ['net_income', 'gross', 'fees', 'ads', 'discounts']:
            if c in df_m.columns: df_m[c] = clean_numeric(df_m, c)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 ยอดโอนสุทธิรวม", f"฿{df_m['net_income'].sum():,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{df_m['gross'].sum():,.0f}")
        m3.metric("📉 ค่า GP รวม", f"฿{df_m['fees'].sum():,.0f}")
        m4.metric("📣 ค่าโฆษณารวม", f"฿{df_m['ads'].sum():,.0f}")

        st.divider()
        cl, cr = st.columns([2, 1])
        with cl:
            if 'month_year' in df_m.columns and 'gross' in df_m.columns and 'net_income' in df_m.columns:
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='Gross', marker_color='#93c5fd'))
                fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='Net', marker_color='#1a6b4a'))
                fig_m.update_layout(barmode='group', title='Gross vs Net รายเดือน', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_m, use_container_width=True)
        with cr:
            if 'fees' in df_m.columns and 'platform' in df_m.columns and df_m['fees'].sum() > 0:
                fig_p = px.pie(df_m, values='fees', names='platform', hole=0.4, title='ค่า GP แยกแอป', color_discrete_sequence=pastel_colors)
                st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("<div class='section-title'>📋 ตารางละเอียดรายเดือน</div>", unsafe_allow_html=True)
        df_m['cost_%'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'].replace(0, pd.NA) * 100).round(1)
        df_m['net_%'] = (df_m['net_income'] / df_m['gross'].replace(0, pd.NA) * 100).round(1)
        show_cols = [c for c in ['month_year','platform','gross','fees','ads','discounts','net_income','cost_%','net_%'] if c in df_m.columns]
        st.dataframe(df_m[show_cols], use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายเดือน")

# ============================================================
# 9. PAGE — บันทึกรายรับ (เพิ่มระบบตรวจสอบความเสถียรแถบสถานะ)
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    display_status_notification()
    rtype = st.radio("ประเภทรายรับ:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["📷 ถ่ายรูปหน้าจอสรุปยอด", "🎙️ พูดบันทึกยอดขาย", "⌨️ พิมพ์เอง", "🖼️ อัปโหลดรูป"], horizontal=True)

    res_raw = None
    if method == "📷 ถ่ายรูปหน้าจอสรุปยอด":
        if st.toggle("📸 เปิดใช้งานกล้องถ่ายรูป"):
            img_cam = st.camera_input("📸 ถ่ายรูปรายงาน")
            if img_cam and st.button("🪄 สกัดยอดจากรูป", type="primary"):
                res_raw = process_extraction(img_cam.read(), rtype, is_bytes=True, mime="image/jpeg")
    elif method == "🎙️ พูดบันทึกยอดขาย":
        audio_rec = st.audio_input("🎙️ พูดบันทึกยอด")
        if audio_rec and st.button("🚀 แปลงเสียงเป็นยอดเงิน", type="primary"):
            res_raw = process_extraction(audio_rec.read(), rtype, is_bytes=True, mime="audio/wav")
    elif method == "⌨️ พิมพ์เอง":
        txt = st.text_area("วางข้อความยอดขายที่นี่:")
        if txt and st.button("🪄 วิเคราะห์ยอดขาย", type="primary"):
            res_raw = process_extraction(txt, rtype)
    elif method == "🖼️ อัปโหลดรูป":
        img_file = st.file_uploader("เลือกรูปภาพ", type=["jpg", "png", "jpeg"])
        if img_file and st.button("🪄 วิเคราะห์จากไฟล์", type="primary"):
            res_raw = process_extraction(img_file.read(), rtype, is_bytes=True, mime="image/jpeg")

    if res_raw:
        st.session_state.tmp_inc_data = pd.DataFrame(res_raw)

    if 'tmp_inc_data' in st.session_state and not st.session_state.tmp_inc_data.empty:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบรายรับก่อนลงบัญชี</div>", unsafe_allow_html=True)
        edited_df = st.data_editor(st.session_state.tmp_inc_data, use_container_width=True, num_rows="dynamic")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 บันทึกลง Cloud", type="primary"):
                if save_to_tab(edited_df, "Income"):
                    del st.session_state.tmp_inc_data
                    st.session_state.status_msg = "บันทึกรายรับร้านเดลิเวอรี่เข้าสู่ระบบคลาวด์เสร็จสมบูรณ์แล้วครับ!"
                    st.session_state.status_type = "success"
                    st.rerun()
                else:
                    st.rerun()
        with c2:
            if st.button("🗑️ ล้างข้อมูล"):
                del st.session_state.tmp_inc_data
                st.rerun()

# ============================================================
# 10. PAGE — บันทึกรายจ่าย (เพิ่มระบบตรวจสอบความเสถียรแถบสถานะ)
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่าย</div>", unsafe_allow_html=True)
    display_status_notification()
    method = st.radio("เลือกวิธีบันทึก:", ["📷 ถ่ายรูปใบเสร็จ", "🎙️ พูดบันทึกเสียง", "⌨️ พิมพ์เอง", "🖼️ อัปโหลดรูป"], horizontal=True)

    df_exp_db = load_expense_data()
    existing_names = df_exp_db['name'].unique().tolist() if not df_exp_db.empty else []

    res_raw = None
    if method == "📷 ถ่ายรูปใบเสร็จ":
        if st.toggle("📸 เปิดใช้งานกล้องถ่ายรูป"):
            img_cam = st.camera_input("📸 เล็งบิล")
            if img_cam and st.button("🪄 สกัดข้อมูลจากรูป", type="primary"):
                res_raw = process_extraction(img_cam.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=existing_names)
    elif method == "🎙️ พูดบันทึกเสียง":
        audio_rec = st.audio_input("🎙️ พูดรายการ")
        if audio_rec and st.button("🚀 แปลงเสียงเป็นรายการ", type="primary"):
            res_raw = process_extraction(audio_rec.read(), "Expense", is_bytes=True, mime="audio/wav", existing_names=existing_names)
    elif method == "⌨️ พิมพ์เอง":
        txt = st.text_area("วางข้อความรายจ่าย:")
        if txt and st.button("🪄 วิเคราะห์ข้อความ", type="primary"):
            res_raw = process_extraction(txt, "Expense", existing_names=existing_names)
    elif method == "🖼️ อัปโหลดรูป":
        img_file = st.file_uploader("เลือกรูปภาพใบเสร็จ", type=["jpg", "png", "jpeg"])
        if img_file and st.button("🪄 วิเคราะห์จากไฟล์", type="primary"):
            res_raw = process_extraction(img_file.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=existing_names)

    if res_raw:
        st.session_state.tmp_exp_data = pd.DataFrame(res_raw)

    if 'tmp_exp_data' in st.session_state and not st.session_state.tmp_exp_data.empty:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบข้อมูลก่อนบันทึก</div>", unsafe_allow_html=True)
        edited_df = st.data_editor(st.session_state.tmp_exp_data, use_container_width=True, num_rows="dynamic")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 ยืนยันบันทึก", type="primary"):
                if save_to_tab(edited_df, "Expense"):
                    del st.session_state.tmp_exp_data
                    st.session_state.status_msg = "บันทึกรายการรายจ่ายวัตถุดิบลงฐานข้อมูลเรียบร้อยแล้วครับพี่กุลเศรษฐ์!"
                    st.session_state.status_type = "success"
                    st.rerun()
                else:
                    st.rerun()
        with c2:
            if st.button("🗑️ ล้างรายการ"):
                del st.session_state.tmp_exp_data
                st.rerun()

# ============================================================
# 11. PAGE — SYNC EMAIL
# ============================================================
elif page == "📧 Sync ยอดจาก Email":
    st.markdown("<div class='page-title'>📧 Sync ยอดเดลิเวอรี่จาก Email</div>", unsafe_allow_html=True)
    display_status_notification()
    if st.button("🔄 โหลดข้อมูลใหม่จาก Email (ผ่าน Sheets)"):
        if conn_gs:
            df_gmail = conn_gs.read(worksheet="Income", ttl=0)
            if not df_gmail.empty:
                st.write("📊 ตัวอย่างข้อมูลล่าสุดที่พบในชีต:")
                st.dataframe(df_gmail.tail(5))
                st.session_state.df_email_sync = df_gmail
    if 'df_email_sync' in st.session_state:
        if st.button("🚀 ยืนยันนำข้อมูลเข้า Cloud Database", type="primary"):
            if save_to_tab(st.session_state.df_email_sync, "Income"):
                st.session_state.status_msg = "ย้ายข้อมูลรายรับจากอีเมลเข้าคลาวด์เรียบร้อย!"
                st.session_state.status_type = "success"
                del st.session_state.df_email_sync
                st.rerun()

# ============================================================
# 12. PAGE — LINE MAN INSIGHT
# ============================================================
elif page == "🎯 LINE MAN Insight":
    st.markdown("<div class='page-title'>🎯 LINE MAN Insight</div>", unsafe_allow_html=True)
    display_status_notification()
    method = st.radio("วิธีอัปโหลดข้อมูล:", ["📷 ถ่ายรูปสด/อัปโหลดรูป", "⌨️ วางข้อความ"], horizontal=True)

    res_insight = []
    if method == "📷 ถ่ายรูปสด/อัปโหลดรูป":
        img_cam = None
        if st.toggle("📸 เปิดใช้งานกล้องเพื่อถ่ายรูปสด"):
            img_cam = st.camera_input("📸 ถ่ายรูปสด")
        img_files = st.file_uploader("หรืออัปโหลดรูปภาพ", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if st.button("🪄 วิเคราะห์เชิงลึก", type="primary"):
            if img_cam:
                res = process_extraction(img_cam.read(), "Insight", is_bytes=True, mime="image/jpeg")
                if res: res_insight.extend(res)
            if img_files:
                for f in img_files:
                    m_type = "image/jpeg" if f.name.lower().endswith("jpg") else f"image/{f.name.split('.')[-1].lower()}"
                    res = process_extraction(f.read(), "Insight", is_bytes=True, mime=m_type)
                    if res: res_insight.extend(res)
            if res_insight:
                st.session_state.tmp_insight = pd.DataFrame(res_insight)

    elif method == "⌨️ วางข้อความ":
        txt = st.text_area("วางข้อมูลข้อความ:")
        if txt and st.button("🪄 วิเคราะห์ข้อความ", type="primary"):
            res = process_extraction(txt, "Insight")
            if res: st.session_state.tmp_insight = pd.DataFrame(res)

    if 'tmp_insight' in st.session_state and not st.session_state.tmp_insight.empty:
        edited_insight = st.data_editor(st.session_state.tmp_insight, use_container_width=True, num_rows="dynamic")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 ยืนยันบันทึก Insight", type="primary"):
                if save_to_tab(edited_insight, "LM_Insight"):
                    st.session_state.status_msg = "บันทึกสถิติข้อมูล LINE MAN Insight เรียบร้อย!"
                    st.session_state.status_type = "success"
                    del st.session_state.tmp_insight
                    st.rerun()
        with c2:
            if st.button("🗑️ ล้างรายการ"):
                del st.session_state.tmp_insight
                st.rerun()

    st.divider()
    df_insight_db = load_insight_data()
    if not df_insight_db.empty and 'type' in df_insight_db.columns:
        st.markdown("<div class='section-title'>🍜 อันดับเมนูขายดี (สะสม)</div>", unsafe_allow_html=True)
        df_menu = df_insight_db[df_insight_db['type'] == 'Menu'].copy()
        if not df_menu.empty:
            df_menu['qty'] = pd.to_numeric(df_menu['qty'], errors='coerce').fillna(0)
            top_menu = df_menu.groupby('name')['qty'].sum().sort_values(ascending=False).reset_index()
            col_g1, col_g2 = st.columns([2, 1])
            with col_g1:
                fig_menu = px.bar(top_menu, x='qty', y='name', orientation='h', title="เมนูยอดฮิต", color_discrete_sequence=[pastel_colors[0]])
                fig_menu.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_menu, use_container_width=True)
            with col_g2:
                st.info(f"**💡 AI แนะนำ:**\nสินค้าขายดีที่สุดคือ **'{top_menu.iloc[0]['name']}'** คุมสต็อกตัวนี้ให้ดีครับ")

        st.markdown("<div class='section-title'>📈 ประสิทธิภาพโฆษณาและโปรโมชั่น</div>", unsafe_allow_html=True)
        df_mkt = df_insight_db[df_insight_db['type'] == 'Marketing'].copy()
        if not df_mkt.empty:
            df_mkt['qty'] = pd.to_numeric(df_mkt['qty'], errors='coerce').fillna(0)
            mkt_stats = df_mkt.groupby('name')['qty'].sum().reset_index()
            ad_orders = mkt_stats[mkt_stats['name'].str.contains("โฆษณา|Listing", na=False)]['qty'].sum()
            promo_use = mkt_stats[mkt_stats['name'].str.contains("โปรโมชั่น|ส่วนลด", na=False)]['qty'].sum()
            m1, m2 = st.columns(2)
            m1.metric("🎯 ออเดอร์จากโฆษณา", f"{ad_orders:,.0f} รายการ")
            m2.metric("🎁 จำนวนการใช้โปรโมชั่น", f"{promo_use:,.0f} ครั้ง")

# ============================================================
# 13. PAGE — AI AGENT
# ============================================================
elif page == "🤖 AI Agent":
    st.markdown("<div class='page-title'>🤖 AI Agent</div>", unsafe_allow_html=True)
    display_status_notification()
    df_i, df_e = load_income_data(), load_expense_data()
    if not df_i.empty or not df_e.empty:
        st.info("🤖 AI Agent - ยังไม่พร้อมใช้งานในเวอร์ชันนี้ กำลังพัฒนาครับพี่กุลเศรษฐ์")
    else:
        st.warning("⚠️ ยังไม่มีข้อมูลในระบบ")

# ============================================================
# 14. PAGE — ALL DATA
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 จัดการฐานข้อมูลหลังบ้าน (Editable)</div>", unsafe_allow_html=True)
    display_status_notification()
    st.info("💡 พี่สามารถคลิกแก้ไขตารางได้โดยตรง และต้องกรอกรหัสความปลอดภัยก่อนกดยืนยันบันทึกครับ")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Income", "📦 Expense", "📅 Monthly", "🎯 Insight"])

    with tab1:
        st.markdown("<div class='section-title'>แก้ไขตารางรายรับ (Income)</div>", unsafe_allow_html=True)
        df_i = load_income_data()
        if not df_i.empty:
            if 'id' in df_i.columns: df_i = df_i[[c for c in df_i.columns if c != 'id'] + ['id']]
            edited_income = st.data_editor(df_i, use_container_width=True, num_rows="dynamic", key="editor_inc")
            col_btn, col_pin = st.columns([3, 1])
            with col_pin: pin_inc = st.text_input("รหัสผ่าน", type="password", max_chars=4, placeholder="PIN 4 หลัก", key="pin_i", label_visibility="collapsed")
            with col_btn:
                if st.button("💾 ยืนยันบันทึกการแก้ไข Income", type="primary", use_container_width=True):
                    if pin_inc == "7727":
                        if update_full_table(edited_income, "income"): 
                            st.session_state.status_msg = "แก้ไขโครงสร้างตารางรายรับบนฐานข้อมูลสำเร็จ!"
                            st.session_state.status_type = "success"
                            st.rerun()
                    else: st.error("❌ รหัสความปลอดภัยไม่ถูกต้อง")
        else: st.info("ไม่มีข้อมูล")

    with tab2:
        st.markdown("<div class='section-title'>แก้ไขตารางรายจ่าย (Expense)</div>", unsafe_allow_html=True)
        df_e = load_expense_data()
        if not df_e.empty:
            if 'id' in df_e.columns: df_e = df_e[[c for c in df_e.columns if c != 'id'] + ['id']]
            edited_expense = st.data_editor(df_e, use_container_width=True, num_rows="dynamic", key="editor_exp")
            col_btn, col_pin = st.columns([3, 1])
            with col_pin: pin_exp = st.text_input("รหัสผ่าน", type="password", max_chars=4, placeholder="PIN 4 หลัก", key="pin_e", label_visibility="collapsed")
            with col_btn:
                if st.button("💾 ยืนยันบันทึกการแก้ไข Expense", type="primary", use_container_width=True):
                    if pin_exp == "7727":
                        if update_full_table(edited_expense, "expense"): 
                            st.session_state.status_msg = "แก้ไขโครงสร้างตารางรายจ่ายบนฐานข้อมูลสำเร็จ!"
                            st.session_state.status_type = "success"
                            st.rerun()
                    else: st.error("❌ รหัสความปลอดภัยไม่ถูกต้อง")
        else: st.info("ไม่มีข้อมูล")

    with tab3:
        st.markdown("<div class='section-title'>แก้ไขสรุปรายเดือน (Monthly)</div>", unsafe_allow_html=True)
        df_m = load_monthly_data()
        if not df_m.empty:
            if 'id' in df_m.columns: df_m = df_m[[c for c in df_m.columns if c != 'id'] + ['id']]
            edited_monthly = st.data_editor(df_m, use_container_width=True, num_rows="dynamic", key="editor_mon")
            col_btn, col_pin = st.columns([3, 1])
            with col_pin: pin_mon = st.text_input("รหัสผ่าน", type="password", max_chars=4, placeholder="PIN 4 หลัก", key="pin_m", label_visibility="collapsed")
            with col_btn:
                if st.button("💾 ยืนยันบันทึกการแก้ไข Monthly", type="primary", use_container_width=True):
                    if pin_mon == "7727":
                        if update_full_table(edited_monthly, "monthly"): 
                            st.session_state.status_msg = "แก้ไขโครงสร้างตารางรายงานประจำเดือนบนฐานข้อมูลสำเร็จ!"
                            st.session_state.status_type = "success"
                            st.rerun()
                    else: st.error("❌ รหัสความปลอดภัยไม่ถูกต้อง")
        else: st.info("ไม่มีข้อมูล")

    with tab4:
        st.markdown("<div class='section-title'>แก้ไขตาราง LINE MAN Insight</div>", unsafe_allow_html=True)
        df_in = load_insight_data()
        if not df_in.empty:
            if 'id' in df_in.columns: df_in = df_in[[c for c in df_in.columns if c != 'id'] + ['id']]
            edited_insight = st.data_editor(df_in, use_container_width=True, num_rows="dynamic", key="editor_ins")
            col_btn, col_pin = st.columns([3, 1])
            with col_pin: pin_ins = st.text_input("รหัสผ่าน", type="password", max_chars=4, placeholder="PIN 4 หลัก", key="pin_in", label_visibility="collapsed")
            with col_btn:
                if st.button("💾 ยืนยันบันทึกการแก้ไข Insight", type="primary", use_container_width=True):
                    if pin_ins == "7727":
                        if update_full_table(edited_insight, "lineman_insight"): 
                            st.session_state.status_msg = "แก้ไขโครงสร้างตารางข้อมูลอินไซต์สำเร็จ!"
                            st.session_state.status_type = "success"
                            st.rerun()
                    else: st.error("❌ รหัสความปลอดภัยไม่ถูกต้อง")
        else: st.info("ไม่มีข้อมูล")

# ============================================================
# 🛠️ ADMIN MIGRATION
# ============================================================
elif page == "🛠️ Admin Migration":
    st.markdown("<div class='page-title'>🛠️ Admin Migration</div>", unsafe_allow_html=True)
    display_status_notification()
    run_migration_process()

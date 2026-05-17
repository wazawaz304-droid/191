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
    --bg-color: #FFFAFA; /* Snow White */
}

html, body, [class*="css"] { 
    font-family: 'IBM Plex Sans Thai', sans-serif !important; 
    background-color: var(--bg-color);
}

#MainMenu, footer { visibility: hidden; }
header { background-color: transparent !important; }

/* Sidebar Pastel */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #A8E6CF 0%, #DCEDC1 100%) !important;
}
[data-testid="stSidebar"] * { color: #555 !important; }

/* Metric Cards */
[data-testid="stMetric"] {
    background: white !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.03) !important;
    border: none !important;
}
[data-testid="stMetricValue"] { font-weight: 500; color: #555 !important; }

/* Buttons */
.stButton > button {
    border-radius: 25px !important;
    background-color: #A8E6CF !important;
    color: #555 !important;
    font-weight: 600 !important;
    border: none !important;
    transition: 0.3s;
}
.stButton > button:hover {
    background-color: #FFD3B6 !important;
    transform: scale(1.02);
}

.page-title { font-size: 2rem; font-weight: 700; color: #555; margin-bottom: 1.5rem; }
.section-title { font-size: 1.1rem; font-weight: 600; color: #555; margin: 1.5rem 0 1rem; padding-left: 0.5rem; border-left: 4px solid var(--primary-color); }
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
# 3. DATA LOADING & UPDATE FUNCTIONS
# ============================================================

@st.cache_data(ttl=60)
def load_data_sql(table_name):
    if conn_sb is None: return pd.DataFrame()
    try:
        date_col = "data" if table_name == "lineman_insight" else ("month_year" if table_name == "monthly" else "date")
        query = f"SELECT * FROM {table_name} ORDER BY {date_col} DESC"
        return conn_sb.query(query)
    except:
        return pd.DataFrame()

def load_income_data(): return load_data_sql("income")
def load_expense_data(): return load_data_sql("expense")
def load_monthly_data(): return load_data_sql("monthly")
def load_insight_data(): return load_data_sql("lineman_insight")

def clean_numeric(df, col_name):
    if col_name in df.columns:
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

# ฟังก์ชันใหม่สำหรับการแก้ไขข้อมูลแบบ Overwrite (Editable Table)
def update_full_table(df, table_name):
    if conn_sb is None or df.empty: return False
    try:
        # เตรียมข้อมูล: ลบ unit_price ออกถ้าเป็นตาราง expense (เพราะเป็น Generated Column ใน DB)
        save_df = df.copy()
        if table_name == "expense" and "unit_price" in save_df.columns:
            save_df = save_df.drop(columns=["unit_price"])
        
        # จัดการค่าว่าง
        save_df = save_df.where(pd.notnull(save_df), None)
        
        # ใช้ Transaction เพื่อความปลอดภัย: ลบของเก่าและเสียบของใหม่
        with conn_sb.engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {table_name}"))
            save_df.to_sql(table_name, connection, if_exists='append', index=False, method='multi')
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

# ============================================================
# 4. CORE SAVE LOGIC (FOR AI INPUTS)
# ============================================================

def save_to_tab(df, tab):
    if conn_sb is None or df.empty: return False
    try:
        table_map = {"Income": "income", "Expense": "expense", "Monthly": "monthly", "LM_Insight": "lineman_insight"}
        table_name = table_map.get(tab, tab.lower())
        save_df = df.copy()
        save_df.columns = [str(c).strip().lower() for c in save_df.columns]
        
        if table_name == "income":
            save_df['type'] = 'Income'
            if 'date' in save_df.columns: save_df['date'] = pd.to_datetime(save_df['date']).dt.date
        elif table_name == "expense":
            save_df['type'] = 'Expense'
            if "unit_price" in save_df.columns: save_df = save_df.drop(columns=["unit_price"])
            if 'date' in save_df.columns: save_df['date'] = pd.to_datetime(save_df['date']).dt.date
            
        save_df = save_df.where(pd.notnull(save_df), None)
        save_df.to_sql(table_name, conn_sb.engine, if_exists='append', index=False, method='multi')
        st.cache_data.clear()
        return True
    except Exception as e:
        if "unique constraint" in str(e).lower(): st.warning("⚠️ ข้อมูลนี้มีอยู่ในระบบแล้ว")
        else: st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 5. AI EXTRACTION
# ============================================================

def process_extraction(data, p_type, is_bytes=False, mime=None):
    if client is None: return []
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-2.0-flash-lite-preview-02-05"
    
    if p_type == "Expense":
        p = f"สกัดข้อมูลรายจ่ายร้านอาหารเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]"
    else:
        p = f"สกัดรายรับเดลิเวอรี่ร้าน @304 เป็น JSON: [{{'date': '{now_str}', 'app': 'GrabFood/LINE MAN/ShopeeFood', 'net_income': 0, 'gross_sales': 0, 'gp_amount': 0, 'type': 'Income'}}]"
    
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=p), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[p, data])
        
        text_res = res.text.strip()
        start, end = text_res.find('['), text_res.rfind(']') + 1
        return json.loads(text_res[start:end]) if start != -1 else []
    except:
        return []

# ============================================================
# 6. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("<h1 style='color:#555; margin-bottom:0;'>🍜 Nave 304</h1>", unsafe_allow_html=True)
    st.divider()
    page = st.radio("เมนูหลัก", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "📧 Sync ยอดจาก Email", "🎯 LINE MAN Insight", "📋 ข้อมูลทั้งหมด", "🛠️ Admin Migration"], label_visibility="collapsed")
    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 7. PAGE — DASHBOARD (ปรับปรุง: ล็อกสีเข้มชัดเจนแยกตามแอปเดลิเวอรี่)
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    df_i, df_e = load_income_data(), load_expense_data()
    
    t_inc = clean_numeric(df_i, 'net_income').sum() if not df_i.empty else 0
    t_exp = clean_numeric(df_e, 'total_price').sum() if not df_e.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรสะสม", f"฿{t_inc - t_exp:,.0f}")

    st.divider()
    tab1, tab2 = st.tabs(["📈 กราฟรายรับ", "📦 สัดส่วนรายจ่าย"])
    with tab1:
        if not df_i.empty:
            # 🎨 ตั้งค่า Map สีเข้มชัดเจนตามที่พี่สั่งไว้
            app_colors = {
                'LINE MAN': '#2ecc71',      /* เขียวอ่อนสดใส */
                'GrabFood': '#064e3b',      /* เขียวเข้มตัวจริง */
                'ShopeeFood': '#f97316',    /* สีส้มเด่นชัด */
                'หน้าร้าน': '#8b5cf6'        /* สีม่วงโมเดิร์น */
            }
            fig = px.bar(
                df_i, 
                x='date', 
                y='net_income', 
                color='app', 
                title="รายรับรายวันแยกแอป", 
                color_discrete_map=app_colors
            )
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    with tab2:
        if not df_e.empty:
            fig_p = px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่าย", color_discrete_sequence=pastel_colors)
            st.plotly_chart(fig_p, use_container_width=True)

# ============================================================
# 8. PAGE — MONTHLY
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='page-title'>📈 วิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    df_m = load_monthly_data()
    if not df_m.empty:
        st.dataframe(df_m, use_container_width=True)

# ============================================================
# 9. PAGE — INCOME
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์เอง", "📷 ถ่ายรูปหน้าจอ"], horizontal=True)
    if method == "⌨️ พิมพ์เอง":
        txt = st.text_area("วางสรุปยอดขายจากแอป:")
        if txt and st.button("🪄 วิเคราะห์"):
            res = process_extraction(txt, "Income")
            if res: st.session_state.tmp_inc = pd.DataFrame(res)
    
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกลง Cloud"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.success("บันทึกสำเร็จ!")
                st.rerun()

# ============================================================
# 10. PAGE — EXPENSE
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่าย</div>", unsafe_allow_html=True)
    txt = st.text_area("พิมพ์รายการซื้อวัตถุดิบ:")
    if txt and st.button("🪄 วิเคราะห์"):
        res = process_extraction(txt, "Expense")
        if res: st.session_state.tmp_exp = pd.DataFrame(res)
        
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกลง Cloud"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.success("บันทึกสำเร็จ!")
                st.rerun()

# ============================================================
# 11. PAGE — SYNC EMAIL
# ============================================================
elif page == "📧 Sync ยอดจาก Email":
    st.markdown("<div class='page-title'>📧 Sync ยอดจาก Email</div>", unsafe_allow_html=True)
    if st.button("🔄 ดึงข้อมูลล่าสุดจาก Sheets"):
        if conn_gs:
            df = conn_gs.read(worksheet="Income", ttl=0)
            if not df.empty:
                st.dataframe(df.tail(5))
                st.session_state.email_sync = df
    if 'email_sync' in st.session_state:
        if st.button("🚀 ยืนยันนำเข้า Supabase"):
            if save_to_tab(st.session_state.email_sync, "Income"):
                st.success("นำเข้าข้อมูลสำเร็จ!")
                del st.session_state.email_sync

# ============================================================
# 14. PAGE — ALL DATA (อัปเกรด: แก้ไขได้และมีปุ่มยืนยัน)
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 จัดการฐานข้อมูล (Editable)</div>", unsafe_allow_html=True)
    st.info("💡 พี่กุลเศรษฐ์สามารถแก้ข้อมูลในตารางได้เลยครับ เสร็จแล้วอย่าลืมกดปุ่ม 'บันทึกการแก้ไข' ด้านล่างตารางนะครับ")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Income", "📦 Expense", "📅 Monthly", "🎯 Insight"])

    with tab1:
        st.markdown("<div class='section-title'>แก้ไขรายรับ (Income)</div>", unsafe_allow_html=True)
        df_i = load_income_data()
        if not df_i.empty:
            # ย้าย ID ไปหลังสุดเพื่อความสวยงาม
            cols = [c for c in df_i.columns if c != 'id'] + ['id']
            df_i = df_i[cols]
            
            # ใช้ st.data_editor เพื่อให้แก้ไขได้
            edited_income = st.data_editor(df_i, use_container_width=True, num_rows="dynamic", key="editor_inc")
            
            if st.button("💾 ยืนยันบันทึกการแก้ไข Income", type="primary"):
                if update_full_table(edited_income, "income"):
                    st.success("✅ อัปเดตข้อมูลรายรับเรียบร้อย!")
                    st.rerun()
        else: st.info("ยังไม่มีข้อมูล")

    with tab2:
        st.markdown("<div class='section-title'>แก้ไขรายจ่าย (Expense)</div>", unsafe_allow_html=True)
        df_e = load_expense_data()
        if not df_e.empty:
            cols = [c for c in df_e.columns if c != 'id'] + ['id']
            df_e = df_e[cols]
            
            edited_expense = st.data_editor(df_e, use_container_width=True, num_rows="dynamic", key="editor_exp")
            
            if st.button("💾 ยืนยันบันทึกการแก้ไข Expense", type="primary"):
                if update_full_table(edited_expense, "expense"):
                    st.success("✅ อัปเดตข้อมูลรายจ่ายเรียบร้อย!")
                    st.rerun()
        else: st.info("ยังไม่มีข้อมูล")

    with tab3:
        st.markdown("<div class='section-title'>แก้ไขสรุปรายเดือน (Monthly)</div>", unsafe_allow_html=True)
        df_m = load_monthly_data()
        if not df_m.empty:
            cols = [c for c in df_m.columns if c != 'id'] + ['id']
            df_m = df_m[cols]
            
            edited_monthly = st.data_editor(df_m, use_container_width=True, num_rows="dynamic", key="editor_mon")
            
            if st.button("💾 ยืนยันบันทึกการแก้ไข Monthly", type="primary"):
                if update_full_table(edited_monthly, "monthly"):
                    st.success("✅ อัปเดตข้อมูลรายเดือนเรียบร้อย!")
                    st.rerun()

    with tab4:
        st.markdown("<div class='section-title'>แก้ไข LINE MAN Insight</div>", unsafe_allow_html=True)
        df_in = load_insight_data()
        if not df_in.empty:
            cols = [c for c in df_in.columns if c != 'id'] + ['id']
            df_in = df_in[cols]
            
            edited_insight = st.data_editor(df_in, use_container_width=True, num_rows="dynamic", key="editor_ins")
            
            if st.button("💾 ยืนยันบันทึกการแก้ไข Insight", type="primary"):
                if update_full_table(edited_insight, "lineman_insight"):
                    st.success("✅ อัปเดตข้อมูล Insight เรียบร้อย!")
                    st.rerun()

# ============================================================
# 🛠️ ADMIN MIGRATION
# ============================================================
elif page == "🛠️ Admin Migration":
    run_migration_process()

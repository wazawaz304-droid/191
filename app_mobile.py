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
# 1. PAGE CONFIG & STYLING (แก้ไขเรื่องเมนูหาย)
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

/* 폰트 설정 */
html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif !important; }

/* ปรับแต่ง Sidebar ให้เมนูชัดเจนและไม่บังเนื้อหา */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0d3d26 0%, #1a6b4a 100%) !important;
}

/* สีตัวอักษรใน Sidebar */
section[data-testid="stSidebar"] .stMarkdown p, 
section[data-testid="stSidebar"] span, 
section[data-testid="stSidebar"] label { 
    color: rgba(255,255,255,0.95) !important; 
}

/* เมนู Radio ใน Sidebar */
section[data-testid="stSidebar"] .stRadio label {
    padding: 0.6rem 1rem; border-radius: 8px; display: block;
    transition: background 0.2s; font-size: 0.9rem; cursor: pointer;
    color: white !important;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.1) !important; }

/* Metric Cards ในหน้าหลัก */
[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* Custom Cards */
.success-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 1rem; color: #166534; margin-bottom: 1rem; }
.warn-card { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 1rem; color: #92400e; margin-bottom: 1rem; }
.page-title { font-size: 1.6rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. DATA LAYER (เน้นความปลอดภัย ข้อมูลห้ามหาย)
# ============================================================
@st.cache_resource
def get_conn():
    try: return st.connection("gsheets", type=GSheetsConnection)
    except: return None

conn = get_conn()

def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        # ใช้ ttl=0 เพื่อดึงค่าสดเสมอ ป้องกันข้อมูลใหม่ไม่โชว์
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
        # ปรับแต่งข้อมูลก่อนบันทึก
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
        elif tab == "Expense":
            df['type'] = 'Expense'
            # คำนวณราคาต่อหน่วย
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        
        # ป้องกันข้อมูลหาย: เอาของใหม่ต่อท้ายของเดิม (Append)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 3. AI LAYER (สกัดข้อมูลจาก บิล/เสียง/ข้อความ)
# ============================================================
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    try:
        client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
        now_str = datetime.now().strftime("%Y-%m-%d")
        
        if p_type == "Expense":
            names = ", ".join(existing_names) if existing_names else "ไม่มี"
            prompt = f"สกัดข้อมูลรายจ่าย JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. ใช้ชื่อเดิมถ้าคล้าย: [{names}]"
        else:
            prompt = f"สกัดข้อมูลรายได้ JSON: [{{'date': '{now_str}', 'app': 'GrabFood/LINE MAN/ShopeeFood/หน้าร้าน', 'net_income': 0}}]"

        prompt += " ตอบเฉพาะ PURE JSON เท่านั้น"
        
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model="models/gemini-3.1-flash-lite-preview", contents=contents)
        else:
            res = client.models.generate_content(model="models/gemini-3.1-flash-lite-preview", contents=[prompt, data])

        text = res.text.strip()
        # แก้ไขจุดที่เคย Syntax Error (สกัด JSON แบบปลอดภัย)
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
        return []
    except Exception as e:
        st.error(f"AI Error: {e}")
        return []

# ============================================================
# 4. SIDEBAR & NAVIGATION (สร้าง Menu ก่อนใช้งาน)
# ============================================================
st.sidebar.markdown("## 🍜 Nave 304")
st.sidebar.caption("AI Business Master")
st.sidebar.divider()

page = st.sidebar.radio(
    "เมนู",
    ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"],
    label_visibility="collapsed"
)

st.sidebar.divider()
with st.sidebar.expander("⚙️ ตั้งค่า Break-even"):
    st.session_state.setdefault("be_rent", 4000)
    st.session_state["be_rent"] = st.number_input("ค่าเช่า/เดือน", value=st.session_state["be_rent"])
    # สามารถเพิ่มค่าอื่นๆ ได้ที่นี่

if st.sidebar.button("🔄 รีเฟรชข้อมูล"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# 5. PAGE LOGIC
# ============================================================

# --- Dashboard ---
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
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
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น", f"฿{t_inc - t_exp:,.0f}")

    st.divider()
    if not df_i.empty:
        fig = px.bar(df_i.groupby('app')['net_income'].sum().reset_index(), x='app', y='net_income', color='app', title="สัดส่วนรายได้แยกตามช่องทาง")
        st.plotly_chart(fig, use_container_width=True)

# --- บันทึกรายรับ (ครบทุกช่องทาง) ---
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ ข้อความ", "📸 รูปภาพ/อัปโหลด", "🎙️ เสียง", "📁 PDF"], horizontal=True)
    res = None

    if method == "⌨️ ข้อความ":
        txt = st.text_area("วางข้อความรายงานยอดขาย:")
        if st.button("🪄 วิเคราะห์"): res = process_extraction(txt, "Income")
    elif method == "📸 รูปภาพ/อัปโหลด":
        img = st.file_uploader("เลือกรูปภาพ", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์รูป"): res = process_extraction(img.read(), "Income", is_bytes=True, mime="image/jpeg")
    elif method == "🎙️ เสียง":
        audio = st.audio_input("บันทึกเสียงยอดขาย")
        if audio and st.button("🪄 วิเคราะห์เสียง"): res = process_extraction(audio.read(), "Income", is_bytes=True, mime=audio.type)
    elif method == "📁 PDF":
        pdf = st.file_uploader("เลือกไฟล์ PDF", type=['pdf'])
        if pdf and st.button("🪄 วิเคราะห์ PDF"): res = process_extraction(pdf.read(), "Income", is_bytes=True, mime="application/pdf")

    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
        st.success("สกัดข้อมูลสำเร็จ!")
    
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 ยืนยันบันทึก"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- บันทึกรายจ่าย ---
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่าย</div>", unsafe_allow_html=True)
    df_exp_db = load_data("Expense")
    ex_names = df_exp_db['name'].unique().tolist() if not df_exp_db.empty else []
    
    cam = st.camera_input("แสกนบิลรายจ่าย")
    if cam and st.button("🪄 วิเคราะห์บิล"):
        res = process_extraction(cam.getvalue(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=ex_names)
        if res: st.session_state.tmp_exp = pd.DataFrame(res)

    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกรายจ่าย"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- ข้อมูลทั้งหมด ---
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 ข้อมูลดิบในระบบ</div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Income", "Expense", "Monthly"])
    with tab1: st.dataframe(load_data("Income"), use_container_width=True)
    with tab2: st.dataframe(load_data("Expense"), use_container_width=True)
    with tab3: st.dataframe(load_data("Monthly"), use_container_width=True)

# (หน้า AI Agent และ วิเคราะห์รายเดือน สามารถเพิ่ม Logic เข้าไปในลักษณะเดียวกันครับ)

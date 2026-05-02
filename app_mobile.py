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
# 1. CONFIG & CSS (Modern Look)
# ============================================================
st.set_page_config(page_title="Nave 304 Master", layout="wide", page_icon="🍜")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif; }
    [data-testid="stMetric"] { background: white; border-radius: 12px; border: 1px solid #eee; padding: 15px; }
    .stButton>button { border-radius: 10px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CORE FUNCTIONS
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

def safe_parse_json(text):
    if not text: return []
    try:
        raw = text.strip()
        if "```" in raw: raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw.strip())
    except: return []

def call_ai(prompt, contents=None):
    if not client: return None
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt] + (contents or []))
        return res.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def save_to_tab(df, tab):
    try:
        if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)
        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except: return False

# ============================================================
# 3. SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.title("🍜 Nave 304 Master")
    page = st.radio("เมนูหลัก", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "👷 ค่าแรงพนักงาน", "📈 วิเคราะห์รายเดือน", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])
    st.divider()
    with st.expander("⚙️ ตั้งค่าต้นทุนคงที่"):
        rent_day = st.number_input("ค่าเช่า/วัน", value=667)
        util_day = st.number_input("น้ำ+ไฟ/วัน", value=200)
        pkg_pct = st.number_input("Packaging %", value=2.0)
    if st.button("🔄 รีเฟรชข้อมูล"): st.rerun()

# ============================================================
# 4. PAGE: DASHBOARD (สรุปรายวัน-รายจ่าย)
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 Dashboard รายวัน")
    df_i, df_e, df_l = load_data("Income"), load_data("Expense"), load_data("Labor")
    
    inc = clean_numeric(df_i, "net_income").sum()
    exp = clean_numeric(df_e, "total_price").sum()
    lab = clean_numeric(df_l, "amount").sum()
    net = inc - exp - lab - (inc * pkg_pct / 100) - (rent_day + util_day)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับสะสม", f"฿{inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อก", f"฿{exp:,.0f}")
    c3.metric("👷 ค่าแรง", f"฿{lab:,.0f}")
    c4.metric("⚖️ กำไรสุทธิ", f"฿{net:,.0f}", delta=f"{net:,.0f}")

# ============================================================
# 5. PAGE: บันทึกรายรับ (กู้คืนปุ่ม ถ่ายภาพ/อัปโหลด/เสียง)
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.segmented_control("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], default="หน้าร้าน")
    method = st.radio("เลือกวิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกด้วยเสียง", "📷 ถ่ายภาพ/อัปโหลดภาพ"], horizontal=True)
    
    res = None
    today = datetime.now().strftime("%Y-%m-%d")

    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ป้อนข้อมูลยอดขาย:", placeholder="เช่น Grab วันนี้ 1200 บาท 30 ออเดอร์")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"):
            res = safe_parse_json(call_ai(f"สกัดข้อมูล {rtype} เป็น JSON: [{{'date': '{today}', 'app': 'ชื่อแอป', 'net_income': 0, 'order_count': 0}}] จาก: {txt}"))

    elif method == "🎙️ บันทึกด้วยเสียง":
        audio = st.audio_input("กดปุ่มไมค์เพื่อพูดรายการรายรับ")
        if audio and st.button("🚀 ประมวลผลเสียง"):
            res = safe_parse_json(call_ai(f"สกัดข้อมูล {rtype} จากเสียงเป็น JSON", contents=[types.Part.from_bytes(data=audio.read(), mime_type=audio.type)]))

    elif method == "📷 ถ่ายภาพ/อัปโหลดภาพ":
        sub_m = st.radio("ช่องทาง:", ["📸 ใช้กล้องสด", "📁 อัปโหลดไฟล์รูป"], horizontal=True)
        img = st.camera_input("ถ่ายรูปหน้าจอแอป") if sub_m == "📸 ใช้กล้องสด" else st.file_uploader("เลือกรูปภาพ", type=['png','jpg','jpeg'])
        if img and st.button("🪄 วิเคราะห์รูปภาพ"):
            res = safe_parse_json(call_ai(f"สกัดยอด {rtype} จากรูปเป็น JSON", contents=[types.Part.from_bytes(data=img.read() if sub_m=="📁 อัปโหลดไฟล์รูป" else img.getvalue(), mime_type="image/jpeg")]))

    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกลงระบบ"):
            target = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
            if save_to_tab(edited, target):
                del st.session_state.tmp_inc
                st.success("บันทึกสำเร็จ!")
                st.rerun()

# ============================================================
# 6. PAGE: บันทึกรายจ่าย (กู้คืนปุ่ม ถ่ายภาพ/อัปโหลด/เสียง)
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    method_ex = st.radio("เลือกวิธีบันทึก:", ["📸 ถ่ายภาพบิล", "📁 อัปโหลดไฟล์บิล", "🎙️ บันทึกด้วยเสียง", "⌨️ พิมพ์เอง"], horizontal=True)
    
    res_ex = None
    if method_ex == "📸 ถ่ายภาพบิล":
        cam_ex = st.camera_input("สแกนบิลวัตถุดิบ")
        if cam_ex and st.button("🪄 อ่านบิล"):
            res_ex = safe_parse_json(call_ai("สกัดรายจ่ายเป็น JSON: [{'date': 'YYYY-MM-DD', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}]", contents=[types.Part.from_bytes(data=cam_ex.getvalue(), mime_type="image/jpeg")]))

    elif method_ex == "📁 อัปโหลดไฟล์บิล":
        file_ex = st.file_uploader("อัปโหลดรูปบิล", type=['png','jpg','jpeg','pdf'])
        if file_ex and st.button("🪄 อ่านไฟล์"):
            res_ex = safe_parse_json(call_ai("สกัดรายจ่ายจากไฟล์เป็น JSON", contents=[types.Part.from_bytes(data=file_ex.read(), mime_type=file_ex.type)]))

    elif method_ex == "🎙️ บันทึกด้วยเสียง":
        aud_ex = st.audio_input("พูดรายการที่ซื้อ (เช่น ไก่ 2 โล 300 บาท)")
        if aud_ex and st.button("🚀 แปลงเสียง"):
            res_ex = safe_parse_json(call_ai("สกัดรายจ่ายจากเสียงเป็น JSON", contents=[types.Part.from_bytes(data=aud_ex.read(), mime_type=aud_ex.type)]))

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกรายจ่าย"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.success("บันทึกรายจ่ายสำเร็จ!")
                st.rerun()

# ============================================================
# 7. PAGE: ค่าแรงพนักงาน (รวมฟังก์ชัน AI)
# ============================================================
elif page == "👷 ค่าแรงพนักงาน":
    st.header("👷 บันทึกค่าแรงพนักงาน")
    l_method = st.radio("เลือกวิธี:", ["⌨️ พิมพ์ข้อมูล", "🎙️ บันทึกเสียง"], horizontal=True)
    res_l = None
    if l_method == "⌨️ พิมพ์ข้อมูล":
        l_txt = st.text_area("ระบุค่าแรง (เช่น จ่ายน้องนิด 500 บาท)")
        if l_txt and st.button("🪄 วิเคราะห์"):
            res_l = safe_parse_json(call_ai(f"สกัดค่าแรง JSON: [{{'date': '{today}', 'name': 'ชื่อ', 'amount': 0}}] จาก: {l_txt}"))
    elif l_method == "🎙️ บันทึกเสียง":
        l_aud = st.audio_input("พูดรายการค่าแรง")
        if l_aud and st.button("🚀 ประมวลผล"):
            res_l = safe_parse_json(call_ai("สกัดค่าแรงจากเสียงเป็น JSON", contents=[types.Part.from_bytes(data=l_aud.read(), mime_type=l_aud.type)]))
    
    if res_l:
        st.session_state.tmp_lab = pd.DataFrame(res_l)
    if 'tmp_lab' in st.session_state:
        ed_lab = st.data_editor(st.session_state.tmp_lab, use_container_width=True)
        if st.button("💾 บันทึกค่าแรง"):
            if save_to_tab(ed_lab, "Labor"):
                del st.session_state.tmp_lab
                st.rerun()

# --- เมนูอื่นๆ (วิเคราะห์รายเดือน / AI Agent / ข้อมูลทั้งหมด) ---
elif page == "📈 วิเคราะห์รายเดือน":
    st.header("📈 วิเคราะห์รายเดือน")
    df_m = load_sheet("Monthly")
    st.dataframe(df_m)

elif page == "🤖 AI Agent":
    st.header("🤖 AI Agent")
    q = st.chat_input("ปรึกษาธุรกิจ...")
    if q: st.write(call_ai(f"คุณคือที่ปรึกษาธุรกิจร้านเนฟ หมี่ไก่ฉีก คำถาม: {q}"))

elif page == "📋 ข้อมูลทั้งหมด":
    for t in ["Income", "Expense", "Monthly", "Labor"]:
        st.subheader(f"แท็บ {t}")
        st.dataframe(load_data(t), use_container_width=True)

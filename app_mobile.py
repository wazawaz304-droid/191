import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Nave 304 - Business Master", layout="wide", page_icon="📈")

# --- 2. การเชื่อมต่อ ---
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
    st.error(f"⚠️ ไม่พบ API Key ใน Secrets: {e}")

# --- 2.1 ระบบโหลดข้อมูล (แยกแท็บ Income และ Expense) ---
@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()

# --- 3. ฟังก์ชันจัดการข้อมูลและ AI ---

def clean_numeric(df, col_name):
    """ล้างตัวเลขให้พร้อมคำนวณ ป้องกันข้อมูลหาย"""
    if col_name in df.columns:
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

def safe_parse_json(text_response: str):
    """แก้ไข SyntaxError ให้ทำงานได้เสถียรที่สุด"""
    if not text_response: return []
    try:
        content = text_response.strip()
        # ตัด Markdown Code Blocks แบบปลอดภัยในบรรทัดเดียว
        if "```" in content: content = content.split("```")[1]
        if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except:
        return []

def call_gemini_3_1(prompt, contents=None, is_complex_content=False):
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        if response.text:
            st.toast(f"🤖 ประมวลผลด้วย {model_name}", icon="✅")
            return response.text
    except: return None

# (ระบบบันทึกข้อมูลแยกตามประเภท)
def process_extraction(data, p_type, is_bytes=False, mime=None):
    if p_type == "Expense":
        p = "สกัดสินค้าเป็น JSON: [{'date': 'YYYY-MM-DD', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}]"
    elif p_type == "Store":
        p = "สกัดยอดหน้าร้านเป็น JSON: [{'date': 'YYYY-MM-DD', 'app': 'หน้าร้าน', 'net_income': ยอดขาย}]"
    else:
        p = "สกัดรายได้เป็น JSON: [{'date': 'YYYY-MM-DD', 'app': 'ชื่อแอป', 'net_income': ยอดโอน}]"
    
    prompt = p + " ตอบเฉพาะ PURE JSON"
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
        res = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini_3_1(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        return True
    except: return False

# --- 4. UI Layout ---

st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard (แก้ไขข้อมูลหายและกราฟสต๊อก) ---
if page == "📊 Dashboard":
    st.header("📊 สรุปรายงานธุรกิจ")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # คำนวณยอดเงิน
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_e['qty'] = clean_numeric(df_e, 'qty')
    df_e['unit_price'] = df_e['total_price'] / df_e['qty'].replace(0, 1)

    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับสุทธิ", f"฿{t_inc:,.2f}")
    c2.metric("📦 รายจ่ายสต๊อก", f"฿{t_exp:,.2f}")
    c3.metric("📈 กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}")
    
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    
    with tab1:
        if not df_i.empty:
            fig_inc = px.bar(df_i.sort_values('date'), x='date', y='net_income', color='app', title="รายรับรายวันแยกตามช่องทาง")
            st.plotly_chart(fig_inc, use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลรายรับ")

    with tab2:
        if not df_e.empty:
            fig_exp = px.pie(df_e, values='total_price', names='name', title="สัดส่วนรายจ่ายรายวัตถุดิบ")
            st.plotly_chart(fig_exp, use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab3:
        if not df_e.empty and 'name' in df_e.columns:
            st.subheader("วิเคราะห์แนวโน้มราคาต่อหน่วย")
            target = st.selectbox("เลือกวัตถุดิบเพื่อดูกราฟ:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            fig_trend = px.line(df_item, x='date', y='unit_price', markers=True, title=f"ราคา {target} ต่อหน่วย")
            st.plotly_chart(fig_trend, use_container_width=True)

# --- 💰 บันทึกรายรับ (ครบทั้งหน้าร้าน/เดลิเวอรี่/เสียง) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:")
        if txt and st.button("🪄 วิเคราะห์"): res = process_extraction(txt, rtype)
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("พูดรายการรายรับ...")
        if audio and st.button("🚀 ประมวลผลเสียง"):
            res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)
    
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc)
        if st.button("💾 บันทึกลงแท็บ Income"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- 💸 บันทึกรายจ่าย (สแกนบิล/เสียง) ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายสต๊อก")
    method = st.radio("วิธีบันทึก:", ["ยังไม่เลือก", "📸 แสกนบิล", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    if method == "📸 แสกนบิล":
        img = st.camera_input("สแกน")
        if img and st.button("🪄 วิเคราะห์"):
            res_ex = process_extraction(Image.open(img), "Expense")
    elif method == "🎙️ บันทึกเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type)
    
    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- เมนูอื่นๆ ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI Agent")
    q = st.chat_input("ปรึกษาธุรกิจ...")
    if q:
        df_i, df_e = load_data("Income"), load_data("Expense")
        ctx = f"Income: {df_i.tail(5).to_csv()}\nExpense: {df_e.tail(5).to_csv()}"
        st.write(call_gemini_3_1(f"ข้อมูลร้าน:\n{ctx}\nคำถาม: {q}"))

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลดิบ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"))
    with t2: st.dataframe(load_data("Expense"))

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

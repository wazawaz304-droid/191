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
st.set_page_config(page_title="Nave 304 - Multi-Tab System", layout="wide", page_icon="📊")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
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

# --- 2.1 ระบบ Cache ข้อมูลแบบแยกแท็บ ---
@st.cache_data(ttl=60)
def load_data(sheet_name):
    """โหลดข้อมูลโดยระบุชื่อแท็บ (Worksheet)"""
    if conn is None: return pd.DataFrame()
    try:
        # ระบุชื่อแท็บที่ต้องการอ่าน
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()

def call_gemini_3_1(prompt, contents=None, is_complex_content=False):
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        
        if response.text:
            st.toast(f"🤖 AI {model_name} ประมวลผลสำเร็จ", icon="✅")
            return response.text
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
    return None

def safe_parse_json(text_response: str):
    if not text_response: return []
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"): content = content.lstrip()[4:]
        return json.loads(content.strip())
    except: return []

# --- 3. ฟังก์ชัน AI Engine ---

def process_ai_logic(data_input, prompt_type="Expense", is_bytes=False, mime_type=None):
    if prompt_type == "Expense":
        prompt = "สกัดข้อมูลสินค้าเป็น JSON array: [{'date': 'YYYY-MM-DD', 'name': 'ชื่อสินค้า', 'qty': จำนวน, 'unit': 'หน่วย', 'total_price': ราคารวม}] ตอบ PURE JSON"
    elif prompt_type == "Monthly":
        prompt = "สกัดรายงานรายเดือนเป็น JSON array: [{'month_year': 'YYYY-MM', 'platform': 'LM/SF/GF', 'gross': ยอดขายรวม, 'fees': ค่าธรรมเนียม+VAT, 'ads': ค่าโฆษณา+VAT, 'discounts': ส่วนลด, 'net': ยอดโอนสุทธิ}] ตอบ PURE JSON"
    else:
        prompt = "สกัดรายได้รายวันเป็น JSON array: [{'date': 'YYYY-MM-DD', 'app': 'ชื่อแอป', 'gross_sales': ยอดรวม, 'gp_amount': ค่า GP, 'net_income': ยอดโอนสุทธิ}] ตอบ PURE JSON"

    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
        res_text = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_3_1(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# --- 4. บันทึกข้อมูลแบบแยกแท็บ ---

def save_to_tab(df_to_save, tab_name):
    """ฟังก์ชันบันทึกข้อมูลลงแท็บที่ระบุ"""
    if conn is None or df_to_save.empty: return False
    try:
        # อ่านข้อมูลเดิมจากแท็บนั้นมาเพื่อต่อท้าย
        existing_df = load_data(tab_name)
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        
        # อัปเดตกลับไปที่แท็บเดิม
        conn.update(worksheet=tab_name, data=final_df)
        refresh_all_caches()
        st.success(f"✅ บันทึกลงแท็บ {tab_name} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI Layout ---

st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard ---
if page == "📊 Dashboard":
    st.header("📊 แดชบอร์ด (แยกแท็บข้อมูล)")
    
    # โหลดข้อมูลจาก 2 แท็บ
    df_inc = load_data("Income")
    df_exp = load_data("Expense")
    
    tab_ov, tab_monthly = st.tabs(["🏠 ภาพรวม", "📈 รายเดือน"])
    
    with tab_ov:
        # คำนวณรายรับ (Income)
        total_inc = pd.to_numeric(df_inc['net_income'], errors='coerce').sum() if not df_inc.empty else 0
        # คำนวณรายจ่าย (Expense)
        total_exp = pd.to_numeric(df_exp['total_price'], errors='coerce').sum() if not df_exp.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับรวม", f"฿{total_inc:,.2f}")
        c2.metric("รายจ่ายรวม", f"฿{total_exp:,.2f}")
        c3.metric("กำไร", f"฿{total_inc - total_exp:,.2f}")
        
        st.plotly_chart(px.pie(values=[total_inc, total_exp], names=['รายรับ', 'รายจ่าย'], hole=0.4), use_container_width=True)

# --- 💰 บันทึกรายรับ (ลงแท็บ Income) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ (ลงแท็บ Income)")
    mode = st.radio("วิธีนำเข้า:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if mode == "📝 วางข้อความ":
        txt = st.text_area("วางข้อความรายงาน:")
        if txt and st.button("🪄 วิเคราะห์"):
            res = process_ai_logic(txt, prompt_type="Income")
    else:
        f = st.file_uploader("เลือกไฟล์", type=['pdf', 'jpg', 'png'])
        if f and st.button("🪄 วิเคราะห์ไฟล์"):
            res = process_ai_logic(f.read(), prompt_type="Income", is_bytes=True, mime_type=f.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc)
        if st.button("💾 บันทึกรายรับ"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- 💸 บันทึกรายจ่าย (ลงแท็บ Expense) ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย (ลงแท็บ Expense)")
    method = st.radio("วิธีบันทึก:", ["ยังไม่เลือก", "📸 แสกนบิล", "🎙️ บันทึกเสียง"], horizontal=True)
    res = None
    if method == "📸 แสกนบิล":
        img = st.camera_input("สแกนบิล")
        if img and st.button("🪄 วิเคราะห์บิล"):
            res = process_ai_logic(Image.open(img), prompt_type="Expense")
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("พูดรายการ...")
        if audio and st.button("🚀 แปลงเสียง"):
            res = process_ai_logic(audio.read(), prompt_type="Expense", is_bytes=True, mime_type=audio.type)

    if res:
        st.session_state.tmp_exp = pd.DataFrame(res)
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp)
        if st.button("💾 บันทึกรายจ่าย"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- 📋 ข้อมูลทั้งหมด ---
elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลแยกตามแท็บ")
    t1, t2 = st.tabs(["📥 Income Data", "📤 Expense Data"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Expense"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

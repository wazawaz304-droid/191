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
st.set_page_config(page_title="Nave 304 - Business Master", layout="wide", page_icon="🍜")

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
    st.error(f"⚠️ ไม่พบ API Key ใน Secrets: {e}")

# --- 2.1 ระบบ Cache ข้อมูลแยกแท็บ ---
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
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
    return None

def safe_parse_json(text_response: str):
    """แก้ไข Syntax การตัดสตริงให้ปลอดภัยขึ้น"""
    if not text_response: 
        return []
    try:
        content = text_response.strip()
        # ลบ markdown backticks ถ้ามี
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception:
        return []

# --- 3. ฟังก์ชัน AI สำหรับสกัดข้อมูล ---

def process_ai_extraction(data_input, prompt_type="Expense", is_bytes=False, mime_type=None):
    if prompt_type == "Expense":
        p = "สกัดข้อมูลสินค้าเป็น JSON array: [{'date': 'YYYY-MM-DD', 'name': 'ชื่อสินค้า', 'qty': จำนวน, 'unit': 'หน่วย', 'total_price': ราคารวม}]"
    elif prompt_type == "Monthly":
        p = "สกัดรายงานรายเดือนเป็น JSON array: [{'month_year': 'YYYY-MM', 'platform': 'LM/SF/GF', 'gross': ยอดขายรวม, 'fees': ค่าธรรมเนียม+VAT, 'ads': ค่าโฆษณา+VAT, 'discounts': ส่วนลด, 'net_income': ยอดโอนสุทธิ}]"
    else:
        p = "สกัดรายรับเดลิเวอรี่รายวันเป็น JSON array: [{'date': 'YYYY-MM-DD', 'app': 'ชื่อแอป', 'gross_sales': ยอดรวม, 'gp_amount': ค่า GP, 'net_income': ยอดโอนสุทธิ}]"
    
    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data_input, mime_type=mime_type)
        ])]
        res_text = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_3_1(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# --- 4. ฟังก์ชันบันทึกข้อมูลแยกแท็บ ---

def save_to_tab(df_to_save, tab_name):
    if conn is None or df_to_save.empty: return False
    try:
        existing_df = load_data(tab_name)
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(worksheet=tab_name, data=final_df)
        refresh_all_caches()
        st.success(f"✅ บันทึกลงแท็บ {tab_name} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI Layout ---

st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", 
    ["📊 Dashboard", "💰 รายรับเดลิเวอรี่", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 1️⃣ Dashboard ---
if page == "📊 Dashboard":
    st.header("📊 สรุปภาพรวมธุรกิจ")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    t_ov, t_monthly = st.tabs(["🏠 สรุปยอดสะสม", "📈 วิเคราะห์รายเดือน"])
    
    with t_ov:
        inc_sum = pd.to_numeric(df_i['net_income'], errors='coerce').sum() if not df_i.empty else 0
        exp_sum = pd.to_numeric(df_e['total_price'], errors='coerce').sum() if not df_e.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับสุทธิ", f"฿{inc_sum:,.2f}")
        c2.metric("รายจ่ายวัตถุดิบ", f"฿{exp_sum:,.2f}")
        c3.metric("กำไรเบื้องต้น", f"฿{inc_sum - exp_sum:,.2f}")
        
        st.divider()
        fig_pie = px.pie(values=[inc_sum, exp_sum], names=['รายรับ', 'รายจ่าย'], hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with t_monthly:
        if not df_i.empty:
            st.plotly_chart(px.bar(df_i, x='date', y='net_income', color='app' if 'app' in df_i.columns else None), use_container_width=True)

# --- 2️⃣ รายรับเดลิเวอรี่ ---
elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 บันทึกรายรับ (ลงแท็บ Income)")
    rtype = st.radio("ประเภท:", ["รายวัน (Daily)", "สรุปรายเดือน (Monthly)"], horizontal=True)
    mode = st.radio("วิธีนำเข้า:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
    
    res = None
    if mode == "📝 วางข้อความ":
        txt = st.text_area("วางข้อความรายงาน:")
        if txt and st.button("🪄 วิเคราะห์"):
            res = process_ai_extraction(txt, prompt_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Income")
    else:
        f = st.file_uploader("เลือกไฟล์", type=['pdf', 'jpg', 'png'])
        if f and st.button("🪄 วิเคราะห์จากไฟล์"):
            res = process_ai_extraction(f.read(), prompt_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Income", is_bytes=True, mime_type=f.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 บันทึกรายรับ"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- 3️⃣ บันทึกรายจ่าย ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย (ลงแท็บ Expense)")
    method = st.radio("วิธีบันทึก:", ["ยังไม่เลือก", "📸 แสกนบิล/รูปภาพ", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    
    res = None
    if method == "📸 แสกนบิล/รูปภาพ":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = st.camera_input("แสกน") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์"):
            res = process_ai_extraction(Image.open(img) if hasattr(img, 'type') and img.type != "application/pdf" else img, prompt_type="Expense")
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio = st.audio_input("พูดรายการรายจ่าย...")
        if audio and st.button("🚀 แปลงเสียง"):
            res = process_ai_extraction(audio.read(), prompt_type="Expense", is_bytes=True, mime_type=audio.type)

    if res:
        st.session_state.tmp_exp = pd.DataFrame(res)
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกรายจ่าย"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- 4️⃣ AI Agent ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    query = st.chat_input("พิมพ์คำถาม...")
    if query:
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            df_i = load_data("Income")
            df_e = load_data("Expense")
            ctx = f"Income:\n{df_i.tail(10).to_csv()}\nExpense:\n{df_e.tail(10).to_csv()}"
            ans = call_gemini_3_1(f"วิเคราะห์ข้อมูลร้านอาหาร:\n{ctx}\nคำถาม: {query}")
            st.markdown(ans if ans else "AI ไม่สามารถตอบได้")

# --- 5️⃣ ข้อมูลทั้งหมด ---
elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลแยกตามแท็บ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Expense"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

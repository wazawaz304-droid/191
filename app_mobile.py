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
st.set_page_config(page_title="Nave 304 - All-in-One AI Master", layout="wide", page_icon="🍜")

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
    if not text_response: return []
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("
```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"): content = content.lstrip()[4:]
        return json.loads(content.strip())
    except: return []

# --- 3. ฟังก์ชัน AI สำหรับสกัดข้อมูล ---

def process_ai_extraction(data_input, prompt_type="Expense", is_bytes=False, mime_type=None):
    if prompt_type == "Expense":
        p = "สกัดข้อมูลสินค้าเป็น JSON array: [{'date': 'YYYY-MM-DD', 'name': 'ชื่อสินค้า', 'qty': จำนวน, 'unit': 'หน่วย', 'total_price': ราคารวม}]"
    elif prompt_type == "Monthly":
        p = "สกัดรายงานรายเดือนเป็น JSON array: [{'month_year': 'YYYY-MM', 'platform': 'LM/SF/GF', 'gross': ยอดขายรวม, 'fees': ค่าธรรมเนียม+VAT, 'ads': ค่าโฆษณา+VAT, 'discounts': ส่วนลด, 'net_income': ยอดโอนสุทธิ}]"
    else:
        p = "สกัดรายรับเดลิเวอรี่รายวันเป็น JSON array: [{'date': 'YYYY-MM-DD', 'app': 'ชื่อแอป', 'gross_sales': ยอดรวม, 'gp_amount': ค่า GP, 'net_income': ยอดโอนสุทธิ}]"
    
    prompt = p + " ตอบเฉพาะ PURE JSON"
    
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
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
        st.success(f"✅ บันทึกลงแท็บ {tab_name} เรียบร้อย!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI Layout & Sidebar ---

st.sidebar.title("🚀 Nave 304 Business")
# ตรวจสอบว่าเมนูมีครบ 5 รายการ
page = st.sidebar.radio("เลือกเมนูการใช้งาน:", 
    ["📊 Dashboard", "💰 รายรับเดลิเวอรี่", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 1️⃣ เมนู Dashboard ---
if page == "📊 Dashboard":
    st.header("📊 สรุปภาพรวมธุรกิจ")
    df_inc = load_data("Income")
    df_exp = load_data("Expense")
    
    t_ov, t_monthly = st.tabs(["🏠 สรุปยอดสะสม", "📈 วิเคราะห์รายเดือน"])
    
    with t_ov:
        # คำนวณรายรับ (ใช้คอลัมน์ net_income)
        inc_val = pd.to_numeric(df_inc['net_income'], errors='coerce').sum() if not df_inc.empty else 0
        # คำนวณรายจ่าย (ใช้คอลัมน์ total_price)
        exp_val = pd.to_numeric(df_exp['total_price'], errors='coerce').sum() if not df_exp.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับสุทธิ (Income)", f"฿{inc_val:,.2f}")
        c2.metric("รายจ่ายรวม (Expense)", f"฿{exp_val:,.2f}")
        c3.metric("กำไรเบื้องต้น", f"฿{inc_val - exp_val:,.2f}", delta=f"{(inc_val-exp_val):,.0f}")
        
        st.divider()
        st.plotly_chart(px.pie(values=[inc_val, exp_val], names=['รายรับ', 'รายจ่าย'], hole=0.4, title="สัดส่วนรายรับ vs รายจ่าย"), use_container_width=True)

    with t_monthly:
        st.info("ระบบจะดึงข้อมูลจากแท็บ Income มาแสดงแนวโน้มรายเดือนที่นี่")
        if not df_inc.empty:
            st.plotly_chart(px.bar(df_inc, x='date', y='net_income', color='app' if 'app' in df_inc.columns else None, title="รายรับตามช่วงเวลา"), use_container_width=True)

# --- 2️⃣ เมนู รายรับเดลิเวอรี่ ---
elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 บันทึกรายรับ (ลงแท็บ Income)")
    rtype = st.radio("ประเภทรายงาน:", ["รายวัน (Daily)", "สรุปรายเดือน (Monthly)"], horizontal=True)
    mode = st.radio("วิธีนำเข้า:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
    
    res = None
    if mode == "📝 วางข้อความ":
        txt = st.text_area("วางข้อความรายงาน:")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"):
            res = process_ai_extraction(txt, prompt_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Income")
    else:
        f = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf', 'jpg', 'png'])
        if f and st.button("🪄 วิเคราะห์จากไฟล์"):
            res = process_ai_extraction(f.read(), prompt_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Income", is_bytes=True, mime_type=f.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกรายรับ"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- 3️⃣ เมนู บันทึกรายจ่าย ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย (ลงแท็บ Expense)")
    method = st.radio("เลือกวิธีบันทึก:", ["ยังไม่เลือก", "📸 แสกนบิล/รูปภาพ", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    
    res = None
    if method == "📸 แสกนบิล/รูปภาพ":
        sub_mode = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์จากเครื่อง"], horizontal=True)
        img = st.camera_input("แสกนบิล") if sub_mode == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูปบิล", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์บิล"):
            res = process_ai_extraction(Image.open(img) if sub_mode == "📷 ถ่ายรูปสด" or img.type != "application/pdf" else img.read(), prompt_type="Expense")
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio = st.audio_input("พูดรายการรายจ่าย...")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            res = process_ai_extraction(audio.read(), prompt_type="Expense", is_bytes=True, mime_type=audio.type)

    if res:
        st.session_state.tmp_exp = pd.DataFrame(res)
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกรายจ่าย"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- 4️⃣ เมนู AI Agent ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    st.caption("สอบถามข้อมูลกำไร ยอดขาย หรือแนวโน้มธุรกิจได้เลยครับ")
    
    # ดึงข้อมูลทั้ง 2 แท็บเพื่อให้ AI วิเคราะห์ภาพรวม
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    query = st.chat_input("พิมพ์คำถามที่นี่...")
    if query:
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            # เตรียม Context ให้ AI
            context = f"ข้อมูลรายรับล่าสุด:\n{df_i.tail(20).to_csv()}\n\nข้อมูลรายจ่ายล่าสุด:\n{df_e.tail(20).to_csv()}"
            ans = call_gemini_3_1(f"คุณคือ AI ที่ปรึกษาร้านเนฟ หมี่ไก่ฉีก ข้อมูล:\n{context}\nคำถาม: {query}")
            st.markdown(ans if ans else "ขออภัยครับ AI ไม่สามารถตอบได้ในขณะนี้")

# --- 5️⃣ เมนู ข้อมูลทั้งหมด ---
elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลดิบ (แยกตามแท็บ)")
    t1, t2 = st.tabs(["📥 ข้อมูลรายรับ (Income)", "📤 ข้อมูลรายจ่าย (Expense)"])
    with t1:
        st.dataframe(load_data("Income"), use_container_width=True)
    with t2:
        st.dataframe(load_data("Expense"), use_container_width=True)

# --- ส่วนล่าง Sidebar ---
st.sidebar.divider()
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

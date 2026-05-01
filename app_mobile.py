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
st.set_page_config(page_title="Nave 304 - Income Master", layout="wide", page_icon="💰")

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
    if not text_response: return []
    try:
        content = text_response.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except: return []

# --- 3. ฟังก์ชัน AI สกัดข้อมูลรายรับ ---

def process_income_ai(data_input, income_type="Delivery", is_bytes=False, mime_type=None):
    if income_type == "Monthly":
        p = "สกัดรายงานรายเดือน: [{'month_year': 'YYYY-MM', 'platform': 'LM/SF/GF', 'gross': ยอดขาย, 'fees': ค่าธรรมเนียม, 'ads': ค่าโฆษณา, 'discounts': ส่วนลด, 'net_income': ยอดโอนสุทธิ}]"
    elif income_type == "Store":
        p = "สกัดรายได้หน้าร้าน (จากข้อความหรือเสียง): [{'date': 'YYYY-MM-DD', 'app': 'หน้าร้าน', 'gross_sales': ยอดขาย, 'gp_amount': 0, 'net_income': ยอดขายสุทธิ}]"
    else:
        p = "สกัดรายรับเดลิเวอรี่รายวัน: [{'date': 'YYYY-MM-DD', 'app': 'ชื่อแอป', 'gross_sales': ยอดรวม, 'gp_amount': ค่า GP, 'net_income': ยอดโอนสุทธิ}]"
    
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

# --- 4. ฟังก์ชันบันทึกข้อมูล ---

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
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 💰 บันทึกรายรับ (อัปเกรดระบบเสียงหน้าร้าน) ---
if page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ (Income)")
    rtype = st.radio("ประเภทรายรับ:", ["รายวันเดลิเวอรี่ (Daily)", "สรุปรายเดือน (Monthly)", "รายได้หน้าร้าน (Store)"], horizontal=True)
    
    res = None
    if rtype == "รายได้หน้าร้าน (Store)":
        st.subheader("🏠 ยอดขายหน้าร้าน")
        store_method = st.radio("วิธีบันทึกยอดหน้าร้าน:", ["⌨️ พิมพ์เอง", "🎙️ บันทึกเสียง"], horizontal=True)
        
        if store_method == "⌨️ พิมพ์เอง":
            store_txt = st.text_area("เช่น 'ยอดขายหน้าร้านวันนี้ 4,200 บาท'", placeholder="ระบุยอดขาย...")
            if st.button("🪄 วิเคราะห์ยอดขาย"):
                res = process_income_ai(store_txt, income_type="Store")
        else:
            store_audio = st.audio_input("กดปุ่มไมค์แล้วพูด เช่น 'วันนี้ขายหน้าร้านได้ห้าพันบาท'")
            if store_audio and st.button("🚀 ส่งเสียงให้ AI ประมวลผล"):
                with st.spinner("AI กำลังฟังเสียงยอดขาย..."):
                    res = process_income_ai(store_audio.read(), income_type="Store", is_bytes=True, mime_type=store_audio.type)
    else:
        mode = st.radio("วิธีนำเข้า:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
        if mode == "📝 วางข้อความ":
            txt = st.text_area("วางข้อความรายงาน:")
            if txt and st.button("🪄 วิเคราะห์ด้วย AI"):
                res = process_income_ai(txt, income_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Delivery")
        else:
            f = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf', 'jpg', 'png'])
            if f and st.button("🪄 วิเคราะห์จากไฟล์"):
                res = process_income_ai(f.read(), income_type="Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Delivery", is_bytes=True, mime_type=f.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    
    if 'tmp_inc' in st.session_state:
        st.subheader("📝 ตรวจสอบยอดรายรับ")
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกลงแท็บ Income"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

# --- เมนูอื่นๆ (คงความสามารถเดิมไว้ครบถ้วน) ---
elif page == "📊 Dashboard":
    st.header("📊 แดชบอร์ดสรุปยอด")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    if not df_i.empty:
        inc_sum = pd.to_numeric(df_i['net_income'], errors='coerce').sum()
        exp_sum = pd.to_numeric(df_e['total_price'], errors='coerce').sum() if not df_e.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับสุทธิรวม", f"฿{inc_sum:,.2f}")
        c2.metric("รายจ่ายวัตถุดิบ", f"฿{exp_sum:,.2f}")
        c3.metric("กำไรสุทธิ", f"฿{inc_sum - exp_sum:,.2f}")
        st.divider()
        if 'app' in df_i.columns:
            fig = px.bar(df_i.groupby('app')['net_income'].sum().reset_index(), x='app', y='net_income', color='app', title="รายได้แยกตามช่องทาง")
            st.plotly_chart(fig, use_container_width=True)

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย (ลงแท็บ Expense)")
    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล", "🎙️ บันทึกเสียง"], horizontal=True)
    res_ex = None
    if method == "📸 แสกนบิล":
        img = st.camera_input("สแกน")
        if img and st.button("🪄 วิเคราะห์บิล"):
            prompt_ex = "สกัดข้อมูลสินค้าเป็น JSON array: [{'date': 'YYYY-MM-DD', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}] ตอบ PURE JSON"
            res_ex = call_gemini_3_1(prompt_ex, contents=[Image.open(img)])
            if res_ex: st.session_state.tmp_exp = pd.DataFrame(safe_parse_json(res_ex))
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("พูดรายการรายจ่าย...")
        if audio and st.button("🚀 แปลงเสียง"):
            prompt_ex = "สกัดข้อมูลสินค้าเป็น JSON array: [{'date': 'YYYY-MM-DD', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}] ตอบ PURE JSON"
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_ex), types.Part.from_bytes(data=audio.read(), mime_type=audio.type)])]
            res_ex = call_gemini_3_1(prompt_ex, contents=contents, is_complex_content=True)
            if res_ex: st.session_state.tmp_exp = pd.DataFrame(safe_parse_json(res_ex))
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp)
        if st.button("💾 บันทึกรายจ่าย"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    q = st.chat_input("พิมพ์คำถาม...")
    if q:
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            df_i, df_e = load_data("Income"), load_data("Expense")
            ctx = f"Income:\n{df_i.tail(10).to_csv()}\nExpense:\n{df_e.tail(10).to_csv()}"
            ans = call_gemini_3_1(f"ข้อมูลร้าน:\n{ctx}\nคำถาม: {q}")
            st.markdown(ans if ans else "AI ไม่สามารถตอบได้")

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลแยกตามแท็บ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Expense"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

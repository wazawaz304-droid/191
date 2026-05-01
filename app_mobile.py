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
st.set_page_config(page_title="Nave 304 - AI Business Master", layout="wide", page_icon="💰")

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

# --- 2.1 ระบบ Cache ข้อมูล ---
@st.cache_data(ttl=60)
def load_data():
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_data_cache():
    load_data.clear()

def call_gemini_with_fallback(prompt, contents=None, is_complex_content=False):
    model_list = ["models/gemini-2.0-flash", "models/gemini-2.0-flash-lite"]
    for model_name in model_list:
        try:
            if is_complex_content:
                response = client.models.generate_content(model=model_name, contents=contents)
            else:
                input_parts = [prompt] + contents if contents else [prompt]
                response = client.models.generate_content(model=model_name, contents=input_parts)
            return response.text
        except: continue
    return None

def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"): content = content.lstrip()[4:]
        return json.loads(content.strip())
    except: return []

# --- 3. ฟังก์ชัน AI Engine ---

def process_stock_ai(data_input, is_bytes=False, mime_type=None):
    prompt = """สกัดข้อมูลสินค้าเป็น JSON array: [{"date": "YYYY-MM-DD", "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม}] 
    ตอบเฉพาะ PURE JSON เสมอ"""
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

def process_income_ai(data_input, is_monthly=False, is_bytes=False, mime_type=None):
    if is_monthly:
        prompt = """สกัดรายงานรายเดือนเป็น JSON array: [{"month_year": "YYYY-MM", "platform": "LM/SF/GF", "gross": ยอดขายรวม, "fees": ค่าธรรมเนียม+VAT, "ads": ค่าโฆษณา+VAT, "discounts": ส่วนลด, "net": ยอดโอนสุทธิ, "notes": ""}] ตอบ PURE JSON"""
    else:
        prompt = """สกัดรายได้รายวันเป็น JSON array: [{"date": "YYYY-MM-DD", "app": "ชื่อแอป", "gross_sales": ยอดรวม, "gp_amount": ค่า GP, "net_income": ยอดโอนสุทธิ}] ตอบ PURE JSON"""
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# --- 4. บันทึกข้อมูล ---

def save_data_to_sheets(df_to_save: pd.DataFrame, data_type="Expense"):
    if conn is None or df_to_save.empty: return False
    try:
        df_to_save['type'] = data_type
        if data_type == "Monthly":
            df_to_save['date'] = df_to_save['month_year'].astype(str) + "-01"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net'], errors='coerce')
        elif data_type == "Income":
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net_income'], errors="coerce")
        else:
            df_to_save['total_price'] = pd.to_numeric(df_to_save.get('total_price', 0), errors="coerce").fillna(0)

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        refresh_data_cache()
        st.success(f"✅ บันทึก {data_type} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI Layout ---

st.sidebar.title("🍱 Nave 304 Menu")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 รายรับเดลิเวอรี่", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard ---
if page == "📊 Dashboard":
    st.header("📊 แดชบอร์ดวิเคราะห์ธุรกิจ")
    df = load_data()
    if not df.empty:
        df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
        tab_ov, tab_daily, tab_monthly = st.tabs(["🏠 ภาพรวม", "📅 รายวัน", "📈 รายเดือน"])
        with tab_ov:
            t_inc = df[df['type'].isin(['Income', 'Monthly'])]['total_price'].sum()
            t_exp = df[df['type'] == 'Expense']['total_price'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("รายรับสุทธิ", f"฿{t_inc:,.2f}")
            c2.metric("รายจ่ายวัตถุดิบ", f"฿{t_exp:,.2f}")
            c3.metric("กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}", delta=f"{((t_inc-t_exp)/t_inc*100 if t_inc > 0 else 0):.1f}%")
            st.plotly_chart(px.pie(values=[t_inc, t_exp], names=['รายรับ', 'รายจ่าย'], hole=0.4), use_container_width=True)
        with tab_daily:
            inc = df[df['type'] == 'Income']
            if not inc.empty: st.plotly_chart(px.bar(inc.sort_values('date'), x='date', y='total_price', color='name'), use_container_width=True)
        with tab_monthly:
            m_data = df[df['type'] == 'Monthly'].copy()
            if not m_data.empty:
                m_data['gross'] = pd.to_numeric(m_data['gross'], errors='coerce')
                m_data['fees'] = pd.to_numeric(m_data['fees'], errors='coerce')
                m_data['fee_pct'] = (m_data['fees'] / m_data['gross'] * 100).round(2)
                st.plotly_chart(px.bar(m_data, x='month_year', y='total_price', color='platform', barmode='group'), use_container_width=True)
                st.dataframe(m_data[['month_year', 'platform', 'gross', 'fees', 'fee_pct', 'total_price']], use_container_width=True)

# --- 💰 รายรับเดลิเวอรี่ ---
elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวัน (Daily)", "สรุปรายเดือน (Monthly)"], horizontal=True)
    mode = st.radio("ช่องทาง:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if mode == "📝 วางข้อความ":
        txt = st.text_area("วางข้อความรายงานที่นี่:")
        if txt and st.button("🪄 วิเคราะห์"):
            with st.spinner("AI กำลังทำงาน..."): res = process_income_ai(txt, is_monthly=(rtype=="สรุปรายเดือน (Monthly)"))
    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf', 'jpg', 'png', 'jpeg'])
        if file and st.button("🪄 วิเคราะห์ไฟล์"):
            with st.spinner("AI กำลังอ่านไฟล์..."): res = process_income_ai(file.read(), is_monthly=(rtype=="สรุปรายเดือน (Monthly)"), is_bytes=True, mime_type=file.type)
    if res:
        st.session_state.temp_inc = pd.DataFrame(res)
        st.session_state.temp_type = "Monthly" if rtype == "สรุปรายเดือน (Monthly)" else "Income"
    if 'temp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.temp_inc)
        if st.button("💾 ยืนยันบันทึก"):
            if save_data_to_sheets(edited, st.session_state.temp_type):
                del st.session_state.temp_inc
                st.rerun()

# --- 💸 บันทึกรายจ่าย (รวม แสกน + เสียง) ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    ex_method = st.radio("เลือกวิธีบันทึก:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    
    res = None
    if ex_method == "📸 แสกนบิล/อัปโหลดรูป":
        sub_mode = st.radio("รูปแบบ:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์จากเครื่อง"], horizontal=True)
        img_file = st.camera_input("สแกนบิล") if sub_mode == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูปบิล", type=['jpg','png','jpeg'])
        if img_file and st.button("🪄 วิเคราะห์บิล"):
            with st.spinner("AI กำลังอ่านบิล..."): res = process_stock_ai(Image.open(img_file))
            
    elif ex_method == "🎙️ บันทึกด้วยเสียง":
        audio = st.audio_input("พูดรายการสินค้า (เช่น: ไก่สด 5 กิโล 500 บาท)")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            with st.spinner("AI กำลังฟังเสียง..."): res = process_stock_ai(audio.read(), is_bytes=True, mime_type=audio.type)

    if res:
        st.session_state.temp_ex = pd.DataFrame(res)

    if 'temp_ex' in st.session_state:
        st.subheader("📝 ตรวจสอบรายการ")
        edited = st.data_editor(st.session_state.temp_ex, use_container_width=True)
        if st.button("💾 บันทึกลงฐานข้อมูล"):
            if save_data_to_sheets(edited, "Expense"):
                del st.session_state.temp_ex
                st.rerun()

# --- 🤖 AI Agent ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI Business Assistant")
    query = st.chat_input("ถามเกี่ยวกับยอดขายหรือกำไร...")
    if query:
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            df_ctx = load_data().tail(50).to_csv()
            ans = call_gemini_with_fallback(f"ข้อมูลร้านอาหาร:\n{df_ctx}\nคำถาม: {query}")
            st.markdown(ans)

# --- 📋 ข้อมูลทั้งหมด ---
elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลทั้งหมด")
    st.dataframe(load_data(), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

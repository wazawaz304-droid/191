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
st.set_page_config(page_title="Nave 304 - Dashboard Fixed", layout="wide", page_icon="📈")

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
    st.error(f"⚠️ ไม่พบ API Key: {e}")

# --- 2.1 ระบบโหลดข้อมูล (แยกแท็บ) ---
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

# --- 3. ฟังก์ชันแปลงตัวเลขให้ปลอดภัย (ป้องกัน Error ข้อมูลหาย) ---
def clean_numeric(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '').replace('฿', ''), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

# (ฟังก์ชัน AI และการบันทึกคงเดิมไว้เพื่อความต่อเนื่อง)
def call_gemini_3_1(prompt, contents=None, is_complex_content=False):
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        return response.text
    except: return None

def safe_parse_json(text_response: str):
    if not text_response: return []
    try:
        content = text_response.strip()
        if "```" in content: content = content.split("
```")[1]
        if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except: return []

def process_income_ai(data_input, income_type="Delivery", is_bytes=False, mime_type=None):
    p = f"สกัดข้อมูล {income_type} เป็น JSON: [{{'date': 'YYYY-MM-DD', 'app': 'ชื่อ', 'net_income': ยอดเงิน}}]"
    prompt = p + " ตอบเฉพาะ PURE JSON"
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
        res = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini_3_1(prompt, contents=[data_input])
    return safe_parse_json(res)

def save_to_tab(df_to_save, tab_name):
    if conn is None or df_to_save.empty: return False
    try:
        existing = load_data(tab_name)
        final = pd.concat([existing, df_to_save], ignore_index=True)
        conn.update(worksheet=tab_name, data=final)
        refresh_all_caches()
        return True
    except: return False

# --- 5. UI Layout ---

st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard (จุดที่แก้ไข) ---
if page == "📊 Dashboard":
    st.header("📊 รายงานวิเคราะห์ธุรกิจ")
    
    # 1. โหลดข้อมูลจาก 2 แท็บ
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # 2. ทำความสะอาดข้อมูลตัวเลข
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    if 'qty' in df_e.columns:
        df_e['qty'] = clean_numeric(df_e, 'qty')
        df_e['unit_price'] = df_e['total_price'] / df_e['qty'].replace(0, 1)

    # 3. สรุป Metric
    total_inc = df_i['net_income'].sum()
    total_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับสุทธิรวม", f"฿{total_inc:,.2f}")
    c2.metric("📦 รายจ่ายสต๊อก", f"฿{total_exp:,.2f}")
    c3.metric("📈 กำไรเบื้องต้น", f"฿{total_inc - total_exp:,.2f}")
    
    st.divider()

    # 4. แบ่งแท็บกราฟ
    t_daily, t_expense, t_price_trend = st.tabs(["📅 รายรับรายวัน", "🛒 รายจ่ายสต๊อก", "📈 แนวโน้มราคาสินค้า"])
    
    with t_daily:
        if not df_i.empty and 'date' in df_i.columns:
            # กราฟแท่งรายรับรายวัน แยกตามแอป/หน้าร้าน
            fig_daily = px.bar(df_i.sort_values('date'), x='date', y='net_income', color='app' if 'app' in df_i.columns else None,
                              title="แนวโน้มรายรับรายวัน", barmode='group')
            st.plotly_chart(fig_daily, use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลรายรับ")

    with t_expense:
        if not df_e.empty:
            col_l, col_r = st.columns(2)
            with col_l:
                # สัดส่วนรายจ่ายตามชื่อสินค้า
                fig_pie_exp = px.pie(df_e, values='total_price', names='name' if 'name' in df_e.columns else None, title="สัดส่วนค่าใช้จ่ายวัตถุดิบ")
                st.plotly_chart(fig_pie_exp, use_container_width=True)
            with col_r:
                # รายจ่ายรายวัน
                if 'date' in df_e.columns:
                    fig_bar_exp = px.bar(df_e.sort_values('date'), x='date', y='total_price', title="รายจ่ายรายวัน")
                    st.plotly_chart(fig_bar_exp, use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลรายจ่าย")

    with t_price_trend:
        if not df_e.empty and 'name' in df_e.columns and 'date' in df_e.columns:
            st.subheader("วิเคราะห์ราคาวัตถุดิบต่อหน่วย")
            items = sorted(df_e['name'].unique())
            target = st.selectbox("เลือกวัตถุดิบ:", items)
            
            # กรองข้อมูลเฉพาะสินค้าที่เลือก
            df_item = df_e[df_e['name'] == target].copy()
            df_item['date'] = pd.to_datetime(df_item['date'])
            df_item = df_item.sort_values('date')
            
            fig_trend = px.line(df_item, x='date', y='unit_price', markers=True, 
                               title=f"แนวโน้มราคา {target} (ต่อหน่วย)")
            st.plotly_chart(fig_trend, use_container_width=True)
        else: st.info("ข้อมูลไม่เพียงพอสำหรับทำกราฟแนวโน้มราคา")

# --- เมนูอื่นๆ (เหมือนเดิม) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวัน", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธี:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ใส่ข้อมูล:")
        if txt and st.button("🪄 วิเคราะห์"): res = process_income_ai(txt, income_type=rtype)
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("พูด...")
        if audio and st.button("🚀 ประมวลผล"): res = process_income_ai(audio.read(), income_type=rtype, is_bytes=True, mime_type=audio.type)
    
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc)
        if st.button("💾 บันทึก"):
            if save_to_tab(edited, "Income"):
                del st.session_state.tmp_inc
                st.rerun()

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    method = st.radio("เลือกวิธี:", ["📸 แสกนบิล", "🎙️ บันทึกเสียง"], horizontal=True)
    res_ex = None
    if method == "📸 แสกนบิล":
        img = st.camera_input("สแกน")
        if img and st.button("🪄 วิเคราะห์"):
            prompt_ex = "สกัดเป็น JSON: [{'date': 'YYYY-MM-DD', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}]"
            res_ex = call_gemini_3_1(prompt_ex, contents=[Image.open(img)])
            if res_ex: st.session_state.tmp_exp = pd.DataFrame(safe_parse_json(res_ex))
    
    if 'tmp_exp' in st.session_state:
        if st.button("💾 บันทึกลง Expense"):
            if save_to_tab(st.session_state.tmp_exp, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

elif page == "🤖 AI Agent":
    st.header("🤖 AI Assistant")
    q = st.chat_input("ถามคำถาม...")
    if q:
        df_i, df_e = load_data("Income"), load_data("Expense")
        ctx = f"Income:\n{df_i.tail(5).to_csv()}\nExpense:\n{df_e.tail(5).to_csv()}"
        ans = call_gemini_3_1(f"ข้อมูลร้าน:\n{ctx}\nคำถาม: {q}")
        st.write(ans)

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลดิบ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"))
    with t2: st.dataframe(load_data("Expense"))

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

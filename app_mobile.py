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
st.set_page_config(page_title="AI Business Master 2026", layout="wide", page_icon="🍜")

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
    # ตรวจสอบว่ามี secrets ใน streamlit หรือไม่
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
    model_list = [
        "models/gemini-2.0-flash", 
        "models/gemini-2.0-flash-lite",
        "models/gemini-1.5-flash"
    ]
    for model_name in model_list:
        try:
            if is_complex_content:
                response = client.models.generate_content(model=model_name, contents=contents)
            else:
                input_parts = [prompt] + contents if contents else [prompt]
                response = client.models.generate_content(model=model_name, contents=input_parts)
            return response.text
        except:
            continue
    return None

def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:]
        return json.loads(content.strip())
    except Exception:
        return []

# --- 3. ฟังก์ชัน AI Engine ---

def process_stock_ai(data_input, is_bytes=False, mime_type=None):
    prompt = """สกัดข้อมูลสินค้าเป็น JSON array: [{"date": "YYYY-MM-DD", "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม}] 
    ตอบแค่ PURE JSON เท่านั้น"""
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data_input, mime_type=mime_type)
        ])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

def process_monthly_report_ai(data_input, is_bytes=False, mime_type=None):
    prompt = """คุณคือสมุห์บัญชี สกัดข้อมูลรายงานรายเดือนเป็น JSON array:
    [{"month_year": "YYYY-MM", "platform": "LM/SF/GF", "gross": ยอดรวม, "fees": ค่า GP+POS+VAT, "ads": ค่าโฆษณา+VAT, "discounts": ส่วนลด, "net": ยอดโอนสุทธิ, "notes": "หมายเหตุ"}]
    กฎ: ปี พ.ศ. 2569 = ค.ศ. 2026 เสมอ ตอบแค่ PURE JSON"""
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data_input, mime_type=mime_type)
        ])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# --- 4. บันทึกข้อมูล ---

def save_data_to_sheets(df_to_save: pd.DataFrame, data_type="Expense"):
    if conn is None or df_to_save.empty: return False
    try:
        df_to_save['type'] = data_type
        now_str = datetime.now().strftime("%Y-%m-%d")
        
        if data_type == "Monthly":
            df_to_save['date'] = df_to_save['month_year'] + "-01"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net'], errors='coerce')
            df_to_save['name'] = df_to_save['platform'] + " Monthly"
        elif data_type == "Income":
            df_to_save['name'] = df_to_save['app'] + " Income"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net_income'], errors='coerce')
            df_to_save['qty'] = 1
        else:
            df_to_save['qty'] = pd.to_numeric(df_to_save['qty'], errors="coerce").fillna(1)
            df_to_save['total_price'] = pd.to_numeric(df_to_save['total_price'], errors="coerce").fillna(0)

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        refresh_data_cache()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI ---

st.sidebar.title("🚀 AI Business Menu")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 รายรับเดลิเวอรี่", "📸 สแกนบิล", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

if page == "📊 Dashboard":
    st.header("📊 สรุปผลกำไร-ขาดทุน")
    df = load_data()
    if not df.empty:
        df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
        
        # --- การใช้ Tabs (ตรวจสอบย่อหน้าให้ดี) ---
        tab_ov, tab_daily, tab_monthly = st.tabs(["🏠 ภาพรวมร้าน", "📅 สรุปรายวัน", "📈 วิเคราะห์รายเดือน"])
        
        with tab_ov:
            # คำนวณรายรับ (Income + Monthly) และรายจ่าย (Expense)
            t_inc = df[df['type'].isin(['Income', 'Monthly'])]['total_price'].sum()
            t_exp = df[df['type'] == 'Expense']['total_price'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 รายรับรวม (Net)", f"฿{t_inc:,.2f}")
            c2.metric("📦 รายจ่ายวัตถุดิบ", f"฿{t_exp:,.2f}")
            c3.metric("📈 กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}", 
                      delta=f"{((t_inc-t_exp)/t_inc*100 if t_inc > 0 else 0):.1f}%")
            
            st.divider()
            fig_ov = px.pie(values=[t_inc, t_exp], names=['รายรับรวม', 'รายจ่ายวัตถุดิบ'], hole=0.4, title="สัดส่วนรายรับ vs รายจ่าย")
            st.plotly_chart(fig_ov, use_container_width=True)

        with tab_daily:
            daily_inc = df[df['type'] == 'Income'].copy()
            if not daily_inc.empty:
                st.subheader("แนวโน้มรายรับรายวัน")
                fig_daily = px.bar(daily_inc, x='date', y='total_price', color='name', barmode='group', title="รายรับรายวันแยกตามแอป")
                st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายรับรายวัน")

        with tab_monthly:
            m_data = df[df['type'] == 'Monthly'].copy()
            if not m_data.empty:
                m_data['gross'] = pd.to_numeric(m_data['gross'], errors='coerce')
                m_data['fees'] = pd.to_numeric(m_data['fees'], errors='coerce')
                m_data['fee_percent'] = (m_data['fees'] / m_data['gross'] * 100).round(2)
                
                st.subheader("วิเคราะห์ค่าธรรมเนียมและรายได้สุทธิรายเดือน")
                fig_m = px.bar(m_data, x='month_year', y='total_price', color='platform', barmode='group', title="รายได้สุทธิรายเดือน")
                st.plotly_chart(fig_m, use_container_width=True)
                
                st.dataframe(m_data[['month_year', 'platform', 'gross', 'fees', 'fee_percent', 'total_price']], use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลสรุปรายเดือน")
    else:
        st.warning("ยังไม่มีข้อมูลในฐานข้อมูล")

elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 บันทึกรายรับ")
    m_type = st.radio("เลือกประเภท:", ["รายวัน (Daily)", "สรุปรายเดือน (Monthly Report)"], horizontal=True)
    file = st.file_uploader("อัปโหลดไฟล์รายงาน (PDF/รูปภาพ)", type=['pdf', 'jpg', 'png', 'jpeg'])
    
    if file and st.button("🪄 วิเคราะห์ข้อมูล"):
        with st.spinner("AI กำลังอ่านไฟล์..."):
            if m_type == "สรุปรายเดือน (Monthly Report)":
                res = process_monthly_report_ai(file.read(), is_bytes=True, mime_type=file.type)
                if res: 
                    st.session_state.temp_data = pd.DataFrame(res)
                    st.session_state.temp_type = "Monthly"
            else:
                # ใช้ฟังก์ชันสแกนปกติสำหรับรายวัน
                res = process_stock_ai(file.read(), is_bytes=True, mime_type=file.type)
                if res:
                    df_res = pd.DataFrame(res)
                    # แปลงคอลัมน์ให้ตรงกับ Income
                    if 'total_price' in df_res.columns: df_res['net_income'] = df_res['total_price']
                    if 'name' in df_res.columns: df_res['app'] = df_res['name']
                    st.session_state.temp_data = df_res
                    st.session_state.temp_type = "Income"

    if 'temp_data' in st.session_state:
        edited = st.data_editor(st.session_state.temp_data)
        if st.button("💾 ยืนยันบันทึก"):
            if save_data_to_sheets(edited, st.session_state.temp_type):
                st.success("บันทึกเรียบร้อย!")
                del st.session_state.temp_data
                st.rerun()

elif page == "📸 สแกนบิล":
    st.header("📸 สแกนบิลรายจ่ายวัตถุดิบ")
    img = st.camera_input("สแกนบิล")
    if img and st.button("🪄 สแกน"):
        with st.spinner("กำลังอ่านบิล..."):
            res = process_stock_ai(Image.open(img))
            if res: st.session_state.stock_res = pd.DataFrame(res)
    
    if 'stock_res' in st.session_state:
        edited = st.data_editor(st.session_state.stock_res)
        if st.button("💾 บันทึกรายจ่าย"):
            if save_data_to_sheets(edited, "Expense"):
                st.success("บันทึกสำเร็จ")
                del st.session_state.stock_res
                st.rerun()

elif page == "🤖 AI Agent":
    st.header("🤖 AI Business Assistant")
    # ส่วนนี้ใช้ระบบ Chat ธรรมดาเชื่อมกับข้อมูล
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    query = st.chat_input("ถามเกี่ยวกับธุรกิจของคุณ...")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.markdown(query)
        # จำลองการเรียก AI (คุณสามารถดึงข้อมูล CSV ไปให้ AI วิเคราะห์ได้เหมือนโค้ดเดิม)
        with st.chat_message("assistant"):
            st.markdown("ระบบกำลังวิเคราะห์ข้อมูลบัญชีของคุณ... (ฟังก์ชันนี้พร้อมเชื่อมต่อแล้ว)")

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลทั้งหมด")
    df = load_data()
    st.dataframe(df, use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

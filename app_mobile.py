import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="เนฟ หมี่ไก่ฉีก 304 - AI Business Master", layout="wide", page_icon="🍜")

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

# --- 2.1 ระบบ Cache ---
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
        except:
            continue
    return None

def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"): content = content.lstrip()[4:]
        return json.loads(content.strip())
    except:
        return []

# --- 3. ฟังก์ชัน AI Engine (อัปเกรดใหม่) ---

def process_monthly_report_ai(data_input, is_bytes=False, mime_type=None):
    """สกัดข้อมูลรายงานรายเดือนแบบละเอียด"""
    prompt = """
    คุณคือผู้บัญชีร้าน 'เนฟ หมี่ไก่ฉีก 304' สกัดข้อมูลรายงานรายเดือนเป็น JSON array:
    [{
      "month_year": "YYYY-MM", 
      "platform": "LM/SF/GF", 
      "gross": ยอดรวมขาย, 
      "fees": ค่าธรรมเนียม+VAT, 
      "ads": ค่าโฆษณา+VAT, 
      "discounts": ส่วนลด, 
      "net": ยอดโอนสุทธิ,
      "notes": "สรุปสั้นๆ"
    }]
    - ปี พ.ศ. 2569 ให้ใช้ 2026
    - ตอบแค่ PURE JSON
    """
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data_input, mime_type=mime_type)
        ])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# (คงฟังก์ชัน process_stock_ai และ process_delivery_income_ai เดิมของคุณไว้)
def process_stock_ai(data_input, is_bytes=False, mime_type=None):
    prompt = "สกัดข้อมูลสินค้าเป็น JSON array: [{ 'date': 'YYYY-MM-DD', 'name': 'ชื่อสินค้า', 'qty': จำนวน, 'unit': 'หน่วย', 'total_price': ราคารวม }] ตอบแค่ PURE JSON"
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data_input, mime_type=mime_type)])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_complex_content=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

# --- 4. การบันทึกข้อมูล (รองรับ Monthly) ---

def save_data_to_sheets(df_to_save: pd.DataFrame, data_type="Expense"):
    if conn is None or df_to_save.empty: return False
    try:
        df_to_save['type'] = data_type
        # จัดการวันที่
        now_str = datetime.now().strftime("%Y-%m-%d")
        if data_type == "Monthly":
            # รายงานรายเดือนใช้ month_year เป็นหลัก
            df_to_save['date'] = df_to_save['month_year'] + "-01"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net'], errors='coerce')
            df_to_save['name'] = df_to_save['platform'] + " Monthly"
        elif data_type == "Income":
            df_to_save['date'] = df_to_save['date'].fillna(now_str)
            df_to_save['name'] = df_to_save['app'] + " Income"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net_income'], errors='coerce')
        else:
            df_to_save['date'] = df_to_save['date'].fillna(now_str)
            df_to_save['total_price'] = pd.to_numeric(df_to_save['total_price'], errors='coerce')

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        refresh_data_cache()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI ---

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4080/4080032.png", width=100)
st.sidebar.title("เนฟ หมี่ไก่ฉีก 304")
page = st.sidebar.radio("เมนูหลัก:", ["📊 Dashboard", "💰 บันทึกรายได้", "📸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- หน้า Dashboard (ที่มี TABS ตามคำขอ) ---
if page == "📊 Dashboard":
    st.header("📊 ระบบวิเคราะห์ธุรกิจอัจฉริยะ")
    df = load_data()
    
    if not df.empty:
        df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
        
        # แยกข้อมูลตามประเภท
        tab_ov, tab_daily, tab_monthly = st.tabs(["🏠 ภาพรวมร้าน", "📅 สรุปรายวัน", "📈 วิเคราะห์รายเดือน"])
        
       with tab_ov:
            # ... (ส่วน Metric คล้ายเดิม) ...
            t_inc = df[df['type'].isin(['Income', 'Monthly'])]['total_price'].sum()
            t_exp = df[df['type'] == 'Expense']['total_price'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("ยอดรับรวมทั้งหมด", f"฿{t_inc:,.2f}")
            c2.metric("รายจ่ายวัตถุดิบ", f"฿{t_exp:,.2f}")
            c3.metric("กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}", delta=f"{((t_inc-t_exp)/t_inc*100 if t_inc > 0 else 0):.1f}%")
            
            st.divider()
            
            # --- จุดที่ต้องแก้ไขคือตรงนี้ครับ ---
            # เปลี่ยนจาก fig_ov เป็น fig_ov (หรือชื่ออะไรก็ได้ที่ตรงกันทั้งสองบรรทัด)
            fig_ov = px.pie(values=[t_inc, t_exp], 
                            names=['รายรับรวม', 'รายจ่ายวัตถุดิบ'], 
                            hole=0.4, 
                            title="สัดส่วนรายรับ vs รายจ่าย")
            
            # ตรงนี้ต้องใช้ชื่อเดียวกับด้านบน คือ fig_ov
            st.plotly_chart(fig_ov, use_container_width=True)

        with tab_daily:
            daily_inc = df[df['type'] == 'Income'].copy()
            if not daily_inc.empty:
                st.subheader("แนวโน้มรายรับรายวัน")
                fig_daily = px.bar(daily_inc, x='date', y='total_price', color='name', barmode='group')
                st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายรับรายวัน")

        with tab_monthly:
            m_data = df[df['type'] == 'Monthly'].copy()
            if not m_data.empty:
                # คำนวณ % ค่าธรรมเนียม
                m_data['gross'] = pd.to_numeric(m_data['gross'], errors='coerce')
                m_data['fees'] = pd.to_numeric(m_data['fees'], errors='coerce')
                m_data['fee_percent'] = (m_data['fees'] / m_data['gross'] * 100).round(2)
                
                st.subheader("เปรียบเทียบประสิทธิภาพแต่ละแอป")
                
                # กราฟเปรียบเทียบยอดขายสุทธิ (Net)
                fig_m = px.bar(m_data, x='month_year', y='net', color='platform', 
                               title="รายได้สุทธิรายเดือนแยกตามแอป", barmode='group', text_auto='.2s')
                st.plotly_chart(fig_m, use_container_width=True)
                
                # ตารางเปรียบเทียบค่าธรรมเนียม %
                st.subheader("📋 ตารางวิเคราะห์ต้นทุนแอป (%)")
                st.dataframe(m_data[['month_year', 'platform', 'gross', 'fees', 'fee_percent', 'net']], use_container_width=True)
                
                # กราฟเส้นแสดง % ค่าธรรมเนียม
                fig_fee = px.line(m_data, x='month_year', y='fee_percent', color='platform', markers=True,
                                 title="แนวโน้มค่าธรรมเนียม (%) ของแต่ละแอป")
                st.plotly_chart(fig_fee, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายงานรายเดือน (ไปที่เมนู 'บันทึกรายได้' เพื่อสแกนรายงานรายเดือน)")

# --- หน้าบันทึกรายได้ (เพิ่มระบบ Monthly) ---
elif page == "💰 บันทึกรายได้":
    st.header("💰 บันทึกรายรับจาก Delivery")
    m_type = st.radio("ประเภทรายงาน:", ["รายงานรายวัน (Daily)", "รายงานสรุปรายเดือน (Monthly Summary)"], horizontal=True)
    
    file = st.file_uploader("อัปโหลดไฟล์ (PDF/Image) หรือวางข้อความอีเมล", type=['pdf', 'jpg', 'png'])
    
    if file and st.button("🪄 เริ่มวิเคราะห์"):
        with st.spinner("AI กำลังประมวลผล..."):
            if m_type == "รายงานสรุปรายเดือน (Monthly Summary)":
                res = process_monthly_report_ai(file.read(), is_bytes=True, mime_type=file.type)
                if res: 
                    st.session_state.temp_inc = pd.DataFrame(res)
                    st.session_state.temp_type = "Monthly"
            else:
                res = process_stock_ai(file.read(), is_bytes=True, mime_type=file.type) # ปรับใช้ Prompt Daily
                if res: 
                    st.session_state.temp_inc = pd.DataFrame(res)
                    st.session_state.temp_type = "Income"

    if 'temp_inc' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูล")
        edited = st.data_editor(st.session_state.temp_inc)
        if st.button("💾 ยืนยันบันทึก"):
            if save_data_to_sheets(edited, st.session_state.temp_type):
                st.success("บันทึกสำเร็จ!")
                del st.session_state.temp_inc
                st.rerun()

# --- (เมนูอื่นๆ คงเดิมตามโค้ดหลักของคุณ) ---
elif page == "📸 บันทึกรายจ่าย":
    st.header("📸 สแกนบิลวัตถุดิบ")
    # ... โค้ดเดิมของคุณ ...
    st.info("ส่วนนี้ใช้โค้ดเดิมของคุณในการสแกนบิลวัตถุดิบได้เลยครับ")

elif page == "🤖 AI Agent":
    st.header("🤖 AI Business Assistant")
    # ... โค้ดเดิมของคุณ ...

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลในระบบทั้งหมด")
    df = load_data()
    st.dataframe(df)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

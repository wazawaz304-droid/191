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
st.set_page_config(page_title="AI Business Master 2026 - เนฟ หมี่ไก่ฉีก 304", layout="wide", page_icon="💰")

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

# --- 2.1 ระบบ Cache และ Fallback Model ---
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

def get_unique_products():
    df = load_data()
    if not df.empty and 'name' in df.columns:
        expense_df = df[df['type'] != 'Income'] if 'type' in df.columns else df
        return sorted([str(x) for x in expense_df['name'].dropna().unique()])
    return []

def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1] if len(parts) >= 2 else parts[0]
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:]
        return json.loads(content.strip())
    except:
        return []

# --- 3. ฟังก์ชัน AI Engine ---

def process_stock_ai(data_input, is_bytes=False, mime_type=None):
    existing_items = ", ".join(get_unique_products())
    prompt = f"""
    สกัดข้อมูลสินค้าเป็น JSON array: [{{ "date": "YYYY-MM-DD", "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    - date: หาวันที่ในบิลให้อยู่ในรูปแบบ YYYY-MM-DD
    - name: เทียบชื่อเดิม [{existing_items}] หากคล้ายให้ใช้ชื่อเดิม
    ตอบแค่ PURE JSON
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

def process_delivery_income_ai(data_input, is_bytes=False, mime_type=None):
    prompt = """
    สกัดข้อมูลรายได้เดลิเวอรี่รายวันเป็น JSON array:
    [{{ "date": "YYYY-MM-DD", "app": "Grab/LINE MAN/ShopeeFood", "gross_sales": ยอดรวม, "gp_amount": ค่า GP, "net_income": ยอดโอนสุทธิ }}]
    ตอบแค่ PURE JSON
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

def process_monthly_report_ai(data_input, is_bytes=False, mime_type=None):
    prompt = """
    คุณคือสมุห์บัญชี สกัดข้อมูลรายงานสรุปรายเดือนเป็น JSON array:
    [{"month_year": "YYYY-MM", "platform": "LM/SF/GF", "gross": ยอดขายรวม, "fees": ค่า GP+POS+VAT, "ads": ค่าโฆษณา+VAT, "discounts": ส่วนลด, "net": ยอดโอนสุทธิ, "notes": "หมายเหตุ"}]
    กฎ: ปี 2569 = 2026 ตอบแค่ PURE JSON
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

def chat_with_stock_agent(user_message: str):
    df = load_data()
    stock_summary = "ไม่มีข้อมูล" if df.empty else df.tail(300).to_csv(index=False)
    system_instruction = "คุณคือ AI ที่ปรึกษาธุรกิจร้านเนฟ หมี่ไก่ฉีก วิเคราะห์ข้อมูลอย่างมือโปร"
    prompt = f"ข้อมูลบัญชี:\n{stock_summary}\n\nคำถาม: {user_message}"
    return call_gemini_with_fallback(system_instruction, contents=[prompt])

# --- 4. บันทึกข้อมูล ---

def save_data_to_sheets(df_to_save: pd.DataFrame, data_type="Expense"):
    if conn is None or df_to_save.empty: return False
    try:
        df_to_save['type'] = data_type
        now_str = datetime.now().strftime("%Y-%m-%d")

        if data_type == "Monthly":
            df_to_save['date'] = df_to_save['month_year'] + "-01"
            df_to_save['name'] = df_to_save['platform'] + " Monthly"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net'], errors='coerce')
        elif data_type == "Income":
            df_to_save['name'] = df_to_save['app'] + " Income"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net_income'], errors="coerce")
            df_to_save['qty'] = 1
        else:
            df_to_save['qty'] = pd.to_numeric(df_to_save['qty'], errors="coerce").fillna(1)
            df_to_save['total_price'] = pd.to_numeric(df_to_save['total_price'], errors="coerce").fillna(0)
            if 'qty' in df_to_save.columns and 'total_price' in df_to_save.columns:
                df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        refresh_data_cache()
        st.success(f"✅ บันทึก {data_type} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI ---

st.sidebar.title("🚀 AI Business Menu")
page = st.sidebar.radio("เลือกเมนู:", ["📸 สแกนบิล", "🎙️ บันทึกเสียง", "💰 รายรับเดลิเวอรี่", "📊 Dashboard", "📋 ข้อมูลทั้งหมด", "🤖 AI Agent"])

if page == "📸 สแกนบิล":
    st.header("📸 สแกนบิลวัตถุดิบ")
    mode = st.radio("วิธีนำเข้า:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
    img_file = st.camera_input("สแกน") if mode == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
    
    if img_file and st.button("🪄 เริ่มสแกน"):
        with st.spinner("AI กำลังอ่านบิล..."):
            res = process_stock_ai(Image.open(img_file))
            if res: st.session_state.stock_data = pd.DataFrame(res)

    if 'stock_data' in st.session_state:
        edited = st.data_editor(st.session_state.stock_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกค่าวัตถุดิบ"):
            if save_data_to_sheets(edited, "Expense"):
                del st.session_state.stock_data
                st.rerun()

elif page == "🎙️ บันทึกเสียง":
    st.header("🎙️ บันทึกด้วยเสียง")
    audio = st.audio_input("พูดรายการสินค้า...")
    if audio and st.button("🚀 แปลงเป็นข้อมูล"):
        with st.spinner("AI กำลังฟัง..."):
            res = process_stock_ai(audio.read(), is_bytes=True, mime_type=audio.type)
            if res: st.session_state.voice_data = pd.DataFrame(res)

    if 'voice_data' in st.session_state:
        edited = st.data_editor(st.session_state.voice_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกลงสต๊อก"):
            if save_data_to_sheets(edited, "Expense"):
                del st.session_state.voice_data
                st.rerun()

elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 บันทึกรายรับเดลิเวอรี่")
    report_type = st.radio("ประเภทรายงาน:", ["รายวัน (Daily)", "สรุปรายเดือน (Monthly Summary)"], horizontal=True)
    input_method = st.radio("วิธีนำเข้า:", ["📝 วางข้อความ", "📁 อัปโหลดไฟล์ (PDF/รูป)"], horizontal=True)
    
    res = None
    if input_method == "📝 วางข้อความ":
        txt = st.text_area("วางเนื้อหาที่นี่:", height=150)
        if txt and st.button("🪄 วิเคราะห์"):
            with st.spinner("กำลังประมวลผล..."):
                res = process_monthly_report_ai(txt) if report_type == "สรุปรายเดือน (Monthly Summary)" else process_delivery_income_ai(txt)
    else:
        u_file = st.file_uploader("เลือกไฟล์", type=['pdf', 'jpg', 'png', 'jpeg'])
        if u_file and st.button("🪄 วิเคราะห์ไฟล์"):
            with st.spinner("กำลังอ่านไฟล์..."):
                res = process_monthly_report_ai(u_file.read(), is_bytes=True, mime_type=u_file.type) if report_type == "สรุปรายเดือน (Monthly Summary)" else process_delivery_income_ai(u_file.read(), is_bytes=True, mime_type=u_file.type)
    
    if res:
        st.session_state.inc_temp = pd.DataFrame(res)
        st.session_state.inc_temp_type = "Monthly" if report_type == "สรุปรายเดือน (Monthly Summary)" else "Income"

    if 'inc_temp' in st.session_state:
        edited = st.data_editor(st.session_state.inc_temp, use_container_width=True)
        if st.button("💾 ยืนยันบันทึก"):
            if save_data_to_sheets(edited, st.session_state.inc_temp_type):
                del st.session_state.inc_temp
                st.rerun()

elif page == "📊 Dashboard":
    st.header("📊 แดชบอร์ดวิเคราะห์ธุรกิจ")
    df = load_data()
    if not df.empty:
        df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
        tab_ov, tab_daily, tab_monthly = st.tabs(["🏠 ภาพรวมร้าน", "📅 สรุปรายวัน", "📈 วิเคราะห์รายเดือน"])
        
        with tab_ov:
            t_inc = df[df['type'].isin(['Income', 'Monthly'])]['total_price'].sum()
            t_exp = df[df['type'] == 'Expense']['total_price'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 รายรับรวม (Net)", f"฿{t_inc:,.2f}")
            c2.metric("📦 รายจ่ายวัตถุดิบ", f"฿{t_exp:,.2f}")
            c3.metric("📈 กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}", delta=f"{((t_inc-t_exp)/t_inc*100 if t_inc > 0 else 0):.1f}%")
            
            st.divider()
            fig_ov = px.pie(values=[t_inc, t_exp], names=['รายรับ', 'รายจ่าย'], hole=0.4, title="สัดส่วนรายรับ-รายจ่าย")
            st.plotly_chart(fig_ov, use_container_width=True)

        with tab_daily:
            inc = df[df['type'] == 'Income']
            if not inc.empty:
                fig_daily = px.bar(inc.sort_values('date'), x='date', y='total_price', color='name', title="แนวโน้มรายรับรายวัน")
                st.plotly_chart(fig_daily, use_container_width=True)
            else: st.info("ยังไม่มีข้อมูลรายวัน")

        with tab_monthly:
            m_data = df[df['type'] == 'Monthly'].copy()
            if not m_data.empty:
                m_data['gross'] = pd.to_numeric(m_data['gross'], errors='coerce')
                m_data['fees'] = pd.to_numeric(m_data['fees'], errors='coerce')
                m_data['fee_percent'] = (m_data['fees'] / m_data['gross'] * 100).round(2)
                
                st.subheader("เปรียบเทียบยอดโอนสุทธิ (Net)")
                fig_m = px.bar(m_data, x='month_year', y='total_price', color='platform', barmode='group')
                st.plotly_chart(fig_m, use_container_width=True)
                
                st.subheader("วิเคราะห์ต้นทุนแอป (%)")
                fig_fee = px.line(m_data, x='month_year', y='fee_percent', color='platform', markers=True)
                st.plotly_chart(fig_fee, use_container_width=True)
                
                st.dataframe(m_data[['month_year', 'platform', 'gross', 'fees', 'fee_percent', 'total_price']], use_container_width=True)
            else: st.info("ยังไม่มีข้อมูลรายเดือน")

elif page == "🤖 AI Agent":
    st.header("🤖 AI Business Assistant")
    if "agent_msgs" not in st.session_state: st.session_state.agent_msgs = []
    for r, m in st.session_state.agent_msgs:
        with st.chat_message(r): st.markdown(m)
    query = st.chat_input("ถามคำถาม...")
    if query:
        st.session_state.agent_msgs.append(("user", query))
        with st.chat_message("user"): st.markdown(query)
        ans = chat_with_stock_agent(query)
        with st.chat_message("assistant"): st.markdown(ans)
        st.session_state.agent_msgs.append(("assistant", ans))

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลทั้งหมด")
    df = load_data()
    st.dataframe(df, use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

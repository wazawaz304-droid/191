import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import difflib

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Nave 304 - AI Business Master", layout="wide", page_icon="🍜")

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

# --- 2.1 ระบบ Cache ข้อมูล ---
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
    if col_name in df.columns:
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

def safe_parse_json(text_response: str):
    if not text_response: return []
    try:
        content = text_response.strip()
        if "```" in content: content = content.split("```")[1]
        if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except: return []

def call_gemini_3_1(prompt, contents=None, is_complex_content=False):
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        if response.text:
            st.toast(f"🤖 ประมวลผลสำเร็จ", icon="✅")
            return response.text
    except: return None

def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    if p_type == "Expense":
        master_list = ", ".join([f"'{n}'" for n in existing_names]) if existing_names else "ไม่มี (ให้ใช้ชื่อตามบิล)"
        p = f"""คุณคือสมุห์บัญชีร้าน 'เนฟ หมี่ไก่ฉีก 304' สกัดข้อมูลรายจ่ายเป็น JSON array
        กฎการตั้งชื่อ (STRICT RULE):
        1. ตรวจสอบชื่อสินค้าเทียบกับ 'รายชื่อเดิมในระบบ': [{master_list}]
        2. 'ต้อง' จับคู่กับรายชื่อเดิมที่มีความหมายใกล้เคียงก่อนเสมอ (เช่น 'อกไก่สด' ให้ใช้ 'ไก่')
        3. คำนวณ 'unit_price' (total_price / qty) มาให้ด้วย
        รูปแบบ JSON: [{{'date': '{now_str}', 'name': 'ชื่อสินค้า', 'qty': 0, 'unit': 'หน่วย', 'unit_price': 0, 'total_price': 0}}]"""
    elif p_type == "หน้าร้าน":
        p = f"สกัดยอดหน้าร้าน: [{{'date': '{now_str}', 'app': 'หน้าร้าน', 'net_income': ยอดขาย}}]"
    elif p_type == "สรุปรายเดือน":
        p = "สกัดรายงานรายเดือน: [{'month_year': 'YYYY-MM', 'platform': 'แอป', 'gross': 0, 'fees': 0, 'ads': 0, 'discounts': 0, 'net_income': 0}]"
    else:
        p = f"สกัดรายได้เดลิเวอรี่รายวัน: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': ยอดโอน}}]"
    
    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
        res = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini_3_1(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        # 1. จัดการข้อมูลแต่ละประเภท
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)
        
        elif tab == "Expense":
            df['type'] = 'Expense'
            existing_data = load_data("Expense")
            if not existing_data.empty and 'name' in existing_data.columns:
                master_names = existing_data['name'].unique().tolist()
                def match_master_name(name):
                    matches = difflib.get_close_matches(str(name), master_names, n=1, cutoff=0.6)
                    return matches[0] if matches else name
                df['name'] = df['name'].apply(match_master_name)
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
            
        elif tab == "Monthly":
            df['type'] = 'Monthly'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)

        # 2. บันทึกลง Sheet
        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# --- 4. UI Layout ---
st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# (Dashboard และ Monthly วิเคราะห์ใช้โค้ดเดิมของคุณที่ทำงานได้ปกติ)
if page == "📊 Dashboard รายวัน":
    st.header("📊 แดชบอร์ดรายรับ-รายจ่ายรายวัน")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')
    
    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรายวันรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อกรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ ยอดหักลบ (กำไร)", f"฿{t_inc - t_exp:,.0f}")

    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['u_price'] = clean_numeric(df_item, 'total_price') / clean_numeric(df_item, 'qty').replace(0, 1)
            st.plotly_chart(px.line(df_item, x='date', y='u_price', markers=True, title=f"ราคา {target} ต่อหน่วย"), use_container_width=True)

# --- 💸 บันทึกรายจ่าย (จุดที่แก้ไข Logic การจับคู่ชื่อ) ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    df_exp_db = load_data("Expense")
    existing_list = df_exp_db['name'].unique().tolist() if not df_exp_db.empty else []

    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    
    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img_file = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        
        if img_file and st.button("🪄 วิเคราะห์บิล"):
            # แก้ไข: ใช้ img_file.read() ให้ถูกต้อง
            img_data = img_file.read() if sub == "📁 เลือกไฟล์" else img_file.getvalue()
            res_ex = process_extraction(img_data, "Expense", is_bytes=True, mime="image/jpeg", existing_names=existing_list)
            
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type, existing_names=existing_list)

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- (เมนูอื่นๆ คงเดิมแต่จัด Indentation ให้ถูกต้อง) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"): res = process_extraction(txt, rtype)
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("กดพูดรายการรายรับ...")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)
    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf','jpg','png'])
        if file and st.button("🪄 วิเคราะห์ไฟล์"):
            res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 บันทึกลงฐานข้อมูล"):
            target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
            if save_to_tab(edited, target_tab):
                del st.session_state.tmp_inc
                st.rerun()

elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if q:
        df_i, df_e, df_m = load_data("Income"), load_data("Expense"), load_data("Monthly")
        ctx = f"Income Daily: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}"
        with st.chat_message("assistant"):
            st.write(call_gemini_3_1(f"วิเคราะห์ข้อมูลร้านเนฟ หมี่ไก่ฉีก:\n{ctx}\nคำถาม: {q}"))

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลแยกแท็บ")
    t1, t2, t3 = st.tabs(["📥 Income (รายวัน)", "📊 Monthly (รายเดือน)", "📤 Expense (รายจ่าย)"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Monthly"), use_container_width=True)
    with t3: st.dataframe(load_data("Expense"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

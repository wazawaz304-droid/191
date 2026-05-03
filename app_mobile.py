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

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Nave 304 - AI Business Master", layout="wide", page_icon="🍜")

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

# --- 3. ฟังก์ชันจัดการข้อมูล (เน้นความปลอดภัย ข้อมูลห้ามหาย!) ---

def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        # ปิด Cache (ttl=0) เพื่อให้เห็นข้อมูลจริงในชีตเสมอ
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how='all') if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        # ลบสัญลักษณ์เงิน คอมม่า และตัวอักษรอื่นออก ให้เหลือแต่เลข
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        # ดึงข้อมูลเดิมมาตรวจสอบก่อน
        existing = load_data(tab)
        
        # จัดการข้อมูลแยกตามประเภท
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
        elif tab == "Expense":
            df['type'] = 'Expense'
            # Mapping ชื่อเดิม
            if not existing.empty and 'name' in existing.columns:
                master_names = existing['name'].unique().tolist()
                def match_name(n):
                    matches = difflib.get_close_matches(str(n), master_names, n=1, cutoff=0.6)
                    return matches[0] if matches else n
                df['name'] = df['name'].apply(match_name)
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        elif tab == "Monthly":
            df['type'] = 'Monthly'

        # รวมข้อมูล: เอาของใหม่ต่อท้ายของเดิม
        final = pd.concat([existing, df], ignore_index=True)
        
        # อัปเดตกลับไป
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear() # ล้างแคชทั้งหมด
        st.success(f"✅ บันทึกลง {tab} เรียบร้อยแล้ว (รวมทั้งหมด {len(final)} แถว)")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# --- 4. ฟังก์ชัน AI ---
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"
    
    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. ใช้ชื่อเดิมเหล่านี้ถ้าคล้าย: [{names_str}]"
    else:
        p = f"สกัดข้อมูลรายได้เป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': 0}}]"

    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])
        
        text = res.text.strip()
        if "```" in text: text = text.split("```")[1].replace("json", "")
        return json.loads(text)
    except: return []

# --- 5. เมนูและ UI ---
st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 6. แสดงผล ---

if page == "📊 Dashboard รายวัน":
    st.header("📊 แดชบอร์ดรายรับ-รายจ่าย")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # สถิติพื้นฐานเพื่อให้มั่นใจว่าข้อมูลอยู่ครบ
    c1, c2, c3 = st.columns(3)
    if not df_i.empty:
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
        c1.metric("💰 รายรับรวม (ทั้งชีต)", f"฿{df_i['net_income'].sum():,.0f}")
    
    if not df_e.empty:
        df_e['total_price'] = clean_numeric(df_e, 'total_price')
        df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')
        c2.metric("📦 รายจ่ายรวม (ทั้งชีต)", f"฿{df_e['total_price'].sum():,.0f}")
        
    # กราฟย้อนหลัง
    st.divider()
    days = st.selectbox("ดูย้อนหลัง:", [7, 30, 90, 365], index=1)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    
    col1, col2 = st.columns(2)
    with col1:
        mask_i = df_i[df_i['date'] >= cutoff] if not df_i.empty else pd.DataFrame()
        if not mask_i.empty:
            st.plotly_chart(px.bar(mask_i, x='date', y='net_income', color='app', title="แนวโน้มรายรับ"), use_container_width=True)
        else: st.info("ไม่มีรายรับในช่วงวันที่เลือก")
    
    with col2:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่าย"), use_container_width=True)

elif page == "📈 วิเคราะห์รายเดือน":
    st.header("📈 วิเคราะห์รายเดือน")
    df_m = load_data("Monthly")
    if not df_m.empty:
        df_m['net_income'] = clean_numeric(df_m, 'net_income')
        st.dataframe(df_m.sort_values('month_year', ascending=False), use_container_width=True)
    else: st.info("ยังไม่มีข้อมูลรายเดือน")

elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("วางข้อความรายงานยอดขายที่นี่:")
        if st.button("🪄 วิเคราะห์ด้วย AI"): res = process_extraction(txt, rtype)
    else:
        file = st.file_uploader("เลือกไฟล์รูปภาพ/PDF", type=['pdf','jpg','png'])
        if st.button("🪄 วิเคราะห์ไฟล์"):
            res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 ยืนยันบันทึก"):
            if save_to_tab(edited, "Monthly" if rtype=="สรุปรายเดือน" else "Income"):
                del st.session_state.tmp_inc
                st.rerun()

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    df_exp_db = load_data("Expense")
    ex_names = df_exp_db['name'].unique().tolist() if not df_exp_db.empty else []
    
    file = st.file_uploader("แสกนบิลรายจ่าย", type=['jpg','png','jpeg'])
    if file and st.button("🪄 วิเคราะห์บิล"):
        res = process_extraction(file.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=ex_names)
        if res: st.session_state.tmp_exp = pd.DataFrame(res)
        
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกรายจ่าย"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลดิบใน Google Sheets")
    t1, t2, t3 = st.tabs(["รายรับ", "รายจ่าย", "สรุปรายเดือน"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Expense"), use_container_width=True)
    with t3: st.dataframe(load_data("Monthly"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

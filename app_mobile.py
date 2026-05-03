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

# --- 3. ฟังก์ชันจัดการข้อมูล (เน้นความรอบคอบ ข้อมูลไม่หาย) ---

def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        # ใช้ ttl=0 เพื่อดึงข้อมูลสดเสมอ ป้องกันปัญหาข้อมูลหายจาก Cache
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        # ลบสัญลักษณ์เงินและคอมม่าออกให้หมดก่อนแปลงเป็นตัวเลข
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab) # ดึงของเดิมมาก่อน
        
        if tab == "Expense":
            df['type'] = 'Expense'
            # ระบบ Mapping ชื่อเดิม (Fuzzy Match)
            if not existing.empty and 'name' in existing.columns:
                master_names = existing['name'].unique().tolist()
                def match_name(n):
                    m = difflib.get_close_matches(str(n), master_names, n=1, cutoff=0.6)
                    return m[0] if m else n
                df['name'] = df['name'].apply(match_name)
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        
        elif tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
            
        # รวมร่างข้อมูลเดิมกับใหม่ ห้ามทำของเก่าหาย!
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        load_data.clear() # ล้าง Cache เพื่อให้หน้าจออัปเดต
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# --- 4. ฟังก์ชัน AI สกัดข้อมูล ---
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"
    
    if p_type == "Expense":
        names = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = f"สกัดบิลรายจ่าย JSON: [{{'date': '{now_str}', 'name': 'ชื่อสินค้า', 'qty': 0, 'unit': 'หน่วย', 'total_price': 0}}]. จับคู่กับชื่อเดิม: [{names}]"
    else:
        p = f"สกัดรายได้ JSON: [{{'date': '{now_str}', 'app': 'แอป', 'net_income': 0}}]"

    prompt = p + " ตอบเฉพาะ PURE JSON"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])
        
        # Parse JSON
        text = res.text.strip()
        if "```" in text: text = text.split("```")[1].replace("json", "")
        return json.loads(text)
    except: return []

# --- 5. UI Layout (ย้ายมาไว้ก่อนการเรียกใช้ตัวแปร page) ---
st.sidebar.title("🚀 Nave 304 Master")
# บรรทัดนี้สำคัญมาก! ต้องสร้างตัวแปร page ก่อนจะเอาไป if
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 6. ส่วนการแสดงผลแต่ละหน้า ---

if page == "📊 Dashboard รายวัน":
    st.header("📊 แดชบอร์ดรายรับ-รายจ่าย")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # ทำความสะอาดข้อมูลก่อนโชว์
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    # Metrics รวมทั้งหมด
    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรวม (All Time)", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม (All Time)", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรสะสม", f"฿{t_inc - t_exp:,.0f}")

    # กราฟย้อนหลัง
    st.divider()
    days = st.selectbox("ช่วงเวลา:", [7, 30, 90], index=1)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    mask = df_i[df_i['date'] >= cutoff]
    
    if not mask.empty:
        fig = px.bar(mask, x='date', y='net_income', color='app', title=f"รายรับย้อนหลัง {days} วัน")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลในช่วงวันที่เลือก")

elif page == "📈 วิเคราะห์รายเดือน":
    st.header("📈 วิเคราะห์รายเดือน")
    df_m = load_data("Monthly")
    if not df_m.empty:
        df_m['net_income'] = clean_numeric(df_m, 'net_income')
        st.dataframe(df_m.sort_values('month_year', ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายเดือน")

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    df_exp_db = load_data("Expense")
    ex_names = df_exp_db['name'].unique().tolist() if not df_exp_db.empty else []
    
    img = st.file_uploader("สแกนบิล", type=['jpg', 'png', 'jpeg'])
    if img and st.button("🪄 วิเคราะห์"):
        res = process_extraction(img.read(), "Expense", is_bytes=True, mime="image/jpeg", existing_names=ex_names)
        if res:
            st.session_state.tmp_exp = pd.DataFrame(res)
    
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp)
        if st.button("💾 บันทึก"):
            if save_to_tab(edited, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลดิบในระบบ")
    for t in ["Income", "Expense", "Monthly"]:
        st.subheader(f"แผ่นงาน: {t}")
        st.dataframe(load_data(t), use_container_width=True)

# (หน้าอื่นๆ เช่น AI Agent หรือ บันทึกรายรับ สามารถใส่เพิ่มเติมในรูปแบบเดียวกันนี้ได้ครับ)

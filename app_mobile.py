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
import logging

# ==========================================
# 1. การตั้งค่าพื้นฐาน (CONFIGURATION)
# ==========================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜"
)

# ค่าคงที่สำหรับชื่อชีทและโมเดล
TAB_INCOME = "Income"
TAB_EXPENSE = "Expense"
TAB_MONTHLY = "Monthly"
AI_MODEL = "models/gemini-3.1-flash-lite-preview"

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)

# ==========================================
# 2. การเชื่อมต่อ (CONNECTIONS)
# ==========================================
@st.cache_resource
def get_gsheets_conn():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        return None

@st.cache_resource
def get_ai_client():
    try:
        return genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except Exception as e:
        st.error(f"⚠️ ไม่พบ API Key ใน Secrets: {e}")
        return None

conn = get_gsheets_conn()
ai_client = get_ai_client()

# ==========================================
# 3. ฟังก์ชันจัดการข้อมูล (DATA MANAGEMENT)
# ==========================================
@st.cache_data(ttl=60)
def load_data(sheet_name):
    """โหลดข้อมูลจาก Google Sheets พร้อมระบบแคช"""
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        logging.error(f"Error loading {sheet_name}: {e}")
        return pd.DataFrame()

def refresh_all_caches():
    """ล้างแคชข้อมูลทั้งหมด"""
    load_data.clear()

def clean_numeric(df, col_name):
    """ทำความสะอาดข้อมูลตัวเลข (ลบ ฿ และคอมม่า)"""
    if col_name in df.columns:
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''), 
            errors='coerce'
        ).fillna(0)
    return pd.Series([0] * len(df))

def save_to_tab(df, tab):
    """บันทึกข้อมูลลงในแท็บที่กำหนด โดยรวมกับข้อมูลเดิม"""
    if conn is None or df.empty: return False
    try:
        # จัดการโครงสร้างข้อมูลเบื้องต้น
        if tab == TAB_INCOME:
            df['type'] = 'Income'
            if 'name' not in df.columns: 
                df['name'] = df['app'] + " Daily Income"
        elif tab == TAB_EXPENSE:
            df['type'] = 'Expense'
            if 'name' not in df.columns: df['name'] = 'ไม่ได้ระบุ'
        elif tab == TAB_MONTHLY:
            df['type'] = 'Monthly'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)

        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        st.success(f"✅ บันทึกลงแท็บ {tab} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ==========================================
# 4. ฟังก์ชัน AI (AI SERVICES)
# ==========================================
def safe_parse_json(text_response: str):
    """สกัด JSON จากคำตอบของ AI อย่างปลอดภัย"""
    if not text_response: return []
    try:
        content = text_response.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        logging.error(f"JSON Parse Error: {e}")
        return []

def call_gemini(prompt, contents=None, is_complex=False):
    """เรียกใช้ Gemini API"""
    if ai_client is None: return None
    try:
        if is_complex:
            response = ai_client.models.generate_content(model=AI_MODEL, contents=contents)
        else:
            input_parts = [prompt] + (contents if contents else [])
            response = ai_client.models.generate_content(model=AI_MODEL, contents=input_parts)
        
        if response.text:
            st.toast("🤖 AI ประมวลผลสำเร็จ", icon="✅")
            return response.text
    except Exception as e:
        logging.error(f"AI Call Error: {e}")
        return None

def process_extraction(data, p_type, is_bytes=False, mime=None):
    """สกัดข้อมูลด้วย AI ตามประเภทที่กำหนด"""
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    prompts = {
        "Expense": f"สกัดสินค้าเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. หากบิลไม่ระบุวันที่ให้ใช้ {now_str}",
        "หน้าร้าน": f"สกัดยอดหน้าร้านจากข้อความหรือเสียง: [{{'date': '{now_str}', 'app': 'หน้าร้าน', 'net_income': ยอดขาย}}]. วันนี้คือวันที่ {now_str} ให้ใช้วันที่นี้เป็นค่าเริ่มต้น",
        "สรุปรายเดือน": "สกัดรายงานรายเดือนเป็น JSON: [{'month_year': 'YYYY-MM', 'platform': 'แอป', 'gross': 0, 'fees': 0, 'ads': 0, 'discounts': 0, 'net_income': 0}]",
        "default": f"สกัดรายได้เดลิเวอรี่รายวันเป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': ยอดโอน}}]. วันนี้คือวันที่ {now_str}"
    }
    
    p = prompts.get(p_type, prompts["default"])
    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
        res = call_gemini(prompt, contents=contents, is_complex=True)
    else:
        res = call_gemini(prompt, contents=[data])
    
    return safe_parse_json(res)

# ==========================================
# 5. ส่วนแสดงผล UI (UI PAGES)
# ==========================================
def show_dashboard():
    st.header("📊 แดชบอร์ดรายรับ-รายจ่ายรายวัน")
    df_i = load_data(TAB_INCOME)
    df_e = load_data(TAB_EXPENSE)
    
    # ทำความสะอาดข้อมูล
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')
    
    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรายวันรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อกรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ ยอดหักลบ (กำไร)", f"฿{t_inc - t_exp:,.0f}", delta=f"{t_inc - t_exp:,.0f}")
    
    st.divider()
    
    t_daily, t_stock, t_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    
    with t_daily:
        zoom = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True, format_func=lambda x: f"{x} วัน")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=zoom)
        df_f = df_i[df_i['date'] >= cutoff].copy()
        
        if not df_f.empty:
            daily = df_f.groupby('date')['net_income'].sum().reset_index()
            daily['rolling'] = daily['net_income'].rolling(window=7).mean()
            fig = go.Figure()
            for app in df_f['app'].unique():
                d = df_f[df_f['app'] == app]
                fig.add_trace(go.Bar(x=d['date'], y=d['net_income'], name=app))
            fig.add_trace(go.Scatter(x=daily['date'], y=daily['rolling'], name='แนวโน้ม (7วัน)', line=dict(color='orange', dash='dot')))
            fig.update_layout(barmode='stack', title=f"ยอดรายวันย้อนหลัง {zoom} วัน")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("ไม่มีข้อมูลในช่วงนี้")
        
    with t_stock:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่ายสต๊อก"), use_container_width=True)
            
    with t_price:
        if not df_e.empty and 'name' in df_e.columns:
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['u_price'] = df_item['total_price'] / clean_numeric(df_item, 'qty').replace(0, 1)
            st.plotly_chart(px.line(df_item, x='date', y='u_price', markers=True, title=f"แนวโน้มราคา {target} ต่อหน่วย"), use_container_width=True)

def show_monthly_analysis():
    st.header("📈 วิเคราะห์รายเดือน (Deep Dive)")
    df_m = load_data(TAB_MONTHLY)
    
    if not df_m.empty:
        for col in ['net_income', 'gross', 'fees', 'ads']:
            df_m[col] = clean_numeric(df_m, col)
            
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 ยอดโอนสุทธิรายเดือน", f"฿{df_m['net_income'].sum():,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{df_m['gross'].sum():,.0f}")
        m3.metric("📉 ค่า GP/โฆษณารวม", f"฿{df_m['fees'].sum() + df_m['ads'].sum():,.0f}")
        
        st.divider()
        
        c_m1, c_m2 = st.columns([2, 1])
        with c_m1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='ยอดขายรวม (Gross)'))
            fig.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='เงินโอนสุทธิ (Net)'))
            fig.update_layout(barmode='group', title="เปรียบเทียบยอดขาย vs เงินโอนจริง")
            st.plotly_chart(fig, use_container_width=True)
        with c_m2:
            st.plotly_chart(px.pie(df_m, values='fees', names='platform', title="ค่า GP แยกตามแอป"), use_container_width=True)
            
        st.subheader("📋 ตารางสรุปยอดละเอียดรายเดือน")
        df_m['cost_pct'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'] * 100).round(2)
        st.dataframe(df_m[['month_year', 'platform', 'gross', 'fees', 'ads', 'net_income', 'cost_pct']].sort_values('month_year', ascending=False), use_container_width=True)
    else: st.info("ยังไม่มีข้อมูลรายเดือน")

def show_record_income():
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
            
    if res: st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 บันทึกลงฐานข้อมูล"):
            target = TAB_MONTHLY if rtype == "สรุปรายเดือน" else TAB_INCOME
            if save_to_tab(edited, target):
                del st.session_state.tmp_inc
                st.rerun()

def show_record_expense():
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    
    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์บิล"):
            data = Image.open(img) if sub=="📷 ถ่ายรูปสด" else img.read()
            res_ex = process_extraction(data, "Expense", is_bytes=(sub=="📁 เลือกไฟล์"), mime="image/jpeg")
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio = st.audio_input("พูดรายการรายจ่าย...")
        if audio and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio.read(), "Expense", is_bytes=True, mime=audio.type)
            
    if res_ex: st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited, TAB_EXPENSE):
                del st.session_state.tmp_exp
                st.rerun()

def show_ai_agent():
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if q:
        df_i, df_e, df_m = load_data(TAB_INCOME), load_data(TAB_EXPENSE), load_data(TAB_MONTHLY)
        ctx = f"Income Daily: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}"
        with st.chat_message("assistant"):
            st.write(call_gemini(f"วิเคราะห์ข้อมูลร้านเนฟ หมี่ไก่ฉีก:\n{ctx}\nคำถาม: {q}"))

def show_all_data():
    st.header("📋 ข้อมูลแยกแท็บ")
    t1, t2, t3 = st.tabs(["📥 Income (รายวัน)", "📊 Monthly (รายเดือน)", "📤 Expense (รายจ่าย)"])
    with t1: st.dataframe(load_data(TAB_INCOME), use_container_width=True)
    with t2: st.dataframe(load_data(TAB_MONTHLY), use_container_width=True)
    with t3: st.dataframe(load_data(TAB_EXPENSE), use_container_width=True)

# ==========================================
# 6. ส่วนควบคุมหลัก (MAIN CONTROL)
# ==========================================
def main():
    st.sidebar.title("🚀 Nave 304 Master")
    page = st.sidebar.radio(
        "เลือกเมนู:", 
        ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"]
    )
    
    if page == "📊 Dashboard รายวัน": show_dashboard()
    elif page == "📈 วิเคราะห์รายเดือน": show_monthly_analysis()
    elif page == "💰 บันทึกรายรับ": show_record_income()
    elif page == "💸 บันทึกรายจ่าย": show_record_expense()
    elif page == "🤖 AI Agent": show_ai_agent()
    elif page == "📋 ข้อมูลทั้งหมด": show_all_data()
    
    if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
        refresh_all_caches()
        st.rerun()

if __name__ == "__main__":
    main()

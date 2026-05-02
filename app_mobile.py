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

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Nave 304 - Smart Business AI", layout="wide", page_icon="🍜")

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

def process_extraction(data, p_type, is_bytes=False, mime=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    if p_type == "Expense":
        p = f"สกัดสินค้าเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. หากบิลไม่ระบุวันที่ให้ใช้ {now_str}"
    elif p_type == "หน้าร้าน":
        p = f"สกัดยอดหน้าร้านจากข้อความหรือเสียง: [{{'date': '{now_str}', 'app': 'หน้าร้าน', 'net_income': ยอดขาย}}]. วันนี้คือวันที่ {now_str} ให้ใช้วันที่นี้เป็นค่าเริ่มต้น"
    elif p_type == "สรุปรายเดือน":
        p = "สกัดรายงานรายเดือนเป็น JSON: [{'month_year': 'YYYY-MM', 'platform': 'แอป', 'gross': 0, 'fees': 0, 'ads': 0, 'discounts': 0, 'net_income': 0}]"
    else:
        p = f"สกัดรายได้เดลิเวอรี่รายวันเป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': ยอดโอน}}]. วันนี้คือวันที่ {now_str}"
    
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
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)
        elif tab == "Expense":
            df['type'] = 'Expense'
            if 'name' not in df.columns: df['name'] = 'ไม่ได้ระบุ'
        elif tab == "Monthly":
            df['type'] = 'Monthly'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)

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
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard (แยกมิติ Daily vs Monthly) ---
if page == "📊 Dashboard":
    st.header("📊 บทวิเคราะห์ผลประกอบการ (แยกมิติรายวัน/รายเดือน)")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    df_m = load_data("Monthly")
    
    # ล้างข้อมูลตัวเลขทั้งหมด
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_m['net_income'] = clean_numeric(df_m, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    # ส่วน Metric ภาพรวม
    t_inc_daily = df_i['net_income'].sum()
    t_inc_monthly = df_m['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรายวันสะสม", f"฿{t_inc_daily:,.0f}")
    c2.metric("📱 รายรับสรุปรายเดือน", f"฿{t_inc_monthly:,.0f}", help="ยอดโอนสุทธิจากแท็บ Monthly")
    c3.metric("📦 รายจ่ายสต๊อก", f"฿{t_exp:,.0f}")
    
    st.divider()

    # แยกแท็บใน Dashboard ชัดเจน
    tab_daily, tab_monthly, tab_stock = st.tabs(["📅 รายวัน (Daily)", "📊 รายเดือน (Monthly)", "📈 วิเคราะห์สต๊อก"])
    
    with tab_daily:
        st.subheader("แนวโน้มรายรับรายวัน")
        zoom_days = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True, format_func=lambda x: f"{x} วัน", key="zoom_daily")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=zoom_days)
        df_filt = df_i[df_i['date'] >= cutoff].copy()

        if not df_filt.empty:
            daily_total = df_filt.groupby('date')['net_income'].sum().reset_index()
            daily_total['rolling'] = daily_total['net_income'].rolling(window=7).mean()
            fig = go.Figure()
            for app in df_filt['app'].unique():
                d = df_filt[df_filt['app'] == app]
                fig.add_trace(go.Bar(x=d['date'], y=d['net_income'], name=app))
            fig.add_trace(go.Scatter(x=daily_total['date'], y=daily_total['rolling'], name='แนวโน้ม (7วัน)', line=dict(color='orange', dash='dot')))
            fig.update_layout(barmode='stack', hovermode="x unified", title=f"ยอดขายรายวันย้อนหลัง {zoom_days} วัน")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("ไม่มีข้อมูลรายวันในช่วงนี้")

    with tab_monthly:
        if not df_m.empty:
            st.subheader("เปรียบเทียบยอดขาย vs เงินโอนสุทธิ (รายเดือน)")
            df_m['gross'] = clean_numeric(df_m, 'gross')
            
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='ยอดขายรวม (Gross)'))
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='เงินโอนจริง (Net)'))
            fig_m.update_layout(barmode='group', title="ยอดขาย Gross vs Net รายเดือน")
            st.plotly_chart(fig_m, use_container_width=True)

            # ตารางวิเคราะห์ค่า GP/Ads
            st.write("📋 สรุปรายละเอียดรายเดือน")
            st.dataframe(df_m[['month_year', 'platform', 'gross', 'net_income', 'fees', 'ads']].sort_values('month_year', ascending=False), use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลในแท็บ Monthly")

    with tab_stock:
        if not df_e.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่าย"), use_container_width=True)
            with col2:
                target = st.selectbox("เลือกสินค้าดูราคา:", sorted(df_e['name'].unique()))
                df_item = df_e[df_e['name'] == target].sort_values('date')
                df_item['u_price'] = df_item['total_price'] / clean_numeric(df_item, 'qty').replace(0, 1)
                st.plotly_chart(px.line(df_item, x='date', y='u_price', markers=True, title=f"แนวโน้มราคา {target}"), use_container_width=True)

# --- 💰 บันทึกรายรับ ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล (เช่น 'วันนี้หน้าร้านได้ 3000' หรือ วางอีเมลเดลิเวอรี่):")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"):
            res = process_extraction(txt, rtype)
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
            # ตรวจสอบว่าต้องลงแท็บไหน
            target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
            if save_to_tab(edited, target_tab):
                del st.session_state.tmp_inc
                st.rerun()

# --- 💸 บันทึกรายจ่าย ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    
    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์บิล"):
            res_ex = process_extraction(Image.open(img) if sub=="📷 ถ่ายรูปสด" else img.read(), "Expense", is_bytes=(sub=="📁 เลือกไฟล์"), mime="image/jpeg")
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type)

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- 🤖 AI Agent & ข้อมูลทั้งหมด ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if q:
        df_i, df_e, df_m = load_data("Income"), load_data("Expense"), load_data("Monthly")
        ctx = f"รายรับรายวัน:\n{df_i.tail(5).to_csv()}\nรายรับรายเดือน:\n{df_m.tail(3).to_csv()}"
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

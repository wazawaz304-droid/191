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
        # เพิ่ม 'ชื่อมาตรฐาน' และ 'unit_price' เข้าไปในคำสั่ง
        p = f"""สกัดข้อมูลรายจ่ายจากบิลเป็น JSON โดยมีเงื่อนไข:
        1. 'name': ให้เปลี่ยนชื่อสินค้าที่คล้ายกันให้เป็นชื่อมาตรฐานเดียวกันเสมอ 
           (เช่น 'อกไก่', 'ไก่สด', 'น่องไก่' -> ให้ใช้ชื่อ 'ไก่')
           (เช่น 'น้ำมันพืช 1 ลิตร', 'น้ำมันองุ่น' -> ให้ใช้ชื่อ 'น้ำมัน')
        2. 'unit_price': ให้คำนวณราคาต่อหน่วย (total_price หารด้วย qty)
        รูปแบบ JSON: [{{
            'date': '{now_str}', 
            'name': 'ชื่อมาตรฐาน', 
            'qty': 0, 
            'unit': 'หน่วย', 
            'unit_price': 0, 
            'total_price': 0
        }}]
        หากบิลไม่ระบุวันที่ให้ใช้ {now_str}"""
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
            # ตรวจสอบว่ามี unit_price หรือไม่ ถ้าไม่มีให้คำนวณซ้ำอีกทีเพื่อความชัวร์
            if 'unit_price' not in df.columns:
                df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
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
# ปรับปรุงเมนู: แยก Dashboard และ วิเคราะห์รายเดือน
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard รายวัน (เน้น รายรับรายวัน - รายจ่าย) ---
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
    c3.metric("⚖️ ยอดหักลบ (กำไร)", f"฿{t_inc - t_exp:,.0f}", delta=f"{t_inc - t_exp:,.0f}")
    
    st.divider()
    
    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    
    with tab_inc:
        zoom_days = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True, format_func=lambda x: f"{x} วัน", key="z_daily")
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
            fig.update_layout(barmode='stack', hovermode="x unified", title=f"ยอดรายวันย้อนหลัง {zoom_days} วัน")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("ไม่มีข้อมูลรายวันในช่วงนี้")

    with tab_exp:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่ายสต๊อก"), use_container_width=True)

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['u_price'] = df_item['total_price'] / clean_numeric(df_item, 'qty').replace(0, 1)
            st.plotly_chart(px.line(df_item, x='date', y='u_price', markers=True, title=f"แนวโน้มราคา {target} ต่อหน่วย"), use_container_width=True)

# --- 📈 วิเคราะห์รายเดือน (ใหม่: แยกสรุปยอดแบบละเอียด) ---
elif page == "📈 วิเคราะห์รายเดือน":
    st.header("📈 สรุปยอดและวิเคราะห์รายเดือน (Deep Dive)")
    df_m = load_data("Monthly")
    
    if not df_m.empty:
        df_m['net_income'] = clean_numeric(df_m, 'net_income')
        df_m['gross'] = clean_numeric(df_m, 'gross')
        df_m['fees'] = clean_numeric(df_m, 'fees')
        df_m['ads'] = clean_numeric(df_m, 'ads')
        
        # Metric รายเดือน
        total_m_net = df_m['net_income'].sum()
        total_m_gross = df_m['gross'].sum()
        total_fees = df_m['fees'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 ยอดโอนสุทธิรายเดือน", f"฿{total_m_net:,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{total_m_gross:,.0f}")
        m3.metric("📉 ค่า GP/โฆษณารวม", f"฿{total_fees + df_m['ads'].sum():,.0f}")
        
        st.divider()
        
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.subheader("เปรียบเทียบยอดขาย vs เงินโอนจริง")
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='ยอดขายรวม (Gross)'))
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='เงินโอนสุทธิ (Net)'))
            fig_m.update_layout(barmode='group')
            st.plotly_chart(fig_m, use_container_width=True)
            
        with col_m2:
            st.subheader("สัดส่วนค่าธรรมเนียมแอป")
            fig_pie_m = px.pie(df_m, values='fees', names='platform', title="ค่า GP แยกตามแอป")
            st.plotly_chart(fig_pie_m, use_container_width=True)
            
        st.subheader("📋 ตารางสรุปยอดละเอียดรายเดือน")
        # คำนวณ % ต้นทุนให้เห็นชัดๆ
        df_m['cost_pct'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'] * 100).round(2)
        st.dataframe(df_m[['month_year', 'platform', 'gross', 'fees', 'ads', 'net_income', 'cost_pct']].sort_values('month_year', ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในแท็บ Monthly กรุณาบันทึกรายงานสรุปรายเดือนก่อนครับ")

# --- 💰 บันทึกรายรับ (คงเดิม) ---
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

# --- 💸 บันทึกรายจ่าย (คงเดิม) ---
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

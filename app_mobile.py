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
st.set_page_config(page_title="Nave 304 - Smart Dashboard", layout="wide", page_icon="📈")

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

@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

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

# --- 5. UI Layout ---
st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

if page == "📊 Dashboard":
    st.header("📊 บทวิเคราะห์รายได้และกำไร")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # เตรียมข้อมูล
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    
    # สรุป Metric หลัก
    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    avg_inc = df_i.groupby('date')['net_income'].sum().mean() if not df_i.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับสุทธิรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อก", f"฿{t_exp:,.0f}")
    c3.metric("📈 กำไรสุทธิ", f"฿{t_inc - t_exp:,.0f}")
    c4.metric("📅 เฉลี่ยรายวัน", f"฿{avg_inc:,.0f}")
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📅 กราฟรายรับ (ดูง่าย)", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    
    with tab1:
        if not df_i.empty:
            # รวมยอดรายวันเพื่อสร้างเส้นแนวโน้ม
            daily_total = df_i.groupby('date')['net_income'].sum().reset_index()
            daily_total['rolling_avg'] = daily_total['net_income'].rolling(window=7).mean()

            # สร้างกราฟผสม (แท่งซ้อน + เส้นแนวโน้ม)
            fig = go.Figure()

            # เพิ่มกราฟแท่งแยกตามแอป (Stacked)
            for app in df_i['app'].unique():
                df_app = df_i[df_i['app'] == app]
                fig.add_trace(go.Bar(
                    x=df_app['date'], y=df_app['net_income'], name=app,
                    hovertemplate="%{x|%d %b}: ฿%{y:,.0f}"
                ))

            # เพิ่มเส้นค่าเฉลี่ย 7 วัน
            fig.add_trace(go.Scatter(
                x=daily_total['date'], y=daily_total['rolling_avg'],
                name='แนวโน้ม (7 วัน)', line=dict(color='orange', width=3, dash='dot')
            ))

            fig.update_layout(
                title="รายรับรวมรายวัน (ซ้อนแยกแอป) และเส้นแนวโน้ม",
                xaxis_title="วันที่", yaxis_title="ยอดโอนสุทธิ (บาท)",
                barmode='stack', # ให้แท่งซ้อนกัน
                legend_orientation="h",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # กราฟวงกลมแสดงสัดส่วนรายได้
            st.subheader("📱 ส่วนแบ่งรายได้ตามช่องทาง")
            fig_pie = px.pie(df_i, values='net_income', names='app', hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายรับ")

    with tab2:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่ายสต๊อก"), use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab3:
        if not df_e.empty and 'name' in df_e.columns:
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['unit_price'] = clean_numeric(df_item, 'total_price') / clean_numeric(df_item, 'qty').replace(0, 1)
            st.plotly_chart(px.line(df_item, x='date', y='unit_price', markers=True, title=f"แนวโน้มราคา {target}"), use_container_width=True)

# --- คงส่วนอื่นๆ ของระบบบันทึกไว้ตามเดิม ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    # ... โค้ดส่วนบันทึกรายรับเดิมของคุณ ...
    st.info("ใช้ระบบบันทึกแบบพิมพ์/เสียง/ไฟล์ ตามเดิมได้เลยครับ")

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    # ... โค้ดส่วนบันทึกรายจ่ายเดิมของคุณ ...

elif page == "🤖 AI Agent":
    st.header("🤖 AI Agent")
    # ... โค้ด AI Agent เดิมของคุณ ...

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลดิบ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"))
    with t2: st.dataframe(load_data("Expense"))

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

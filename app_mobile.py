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
st.set_page_config(page_title="Nave 304 - Smart Dashboard", layout="wide", page_icon="🍜")

# --- 2. การเชื่อมต่อ (คงเดิม) ---
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

# --- 5. UI Layout ---
st.sidebar.title("🚀 Nave 304 Master")
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

if page == "📊 Dashboard":
    st.header("📊 บทวิเคราะห์ผลประกอบการ")
    
    # โหลดข้อมูล
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    # จัดการข้อมูลเบื้องต้น
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    # --- ส่วนที่ 1: Metric สรุปยอด ---
    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรวมทั้งหมด", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อกสะสม", f"฿{t_exp:,.0f}")
    c3.metric("📈 กำไร (Income - Expense)", f"฿{t_inc - t_exp:,.0f}")
    
    st.divider()

    # --- ส่วนที่ 2: กราฟรายรับ (Smart Zoom) ---
    st.subheader("📅 กราฟรายรับแยกตามช่องทาง")
    
    # ปุ่มเลือกช่วงเวลา
    days_to_show = st.radio("เลือกช่วงเวลาดูย้อนหลัง:", 
                            [7, 30, 60, 90], 
                            format_func=lambda x: f"ย้อนหลัง {x} วัน",
                            horizontal=True)

    # กรองข้อมูลตามช่วงเวลาที่เลือก
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days_to_show)
    df_filtered = df_i[df_i['date'] >= cutoff_date].copy()

    if not df_filtered.empty:
        # เตรียมข้อมูลแนวโน้ม
        daily_total = df_filtered.groupby('date')['net_income'].sum().reset_index()
        daily_total['rolling_avg'] = daily_total['net_income'].rolling(window=min(7, len(daily_total))).mean()

        fig = go.Figure()

        # เพิ่มแท่งซ้อน (Stacked Bar)
        for app in df_filtered['app'].unique():
            d_app = df_filtered[df_filtered['app'] == app]
            fig.add_trace(go.Bar(
                x=d_app['date'], y=d_app['net_income'], name=app,
                textposition='auto',
                hovertemplate="%{x|%d %b}: ฿%{y:,.0f}"
            ))

        # เพิ่มเส้นแนวโน้ม
        fig.add_trace(go.Scatter(
            x=daily_total['date'], y=daily_total['rolling_avg'],
            name='แนวโน้มเฉลี่ย', line=dict(color='orange', width=3, dash='dot')
        ))

        fig.update_layout(
            barmode='stack',
            xaxis_title="วันที่",
            yaxis_title="รายได้ (บาท)",
            legend_orientation="h",
            hovermode="x unified",
            margin=dict(l=0, r=0, t=30, b=0),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"ไม่มีข้อมูลในช่วง {days_to_show} วันที่ผ่านมา")

    # --- ส่วนที่ 3: สรุปอื่นๆ ---
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📱 สัดส่วนรายได้")
        fig_pie = px.pie(df_i, values='net_income', names='app', hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_r:
        if not df_e.empty:
            st.subheader("📈 แนวโน้มราคาวัตถุดิบ")
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['u_price'] = clean_numeric(df_item, 'total_price') / clean_numeric(df_item, 'qty').replace(0, 1)
            # แสดงย้อนหลัง 30 วันเสมอสำหรับราคาสินค้าเพื่อให้เห็นเทรนด์
            st.plotly_chart(px.line(df_item.tail(30), x='date', y='u_price', markers=True), use_container_width=True)

# --- ส่วนอื่นๆ ของระบบ (คงเดิม) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    # ... โค้ดบันทึกรายรับเดิมของคุณ ...
    st.info("ใช้ระบบบันทึกแบบเดิมที่คุณถนัดได้เลยครับ")

elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่าย")
    # ... โค้ดบันทึกรายจ่ายเดิมของคุณ ...

elif page == "🤖 AI Agent":
    st.header("🤖 AI Agent")
    # ... โค้ด AI Agent เดิมของคุณ ...

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ฐานข้อมูลดิบ")
    t1, t2 = st.tabs(["📥 Income", "📤 Expense"])
    with t1: st.dataframe(load_data("Income"))
    with t2: st.dataframe(load_data("Expense"))

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    st.cache_data.clear()
    st.rerun()

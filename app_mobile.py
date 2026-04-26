import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from PIL import Image
import json
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="AI Stock Master", layout="wide")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
# หมายเหตุ: สำหรับ Google Sheets คุณต้องตั้งค่า Secrets ใน Streamlit Cloud หรือไฟล์ .streamlit/secrets.toml
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ ยังไม่ได้เชื่อมต่อ Google Sheets (ตรวจสอบ secrets.toml)")

# แก้ไขเพื่อให้ไปดึงรหัสจากไฟล์ลับแทน
client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- 3. ฟังก์ชันการทำงาน ---
def process_with_ai(img):
    prompt = """
    Extract items into JSON array: 
    - name (ชื่อสินค้า), 
    - qty (จำนวนเลข), 
    - unit (หน่วย เช่น แผง, ถุง, ขวด), 
    - total_price (ราคารวมรายการนั้น)
    Return ONLY pure JSON.
    """
    response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

# --- 4. เมนูหลัก (Sidebar) ---
st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("ไปที่หน้า:", ["📸 สแกนบิลใหม่", "📊 Dashboard & ประวัติราคา", "📋 ตารางสต๊อกทั้งหมด"])

# --- หน้าที่ 1: สแกนบิลใหม่ ---
if page == "📸 สแกนบิลใหม่":
    st.header("📸 สแกนบิลเข้าสต๊อก")
    
    # แก้ปัญหาปุ่มหาย: แสดงตัวเลือกให้ชัดเจน
    input_type = st.radio("เลือกวิธีนำเข้ารูป:", ["📷 ถ่ายรูปสด", "📁 เลือกจากไฟล์ในเครื่อง"], horizontal=True)
    
    if input_type == "📷 ถ่ายรูปสด":
        img_file = st.camera_input("ส่องกล้องไปที่บิล")
    else:
        img_file = st.file_uploader("เลือกรูปภาพบิล", type=['jpg', 'png', 'jpeg'])

    if img_file:
        img = Image.open(img_file)
        st.image(img, caption="รูปภาพที่เลือก", use_container_width=True)
        
        if st.button("🪄 เริ่มสแกนด้วย AI"):
            with st.spinner('กำลังประมวลผล...'):
                try:
                    raw_data = process_with_ai(img)
                    st.session_state.bill_data = pd.DataFrame(raw_data)
                    st.success("สแกนสำเร็จ! โปรดตรวจสอบข้อมูลด้านล่าง")
                except Exception as e:
                    st.error(f"AI อ่านไม่ออก: {e}")

    # ตารางแก้ไขข้อมูล
    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไขข้อมูล")
        edited_df = st.data_editor(st.session_state.bill_data, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 บันทึกลง Google Sheets"):
            try:
                # เพิ่มวันที่บันทึก
                edited_df['date'] = datetime.now().strftime("%Y-%m-%d")
                # รวมราคาต่อหน่วย (สำหรับประวัติราคา)
                edited_df['unit_price'] = edited_df['total_price'] / edited_df['qty']
                
                # อ่านข้อมูลเดิมและ Append ใหม่
                existing_df = conn.read(ttl=0)
                final_df = pd.concat([existing_df, edited_df], ignore_index=True)
                conn.update(data=final_df)
                
                st.success("บันทึกเรียบร้อย! ข้อมูลถูกส่งไปที่ Google Sheets แล้ว")
                del st.session_state.bill_data
            except Exception as e:
                st.error(f"บันทึกไม่ได้: {e}")

# --- หน้าที่ 2: Dashboard ---
elif page == "📊 Dashboard & ประวัติราคา":
    st.header("📊 วิเคราะห์ข้อมูล")
    try:
        df = conn.read()
        if not df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 สัดส่วนรายจ่าย")
                fig_pie = px.pie(df, values='total_price', names='name', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("📈 แนวโน้มราคา")
                item_list = df['name'].unique()
                selected_item = st.selectbox("เลือกสินค้า:", item_list)
                item_df = df[df['name'] == selected_item].sort_values('date')
                fig_line = px.line(item_df, x='date', y='unit_price', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลในฐานข้อมูล")
    except:
        st.warning("ไม่สามารถโหลดข้อมูลได้ ตรวจสอบการเชื่อมต่อ Google Sheets")

# --- หน้าที่ 3: ตารางสต๊อก ---
elif page == "📋 ตารางสต๊อกทั้งหมด":
    st.header("📋 รายการทั้งหมดใน Google Sheets")
    try:
        data = conn.read(ttl=1)
        st.dataframe(data, use_container_width=True)
    except:
        st.error("โหลดข้อมูลไม่ได้")

if st.sidebar.button("🔄 ดึงข้อมูลใหม่จาก Sheet"):
    st.cache_data.clear() # สั่งล้างความจำที่ค้างอยู่ทั้งหมด
    st.rerun()           # สั่งให้แอปเริ่มทำงานใหม่ทันที

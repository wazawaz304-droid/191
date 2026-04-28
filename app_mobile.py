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
st.set_page_config(page_title="AI Stock Master 2026", layout="wide", page_icon="📦")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⚠️ การเชื่อมต่อ Google Sheets ผิดพลาด: {e}")

client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- ฟังก์ชันช่วย: ดึงรายชื่อสินค้าเดิม (เพื่อระบบเดาคำ) ---
def get_unique_products():
    try:
        df = conn.read(ttl="1m")
        if not df.empty and 'name' in df.columns:
            return sorted([str(x) for x in df['name'].unique() if x])
        return []
    except:
        return []

# --- ฟังก์ชันช่วย: แกะ JSON อย่างปลอดภัย ---
def safe_parse_json(text_response):
    try:
        # ลอกเปลือก Markdown Block ออก
        if "```" in text_response:
            content = text_response.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        else:
            content = text_response
        return json.loads(content.strip())
    except Exception as e:
        st.error(f"❌ AI ส่งข้อมูลผิดรูปแบบ: {e}")
        return []

# --- 3. ฟังก์ชันการทำงาน (AI Engine) ---

def process_with_ai(img):
    existing_items = get_unique_products()
    items_str = ", ".join(existing_items)
    
    # ใช้ {{ }} เพื่อป้องกัน Invalid format specifier error
    prompt = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากรูปภาพบิลเป็น JSON array:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎ:
    1. ตรวจกับลิสต์สินค้าเดิม: [{items_str}]
    2. หากคล้ายกันให้ใช้ชื่อจากลิสต์เดิมเป๊ะๆ
    3. ตอบเป็น PURE JSON เท่านั้น
    """
    # ระบุ 'models/' นำหน้าเพื่อป้องกัน ClientError
    response = client.models.generate_content(model="models/gemini-2.5-flash", contents=[prompt, img])
    return safe_parse_json(response.text)

def process_audio_with_ai(audio_bytes, mime_type="audio/wav"):
    existing_items = get_unique_products()
    items_str = ", ".join(existing_items)

    prompt_text = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากเสียงพูดเป็น JSON array:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎ: Match ชื่อสินค้าให้ตรงกับรายการที่มีอยู่: [{items_str}]
    ตอบเป็น PURE JSON เท่านั้น ห้ามมีคำอธิบาย
    """
    try:
        user_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            ]
        )
        response = client.models.generate_content(model="models/gemini-2.5-flash", contents=[user_content])
        return safe_parse_json(response.text)
    except Exception as e:
        st.error(f"AI ประมวลผลเสียงไม่ได้: {e}")
        return None

# --- 4. เมนูหลัก (Sidebar) ---
st.sidebar.title("🚀 AI Stock Menu")
page = st.sidebar.radio("เลือกหน้าที่ต้องการ:", 
    ["📸 สแกนบิลใหม่", "🎙️ บันทึกด้วยเสียง", "📊 Dashboard & ประวัติราคา", "📋 ตารางสต๊อกทั้งหมด"])

# ฟังก์ชันบันทึกข้อมูล (ใช้ร่วมกัน)
def save_data_to_sheets(df_to_save):
    try:
        df_to_save['date'] = datetime.now().strftime("%Y-%m-%d")
        df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']
        existing_df = conn.read(ttl=0)
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        st.success("💾 บันทึกลง Google Sheets เรียบร้อยแล้ว!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- หน้าที่ 1: สแกนบิลใหม่ ---
if page == "📸 สแกนบิลใหม่":
    st.header("📸 สแกนบิลเข้าสต๊อก")
    input_type = st.radio("วิธีนำเข้ารูปภาพ:", ["ยังไม่เลือก", "📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)

    img_file = None
    if input_type == "📷 ถ่ายรูปสด":
        img_file = st.camera_input("สแกนบิล")
    elif input_type == "📁 เลือกไฟล์":
        img_file = st.file_uploader("เลือกรูปภาพ", type=['jpg', 'png', 'jpeg'])
    
    if img_file:
        img = Image.open(img_file)
        if st.button("🪄 เริ่มสแกนด้วย AI"):
            with st.spinner('กำลังประมวลผล...'):
                data = process_with_ai(img)
                if data:
                    st.session_state.bill_data = pd.DataFrame(data)

    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข")
        product_suggestions = get_unique_products()
        edited_df = st.data_editor(
            st.session_state.bill_data, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "name": st.column_config.SelectboxColumn("ชื่อสินค้า", options=product_suggestions, required=True),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "total_price": st.column_config.NumberColumn("ราคารวม", format="%.2f ฿")
            }
        )
        if st.button("💾 ยืนยันบันทึกข้อมูลบิล"):
            if save_data_to_sheets(edited_df):
                del st.session_state.bill_data
                st.rerun()

# --- หน้าที่ 2: บันทึกด้วยเสียง ---
elif page == "🎙️ บันทึกด้วยเสียง":
    st.header("🎙️ บันทึกรายการด้วยเสียง")
    audio_value = st.audio_input("กดปุ่มเพื่อเริ่มพูด")
    
    if audio_value:
        if st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            with st.spinner('AI กำลังฟัง...'):
                res_data = process_audio_with_ai(audio_value.read(), mime_type=audio_value.type)
                if res_data:
                    st.session_state.voice_data = pd.DataFrame(res_data)

    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูลจากเสียง")
        product_suggestions = get_unique_products()
        edited_voice_df = st.data_editor(
            st.session_state.voice_data, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "name": st.column_config.SelectboxColumn("ชื่อสินค้า", options=product_suggestions, required=True)
            }
        )
        if st.button("💾 ยืนยันบันทึกจากเสียง"):
            if save_data_to_sheets(edited_voice_df):
                del st.session_state.voice_data
                st.rerun()

# --- หน้าที่ 3: Dashboard ---
elif page == "📊 Dashboard & ประวัติราคา":
    st.header("📊 วิเคราะห์ข้อมูล")
    df = conn.read(ttl=0)
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.pie(df, values='total_price', names='name', hole=0.4, title="💰 สัดส่วนรายจ่าย"), use_container_width=True)
        with col2:
            items = df['name'].unique()
            target = st.selectbox("เลือกสินค้า:", items)
            item_df = df[df['name'] == target].sort_values('date')
            st.plotly_chart(px.line(item_df, x='date', y='unit_price', markers=True, title=f"📈 ราคาต่อหน่วย: {target}"), use_container_width=True)
    else: st.info("ยังไม่มีข้อมูล")

# --- หน้าที่ 4: ตารางสต๊อก ---
elif page == "📋 ตารางสต๊อกทั้งหมด":
    st.header("📋 ข้อมูลทั้งหมด")
    st.dataframe(conn.read(ttl=0), use_container_width=True)

# --- Sidebar Extra ---
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🔍 ตรวจเช็กชื่อโมเดล"):
    try:
        for m in client.models.list(): st.code(m.name)
    except Exception as e: st.error(f"Error: {e}")

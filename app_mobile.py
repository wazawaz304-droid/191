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
st.set_page_config(page_title="AI Stock Master 2026", layout="wide")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ ยังไม่ได้เชื่อมต่อ Google Sheets (ตรวจสอบ secrets.toml)")

client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- 3. ฟังก์ชันการทำงาน (AI Engine) ---

def process_with_ai(img):
    prompt = "Extract items into JSON array: name, qty, unit, total_price. Return ONLY pure JSON."
    response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

def process_audio_with_ai(audio_bytes, mime_type="audio/wav"):
    prompt_text = "สกัดข้อมูลสินค้าจากเสียงพูดนี้เป็น JSON array: name, qty, unit, total_price ตอบเป็น PURE JSON เท่านั้น"
    try:
        user_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            ]
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[user_content]
        )
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"AI ฟังไม่ชัด: {e}")
        return None

# --- 4. เมนูหลัก (Sidebar) ---
st.sidebar.title("🚀 AI Stock Menu")
# *** เพิ่มเมนูเสียงเข้าไปตรงนี้แล้วครับ ***
page = st.sidebar.radio("เลือกหน้าที่ต้องการ:", 
    ["📸 สแกนบิลใหม่", "🎙️ บันทึกด้วยเสียง", "📊 Dashboard & ประวัติราคา", "📋 ตารางสต๊อกทั้งหมด"])

# --- ส่วนกลาง: ฟังก์ชันบันทึกข้อมูล (ใช้ร่วมกัน) ---
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
# --- หน้าที่ 1: สแกนบิลใหม่ (ปรับปรุงให้เลือกก่อนเปิดกล้อง) ---
if page == "📸 สแกนบิลใหม่":
    st.header("📸 สแกนบิลเข้าสต๊อก")
    
    # 1. สร้างตัวเลือกเริ่มต้นแบบ 'ยังไม่เลือก' เพื่อไม่ให้กล้องเปิดอัตโนมัติ
    input_type = st.radio(
        "คุณต้องการนำเข้ารูปภาพด้วยวิธีใด?", 
        ["ยังไม่เลือก", "📷 ถ่ายรูปสด (Camera)", "📁 เลือกไฟล์จากเครื่อง (Upload)"], 
        index=0, # ตั้งค่าให้เป็น 'ยังไม่เลือก' ไว้ก่อน
        horizontal=True
    )

    img_file = None # ตัวแปรเก็บไฟล์ภาพ

    # 2. แสดง Widget ตามที่เลือกเท่านั้น
    if input_type == "📷 ถ่ายรูปสด (Camera)":
        img_file = st.camera_input("ส่องกล้องไปที่บิลแล้วกดถ่ายรูป")
    
    elif input_type == "📁 เลือกไฟล์จากเครื่อง (Upload)":
        img_file = st.file_uploader("เลือกไฟล์รูปภาพบิล (JPG, PNG)", type=['jpg', 'png', 'jpeg'])
    
    else:
        st.info("💡 โปรดเลือกวิธีการนำเข้รูปภาพด้านบน เพื่อเริ่มต้นการสแกน")

    # 3. เมื่อมีรูปภาพเข้ามาแล้ว (ไม่ว่าจะจากกล้องหรือไฟล์)
    if img_file:
        img = Image.open(img_file)
        st.image(img, caption="รูปภาพที่เตรียมประมวลผล", use_container_width=True)
        
        if st.button("🪄 เริ่มสแกนด้วย AI"):
            with st.spinner('AI กำลังอ่านบิล...'):
                try:
                    # เรียกใช้ฟังก์ชัน AI ตัวเดิม
                    data = process_with_ai(img)
                    st.session_state.bill_data = pd.DataFrame(data)
                    st.success("✅ สแกนสำเร็จ!")
                except Exception as e:
                    st.error(f"❌ AI อ่านไม่ออก: {e}")

    # 4. ส่วนแสดงตารางแก้ไขข้อมูล (เหมือนเดิม)
    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไขข้อมูล")
        edited_df = st.data_editor(st.session_state.bill_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 ยืนยันบันทึกข้อมูลบิล"):
            if save_data_to_sheets(edited_df):
                del st.session_state.bill_data
                st.rerun() # รีเฟรชหน้าเพื่อให้ตารางหายไปหลังบันทึก

# --- หน้าที่ 2: บันทึกด้วยเสียง (แก้ไข Syntax และ Logic แล้ว) ---
elif page == "🎙️ บันทึกด้วยเสียง":
    st.header("🎙️ บันทึกรายการด้วยเสียง")
    audio_value = st.audio_input("กดเพื่อพูดรายการสินค้า")
    
    if audio_value:
        if st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            with st.spinner('AI กำลังตั้งใจฟัง...'):
                # *** แก้ไข Try-Except ตรงนี้แล้วครับ ***
                try:
                    res_data = process_audio_with_ai(audio_value.read(), mime_type=audio_value.type)
                    if res_data:
                        st.session_state.voice_data = pd.DataFrame(res_data)
                        st.success("แปลงข้อมูลสำเร็จ!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูลจากเสียงพูด")
        edited_voice_df = st.data_editor(st.session_state.voice_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 ยืนยันบันทึกจากเสียง"):
            if save_data_to_sheets(edited_voice_df):
                del st.session_state.voice_data

# --- หน้าที่ 3: Dashboard ---
elif page == "📊 Dashboard & ประวัติราคา":
    st.header("📊 วิเคราะห์ข้อมูล")
    df = conn.read(ttl=0)
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_pie = px.pie(df, values='total_price', names='name', hole=0.4, title="💰 สัดส่วนรายจ่าย")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            selected_item = st.selectbox("เลือกสินค้า:", df['name'].unique())
            item_df = df[df['name'] == selected_item].sort_values('date')
            fig_line = px.line(item_df, x='date', y='unit_price', markers=True, title=f"📈 ราคา: {selected_item}")
            st.plotly_chart(fig_line, use_container_width=True)
    else: st.info("ยังไม่มีข้อมูล")

# --- หน้าที่ 4: ตารางสต๊อก ---
elif page == "📋 ตารางสต๊อกทั้งหมด":
    st.header("📋 ข้อมูลทั้งหมด")
    st.dataframe(conn.read(ttl=0), use_container_width=True)

# --- ปุ่มพิเศษที่ Sidebar ---
if st.sidebar.button("🔄 ดึงข้อมูลใหม่จาก Sheet"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔍 ตรวจเช็กชื่อโมเดล"):
    try:
        for m in client.models.list(): st.code(m.name)
    except Exception as e: st.error(f"Error: {e}")

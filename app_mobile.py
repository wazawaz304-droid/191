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
st.set_page_config(page_title="AI Stock Master 2026", layout="wide", page_icon="🚀")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")

# ดึง API Key จาก Secrets (ต้องตั้งค่าใน Streamlit Cloud Secrets)
try:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
except:
    st.error("🔑 ไม่พบ API Key ในระบบ Secrets โปรดตรวจสอบการตั้งค่า")

# --- ฟังก์ชันช่วยดึงรายชื่อสินค้าเดิม (เพื่อทำระบบเดาคำและ AI Match) ---
def get_unique_products():
    try:
        # อ่านข้อมูลสดๆ (ตั้ง TTL 1 นาทีเพื่อให้ดึงข้อมูลใหม่บ่อยขึ้น)
        df = conn.read(ttl="1m")
        if not df.empty and 'name' in df.columns:
            return sorted([str(x) for x in df['name'].unique() if x])
        return []
    except:
        return []

# --- ฟังก์ชันช่วยแกะ JSON อย่างปลอดภัย (ป้องกัน Error เวลา AI แถมคำพูด) ---
def safe_parse_json(text_response):
    try:
        # ลอกเปลือก Markdown (```json ... ```) ออกถ้ามี
        if "```" in text_response:
            content = text_response.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        else:
            content = text_response
        return json.loads(content.strip())
    except Exception as e:
        st.error(f"❌ AI ส่งข้อมูลผิดรูปแบบ: {e}")
        st.info(f"ข้อมูลต้นฉบับจาก AI: {text_response}")
        return []

# --- 3. ฟังก์ชัน AI Engine (Match ชื่อสินค้าอัตโนมัติ) ---

def process_with_ai(img):
    existing_items = get_unique_products()
    items_list_str = ", ".join(existing_items)
    
    # ใช้ {{ }} เพื่อป้องกัน f-string error ใน Python (Invalid format specifier)
    prompt = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากรูปภาพบิลเป็น JSON array ในรูปแบบนี้เท่านั้น:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎการทำงาน:
    1. ตรวจสอบชื่อสินค้ากับลิสต์เดิมที่มีในระบบ: [{items_list_str}]
    2. หากชื่อคล้ายกันมาก (เช่น 'ไข่ไก่สด' แต่ในระบบมี 'ไข่ไก่') ให้เลือกใช้ชื่อในลิสต์เดิม ('ไข่ไก่')
    3. ตอบกลับเป็น PURE JSON เท่านั้น ห้ามมีคำอธิบายอื่น
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, img])
    return safe_parse_json(response.text)

def process_audio_with_ai(audio_bytes, mime_type="audio/wav"):
    existing_items = get_unique_products()
    items_list_str = ", ".join(existing_items)

    prompt_text = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากเสียงพูดเป็น JSON array ในรูปแบบนี้เท่านั้น:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎการทำงาน:
    1. ตรวจสอบชื่อสินค้ากับลิสต์เดิมที่มีในระบบ: [{items_list_str}]
    2. หากพูดคล้ายกันมาก ให้ Match ชื่อให้ตรงกับลิสต์เดิม (เช่น พูดว่า 'ไข่ไก่ครับ' -> ให้ใช้ 'ไข่ไก่')
    3. ตัดคำพูดที่ไม่จำเป็นออก ให้เหลือแค่ใจความหลัก
    ตอบเป็น PURE JSON เท่านั้น
    """
    
    try:
        user_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            ]
        )
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[user_content])
        return safe_parse_json(response.text)
    except Exception as e:
        st.error(f"❌ AI ประมวลผลเสียงไม่ได้: {e}")
        return []

# --- ฟังก์ชันบันทึกข้อมูลลง Sheet ---
def save_data_to_sheets(df_to_save):
    try:
        df_to_save['date'] = datetime.now().strftime("%Y-%m-%d")
        df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']
        
        # อ่านข้อมูลเดิมมาต่อท้าย
        existing_df = conn.read(ttl=0)
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        st.success("✅ บันทึกข้อมูลลง Google Sheets เรียบร้อย!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 4. การแสดงผล UI (Streamlit) ---
st.sidebar.title("🚀 AI Stock Master")
page = st.sidebar.radio("เลือกเมนู:", ["📸 สแกนบิลสินค้า", "🎙️ บันทึกด้วยเสียง", "📊 Dashboard", "📋 ดูข้อมูลทั้งหมด"])

# เตรียมข้อมูลสินค้าสำหรับระบบเดาคำ (Dropdown)
product_suggestions = get_unique_products()

# --- หน้าสแกนบิล ---
if page == "📸 สแกนบิลสินค้า":
    st.header("📸 สแกนบิลสินค้า")
    choice = st.radio("เลือกวิธีนำเข้า:", ["ยังไม่เลือก", "📷 ถ่ายรูปสด", "📁 อัปโหลดรูปภาพ"], horizontal=True)
    
    img_file = None
    if choice == "📷 ถ่ายรูปสด":
        img_file = st.camera_input("สแกนบิล")
    elif choice == "📁 อัปโหลดรูปภาพ":
        img_file = st.file_uploader("เลือกไฟล์รูปภาพ", type=['jpg', 'jpeg', 'png'])
    else:
        st.info("💡 โปรดเลือกวิธีนำเข้ารูปภาพด้านบนเพื่อเริ่มต้น")

    if img_file:
        img = Image.open(img_file)
        if st.button("🪄 เริ่มสแกนด้วย AI"):
            with st.spinner("AI กำลังอ่านข้อมูล..."):
                data = process_with_ai(img)
                if data:
                    st.session_state.bill_data = pd.DataFrame(data)

    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข")
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
        if st.button("💾 ยืนยันบันทึกลงสต๊อก"):
            if save_data_to_sheets(edited_df):
                del st.session_state.bill_data
                st.rerun()

# --- หน้าบันทึกด้วยเสียง ---
elif page == "🎙️ บันทึกด้วยเสียง":
    st.header("🎙️ บันทึกรายการด้วยเสียง")
    audio_val = st.audio_input("กดเพื่อพูด (เช่น: ไข่ไก่ 2 แผง ราคา 200 บาท)")
    
    if audio_val:
        if st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            with st.spinner("AI กำลังวิเคราะห์เสียง..."):
                res = process_audio_with_ai(audio_val.read(), mime_type=audio_val.type)
                if res:
                    st.session_state.voice_data = pd.DataFrame(res)

    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูลจากเสียงพูด")
        edited_voice = st.data_editor(
            st.session_state.voice_data, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "name": st.column_config.SelectboxColumn("ชื่อสินค้า", options=product_suggestions, required=True),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "total_price": st.column_config.NumberColumn("ราคารวม", format="%.2f ฿")
            }
        )
        if st.button("💾 ยืนยันบันทึกรายการเสียง"):
            if save_data_to_sheets(edited_voice):
                del st.session_state.voice_data
                st.rerun()

# --- หน้า Dashboard ---
elif page == "📊 Dashboard":
    st.header("📊 วิเคราะห์ข้อมูล")
    df_db = conn.read(ttl=0)
    if not df_db.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(df_db, values='total_price', names='name', hole=0.4, title="💰 สัดส่วนรายจ่าย"), use_container_width=True)
        with c2:
            items = df_db['name'].unique()
            target = st.selectbox("เลือกสินค้าเพื่อดูประวัติราคา:", items)
            item_df = df_db[df_db['name'] == target].sort_values('date')
            st.plotly_chart(px.line(item_df, x='date', y='unit_price', markers=True, title=f"📈 ราคาต่อหน่วย: {target}"), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")

# --- หน้าดูข้อมูลทั้งหมด ---
elif page == "📋 ดูข้อมูลทั้งหมด":
    st.header("📋 รายการทั้งหมดใน Google Sheets")
    st.dataframe(conn.read(ttl=0), use_container_width=True)

# Sidebar buttons
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล (Refresh)"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🔍 ตรวจสอบโมเดลที่ใช้ได้"):
    try:
        for m in client.models.list(): st.code(m.name)
    except Exception as e: st.error(f"Error: {e}")

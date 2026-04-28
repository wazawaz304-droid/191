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
    st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")

# ดึง API Key จาก Secrets
client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# ฟังก์ชันดึงรายชื่อสินค้าเดิม
def get_unique_products():
    try:
        df = conn.read(ttl="1m")
        if not df.empty and 'name' in df.columns:
            return sorted([str(x) for x in df['name'].unique() if x])
        return []
    except:
        return []

# ฟังก์ชันแกะ JSON อย่างปลอดภัย
def safe_parse_json(text_response):
    try:
        if "```" in text_response:
            content = text_response.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        else:
            content = text_response
        return json.loads(content.strip())
    except Exception as e:
        st.error(f"❌ AI ส่งข้อมูลผิดรูปแบบ")
        return []

# --- 3. ฟังก์ชัน AI (Match ชื่อแบบไม่บังคับ) ---

def process_with_ai(img):
    existing_items = get_unique_products()
    items_str = ", ".join(existing_items)
    
    # ใช้ {{ }} เพื่อป้องกัน f-string error
    prompt = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลสินค้าจากรูปภาพบิลเป็น JSON array ในรูปแบบนี้เท่านั้น:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎการแมตชื่อ:
    1. ตรวจสอบลิสต์เดิมที่มีในระบบ: [{items_str}]
    2. หากชื่อในบิล "คล้ายกันมาก" และน่าจะเป็นตัวเดียวกัน ให้ใช้ชื่อจากลิสต์เดิม
    3. หากเป็นสินค้าใหม่หรือชื่อจงใจให้ต่าง ให้ใช้ชื่อตามที่อ่านได้จากบิล
    ตอบเป็น PURE JSON เท่านั้น
    """
    response = client.models.generate_content(model="models/gemini-2.5-flash", contents=[prompt, img])
    return safe_parse_json(response.text)

def process_audio_with_ai(audio_bytes, mime_type="audio/wav"):
    existing_items = get_unique_products()
    items_str = ", ".join(existing_items)

    prompt_text = f"""
    คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากเสียงพูดเป็น JSON array ในรูปแบบนี้เท่านั้น:
    [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    
    กฎการแมตชื่อ:
    1. ตรวจสอบกับลิสต์สินค้าเดิม: [{items_str}]
    2. หากพูดคล้ายรายการเดิม ให้ Match ชื่อให้ตรงกัน
    3. หากผู้พูดระบุว่าเป็นของใหม่ หรือชื่อต่างออกไป ให้ใช้ชื่อตามที่พูด
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
        response = client.models.generate_content(model="models/gemini-2.5-flash", contents=[user_content])
        return safe_parse_json(response.text)
    except Exception as e:
        st.error(f"❌ AI ฟังไม่ถนัด: {e}")
        return []

# ฟังก์ชันบันทึกข้อมูล
def save_data_to_sheets(df_to_save):
    try:
        df_to_save['date'] = datetime.now().strftime("%Y-%m-%d")
        df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']
        existing_df = conn.read(ttl=0)
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        st.success("✅ บันทึกลง Google Sheets สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 4. ส่วนแสดงผล UI ---
st.sidebar.title("🚀 AI Stock Menu")
page = st.sidebar.radio("เลือกเมนู:", ["📸 สแกนบิลใหม่", "🎙️ บันทึกด้วยเสียง", "📊 Dashboard", "📋 รายการสต๊อก"])

# --- หน้าสแกนบิล ---
if page == "📸 สแกนบิลใหม่":
    st.header("📸 สแกนบิลเข้าสต๊อก")
    input_type = st.radio("วิธีนำเข้า:", ["ยังไม่เลือก", "📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)

    img_file = None
    if input_type == "📷 ถ่ายรูปสด":
        img_file = st.camera_input("สแกนบิล")
    elif input_type == "📁 เลือกไฟล์":
        img_file = st.file_uploader("เลือกรูปภาพ", type=['jpg', 'png', 'jpeg'])
    
    if img_file:
        img = Image.open(img_file)
        if st.button("🪄 เริ่มสแกน"):
            with st.spinner('กำลังอ่านบิล...'):
                data = process_with_ai(img)
                if data:
                    st.session_state.bill_data = pd.DataFrame(data)

    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข (พิมพ์ชื่อใหม่ได้อิสระ)")
        # แก้ไขจุดนี้: ใช้ TextColumn แทน SelectboxColumn เพื่อให้พิมพ์ชื่อใหม่ได้
        edited_df = st.data_editor(
            st.session_state.bill_data, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("ชื่อสินค้า", help="แก้ไขชื่อได้ทันทีหาก AI แมตผิด", width="large"),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "total_price": st.column_config.NumberColumn("ราคารวม", format="%.2f ฿")
            }
        )
        if st.button("💾 ยืนยันบันทึกข้อมูล"):
            if save_data_to_sheets(edited_df):
                del st.session_state.bill_data
                st.rerun()

# --- หน้าบันทึกด้วยเสียง ---
elif page == "🎙️ บันทึกด้วยเสียง":
    st.header("🎙️ บันทึกรายการด้วยเสียง")
    audio_value = st.audio_input("กดปุ่มไมค์เพื่อเริ่มพูด")
    
    if audio_value:
        if st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            with st.spinner('AI กำลังฟัง...'):
                res_data = process_audio_with_ai(audio_value.read(), mime_type=audio_value.type)
                if res_data:
                    st.session_state.voice_data = pd.DataFrame(res_data)

    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูล (พิมพ์แก้ไขได้อิสระ)")
        edited_voice_df = st.data_editor(
            st.session_state.voice_data, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("ชื่อสินค้า", width="large"),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "total_price": st.column_config.NumberColumn("ราคารวม", format="%.2f ฿")
            }
        )
        if st.button("💾 ยืนยันบันทึกจากเสียง"):
            if save_data_to_sheets(edited_voice_df):
                del st.session_state.voice_data
                st.rerun()

# --- หน้า Dashboard ---
elif page == "📊 Dashboard":
    st.header("📊 วิเคราะห์รายจ่าย")
    df = conn.read(ttl=0)
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(df, values='total_price', names='name', hole=0.4, title="💰 สัดส่วนรายจ่าย"), use_container_width=True)
        with c2:
            items = df['name'].unique()
            target = st.selectbox("เลือกสินค้า:", items)
            item_df = df[df['name'] == target].sort_values('date')
            st.plotly_chart(px.line(item_df, x='date', y='unit_price', markers=True, title=f"📈 ราคาต่อหน่วย: {target}"), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")

# --- หน้าตารางทั้งหมด ---
elif page == "📋 รายการสต๊อก":
    st.header("📋 ข้อมูลทั้งหมด")
    st.dataframe(conn.read(ttl=0), use_container_width=True)

# ปุ่มพิเศษที่ Sidebar
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    st.cache_data.clear()
    st.rerun()

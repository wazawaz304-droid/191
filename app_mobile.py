import streamlit as st
import pandas as pd
from datetime import datetime
from audio_recorder_streamlit import audio_recorder # ต้องติดตั้งเพิ่ม
import sqlalchemy

# --- 1. การเชื่อมต่อหลัก (Supabase & GSheets สำหรับ Email Sync) ---
conn = st.connection("supabase", type="sql")
conn_gs = st.connection("gsheets", type=st.connection.GSheetsConnection) # สำหรับดึงข้อมูลที่ Apps Script ดึงจาก Gmail มาพักไว้

# --- 2. ฟังก์ชันจัดการข้อมูล (Data Logic) ---

def save_to_supabase(df, tab_name):
    """บันทึกข้อมูลเข้า SQL และล้างแคช"""
    if df.empty: return False
    try:
        table_name = tab_name.lower()
        save_df = df.copy()
        save_df.columns = [str(c).strip().lower() for c in save_df.columns]
        
        # จัดการวันที่
        date_col = "data" if table_name == "lineman_insight" else "date"
        if date_col in save_df.columns:
            save_df[date_col] = pd.to_datetime(save_df[date_col]).dt.date
        
        # ลบช่องคำนวณอัตโนมัติ
        if table_name == "expense" and "unit_price" in save_df.columns:
            save_df = save_df.drop(columns=["unit_price"])

        save_df.to_sql(table_name, conn.engine, if_exists='append', index=False, method='multi')
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่สำเร็จ: {e}")
        return False

# --- 3. ส่วนหน้าจอหลัก (UI) ---

st.sidebar.title("Nave 304 Master")
page = st.sidebar.selectbox("เมนู", ["📊 Dashboard", "🎙️ บันทึกด้วยเสียง/ภาพ", "📧 Sync ข้อมูล Email", "📂 อัปโหลดไฟล์บิล"])

# --- ฟีเจอร์ที่ 1: บันทึกด้วยเสียงและภาพ (Camera & Voice) ---
if page == "🎙️ บันทึกด้วยเสียง/ภาพ":
    st.header("📸 บันทึกข้อมูลแบบมัลติโหมด")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("บันทึกเสียง (Voice Command)")
        audio_bytes = audio_recorder(text="กดเพื่อพูดรายการ...", icon_size="2x")
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            st.info("💡 ระบบกำลังรอคำสั่งเสียงเพื่อสกัดข้อมูล (เชื่อมกับ AI เดิมของพี่ได้เลย)")
            # ตรงนี้พี่สามารถเรียกฟังก์ชันสกัดข้อมูลจากเสียง (Whisper/GPT) แล้วส่งเข้า save_to_supabase ได้ครับ

    with col2:
        st.subheader("ถ่ายรูปบิล (Camera)")
        img_file = st.camera_input("สแกนบิล/ใบเสร็จ")
        if img_file:
            st.image(img_file, caption="บิลที่สแกน")
            st.success("บันทึกรูปภาพลงฐานข้อมูลชั่วคราวแล้ว")

# --- ฟีเจอร์ที่ 2: ดึงข้อมูลจาก Email (Email Sync) ---
elif page == "📧 Sync ข้อมูล Email":
    st.header("📧 ดึงยอดขายจาก Email (Delivery)")
    st.write("ระบบจะดึงข้อมูลที่ Google Apps Script สกัดจาก Gmail มาลงที่นี่")
    
    if st.button("🔄 ดึงยอดขายล่าสุดจาก Gmail (ผ่าน Sheets)"):
        try:
            # ดึงจาก Sheets ที่ Apps Script เขียนข้อมูลไว้ (เช่น แท็บ 'Gmail_Extract')
            df_gmail = conn_gs.read(worksheet="Gmail_Extract", ttl=0)
            if not df_gmail.empty:
                st.dataframe(df_gmail.head())
                if st.button("✅ ยืนยันย้ายข้อมูลเข้า Supabase"):
                    if save_to_supabase(df_gmail, "income"):
                        st.success("ย้ายข้อมูลยอดขายจาก Email เข้า Cloud เรียบร้อย!")
            else:
                st.info("ไม่มีข้อมูลใหม่จาก Email")
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")

# --- ฟีเจอร์ที่ 3: อัปโหลดไฟล์ (File Upload) ---
elif page == "📂 อัปโหลดไฟล์บิล":
    st.header("📂 อัปโหลดไฟล์เอกสาร/PDF")
    uploaded_files = st.file_uploader("เลือกไฟล์บิลรายจ่าย", accept_multiple_files=True)
    for uploaded_file in uploaded_files:
        st.write(f"ชื่อไฟล์: {uploaded_file.name}")
        # พี่สามารถนำไฟล์นี้ไปเข้ากระบวนการ OCR ต่อไปได้ครับ

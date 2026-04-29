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
st.set_page_config(page_title="AI Stock & Income 2026", layout="wide", page_icon="💰")

# --- 2. การเชื่อมต่อ ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ เชื่อมต่อ Google Sheets ไม่ได้")

client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- 3. AI Engine (ระบบ Fallback สลับโมเดลอัตโนมัติ) ---

def call_gemini_with_fallback(prompt, contents=None, is_audio=False):
    """ฟังก์ชันอัจฉริยะ: ถ้าตัวหลักโควตาเต็ม จะสลับไปใช้ตัวสำรองทันที"""
    # เรียงลำดับโมเดล: 3.1 Lite (เร็ว/โควตาเยอะ) -> 2.0 Lite -> 2.0 Flash
    model_list = [
        "models/gemini-3.1-flash-lite-preview", 
        "models/gemini-2.0-flash-lite", 
        "models/gemini-2.0-flash"
    ]
    
    for model_name in model_list:
        try:
            if is_audio:
                # สำหรับเสียง ส่ง contents ที่ห่อ types.Content มาแล้ว
                response = client.models.generate_content(model=model_name, contents=contents)
            else:
                # สำหรับข้อความและรูปภาพ
                input_parts = [prompt] + contents if contents else [prompt]
                response = client.models.generate_content(model=model_name, contents=input_parts)
            return response.text
        except Exception as e:
            if "429" in str(e): # ถ้า Quota เต็ม ให้ลอง Model ถัดไป
                continue
            else:
                st.warning(f"⚠️ {model_name} พบปัญหา: {e}")
                continue
    return None

def safe_parse_json(text):
    if not text: return []
    try:
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text.strip())
    except:
        return []

# --- ฟังก์ชันหลักสำหรับเรียกใช้ AI ---

def process_stock_ai(img_or_audio, is_audio=False, mime_type=None):
    # ดึงรายชื่อสินค้าเดิมมาช่วย AI Match ชื่อ
    try:
        existing_items = ", ".join(conn.read().name.unique().tolist())
    except:
        existing_items = ""

    prompt = f"""
    สกัดข้อมูลสินค้าเป็น JSON array: [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    เทียบชื่อเดิม: [{existing_items}]
    ตอบแค่ PURE JSON เท่านั้น
    """
    
    if is_audio:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=img_or_audio, mime_type=mime_type)
        ])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_audio=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[img_or_audio])
    
    return safe_parse_json(res_text)

def process_delivery_ai(email_text):
    prompt = """
    สกัดยอดรายรับเดลิเวอรี่เป็น JSON:
    [{{ "app": "Grab/LINE MAN/ShopeeFood", "net_income": ยอดสุทธิ, "gross_sales": ยอดรวม, "gp_amount": ค่า GP }}]
    ตอบแค่ PURE JSON เท่านั้น
    """
    res_text = call_gemini_with_fallback(prompt, contents=[email_text])
    return safe_parse_json(res_text)

# --- 4. การจัดการข้อมูล (Save Data) ---

def save_to_sheets(df, data_type="Expense"):
    try:
        df['type'] = data_type
        df['date'] = datetime.now().strftime("%Y-%m-%d")
        if data_type == "Expense":
            df['unit_price'] = df['total_price'] / df['qty'].replace(0, 1)
        else:
            df['name'] = df['app'] + " Income"
            df['total_price'] = df['net_income']
            df['qty'] = 1
        
        # โหลดข้อมูลเก่ามาต่อท้าย
        final_df = pd.concat([conn.read(ttl=0), df], ignore_index=True)
        conn.update(data=final_df)
        st.success(f"✅ บันทึก {data_type} สำเร็จ!")
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. หน้าจอ UI ---

st.sidebar.title("🚀 AI Business Master")
page = st.sidebar.radio("เมนูหลัก:", ["📸 สแกนบิล", "🎙️ บันทึกเสียง", "💰 รายรับเดลิเวอรี่", "📊 Dashboard"])

if page == "📸 สแกนบิล":
    st.header("📸 สแกนบิลวัตถุดิบ")
    img_file = st.camera_input("สแกน") or st.file_uploader("เลือกรูป", type=['jpg','png'])
    if img_file and st.button("🪄 วิเคราะห์บิล"):
        with st.spinner("AI กำลังอ่าน..."):
            res = process_stock_ai(Image.open(img_file))
            if res: st.session_state.stock_data = pd.DataFrame(res)
            
    if 'stock_data' in st.session_state:
        edited = st.data_editor(st.session_state.stock_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกค่าวัตถุดิบ"):
            if save_to_sheets(edited, "Expense"):
                del st.session_state.stock_data
                st.rerun()

elif page == "🎙️ บันทึกเสียง":
    st.header("🎙️ บันทึกด้วยเสียง")
    audio = st.audio_input("พูดรายการสินค้า...")
    if audio and st.button("🚀 แปลงเป็นข้อมูล"):
        with st.spinner("AI กำลังฟัง..."):
            res = process_stock_ai(audio.read(), is_audio=True, mime_type=audio.type)
            if res: st.session_state.voice_data = pd.DataFrame(res)
            
    if 'voice_data' in st.session_state:
        edited = st.data_editor(st.session_state.voice_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 บันทึกลงสต๊อก"):
            if save_to_sheets(edited, "Expense"):
                del st.session_state.voice_data
                st.rerun()

elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 รายรับจากเดลิเวอรี่")
    txt = st.text_area("วางข้อความจากอีเมล Grab/LINE MAN/ShopeeFood ที่นี่:")
    if st.button("🪄 สรุปยอดเงิน"):
        with st.spinner("กำลังคำนวณ..."):
            res = process_delivery_ai(txt)
            if res: st.session_state.inc_data = pd.DataFrame(res)
            
    if 'inc_data' in st.session_state:
        edited = st.data_editor(st.session_state.inc_data, use_container_width=True)
        if st.button("💾 บันทึกรายรับ"):
            if save_to_sheets(edited, "Income"):
                del st.session_state.inc_data
                st.rerun()

elif page == "📊 Dashboard":
    st.header("📊 สรุปผลกำไร-ขาดทุน")
    df = conn.read(ttl=0)
    if not df.empty:
        # แยกยอดรายรับและรายจ่าย
        inc = df[df['type'] == 'Income']['total_price'].sum() if 'type' in df.columns else 0
        exp = df[df['type'] != 'Income']['total_price'].sum() if 'type' in df.columns else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับทั้งหมด", f"฿{inc:,.2f}")
        c2.metric("รายจ่ายวัตถุดิบ", f"฿{exp:,.2f}")
        c3.metric("กำไรเบื้องต้น", f"฿{inc - exp:,.2f}", delta_color="normal")
        
        st.divider()
        if not df[df['type'] != 'Income'].empty:
            st.plotly_chart(px.pie(df[df['type'] != 'Income'], values='total_price', names='name', title="สัดส่วนรายจ่ายวัตถุดิบ"), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")

if st.sidebar.button("🔄 รีเฟรชข้อมูล"):
    st.cache_data.clear()
    st.rerun()

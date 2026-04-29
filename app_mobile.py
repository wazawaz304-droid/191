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
st.set_page_config(page_title="AI Business Master 2026", layout="wide", page_icon="💰")

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
    st.error(f"⚠️ ไม่พบ API Key: {e}")

# --- 2.1 ระบบ Cache และ Fallback Model ---

@st.cache_data(ttl=60)
def load_data():
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_data_cache():
    load_data.clear()

def call_gemini_with_fallback(prompt, contents=None, is_audio=False):
    """ระบบสลับโมเดลอัตโนมัติ: เน้น 3.1 Lite เป็นตัวหลัก เพื่อแก้ปัญหา Quota เต็ม"""
    model_list = [
        "models/gemini-3.1-flash-lite-preview", 
        "models/gemini-2.0-flash-lite",          
        "models/gemini-2.0-flash"               
    ]
    
    for model_name in model_list:
        try:
            if is_audio:
                response = client.models.generate_content(model=model_name, contents=contents)
            else:
                input_parts = [prompt] + contents if contents else [prompt]
                response = client.models.generate_content(model=model_name, contents=input_parts)
            return response.text
        except Exception as e:
            if "429" in str(e): # ถ้าโควตาเต็ม ข้ามไปตัวถัดไปเงียบๆ
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

# --- 3. ฟังก์ชัน AI Engine ---

def process_stock_ai(data_input, is_audio=False, mime_type=None):
    """วิเคราะห์บิล/เสียง (Expense)"""
    df_temp = load_data()
    existing_items = ", ".join(df_temp[df_temp['type'] != 'Income']['name'].unique().tolist()) if not df_temp.empty and 'name' in df_temp.columns else ""
    
    prompt = f"""
    สกัดข้อมูลสินค้าเป็น JSON array: [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    เทียบชื่อเดิม: [{existing_items}] (หากคล้ายให้ใช้ชื่อเดิม)
    ตอบแค่ PURE JSON เท่านั้น
    """
    if is_audio:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data_input, mime_type=mime_type)
        ])]
        res_text = call_gemini_with_fallback(prompt, contents=contents, is_audio=True)
    else:
        res_text = call_gemini_with_fallback(prompt, contents=[data_input])
    return safe_parse_json(res_text)

def process_delivery_income_ai(email_text):
    """วิเคราะห์รายได้จากอีเมลแอป (Income)"""
    prompt = """
    สกัดข้อมูลรายได้เดลิเวอรี่เป็น JSON array:
    [{{ "app": "Grab/LINE MAN/ShopeeFood", "gross_sales": ยอดรวม, "gp_amount": ค่า GP, "net_income": ยอดโอนสุทธิ }}]
    ตอบแค่ PURE JSON
    """
    res_text = call_gemini_with_fallback(prompt, contents=[email_text])
    return safe_parse_json(res_text)

# --- 4. บันทึกข้อมูล ---

def save_to_sheets(df, data_type="Expense"):
    if conn is None: return False
    try:
        df['type'] = data_type
        df['date'] = datetime.now().strftime("%Y-%m-%d")
        
        # จัดการข้อมูลตัวเลข
        if data_type == "Expense":
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(1)
            df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
            df['unit_price'] = df['total_price'] / df['qty'].replace(0, 1)
        else:
            df['name'] = df['app'] + " Income"
            df['total_price'] = pd.to_numeric(df['net_income'], errors='coerce').fillna(0)
            df['qty'] = 1
            
        final_df = pd.concat([load_data(), df], ignore_index=True)
        conn.update(data=final_df)
        st.success(f"✅ บันทึก {data_type} สำเร็จ!")
        refresh_data_cache()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI ---

st.sidebar.title("🚀 AI Business Master")
page = st.sidebar.radio("เลือกเมนู:", ["📸 สแกนบิล", "🎙️ บันทึกเสียง", "💰 รายรับเดลิเวอรี่", "📊 Dashboard", "📋 ข้อมูลทั้งหมด", "🤖 AI Agent"])

if page == "📸 สแกนบิล":
    st.header("📸 สแกนบิลวัตถุดิบ")
    mode = st.radio("วิธีนำเข้า:", ["ยังไม่เลือก", "📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
    img_file = st.camera_input("สแกน") if mode == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg']) if mode == "📁 เลือกไฟล์" else None
    
    if img_file and st.button("🪄 เริ่มวิเคราะห์"):
        with st.spinner("AI 3.1 Lite กำลังอ่านบิล..."):
            res = process_stock_ai(Image.open(img_file))
            if res: st.session_state.stock_data = pd.DataFrame(res)
            else: st.warning("อ่านบิลไม่ออก กรุณาลองใหม่อีกครั้ง")
            
    if 'stock_data' in st.session_state and not st.session_state.stock_data.empty:
        st.subheader("📝 ตรวจสอบและแก้ไข")
        edited = st.data_editor(st.session_state.stock_data, use_container_width=True, num_rows="dynamic",
                               column_config={"name": st.column_config.TextColumn("ชื่อสินค้า (พิมพ์ใหม่ได้อิสระ)")})
        if st.button("💾 บันทึกค่าวัตถุดิบ"):
            if save_to_sheets(edited, "Expense"):
                del st.session_state.stock_data
                st.rerun()

elif page == "🎙️ บันทึกเสียง":
    st.header("🎙️ บันทึกด้วยเสียง")
    audio = st.audio_input("พูดรายการสินค้า (เช่น ไข่ไก่ 2 แผง 240 บาท)")
    if audio and st.button("🚀 แปลงเป็นข้อมูล"):
        with st.spinner("AI กำลังฟัง..."):
            res = process_stock_ai(audio.read(), is_audio=True, mime_type=audio.type)
            if res: st.session_state.voice_data = pd.DataFrame(res)
            else: st.warning("AI ฟังไม่ชัด ลองพูดใหม่อีกครั้ง")
            
    if 'voice_data' in st.session_state and not st.session_state.voice_data.empty:
        st.subheader("📝 ตรวจสอบและแก้ไข")
        edited = st.data_editor(st.session_state.voice_data, use_container_width=True, num_rows="dynamic",
                               column_config={"name": st.column_config.TextColumn("ชื่อสินค้า (พิมพ์ใหม่ได้อิสระ)")})
        if st.button("💾 บันทึกลงสต๊อก"):
            if save_to_sheets(edited, "Expense"):
                del st.session_state.voice_data
                st.rerun()

elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 รายรับจากแอปเดลิเวอรี่")
    email_txt = st.text_area("วางเนื้อหาอีเมลรายงานยอดขาย (Grab/LINE MAN/ShopeeFood) ที่นี่:", height=250)
    if st.button("🪄 วิเคราะห์รายได้"):
        with st.spinner("AI กำลังคำนวณยอด..."):
            res = process_delivery_income_ai(email_txt)
            if res: st.session_state.inc_data = pd.DataFrame(res)
            else: st.warning("วิเคราะห์ไม่สำเร็จ โปรดตรวจสอบข้อความที่คัดลอกมา")
            
    if 'inc_data' in st.session_state and not st.session_state.inc_data.empty:
        st.subheader("📝 ตรวจสอบรายได้")
        edited = st.data_editor(st.session_state.inc_data, use_container_width=True)
        if st.button("💾 บันทึกรายรับ"):
            if save_to_sheets(edited, "Income"):
                del st.session_state.inc_data
                st.rerun()

elif page == "📊 Dashboard":
    st.header("📊 สรุปผลกำไร-ขาดทุน")
    df = load_data()
    if not df.empty and 'type' in df.columns:
        # ทำให้แน่ใจว่า total_price เป็นตัวเลข
        df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0)
        
        inc = df[df['type'] == 'Income']
        exp = df[df['type'] == 'Expense']
        t_inc = inc['total_price'].sum() if not inc.empty else 0
        t_exp = exp['total_price'].sum() if not exp.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับเดลิเวอรี่ทั้งหมด", f"฿{t_inc:,.2f}")
        c2.metric("รายจ่ายวัตถุดิบทั้งหมด", f"฿{t_exp:,.2f}")
        c3.metric("กำไรเบื้องต้น", f"฿{t_inc - t_exp:,.2f}", delta_color="normal")
        
        st.divider()
        col_l, col_r = st.columns(2)
        with col_l:
            if not inc.empty: 
                st.plotly_chart(px.bar(inc, x='date', y='total_price', color='name', title="รายรับแยกตามแอป"), use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายรับ")
        with col_r:
            if not exp.empty: 
                st.plotly_chart(px.pie(exp, values='total_price', names='name', title="สัดส่วนรายจ่ายวัตถุดิบ"), use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายจ่าย")
    else: 
        st.info("ยังไม่มีข้อมูลในระบบ หรือ โครงสร้างข้อมูลยังไม่สมบูรณ์")

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ประวัติรายการทั้งหมด")
    df = load_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูล")

elif page == "🤖 AI Agent":
    st.header("🤖 AI Business Assistant")
    if "msgs" not in st.session_state: st.session_state.msgs = []
    
    for r, m in st.session_state.msgs:
        with st.chat_message(r): st.markdown(m)
    
    query = st.chat_input("ถามเกี่ยวกับยอดขาย กำไร หรือสต๊อก...")
    if query:
        st.session_state.msgs.append(("user", query))
        with st.chat_message("user"): st.markdown(query)
        
        # ดึงข้อมูลล่าสุด 150 แถวเพื่อไม่ให้เกิน Limit Token
        df_agent = load_data()
        csv_data = df_agent.tail(150).to_csv(index=False) if not df_agent.empty else "ไม่มีข้อมูล"
        sys_msg = "คุณคือที่ปรึกษาธุรกิจร้าน Nave Mee Kai Cheek @ 304 ข้อมูล CSV ประกอบด้วย Income (รายรับ) และ Expense (รายจ่าย) ช่วยวิเคราะห์และตอบเป็นภาษาไทยอย่างกระชับ"
        full_prompt = f"Data:\n{csv_data}\n\nQuestion: {query}"
        
        with st.spinner("Agent กำลังคิด..."):
            ans = call_gemini_with_fallback(sys_msg, contents=[full_prompt])
            if ans:
                st.session_state.msgs.append(("assistant", ans))
                with st.chat_message("assistant"): st.markdown(ans)
            else:
                st.error("Agent ไม่สามารถตอบได้ในขณะนี้ โปรดลองใหม่")

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

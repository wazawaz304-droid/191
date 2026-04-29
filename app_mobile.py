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

def get_unique_products():
    df = load_data()
    if not df.empty and 'name' in df.columns:
        expense_df = df[df['type'] != 'Income'] if 'type' in df.columns else df
        return sorted([str(x) for x in expense_df['name'].dropna().unique()])
    return []

def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            if len(parts) >= 2:
                content = parts[1]
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:]
        return json.loads(content.strip())
    except Exception:
        st.error("❌ AI ส่งข้อมูลผิดรูปแบบ")
        return []

# --- 3. ฟังก์ชัน AI Engine ---

def process_stock_ai(data_input, is_audio=False, mime_type=None):
    existing_items = ", ".join(get_unique_products())
    prompt = f"""
    สกัดข้อมูลสินค้าเป็น JSON array: [{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]
    เทียบชื่อเดิม: [{existing_items}] (หากคล้ายให้ใช้ชื่อเดิม)
    ตอบแค่ PURE JSON
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
    prompt = """
    สกัดข้อมูลรายได้จากอีเมลเดลิเวอรี่เป็น JSON array:
    [{{ "app": "Grab/LINE MAN/ShopeeFood", "gross_sales": ยอดรวม, "gp_amount": ค่า GP, "net_income": ยอดโอนสุทธิ }}]
    ตอบแค่ PURE JSON
    """
    res_text = call_gemini_with_fallback(prompt, contents=[email_text])
    return safe_parse_json(res_text)

def chat_with_stock_agent(user_message: str):
    df = load_data()
    if df.empty:
        stock_summary = "ไม่มีข้อมูล"
    else:
        stock_summary = df.tail(300).to_csv(index=False)

    system_instruction = """
คุณคือ AI Agent ที่ปรึกษาธุรกิจร้านอาหาร ข้อมูลที่ให้มี 'type' (Income=รายรับ, Expense=รายจ่ายวัตถุดิบ)
ให้วิเคราะห์กำไร, แนวโน้มค่าใช้จ่าย และรายรับจากแอปต่างๆ เป็นภาษาไทยอย่างกระชับ
"""
    prompt = f"ข้อมูลบัญชี:\n{stock_summary}\n\nคำถาม: {user_message}"
    
    res = call_gemini_with_fallback(system_instruction, contents=[prompt])
    return res if res else "ขออภัยครับ ระบบประมวลผลมีปัญหาชั่วคราว"

# --- 4. บันทึกข้อมูล ---

def save_data_to_sheets(df_to_save: pd.DataFrame, data_type="Expense"):
    if conn is None: return False
    try:
        if df_to_save.empty: return False
        
        df_to_save['type'] = data_type
        df_to_save['date'] = datetime.now().strftime("%Y-%m-%d")
        
        if data_type == "Expense":
            df_to_save['qty'] = pd.to_numeric(df_to_save['qty'], errors="coerce").fillna(1)
            df_to_save['total_price'] = pd.to_numeric(df_to_save['total_price'], errors="coerce").fillna(0)
            df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']
        else:
            if 'app' in df_to_save.columns:
                df_to_save['name'] = df_to_save['app'] + " Income"
            else:
                df_to_save['name'] = "Delivery Income"
            df_to_save['total_price'] = pd.to_numeric(df_to_save['net_income'], errors="coerce").fillna(0)
            df_to_save['qty'] = 1

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)
        conn.update(data=final_df)
        st.success(f"✅ บันทึก {data_type} สำเร็จ!")
        refresh_data_cache()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. UI ---

st.sidebar.title("🚀 AI Business Menu")
page = st.sidebar.radio("เลือกเมนู:", ["📸 สแกนบิล", "🎙️ บันทึกเสียง", "💰 รายรับเดลิเวอรี่", "📊 Dashboard", "📋 ข้อมูลทั้งหมด", "🤖 AI Agent"])

if page == "📸 สแกนบิล":
    st.header("📸 สแกนบิลวัตถุดิบ")
    mode = st.radio("วิธีนำเข้า:", ["ยังไม่เลือก", "📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
    img_file = st.camera_input("สแกน") if mode == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg']) if mode == "📁 เลือกไฟล์" else None
    
    if img_file and st.button("🪄 เริ่มสแกน", disabled=st.session_state.get("scanning", False)):
        st.session_state.scanning = True
        with st.spinner("AI 3.1 Lite กำลังอ่านบิล..."):
            res = process_stock_ai(Image.open(img_file))
            if res: st.session_state.stock_data = pd.DataFrame(res)
            else: st.warning("AI อ่านบิลไม่ออก ลองถ่ายให้ชัดขึ้นครับ")
        st.session_state.scanning = False
            
    if 'stock_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข")
        edited = st.data_editor(st.session_state.stock_data, use_container_width=True, num_rows="dynamic",
                               column_config={"name": st.column_config.TextColumn("ชื่อสินค้า (พิมพ์ใหม่ได้อิสระ)")})
        if st.button("💾 บันทึกค่าวัตถุดิบ"):
            if save_data_to_sheets(edited, "Expense"):
                del st.session_state.stock_data
                st.rerun()

elif page == "🎙️ บันทึกเสียง":
    st.header("🎙️ บันทึกด้วยเสียง")
    audio = st.audio_input("พูดรายการสินค้า (เช่น ไข่ไก่ 2 แผง 240 บาท)")
    if audio and st.button("🚀 แปลงเป็นข้อมูล", disabled=st.session_state.get("listening", False)):
        st.session_state.listening = True
        with st.spinner("AI กำลังฟัง..."):
            res = process_stock_ai(audio.read(), is_audio=True, mime_type=audio.type)
            if res: st.session_state.voice_data = pd.DataFrame(res)
            else: st.warning("AI ฟังไม่ถนัด โปรดลองอีกครั้ง")
        st.session_state.listening = False
            
    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข")
        edited = st.data_editor(st.session_state.voice_data, use_container_width=True, num_rows="dynamic",
                               column_config={"name": st.column_config.TextColumn("ชื่อสินค้า (พิมพ์ใหม่ได้อิสระ)")})
        if st.button("💾 บันทึกลงสต๊อก"):
            if save_data_to_sheets(edited, "Expense"):
                del st.session_state.voice_data
                st.rerun()

elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 รายรับจากแอปเดลิเวอรี่")
    email_txt = st.text_area("วางเนื้อหาอีเมลรายงานยอดขาย (Grab/LINE MAN/ShopeeFood) ที่นี่:", height=200)
    if st.button("🪄 วิเคราะห์รายได้"):
        with st.spinner("AI กำลังคำนวณยอด..."):
            res = process_delivery_income_ai(email_txt)
            if res: st.session_state.inc_data = pd.DataFrame(res)
            
    if 'inc_data' in st.session_state:
        st.subheader("📝 ตรวจสอบยอดสุทธิ")
        edited = st.data_editor(st.session_state.inc_data, use_container_width=True)
        if st.button("💾 บันทึกรายรับ"):
            if save_data_to_sheets(edited, "Income"):
                del st.session_state.inc_data
                st.rerun()

elif page == "📊 Dashboard":
    st.header("📊 สรุปผลกำไร-ขาดทุน")
    df = load_data()
    if not df.empty and 'type' in df.columns:
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

        # --- กราฟ: การเปลี่ยนแปลงราคาวัตถุดิบ (ซูม/เลื่อนได้) ---
        st.divider()
        st.subheader("📈 แนวโน้มราคาวัตถุดิบ (Price Fluctuation)")
        if not exp.empty:
            exp_items = exp.dropna(subset=['name']).copy()
            items_list = sorted(exp_items['name'].unique())
            
            if len(items_list) > 0:
                selected_item = st.selectbox("เลือกวัตถุดิบเพื่อดูแนวโน้มราคาต่อหน่วย:", items_list)
                
                item_df = exp_items[exp_items['name'] == selected_item].copy()
                
                # แปลงข้อมูลเป็น Datetime และ ตัวเลข
                item_df['date'] = pd.to_datetime(item_df['date'], errors='coerce')
                item_df['unit_price'] = pd.to_numeric(item_df['unit_price'], errors='coerce')
                item_df = item_df.dropna(subset=['date', 'unit_price'])
                
                # หาค่าเฉลี่ยรายวันกรณีซื้อหลายบิลในวันเดียวกัน
                item_df = item_df.groupby('date', as_index=False)['unit_price'].mean()
                
                # กรองข้อมูลย้อนหลังสูงสุด 180 วัน
                today = pd.Timestamp.now()
                days_180_ago = today - pd.Timedelta(days=180)
                days_30_ago = today - pd.Timedelta(days=30)
                
                item_df = item_df[item_df['date'] >= days_180_

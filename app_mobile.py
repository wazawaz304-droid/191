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

@st.cache_resource
def get_conn():
    """สร้างและ cache การเชื่อมต่อ Google Sheets"""
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        return None

conn = get_conn()

# ดึง API Key จาก Secrets
client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- 2.1 Cache ข้อมูลจาก Google Sheets ---

@st.cache_data(ttl=60)
def load_data():
    """โหลดข้อมูลทั้งหมดจาก Google Sheets พร้อม cache 60 วินาที"""
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(ttl=0)
        if df is None:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"⚠️ อ่านข้อมูลจาก Google Sheets ไม่ได้: {e}")
        return pd.DataFrame()

def refresh_data_cache():
    """เคลียร์ cache ข้อมูล"""
    load_data.clear()

# ฟังก์ชันดึงรายชื่อสินค้าเดิม
def get_unique_products():
    df = load_data()
    if not df.empty and 'name' in df.columns:
        return sorted([str(x) for x in df['name'].dropna().unique()])
    return []

# ฟังก์ชันแกะ JSON อย่างปลอดภัย
def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:  
            # กรณีตอบเป็น code block  
            parts = text_response.split("```")
            # เอาชิ้นที่อยู่ระหว่าง ``` ... ```
            if len(parts) >= 2:
                content = parts[1]
            # ตัดคำว่า json ออกถ้ามี
            if content.lstrip().startswith("json"):
                content = content.lstrip()[4:]
        return json.loads(content.strip())
    except Exception:
        st.error("❌ AI ส่งข้อมูลผิดรูปแบบ (ไม่ใช่ JSON ที่อ่านได้)")
        return []

# --- 3. ฟังก์ชัน AI สำหรับบิลรูปภาพและเสียง ---

def build_prompt_from_image(existing_items):
    items_str = ", ".join(existing_items)
    return f"""
คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลสินค้าจากรูปภาพบิลเป็น JSON array เท่านั้น ในรูปแบบ:

[{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]

กฎการแมตชื่อ:
1. ตรวจสอบลิสต์เดิมที่มีในระบบ: [{items_str}]
2. หากชื่อในบิล "คล้ายกันมาก" และน่าจะเป็นตัวเดียวกัน ให้ใช้ชื่อจากลิสต์เดิม
3. หากเป็นสินค้าใหม่หรือชื่อจงใจให้ต่าง ให้ใช้ชื่อตามที่อ่านได้จากบิล
ห้ามตอบคำอธิบายอื่น ๆ เพิ่ม ตอบเป็น PURE JSON เท่านั้น
"""

def build_prompt_from_audio(existing_items):
    items_str = ", ".join(existing_items)
    return f"""
คุณคือผู้ช่วยจัดการสต๊อค สกัดข้อมูลจากเสียงพูดเป็น JSON array เท่านั้น ในรูปแบบ:

[{{ "name": "ชื่อสินค้า", "qty": จำนวน, "unit": "หน่วย", "total_price": ราคารวม }}]

กฎการแมตชื่อ:
1. ตรวจสอบกับลิสต์สินค้าเดิม: [{items_str}]
2. หากพูดคล้ายรายการเดิม ให้ Match ชื่อให้ตรงกัน
3. หากผู้พูดระบุว่าเป็นของใหม่ หรือชื่อต่างออกไป ให้ใช้ชื่อตามที่พูด
ห้ามตอบคำอธิบายอื่น ๆ เพิ่ม ตอบเป็น PURE JSON เท่านั้น
"""

def process_with_ai(img):
    existing_items = get_unique_products()
    prompt = build_prompt_from_image(existing_items)

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt, img]
        )
        return safe_parse_json(response.text)
    except Exception as e:
        st.error(f"❌ เรียกใช้ AI ไม่สำเร็จ: {e}")
        return []

def process_audio_with_ai(audio_bytes, mime_type="audio/wav"):
    existing_items = get_unique_products()
    prompt_text = build_prompt_from_audio(existing_items)

    try:
        user_content = types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            ]
        )
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[user_content]
        )
        return safe_parse_json(response.text)
    except Exception as e:
        st.error(f"❌ AI ฟังไม่ถนัดหรือเกิดข้อผิดพลาด: {e}")
        return []

# --- 3.1 ฟังก์ชัน AI Agent (คุยกับข้อมูลสต๊อค) ---

def chat_with_stock_agent(user_message: str):
    """
    ให้ AI Agent อ่านข้อมูลจาก Google Sheets (ผ่าน DataFrame) แล้วตอบคำถามเกี่ยวกับสต๊อค/การใช้จ่าย
    """
    df = load_data()

    # เตรียมข้อมูลแบบย่อให้ AI เห็น (ลดขนาดถ้าข้อมูลเยอะ)
    if df.empty:
        stock_summary = "ตอนนี้ยังไม่มีข้อมูลสินค้าในระบบเลย"
    else:
        # เลือกคอลัมน์สำคัญ
        cols = [c for c in df.columns if c in ["name", "qty", "unit", "total_price", "unit_price", "date"]]
        small_df = df[cols].copy()

        # ถ้าข้อมูลเยอะมาก ตัดให้เหลือเฉพาะล่าสุด 300 แถว
        if len(small_df) > 300:
            small_df = small_df.sort_values("date").tail(300)

        stock_summary = small_df.to_csv(index=False)

    system_instruction = """
คุณคือ AI Agent ผู้ช่วยจัดการสต๊อคและการซื้อของสำหรับร้านค้า/ครัว
ข้อมูลที่ให้คุณคือตาราง CSV จาก Google Sheets ซึ่งมีอย่างน้อย:
- name: ชื่อสินค้า
- qty: จำนวนที่ซื้อในแต่ละครั้ง
- unit: หน่วย เช่น ฟอง, กิโล, แพ็ค
- total_price: ราคารวมต่อบิลสำหรับสินค้านั้น
- unit_price: ราคาต่อหน่วย
- date: วันที่ซื้อ (รูปแบบ YYYY-MM-DD)

บทบาทของคุณ:
1. ตอบคำถามเกี่ยวกับ:
   - ยอดใช้จ่ายรวม, รายเดือน, รายสินค้า
   - เทรนด์ราคาต่อหน่วยของสินค้า
   - เปรียบเทียบราคาสินค้าต่าง ๆ
2. ให้คำแนะนำ:
   - ควรสต๊อกอะไรเพิ่ม หรืออะไรเริ่มเยอะเกินไป (จากความถี่การซื้อ)
   - แนวโน้มราคาสินค้า (ขึ้น/ลง) จากข้อมูลย้อนหลัง
3. ถ้าข้อมูลไม่พอให้สรุปแนวคิดทั่วไปแทน แต่ให้บอกชัดว่า "ข้อมูลไม่พอ"

กติกา:
- ให้คำตอบเป็นภาษาไทย เข้าใจง่าย
- ถ้าเป็นคำถามเชิงตัวเลข ให้สรุปเป็นข้อ ๆ หรือ bullet list สั้น ๆ
- ถ้าผู้ใช้ถามนอกเหนือจากสต๊อคหรือการเงิน ให้ตอบแบบสั้น ๆ แล้วพยายามโยงกลับมาที่บริบทสต๊อค
"""

    prompt = f"""
นี่คือข้อมูลสต๊อคและการซื้อสินค้าล่าสุดในรูปแบบ CSV:

{stock_summary}

คำถามจากผู้ใช้:
{user_message}

ให้ตอบเป็นภาษาไทย กระชับ และอ้างอิงจากข้อมูลใน CSV เท่าที่ทำได้
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[
                types.Part.from_text(text=system_instruction),
                types.Part.from_text(text=prompt),
            ]
        )
        return response.text
    except Exception as e:
        st.error(f"❌ AI Agent ตอบไม่ได้: {e}")
        return "ตอนนี้ Agent มีปัญหาในการประมวลผล ลองใหม่ภายหลังหรือตรวจสอบการตั้งค่า API Key/Model"

# --- 4. ฟังก์ชันบันทึกข้อมูลลง Google Sheets ---

def save_data_to_sheets(df_to_save: pd.DataFrame):
    if conn is None:
        st.error("❌ ยังไม่สามารถเชื่อมต่อ Google Sheets ได้")
        return False

    try:
        if df_to_save.empty:
            st.warning("ไม่มีข้อมูลให้บันทึก")
            return False

        # แปลงคอลัมน์ qty / total_price ให้เป็นตัวเลข
        df_to_save['qty'] = pd.to_numeric(df_to_save['qty'], errors="coerce")
        df_to_save['total_price'] = pd.to_numeric(df_to_save['total_price'], errors="coerce")

        # ตัดแถวที่ข้อมูลไม่ครบหรือ qty=0 ออก
        df_to_save = df_to_save.dropna(subset=['qty', 'total_price'])
        df_to_save = df_to_save[df_to_save['qty'] != 0]

        if df_to_save.empty:
            st.warning("ข้อมูลไม่ถูกต้อง: qty เป็น 0 หรือค่าราคา/จำนวนว่าง")
            return False

        df_to_save['date'] = datetime.now().strftime("%Y-%m-%d")
        df_to_save['unit_price'] = df_to_save['total_price'] / df_to_save['qty']

        existing_df = load_data()
        final_df = pd.concat([existing_df, df_to_save], ignore_index=True)

        conn.update(data=final_df)
        st.success("✅ บันทึกลง Google Sheets สำเร็จ!")

        # รีเฟรช cache
        refresh_data_cache()
        return True

    except Exception as e:
        st.error(f"❌ บันทึกไม่ได้: {e}")
        return False

# --- 5. ส่วนแสดงผล UI ---

st.sidebar.title("🚀 AI Stock Menu")
page = st.sidebar.radio(
    "เลือกเมนู:",
    [
        "📸 สแกนบิลใหม่",
        "🎙️ บันทึกด้วยเสียง",
        "📊 Dashboard",
        "📋 รายการสต๊อก",
        "🤖 AI Agent",
    ]
)

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
        if st.button("🪄 เริ่มสแกน", disabled=st.session_state.get("scanning", False)):
            st.session_state.scanning = True
            with st.spinner('กำลังอ่านบิลด้วย AI...'):
                data = process_with_ai(img)
            st.session_state.scanning = False

            if data:
                st.session_state.bill_data = pd.DataFrame(data)
            else:
                st.warning("AI ยังอ่านบิลไม่ออก ลองถ่ายให้ชัดขึ้นหรืออีกมุมหนึ่ง")

    if 'bill_data' in st.session_state:
        st.subheader("📝 ตรวจสอบและแก้ไข (พิมพ์ชื่อใหม่ได้อิสระ)")
        edited_df = st.data_editor(
            st.session_state.bill_data,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn(
                    "ชื่อสินค้า",
                    help="แก้ไขชื่อได้ทันทีหาก AI แมตผิด",
                    width="large"
                ),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "unit": st.column_config.TextColumn("หน่วย"),
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
    audio_value = st.audio_input("กดปุ่มไมค์เพื่อเริ่มพูด (เช่น 'ไข่ไก่เบอร์ 2 จำนวน 30 ฟอง ราคา 120 บาท')")

    if audio_value:
        if st.button("🚀 แปลงเสียงเป็นข้อมูล", disabled=st.session_state.get("listening", False)):
            st.session_state.listening = True
            with st.spinner('AI กำลังฟัง...'):
                res_data = process_audio_with_ai(audio_value.read(), mime_type=audio_value.type)
            st.session_state.listening = False

            if res_data:
                st.session_state.voice_data = pd.DataFrame(res_data)
            else:
                st.warning("AI ฟังไม่ชัดหรือถอดความไม่ได้ ลองพูดใหม่ให้ชัดขึ้น")

    if 'voice_data' in st.session_state:
        st.subheader("📝 ตรวจสอบข้อมูล (พิมพ์แก้ไขได้อิสระ)")
        edited_voice_df = st.data_editor(
            st.session_state.voice_data,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("ชื่อสินค้า", width="large"),
                "qty": st.column_config.NumberColumn("จำนวน", min_value=0),
                "unit": st.column_config.TextColumn("หน่วย"),
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
    df = load_data()

    if df.empty:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")
    else:
        required_cols = {"name", "total_price", "date", "unit_price"}
        if not required_cols.issubset(df.columns):
            st.warning("ข้อมูลยังไม่ครบ (ต้องมี name, total_price, date, unit_price) ลองบันทึกข้อมูลจากบิลหรือเสียงก่อน")
        else:
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'], errors="coerce")
            df = df.dropna(subset=['date'])

            if df.empty:
                st.info("ยังไม่มีข้อมูลวันที่ ที่สามารถนำมาวิเคราะห์ได้")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    fig_pie = px.pie(
                        df,
                        values='total_price',
                        names='name',
                        hole=0.4,
                        title="💰 สัดส่วนรายจ่าย"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with c2:
                    items = df['name'].dropna().unique()
                    if len(items) == 0:
                        st.info("ยังไม่มีชื่อสินค้าให้เลือก")
                    else:
                        target = st.selectbox("เลือกสินค้า:", items)
                        item_df = df[df['name'] == target].sort_values('date')
                        fig_line = px.line(
                            item_df,
                            x='date',
                            y='unit_price',
                            markers=True,
                            title=f"📈 ราคาต่อหน่วย: {target}"
                        )
                        st.plotly_chart(fig_line, use_container_width=True)

# --- หน้าตารางทั้งหมด ---
elif page == "📋 รายการสต๊อก":
    st.header("📋 ข้อมูลทั้งหมด")
    df = load_data()
    if df.empty:
        st.info("ยังไม่มีข้อมูลในฐานข้อมูล")
    else:
        st.dataframe(df, use_container_width=True)

# --- หน้า AI Agent ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI Stock Agent")
    st.caption("คุยกับผู้ช่วยอัจฉริยะที่มองเห็นข้อมูลใน Google Sheets ของคุณ")

    with st.expander("ตัวอย่างคำถามที่คุณอาจลองถาม", expanded=False):
        st.markdown(
            """
- เดือนนี้ใช้เงินซื้อวัตถุดิบไปประมาณเท่าไหร่?
- ช่วงหลัง ๆ ราคาต่อหน่วยของ 'ไข่ไก่เบอร์ 2' มีแนวโน้มขึ้นหรือลง?
- สินค้าอะไรใช้เงินเยอะที่สุดในเดือนที่ผ่านมา?
- ถ้าอยากลดต้นทุน ควรโฟกัสดูสินค้าตัวไหนก่อน?
            """.strip()
        )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    # แสดงประวัติการคุย
    for role, msg in st.session_state.agent_messages:
        if role == "user":
            with st.chat_message("user"):
                st.markdown(msg)
        else:
            with st.chat_message("assistant"):
                st.markdown(msg)

    # กล่อง chat input
    user_input = st.chat_input("พิมพ์คำถามเกี่ยวกับสต๊อคหรือการใช้จ่ายของคุณที่นี่...")

    if user_input:
        # เก็บข้อความของผู้ใช้
        st.session_state.agent_messages.append(("user", user_input))

        # แสดงทันที
        with st.chat_message("user"):
            st.markdown(user_input)

        # ให้ Agent ตอบ
        with st.chat_message("assistant"):
            with st.spinner("Agent กำลังคิดจากข้อมูลสต๊อคของคุณ..."):
                answer = chat_with_stock_agent(user_input)
            st.markdown(answer)

        # เก็บข้อความของ Agent
        st.session_state.agent_messages.append(("assistant", answer))

# ปุ่มพิเศษที่ Sidebar
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_data_cache()
    st.rerun()

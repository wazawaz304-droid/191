import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="AI Stock & Revenue Master 2026", layout="wide", page_icon="💰")

# --- 2. การเชื่อมต่อ Google Sheets และ AI ---
@st.cache_resource
def get_conn():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"⚠️ เชื่อมต่อ Google Sheets ไม่ได้: {e}")
        return None

conn = get_conn()
client = genai.Client(api_key=st.secrets["gemini"]["api_key"])

# --- 2.1 การจัดการข้อมูล (Data Handling) ---
@st.cache_data(ttl=60)
def load_data(worksheet="Sheet1"):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_all_cache():
    load_data.clear()

# --- 3. ฟังก์ชัน Gmail & Revenue ---
def clean_html(raw_html):
    """กรอง HTML เอาเฉพาะข้อความเพื่อประหยัด Token"""
    soup = BeautifulSoup(raw_html, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()
    return soup.get_text(separator=' ')

def fetch_delivery_emails():
    user = st.secrets["gmail"]["user"]
    pwd = st.secrets["gmail"]["password"]
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)
        mail.select("INBOX")
        
        # ค้นหาโดยใช้เพียง 'ผู้ส่ง' เท่านั้น (เพื่อให้ IMAP ทำงานง่ายที่สุดและไม่เกิด Error)
        search_targets = [
            {"platform": "LINE MAN", "from": "no-reply-merchant@lmwn.com", "keyword": "รายงานยอดขายรายวัน"},
            {"platform": "ShopeeFood", "from": "noreply.th@shopeefood.com", "keyword": "รายงานการโอนเงิน"},
            {"platform": "Grab", "from": "no-reply@grab.com", "keyword": "สรุปยอดขาย"}
        ]
        
        all_contents = []
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for target in search_targets:
            # ค้นหาอีเมลทั้งหมดจากผู้ส่งรายนี้ (ไม่ระบุวันที่ในคำสั่ง search เพื่อป้องกัน Server งง)
            status, data = mail.search(None, f'(FROM "{target["from"]}")')
            
            if status == "OK":
                # ดึงเฉพาะ 15 ฉบับล่าสุดมาตรวจสอบ (เพื่อความรวดเร็ว)
                email_ids = data[0].split()[-15:] 
                
                for e_id in reversed(email_ids): # ตรวจสอบจากใหม่ไปเก่า
                    _, msg_data = mail.fetch(e_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # 1. ตรวจสอบวันที่จาก Header ของอีเมลโดยตรง
                    date_str = msg.get("Date")
                    email_date = email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
                    
                    # ถ้าเก่ากว่า 7 วันแล้ว ให้หยุดตรวจเช็คผู้ส่งรายนี้
                    if email_date < cutoff_date:
                        break
                        
                    # 2. ถอดรหัสหัวข้ออีเมล (Subject)
                    subject_raw = decode_header(msg.get("Subject"))
                    subject_text = ""
                    for content, encoding in subject_raw:
                        if isinstance(content, bytes):
                            try: subject_text += content.decode(encoding or "utf-8")
                            except: subject_text += content.decode("tis-620", errors="ignore")
                        else: subject_text += str(content)
                    
                    # 3. ถ้าหัวข้อมี Keyword ที่ต้องการ ให้ดึงเนื้อหา
                    if target["keyword"] in subject_text:
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() in ["text/plain", "text/html"]:
                                    charset = part.get_content_charset() or 'utf-8'
                                    body = part.get_payload(decode=True).decode(charset, errors='ignore')
                                    break
                        else:
                            charset = msg.get_content_charset() or 'utf-8'
                            body = msg.get_payload(decode=True).decode(charset, errors='ignore')
                        
                        if body:
                            all_contents.append({"platform": target["platform"], "content": clean_html(body)})
        
        mail.logout()
        return all_contents
    except Exception as e:
        st.error(f"📧 Gmail Error: {str(e)}")
        return []
def process_revenue_ai(email_text):
    """ใช้ Gemini สกัดข้อมูลรายรับจากข้อความอีเมล"""
    prompt = """
    คุณคือผู้ช่วยบัญชี สกัดข้อมูลรายรับจากอีเมลเดลิเวอรี่เป็น JSON object:
    { "date": "YYYY-MM-DD", "platform": "ชื่อแอป", "gross_sales": ยอดขายรวม, "gp_amount": ค่า GP, "net_payout": ยอดโอนสุทธิ }
    
    กฎ:
    1. LINE MAN: ยอดขาย E-Payment(Gross), ค่าบริการ GP (รวม VAT)(GP)
    2. ShopeeFood: ยอดรายการ(Gross), ค่าธรรมเนียม (GP)(GP)
    3. Grab: ยอดรายการ(Gross), ค่าคอมมิชชันและภาษีทั้งหมด(GP)
    4. สกัด 'ยอดโอนสุทธิ' มาให้ตรงตามเมล
    ตอบเป็น PURE JSON เท่านั้น
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", # หรือใช้ 1.5-flash ตามที่คุณมี
            contents=[prompt, email_text]
        )
        # ใช้ safe_parse_json เดิมที่คุณมี (จำลองในที่นี้)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return None

# --- 4. ฟังก์ชัน AI เดิม (Stock) ---
def safe_parse_json(text_response: str):
    try:
        content = text_response
        if "```" in text_response:
            parts = text_response.split("```")
            content = parts[1]
            if content.lstrip().startswith("json"): content = content.lstrip()[4:]
        return json.loads(content.strip())
    except:
        return []

def process_with_ai(img):
    prompt = "สกัดข้อมูลสินค้าจากรูปภาพบิลเป็น JSON array: [{ 'name': 'ชื่อ', 'qty': จำนวน, 'unit': 'หน่วย', 'total_price': ราคารวม }]"
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, img])
        return safe_parse_json(response.text)
    except: return []

# --- 5. หน้าจอ UI ---
st.sidebar.title("🚀 Smart Restaurant AI")
page = st.sidebar.radio("เมนู:", ["📸 สแกนสต๊อก", "💰 รายรับเดลิเวอรี่", "📊 Dashboard", "📋 รายการทั้งหมด", "🤖 AI Agent"])

# --- หน้าสแกนสต๊อก ---
if page == "📸 สแกนสต๊อก":
    st.header("📸 สแกนบิลเข้าสต๊อก")
    img_file = st.camera_input("ถ่ายรูปบิล")
    if img_file:
        img = Image.open(img_file)
        if st.button("🪄 สแกนบิล"):
            with st.spinner('AI กำลังอ่าน...'):
                data = process_with_ai(img)
                if data: st.session_state.bill_data = pd.DataFrame(data)
    
    if 'bill_data' in st.session_state:
        edited_df = st.data_editor(st.session_state.bill_data, num_rows="dynamic")
        if st.button("💾 บันทึกสต๊อก"):
            # โค้ดบันทึกของเดิม (ลง Sheet1)
            existing = load_data("Sheet1")
            edited_df['date'] = datetime.now().strftime("%Y-%m-%d")
            final_df = pd.concat([existing, edited_df], ignore_index=True)
            conn.update(worksheet="Sheet1", data=final_df)
            st.success("บันทึกแล้ว!")

# --- หน้าใหม่: รายรับเดลิเวอรี่ ---
elif page == "💰 รายรับเดลิเวอรี่":
    st.header("💰 ดึงรายรับจาก Gmail (7 วันล่าสุด)")
    if st.button("📩 เริ่มดึงข้อมูลจาก Gmail"):
        with st.spinner("กำลังค้นหาอีเมลและประมวลผลด้วย AI..."):
            emails = fetch_delivery_emails()
            revenue_results = []
            for item in emails:
                res = process_revenue_ai(item['content'])
                if res: revenue_results.append(res)
            
            if revenue_results:
                st.session_state.revenue_temp = pd.DataFrame(revenue_results)
                st.success(f"พบข้อมูลรายรับ {len(revenue_results)} รายการ")
            else:
                st.warning("ไม่พบอีเมลรายงานยอดขายใหม่")

    if 'revenue_temp' in st.session_state:
        st.subheader("📝 ตรวจสอบยอดเงินโอนสุทธิ")
        rev_df = st.data_editor(st.session_state.revenue_temp, use_container_width=True)
        if st.button("💾 ยืนยันบันทึกลง Google Sheets"):
            existing_rev = load_data("Revenue")
            final_rev = pd.concat([existing_rev, rev_df], ignore_index=True).drop_duplicates()
            conn.update(worksheet="Revenue", data=final_rev)
            st.success("บันทึกรายรับลงแท็บ Revenue เรียบร้อย!")
            refresh_all_cache()

# --- หน้า Dashboard ---
elif page == "📊 Dashboard":
    st.header("📊 วิเคราะห์ภาพรวมธุรกิจ")
    stock_df = load_data("Sheet1")
    rev_df = load_data("Revenue")
    
    col1, col2 = st.columns(2)
    with col1:
        if not rev_df.empty:
            fig_rev = px.bar(rev_df, x='date', y='net_payout', color='platform', title="💰 ยอดโอนสุทธิรายวัน", barmode='group')
            st.plotly_chart(fig_rev, use_container_width=True)
    with col2:
        if not stock_df.empty:
            stock_df['total_price'] = pd.to_numeric(stock_df['total_price'])
            fig_stock = px.pie(stock_df, values='total_price', names='name', title="💸 สัดส่วนค่าวัตถุดิบ", hole=0.4)
            st.plotly_chart(fig_stock, use_container_width=True)

    if not rev_df.empty:
        st.subheader("📈 วิเคราะห์ส่วนต่าง GP")
        rev_df['GP_Percent'] = (rev_df['gp_amount'] / rev_df['gross_sales']) * 100
        fig_gp = px.line(rev_df, x='date', y='GP_Percent', color='platform', title="เปอร์เซ็นต์ GP ที่ถูกหัก (%)")
        st.plotly_chart(fig_gp, use_container_width=True)

# --- หน้าอื่นๆ คงเดิม ---
elif page == "📋 รายการทั้งหมด":
    t1, t2 = st.tabs(["📦 สต๊อกสินค้า", "💰 รายรับเดลิเวอรี่"])
    with t1: st.dataframe(load_data("Sheet1"), use_container_width=True)
    with t2: st.dataframe(load_data("Revenue"), use_container_width=True)

elif page == "🤖 AI Agent":
    st.write("ฟีเจอร์ AI Agent เชื่อมต่อข้อมูลทั้งรายรับและรายจ่าย...")
    # (เพิ่ม Logic ให้ AI Agent อ่าน rev_df เพิ่มจากเดิม)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_cache()
    st.rerun()

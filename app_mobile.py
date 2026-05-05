import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
from PIL import Image
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import difflib

# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
)

st.markdown("""
<style>
@import url(\'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap\');

html, body, [class*="css"] { font-family: \'IBM Plex Sans Thai\', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.25rem 2rem 3rem; max-width: 1300px; }

/* Sidebar Background */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"] {
    background: linear-gradient(175deg, #0d3d26 0%, #1a6b4a 100%) !important;
    background-color: #0d3d26 !important;
}

/* Ensure all text within the sidebar is white by default */
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

/* Specific adjustments for sidebar elements */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    font-weight: 500;
}
[data-testid="stSidebar"] small { color: rgba(255,255,255,0.8) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2) !important; }

/* Labels for st.number_input within the sidebar (general) */
[data-testid="stSidebar"] .stNumberInput label p {
    color: #FFFFFF !important; /* White text for labels */
    font-weight: 600 !important;
}

/* Input fields within the sidebar */
[data-testid="stSidebar"] input[type="number"],
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] textarea {
    background-color: #FFFFFF !important; /* White background for input fields */
    color: #111827 !important; /* Dark text for input fields */
    border: 2px solid #1a6b4a !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* Specific for st.number_input container background */
[data-testid="stSidebar"] .stNumberInput div[data-baseweb="input"] {
    background-color: #FFFFFF !important;
    border-radius: 8px !important;
}

/* Input text color within number inputs in sidebar expander (most specific) */
[data-testid="stSidebar"] .stExpander .stNumberInput input[type="number"] {
    color: #111827 !important; /* Ensure dark text for typed numbers */
    background-color: #FFFFFF !important; /* Ensure white background */
}

/* Even more specific targeting for the input text itself within the number input */
[data-testid="stSidebar"] .stExpander .stNumberInput div[data-baseweb="input"] > div > input {
    color: #111827 !important;
    background-color: #FFFFFF !important;
}

/* Expander styling in sidebar */
[data-testid="stSidebar"] .stExpander {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
}

/* Expander header text */
[data-testid="stSidebar"] .stExpander div[role="button"] p {
    color: #FFFFFF !important;
}

/* Radio buttons in sidebar */
[data-testid="stSidebar"] .stRadio label {
    padding: 0.5rem 0.9rem; border-radius: 8px; display: block;
    transition: background 0.15s; font-size: 0.875rem; cursor: pointer;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.15); }

/* Buttons in sidebar */
[data-testid="stSidebar"] .stButton > button {
    background: #ffffff !important;
    border: none !important;
    color: #0d3d26 !important; 
    width: 100%; border-radius: 8px;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #f0fdf4 !important; }

/* Hide sidebar collapse button */
[data-testid="collapsedControl"] {
    background: #1a6b4a !important;
    border-radius: 0 8px 8px 0 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.1); }
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; color: #6b7280 !important; font-weight: 500; text-transform: uppercase; letter-spacing: 0.4px; }
[data-testid="stMetricValue"] { font-size: 1.55rem !important; font-weight: 600; color: #111827; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f3f4f6; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-size: 0.85rem; color: #6b7280; padding: 0.4rem 1rem; }
.stTabs [aria-selected="true"] { background: white !important; color: #111827 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }

/* Buttons */
.stButton > button { border-radius: 10px; font-weight: 500; font-size: 0.875rem; transition: all 0.15s; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg,#1a6b4a,#2e8b62); color: white; border: none; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0,0,0,0.13); }

/* Radio */
.stRadio [data-baseweb="radio"] { gap: 6px; }

/* Selectbox / input */
.stTextArea textarea, .stTextInput input { border-radius: 10px !important; }

/* Custom cards */
.kpi-row { display: flex; gap: 12px; margin-bottom: 1rem; }
.info-card {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 12px; padding: 0.8rem 1rem;
    font-size: 0.85rem; color: #1e40af; margin-bottom: 0.75rem;
}
.warn-card {
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 12px; padding: 0.8rem 1rem;
    font-size: 0.85rem; color: #92400e; margin-bottom: 0.75rem;
}
.success-card {
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-radius: 12px; padding: 0.8rem 1rem;
    font-size: 0.85rem; color: #166534; margin-bottom: 0.75rem;
}
.section-title {
    font-size: 1rem; font-weight: 600; color: #111827;
    padding-bottom: 0.4rem; border-bottom: 2px solid #e5e7eb;
    margin: 1.2rem 0 0.8rem;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin-bottom: 0.1rem; }
.page-sub   { font-size: 0.875rem; color: #6b7280; margin-bottom: 1.1rem; }

@media (max-width: 768px) {
    .block-container { padding: 0.8rem 0.6rem 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONNECTIONS
# ============================================================
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
    client = None

# ============================================================
# 3. DATA FUNCTIONS (ตาม logic เดิม ไม่เปลี่ยน)
# ============================================================
def load_data(sheet_name):
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how=\'all\') if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        cleaned = df[col_name].astype(str).str.replace(r\'[^0-9.]\', \'\', regex=True)
        return pd.to_numeric(cleaned, errors=\'coerce\').fillna(0)
    return pd.Series([0.0] * len(df))

def save_to_tab(df, tab):
    if conn is None or df.empty:
        return False
    try:
        existing = load_data(tab)
        if tab == "Income":
            df[\'type\'] = \'Income\'
            if \'app\' not in df.columns:
                df[\'app\'] = \'หน้าร้าน\'
        elif tab == "Expense":
            df[\'type\'] = \'Expense\'
            if not existing.empty and \'name\' in existing.columns:
                master_names = existing[\'name\'].unique().tolist()
                def match_name(n):
                    matches = difflib.get_close_matches(str(n), master_names, n=1, cutoff=0.6)
                    return matches[0] if matches else n
                df[\'name\'] = df[\'name\'].apply(match_name)
            df[\'unit_price\'] = clean_numeric(df, \'total_price\') / clean_numeric(df, \'qty\').replace(0, 1)
        elif tab == "Monthly":
            df[\'type\'] = \'Monthly\'

        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 4. AI FUNCTION (ตาม logic เดิม ไม่เปลี่ยน)
# ============================================================
def process_extraction(data, p_type, is_bytes=False, mime=None, existing_names=None):
    if client is None:
        st.error("ไม่พบ Gemini API Key")
        return []
    now_str = datetime.now().strftime("%Y-%m-%d")
    model_name = "models/gemini-3.1-flash-lite-preview"

    if p_type == "Expense":
        names_str = ", ".join(existing_names) if existing_names else "ไม่มี"
        p = (f"สกัดข้อมูลรายจ่ายเป็น JSON: [{{\'date\': \'{now_str}\' , \'name\': \'สินค้า\', "
             f"\'qty\': 1, \'unit\': \'หน่วย\', \'total_price\': 0}}]. "
             f"ใช้ชื่อเดิมเหล่านี้ถ้าคล้าย: [{names_str}]")
    else:
        p = (f"สกัดข้อมูลรายได้เป็น JSON: [{{\'date\': \'{now_str}\' , "
             f"\'app\': \'ชื่อแอป\', \'net_income\': 0}}]")

    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    try:
        if is_bytes:
            contents = [types.Content(role="user", parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=data, mime_type=mime),
            ])]
            res = client.models.generate_content(model=model_name, contents=contents)
        else:
            res = client.models.generate_content(model=model_name, contents=[prompt, data])

        text = res.text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "")
        return json.loads(text)
    except:
        return []

# ============================================================
# 5. SIDEBAR
# ============================================================
st.sidebar.markdown("## 🍜 Nave 304")
st.sidebar.markdown("<small style=\'opacity:.85\'>AI Business Master</small>", unsafe_allow_html=True)
st.sidebar.divider()

page = st.sidebar.radio(
    "เมนู",
    [
        "📊 Dashboard รายวัน",
        "📈 วิเคราะห์รายเดือน",
        "💰 บันทึกรายรับ",
        "💸 บันทึกรายจ่าย",
        "🤖 AI Agent",
        "📋 ข้อมูลทั้งหมด",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()

# Break-even settings — ใช้ with st.sidebar แล้ว st.number_input ข้างใน
st.session_state.setdefault("be_rent",     4000)
st.session_state.setdefault("be_electric",  800)
st.session_state.setdefault("be_water",     400)
st.session_state.setdefault("be_other",       0)

_be_exp = st.sidebar.expander("⚙️ ต้นทุนคงที่ (Break-even)")
with _be_exp:
    st.session_state["be_rent"]     = st.number_input("🏠 ค่าเช่า/เดือน (฿)",      value=st.session_state["be_rent"],     step=500, min_value=0)
    st.session_state["be_electric"] = st.number_input("⚡ ค่าไฟ/เดือน (฿)",       value=st.session_state["be_electric"], step=100, min_value=0)
    st.session_state["be_water"]    = st.number_input("💧 ค่าน้ำ/เดือน (฿)",       value=st.session_state["be_water"],    step=50,  min_value=0)
    st.session_state["be_other"]    = st.number_input("🛠️ อื่นๆ/เดือน (฿)",        value=st.session_state["be_other"],    step=100, min_value=0)

fixed_cost_monthly = (
    st.session_state["be_rent"] + 
    st.session_state["be_electric"] + 
    st.session_state["be_water"] + 
    st.session_state["be_other"]
)

st.sidebar.divider()
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# 6. MAIN CONTENT
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class=\'page-title\'>📊 แดชบอร์ดรายรับ-รายจ่ายรายวัน</div>", unsafe_allow_html=True)
    st.markdown("<div class=\'page-sub\'>สรุปความเคลื่อนไหวล่าสุดจาก Google Sheets</div>", unsafe_allow_html=True)

    df_i = load_data("Income")
    df_e = load_data("Expense")

    df_i[\'net_income\'] = clean_numeric(df_i, \'net_income\')
    df_e[\'total_price\'] = clean_numeric(df_e, \'total_price\')
    df_i[\'date\'] = pd.to_datetime(df_i[\'date\'], errors=\'coerce\')
    df_e[\'date\'] = pd.to_datetime(df_e[\'date\'], errors=\'coerce\')

    t_inc = df_i[\'net_income\'].sum()
    t_exp = df_e[\'total_price\'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับสะสม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อก", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น", f"฿{t_inc - t_exp:,.0f}", delta=f"{t_inc - t_exp:,.0f}")

    st.divider()

    t_inc_tab, t_exp_tab, t_be_tab = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "🎯 จุดคุ้มทุน (BEP)"])

    with t_inc_tab:
        zoom = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True, format_func=lambda x: f"{x} วัน", key="z_daily")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=zoom)
        df_f = df_i[df_i[\'date\'] >= cutoff].copy()
        if not df_f.empty:
            daily = df_f.groupby(\'date\')[\'net_income\'].sum().reset_index()
            daily[\'rolling\'] = daily[\'net_income\'].rolling(window=7).mean()
            fig = go.Figure()
            for app in df_f[\'app\'].unique():
                d = df_f[df_f[\'app\'] == app]
                fig.add_trace(go.Bar(x=d[\'date\'], y=d[\'net_income\'], name=app))
            fig.add_trace(go.Scatter(x=daily[\'date\'], y=daily[\'rolling\'], name=\'เฉลี่ย 7 วัน\', line=dict(color=\'#f59e0b\', width=3, dash=\'dot\')))
            fig.update_layout(barmode=\'stack\', hovermode="x unified", height=400, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลในช่วงนี้")

    with t_exp_tab:
        if not df_e.empty:
            fig_pie = px.pie(df_e, values=\'total_price\', names=\'name\', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(height=400, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with t_be_tab:
        st.markdown("<div class=\'section-title\'>การวิเคราะห์จุดคุ้มทุน (Break-even Analysis)</div>", unsafe_allow_html=True)
        # คำนวณกำไรต่อวัน (เฉลี่ย 30 วันล่าสุด)
        df_30 = df_i[df_i[\'date\'] >= (pd.Timestamp.now() - pd.Timedelta(days=30))]
        avg_daily_net = df_30[\'net_income\'].sum() / 30 if not df_30.empty else 0
        
        col_be1, col_be2 = st.columns(2)
        with col_be1:
            st.markdown(f"""
            <div class=\'info-card\'>
                <b>📊 สรุปต้นทุนคงที่:</b><br>
                • รวมทั้งหมด: ฿{fixed_cost_monthly:,.0f} / เดือน<br>
                • เฉลี่ยต่อวัน: ฿{fixed_cost_monthly/30:,.2f}
            </div>
            """, unsafe_allow_html=True)
        
        with col_be2:
            if avg_daily_net > 0:
                days_to_be = fixed_cost_monthly / avg_daily_net
                st.markdown(f"""
                <div class=\'success-card\'>
                    <b>🎯 เป้าหมายความปลอดภัย:</b><br>
                    • รายได้เฉลี่ยปัจจุบัน: ฿{avg_daily_net:,.0f} / วัน<br>
                    • ต้องขายให้ได้ <b>{days_to_be:.1f} วัน</b> เพื่อคุ้มทุนคงที่
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("ยังไม่มีข้อมูลรายได้เฉลี่ยเพื่อคำนวณ")

elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class=\'page-title\'>📈 วิเคราะห์รายเดือน (Deep Dive)</div>", unsafe_allow_html=True)
    df_m = load_data("Monthly")
    if not df_m.empty:
        for c in [\'net_income\',\'gross\',\'fees\',\'ads\']: df_m[c] = clean_numeric(df_m, c)
        st.dataframe(df_m.sort_values(\'month_year\', ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายเดือน")

elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class=\'page-title\'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"): res = process_extraction(txt, rtype)
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("กดพูดรายการรายรับ...")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)
    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=[\'pdf\',\'jpg\',\'png\'])
        if file and st.button("🪄 วิเคราะห์ไฟล์"):
            res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if \'tmp_inc\' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 บันทึกลงฐานข้อมูล"):
            target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
            if save_to_tab(edited, target_tab):
                del st.session_state.tmp_inc
                st.rerun()
# --- 💸 บันทึกรายจ่าย (คงเดิม) ---
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class=\'page-title\'>💸 บันทึกรายจ่ายวัตถุดิบ</div>", unsafe_allow_html=True)
    df_exp_db = load_data("Expense")
    ex_names = df_exp_db[\'name\'].unique().tolist() if not df_exp_db.empty else []
    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    
    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=[\'jpg\',\'png\',\'jpeg\'])
        if img and st.button("🪄 วิเคราะห์บิล"):
            res_ex = process_extraction(Image.open(img) if sub=="📷 ถ่ายรูปสด" else img.read(), "Expense", is_bytes=(sub=="📁 เลือกไฟล์"), mime="image/jpeg", existing_names=ex_names)
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type, existing_names=ex_names)
    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if \'tmp_exp\' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()
# --- 🤖 AI Agent & ข้อมูลทั้งหมด ---
elif page == "🤖 AI Agent":
    st.markdown("<div class=\'page-title\'>🤖 AI ที่ปรึกษาธุรกิจ</div>", unsafe_allow_html=True)
    q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if q:
        df_i, df_e, df_m = load_data("Income"), load_data("Expense"), load_data("Monthly")
        ctx = f"Income Daily: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}"
        with st.chat_message("assistant"):
            if client:
                res = client.models.generate_content(model="models/gemini-2.0-flash", contents=[f"วิเคราะห์ข้อมูลร้าน Nave 304:\n{ctx}\nคำถาม: {q}"])
                st.write(res.text)
            else: st.error("AI ไม่พร้อมใช้งาน")

elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class=\'page-title\'>📋 ข้อมูลดิบแยกแท็บ</div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["📥 Income (รายวัน)", "📊 Monthly (รายเดือน)", "📤 Expense (รายจ่าย)"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Monthly"), use_container_width=True)
    with t3: st.dataframe(load_data("Expense"), use_container_width=True)

# --- Refresh Button (moved to the end of sidebar logic) ---
# This button was duplicated, keeping only one at the end of the sidebar logic
# if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
#     st.cache_data.clear()
#     st.rerun()
    except:
        return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()

# --- 3. ฟังก์ชันจัดการข้อมูลและ AI ---

def clean_numeric(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''), errors='coerce').fillna(0)
    return pd.Series([0] * len(df))

def safe_parse_json(text_response: str):
    if not text_response: return []
    try:
        content = text_response.strip()
        if "```" in content: content = content.split("```")[1]
        if content.startswith("json"): content = content[4:]
        return json.loads(content.strip())
    except: return []

def call_gemini_3_1(prompt, contents=None, is_complex_content=False):
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        if response.text:
            st.toast(f"🤖 ประมวลผลสำเร็จ", icon="✅")
            return response.text
    except: return None

def process_extraction(data, p_type, is_bytes=False, mime=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    if p_type == "Expense":
        p = f"สกัดสินค้าเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}]. หากบิลไม่ระบุวันที่ให้ใช้ {now_str}"
    elif p_type == "หน้าร้าน":
        p = f"สกัดยอดหน้าร้านจากข้อความหรือเสียง: [{{'date': '{now_str}', 'app': 'หน้าร้าน', 'net_income': ยอดขาย}}]. วันนี้คือวันที่ {now_str} ให้ใช้วันที่นี้เป็นค่าเริ่มต้น"
    elif p_type == "สรุปรายเดือน":
        p = "สกัดรายงานรายเดือนเป็น JSON: [{'month_year': 'YYYY-MM', 'platform': 'แอป', 'gross': 0, 'fees': 0, 'ads': 0, 'discounts': 0, 'net_income': 0}]"
    else:
        p = f"สกัดรายได้เดลิเวอรี่รายวันเป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': ยอดโอน}}]. วันนี้คือวันที่ {now_str}"
    
    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    if is_bytes:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=data, mime_type=mime)])]
        res = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini_3_1(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)
        elif tab == "Expense":
            df['type'] = 'Expense'
            if 'name' not in df.columns: df['name'] = 'ไม่ได้ระบุ'
        elif tab == "Monthly":
            df['type'] = 'Monthly'
            if 'net' in df.columns: df.rename(columns={'net': 'net_income'}, inplace=True)

        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# --- 4. UI Layout ---
st.sidebar.title("🚀 Nave 304 Master")
# ปรับปรุงเมนู: แยก Dashboard และ วิเคราะห์รายเดือน
page = st.sidebar.radio("เลือกเมนู:", ["📊 Dashboard รายวัน", "📈 วิเคราะห์รายเดือน", "💰 บันทึกรายรับ", "💸 บันทึกรายจ่าย", "🤖 AI Agent", "📋 ข้อมูลทั้งหมด"])

# --- 📊 Dashboard รายวัน (เน้น รายรับรายวัน - รายจ่าย) ---
if page == "📊 Dashboard รายวัน":
    st.header("📊 แดชบอร์ดรายรับ-รายจ่ายรายวัน")
    df_i = load_data("Income")
    df_e = load_data("Expense")
    
    df_i['net_income'] = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc = df_i['net_income'].sum()
    t_exp = df_e['total_price'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรายวันรวม", f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายสต๊อกรวม", f"฿{t_exp:,.0f}")
    c3.metric("⚖️ ยอดหักลบ (กำไร)", f"฿{t_inc - t_exp:,.0f}", delta=f"{t_inc - t_exp:,.0f}")
    
    st.divider()
    
    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])
    
    with tab_inc:
        zoom_days = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True, format_func=lambda x: f"{x} วัน", key="z_daily")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=zoom_days)
        df_filt = df_i[df_i['date'] >= cutoff].copy()
        
        if not df_filt.empty:
            daily_total = df_filt.groupby('date')['net_income'].sum().reset_index()
            daily_total['rolling'] = daily_total['net_income'].rolling(window=7).mean()
            fig = go.Figure()
            for app in df_filt['app'].unique():
                d = df_filt[df_filt['app'] == app]
                fig.add_trace(go.Bar(x=d['date'], y=d['net_income'], name=app))
            fig.add_trace(go.Scatter(x=daily_total['date'], y=daily_total['rolling'], name='แนวโน้ม (7วัน)', line=dict(color='orange', dash='dot')))
            fig.update_layout(barmode='stack', hovermode="x unified", title=f"ยอดรายวันย้อนหลัง {zoom_days} วัน")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("ไม่มีข้อมูลรายวันในช่วงนี้")

    with tab_exp:
        if not df_e.empty:
            st.plotly_chart(px.pie(df_e, values='total_price', names='name', hole=0.4, title="สัดส่วนรายจ่ายสต๊อก"), use_container_width=True)

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            target = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item = df_e[df_e['name'] == target].sort_values('date')
            df_item['u_price'] = df_item['total_price'] / clean_numeric(df_item, 'qty').replace(0, 1)
            st.plotly_chart(px.line(df_item, x='date', y='u_price', markers=True, title=f"แนวโน้มราคา {target} ต่อหน่วย"), use_container_width=True)

# --- 📈 วิเคราะห์รายเดือน (ใหม่: แยกสรุปยอดแบบละเอียด) ---
elif page == "📈 วิเคราะห์รายเดือน":
    st.header("📈 สรุปยอดและวิเคราะห์รายเดือน (Deep Dive)")
    df_m = load_data("Monthly")
    
    if not df_m.empty:
        df_m['net_income'] = clean_numeric(df_m, 'net_income')
        df_m['gross'] = clean_numeric(df_m, 'gross')
        df_m['fees'] = clean_numeric(df_m, 'fees')
        df_m['ads'] = clean_numeric(df_m, 'ads')
        
        # Metric รายเดือน
        total_m_net = df_m['net_income'].sum()
        total_m_gross = df_m['gross'].sum()
        total_fees = df_m['fees'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 ยอดโอนสุทธิรายเดือน", f"฿{total_m_net:,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{total_m_gross:,.0f}")
        m3.metric("📉 ค่า GP/โฆษณารวม", f"฿{total_fees + df_m['ads'].sum():,.0f}")
        
        st.divider()
        
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.subheader("เปรียบเทียบยอดขาย vs เงินโอนจริง")
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'], name='ยอดขายรวม (Gross)'))
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'], name='เงินโอนสุทธิ (Net)'))
            fig_m.update_layout(barmode='group')
            st.plotly_chart(fig_m, use_container_width=True)
            
        with col_m2:
            st.subheader("สัดส่วนค่าธรรมเนียมแอป")
            fig_pie_m = px.pie(df_m, values='fees', names='platform', title="ค่า GP แยกตามแอป")
            st.plotly_chart(fig_pie_m, use_container_width=True)
            
        st.subheader("📋 ตารางสรุปยอดละเอียดรายเดือน")
        # คำนวณ % ต้นทุนให้เห็นชัดๆ
        df_m['cost_pct'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'] * 100).round(2)
        st.dataframe(df_m[['month_year', 'platform', 'gross', 'fees', 'ads', 'net_income', 'cost_pct']].sort_values('month_year', ascending=False), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในแท็บ Monthly กรุณาบันทึกรายงานสรุปรายเดือนก่อนครับ")

# --- 💰 บันทึกรายรับ (คงเดิม) ---
elif page == "💰 บันทึกรายรับ":
    st.header("💰 บันทึกรายรับ")
    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res = None
    
    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI"): res = process_extraction(txt, rtype)
    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("กดพูดรายการรายรับ...")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล"):
            res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)
    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf','jpg','png'])
        if file and st.button("🪄 วิเคราะห์ไฟล์"):
            res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)
            
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True)
        if st.button("💾 บันทึกลงฐานข้อมูล"):
            target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
            if save_to_tab(edited, target_tab):
                del st.session_state.tmp_inc
                st.rerun()

# --- 💸 บันทึกรายจ่าย (คงเดิม) ---
elif page == "💸 บันทึกรายจ่าย":
    st.header("💸 บันทึกรายจ่ายวัตถุดิบ")
    method = st.radio("เลือกวิธี:", ["ยังไม่เลือก", "📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"], horizontal=True)
    res_ex = None
    
    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์บิล"):
            res_ex = process_extraction(Image.open(img) if sub=="📷 ถ่ายรูปสด" else img.read(), "Expense", is_bytes=(sub=="📁 เลือกไฟล์"), mime="image/jpeg")
    elif method == "🎙️ บันทึกด้วยเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง"):
            res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type)

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True)
        if st.button("💾 บันทึกลงแท็บ Expense"):
            if save_to_tab(edited_ex, "Expense"):
                del st.session_state.tmp_exp
                st.rerun()

# --- 🤖 AI Agent & ข้อมูลทั้งหมด ---
elif page == "🤖 AI Agent":
    st.header("🤖 AI ที่ปรึกษาธุรกิจ")
    q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if q:
        df_i, df_e, df_m = load_data("Income"), load_data("Expense"), load_data("Monthly")
        ctx = f"Income Daily: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}"
        with st.chat_message("assistant"):
            st.write(call_gemini_3_1(f"วิเคราะห์ข้อมูลร้านเนฟ หมี่ไก่ฉีก:\n{ctx}\nคำถาม: {q}"))

elif page == "📋 ข้อมูลทั้งหมด":
    st.header("📋 ข้อมูลแยกแท็บ")
    t1, t2, t3 = st.tabs(["📥 Income (รายวัน)", "📊 Monthly (รายเดือน)", "📤 Expense (รายจ่าย)"])
    with t1: st.dataframe(load_data("Income"), use_container_width=True)
    with t2: st.dataframe(load_data("Monthly"), use_container_width=True)
    with t3: st.dataframe(load_data("Expense"), use_container_width=True)

if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

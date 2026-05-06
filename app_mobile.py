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

# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Nave 304 - AI Business Master",
    layout="wide",
    page_icon="🍜",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.25rem 2rem 3rem; max-width: 1300px; }

/* ── Sidebar — แสดงตลอดเวลา ปิดไม่ได้ ── */
[data-testid="collapsedControl"] { display: none !important; }
button[kind="header"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(175deg, #0d3d26 0%, #1a6b4a 100%) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: rgba(255,255,255,0.9) !important; }
[data-testid="stSidebar"] hr  { border-color: rgba(255,255,255,0.2) !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.13) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    color: #fff !important; width: 100%; border-radius: 8px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #fff !important; border-radius: 6px !important;
}
[data-testid="collapsedControl"] {
    background: #1a6b4a !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: white; border: 1px solid #e5e7eb;
    border-radius: 14px; padding: 1rem 1.25rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0,0,0,0.1);
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; color: #6b7280 !important;
    font-weight: 500; text-transform: uppercase; letter-spacing: 0.4px;
}
[data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 600; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #f3f4f6; border-radius: 10px; padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; font-size: 0.85rem; color: #6b7280; padding: 0.4rem 1rem;
}
.stTabs [aria-selected="true"] {
    background: white !important; color: #111827 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px; font-weight: 500; font-size: 0.875rem;
    transition: all 0.15s;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#1a6b4a,#2e8b62);
    color: white; border: none;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.13);
}

/* ── Custom alert cards ── */
.success-card {
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-left: 4px solid #22c55e;
    border-radius: 10px; padding: 0.8rem 1rem;
    font-size: 0.875rem; color: #166534; margin-bottom: 0.75rem;
}
.warn-card {
    background: #fffbeb; border: 1px solid #fde68a;
    border-left: 4px solid #f59e0b;
    border-radius: 10px; padding: 0.8rem 1rem;
    font-size: 0.875rem; color: #92400e; margin-bottom: 0.75rem;
}
.info-card {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-left: 4px solid #3b82f6;
    border-radius: 10px; padding: 0.8rem 1rem;
    font-size: 0.875rem; color: #1e40af; margin-bottom: 0.75rem;
}
.section-title {
    font-size: 1rem; font-weight: 600; color: #111827;
    padding-bottom: 0.4rem; border-bottom: 2px solid #e5e7eb;
    margin: 1.2rem 0 0.8rem;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin-bottom: 0.1rem; }
.page-sub   { font-size: 0.875rem; color: #6b7280; margin-bottom: 1rem; }

/* ── Mobile: ซ่อน sidebar + เว้นที่ด้านบนให้ top nav ── */
@media (max-width: 768px) {
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"]  { display: none !important; }
    .block-container { padding: 70px 0.6rem 2rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetric"] { padding: 0.7rem 0.8rem !important; }
}

/* ── Mobile top nav bar ── */
.mobile-nav {
    display: none;
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: linear-gradient(90deg, #0d3d26, #1a6b4a);
    padding: 8px 4px env(safe-area-inset-top, 4px);
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.mobile-nav-inner {
    display: flex;
    justify-content: flex-start;
    gap: 4px;
    min-width: max-content;
    padding: 0 4px;
}
.mnav-btn {
    display: flex; flex-direction: row; align-items: center; gap: 5px;
    color: rgba(255,255,255,0.7); font-size: 12px; font-weight: 500;
    background: none; border: none; cursor: pointer;
    padding: 6px 12px; border-radius: 20px; white-space: nowrap;
    font-family: 'IBM Plex Sans Thai', sans-serif; transition: all 0.15s;
    border: 1px solid transparent;
}
.mnav-btn.active {
    color: #fff;
    background: rgba(255,255,255,0.2);
    border-color: rgba(255,255,255,0.3);
}
.mnav-icon { font-size: 15px; line-height: 1; }
@media (max-width: 768px) { .mobile-nav { display: block; } }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. CONNECTIONS (เดิม)
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
    st.error(f"⚠️ ไม่พบ API Key ใน Secrets: {e}")
    client = None


# ============================================================
# 3. DATA FUNCTIONS (เดิมทุกอย่าง)
# ============================================================
@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()

def clean_numeric(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''),
            errors='coerce'
        ).fillna(0)
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
    if client is None: return None
    model_name = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        if response.text:
            st.toast("🤖 ประมวลผลสำเร็จ", icon="✅")
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
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data, mime_type=mime),
        ])]
        res = call_gemini_3_1(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini_3_1(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab)
        if tab == "Income":
            df['type'] = 'Income'
            if 'name' not in df.columns:
                df['name'] = df['app'] + " Daily Income"
            if 'qty' not in df.columns: df['qty'] = 1
            if 'unit' not in df.columns: df['unit'] = "วัน"
            if 'total_price' not in df.columns: df['total_price'] = df['net_income']
            if 'unit_price' not in df.columns: df['unit_price'] = df['net_income']
            df['app'] = df['app'].apply(
                lambda x: "GrabFood" if "grab" in str(x).lower() else x
            )
        cols_order = ['name','qty','unit','total_price','date','unit_price',
                      'app','net_income','gross_sales','gp_amount','type']
        for col in cols_order:
            if col not in df.columns: df[col] = ""
        df = df[cols_order]
        final = pd.concat([existing, df], ignore_index=True)
        if tab == "Income":
            final['date'] = pd.to_datetime(final['date']).dt.strftime('%Y-%m-%d')
            final = final.drop_duplicates(subset=['date','app','net_income'], keep='first')
            final = final.sort_values(by='date', ascending=False)
        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False


# ============================================================
# 4. NAVIGATION — Desktop: sidebar / Mobile: bottom nav bar
# ============================================================

PAGES = [
    ("📊", "Dashboard",  "📊 Dashboard รายวัน"),
    ("📈", "รายเดือน",   "📈 วิเคราะห์รายเดือน"),
    ("💰", "รายรับ",     "💰 บันทึกรายรับ"),
    ("💸", "รายจ่าย",    "💸 บันทึกรายจ่าย"),
    ("🤖", "AI",         "🤖 AI Agent"),
    ("📋", "ข้อมูล",     "📋 ข้อมูลทั้งหมด"),
]
PAGE_KEYS = [p[2] for p in PAGES]

# Desktop sidebar
st.sidebar.title("🍜 Nave 304 Master")
st.sidebar.divider()
page = st.sidebar.radio("เลือกเมนู:", PAGE_KEYS)
st.sidebar.divider()

# Break-even settings
st.session_state.setdefault("be_rent",     4000)
st.session_state.setdefault("be_electric",  800)
st.session_state.setdefault("be_water",     400)
st.session_state.setdefault("be_other",       0)
_exp = st.sidebar.expander("⚙️ ตั้งค่า Break-even/เดือน")
st.session_state["be_rent"]     = _exp.number_input("🏠 ค่าเช่า (฿)",  value=st.session_state["be_rent"],     step=500, min_value=0)
st.session_state["be_electric"] = _exp.number_input("💡 ค่าไฟ (฿)",   value=st.session_state["be_electric"], step=100, min_value=0)
st.session_state["be_water"]    = _exp.number_input("🚿 ค่าน้ำ (฿)",  value=st.session_state["be_water"],    step=100, min_value=0)
st.session_state["be_other"]    = _exp.number_input("📦 อื่นๆ (฿)",   value=st.session_state["be_other"],    step=100, min_value=0)
st.sidebar.divider()
if st.sidebar.button("🔄 รีเฟรชฐานข้อมูล"):
    refresh_all_caches()
    st.rerun()

# Mobile nav — pure HTML anchor horizontal bar
st.session_state.setdefault("mobile_page", None)
_mi = st.session_state.get("mobile_page")
if _mi is not None and 0 <= _mi < len(PAGE_KEYS):
    page = PAGE_KEYS[_mi]

_NAV_CSS = """<style>
@media(max-width:768px){
  section[data-testid="stSidebar"]{display:none!important}
  [data-testid="collapsedControl"]{display:none!important}
  .block-container{padding-top:68px!important}
}
.mnb{
  display:none;
  position:fixed;top:0;left:0;right:0;z-index:9999;
  background:linear-gradient(90deg,#0d3d26,#1a6b4a);
  padding:8px;
  box-shadow:0 2px 10px rgba(0,0,0,.4);
  overflow-x:auto;white-space:nowrap;
  -webkit-overflow-scrolling:touch;scrollbar-width:none;
}
.mnb::-webkit-scrollbar{display:none}
.mnb a{
  display:inline-block;
  color:rgba(255,255,255,.75);
  font-size:13px;font-weight:500;
  padding:5px 14px;margin-right:4px;
  border-radius:20px;
  border:1px solid rgba(255,255,255,.2);
  text-decoration:none;
}
.mnb a.on{
  background:rgba(255,255,255,.22);
  color:#fff;
  border-color:rgba(255,255,255,.4);
}
@media(max-width:768px){.mnb{display:block}}
</style>"""
st.markdown(_NAV_CSS, unsafe_allow_html=True)

_cur = st.session_state.get("mobile_page") or 0
_nav_items = ""
for _i, (_icon, _label, _key) in enumerate(PAGES):
    _cls = "on" if _i == _cur else ""
    _nav_items += f'<a href="?p={_i}" class="{_cls}">{_icon} {_label}</a>'
st.markdown(f'<div class="mnb">{_nav_items}</div>', unsafe_allow_html=True)

_qp = st.query_params
if "p" in _qp:
    try:
        _pi = int(_qp["p"])
        if 0 <= _pi < len(PAGE_KEYS):
            if st.session_state.get("mobile_page") != _pi:
                st.session_state["mobile_page"] = _pi
                st.query_params.clear()
                st.rerun()
            page = PAGE_KEYS[_pi]
    except:
        pass


# ============================================================
# 5. PAGE — DASHBOARD รายวัน
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>ภาพรวมรายรับ-รายจ่าย และ Break-even วันนี้</div>", unsafe_allow_html=True)

    df_i = load_data("Income")
    df_e = load_data("Expense")

    df_i['net_income']  = clean_numeric(df_i, 'net_income')
    df_e['total_price'] = clean_numeric(df_e, 'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc   = df_i['net_income'].sum()
    t_exp   = df_e['total_price'].sum()
    profit  = t_inc - t_exp

    # ── คำนวณ Break-even ──
    fixed_monthly = (
        st.session_state["be_rent"] +
        st.session_state["be_electric"] +
        st.session_state["be_water"] +
        st.session_state["be_other"]
    )
    days_in_month       = 26
    fixed_daily         = fixed_monthly / days_in_month
    food_cost_pct       = (t_exp / t_inc * 100) if t_inc > 0 else 0
    contribution_margin = max(1 - food_cost_pct / 100, 0.01)
    be_daily            = fixed_daily / contribution_margin

    today     = pd.Timestamp.now().normalize()
    today_inc = df_i[df_i['date'] >= today]['net_income'].sum() if not df_i.empty else 0
    passed_be = (today_inc >= be_daily) and (be_daily > 0)
    gap       = be_daily - today_inc

    # ── Banner Break-even ──
    if fixed_monthly > 0:
        if passed_be:
            st.markdown(
                f"<div class='success-card'>✅ <b>ผ่าน Break-even แล้ว!</b> "
                f"วันนี้รายรับ ฿{today_inc:,.0f} — เกินเป้า ฿{be_daily:,.0f} อยู่ "
                f"<b>฿{today_inc - be_daily:,.0f}</b></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='warn-card'>⚠️ <b>ยังไม่ถึง Break-even</b> "
                f"วันนี้รายรับ ฿{today_inc:,.0f} — ต้องขายเพิ่มอีก <b>฿{gap:,.0f}</b> "
                f"(เป้าวันละ ฿{be_daily:,.0f})</div>",
                unsafe_allow_html=True,
            )

    # ── KPI 4 ช่อง ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับรวม",   f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม",  f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น", f"฿{profit:,.0f}",
              delta=f"{profit/t_inc*100:.1f}% margin" if t_inc > 0 else None)
    c4.metric("🎯 Break-even/วัน",
              f"฿{be_daily:,.0f}" if fixed_monthly > 0 else "ตั้งค่าก่อน",
              delta="ผ่านแล้ว ✅" if passed_be else f"ขาดอีก ฿{gap:,.0f}",
              delta_color="normal" if passed_be else "inverse")

    # ── Progress bar ──
    if be_daily > 0:
        pct       = min(today_inc / be_daily, 1.0)
        bar_color = "#22c55e" if passed_be else "#f59e0b"
        st.markdown(
            f"<div style='margin:.5rem 0 1rem'>"
            f"<div style='display:flex;justify-content:space-between;font-size:.78rem;color:#6b7280;margin-bottom:4px'>"
            f"<span>รายรับวันนี้ ฿{today_inc:,.0f}</span><span>เป้า ฿{be_daily:,.0f}</span></div>"
            f"<div style='background:#e5e7eb;border-radius:8px;height:10px;overflow:hidden'>"
            f"<div style='background:{bar_color};width:{pct*100:.1f}%;height:100%;border-radius:8px'></div></div>"
            f"<div style='font-size:.75rem;color:#6b7280;margin-top:2px;text-align:right'>"
            f"{pct*100:.0f}% of break-even</div></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Tabs กราฟ ──
    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 สรุปรายจ่าย", "📈 ราคาวัตถุดิบ"])

    with tab_inc:
        zoom_days = st.radio("ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True,
                             format_func=lambda x: f"{x} วัน", key="z_daily")
        cutoff   = pd.Timestamp.now() - pd.Timedelta(days=zoom_days)
        df_filt  = df_i[df_i['date'] >= cutoff].copy()

        if not df_filt.empty:
            daily_total = df_filt.groupby('date')['net_income'].sum().reset_index()
            daily_total['rolling'] = daily_total['net_income'].rolling(window=7, min_periods=1).mean()

            # สีแต่ละแอป — ชัดเจน แตกต่างกัน
            colors   = {
                'Grab':      '#00b14f',
                'GrabFood':  '#00b14f',
                'Line Man':  '#0094ff',
                'Shopee':    '#f97316',
                'foodpanda': '#e11d74',
                'หน้าร้าน':  '#8b5cf6',
            }
            fallback = ['#06b6d4','#f43f5e','#eab308','#14b8a6','#64748b']
            fb_idx   = 0
            fig      = go.Figure()
            for app in df_filt['app'].unique():
                d = df_filt[df_filt['app'] == app]
                if app not in colors:
                    colors[app] = fallback[fb_idx % len(fallback)]
                    fb_idx += 1
                fig.add_trace(go.Bar(
                    x=d['date'], y=d['net_income'], name=app,
                    marker_color=colors[app], marker_line_width=0, opacity=0.92,
                ))
            fig.add_trace(go.Scatter(
                x=daily_total['date'], y=daily_total['rolling'],
                name='แนวโน้ม (7วัน)', mode='lines',
                line=dict(color='#fbbf24', dash='dot', width=2.5),
            ))
            fig.update_layout(
                barmode='stack', hovermode='x unified',
                title=f"ยอดรายวันย้อนหลัง {zoom_days} วัน",
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(l=0, r=0, t=48, b=0), bargap=0.25,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลรายวันในช่วงนี้")

    with tab_exp:
        if not df_e.empty:
            col_l, col_r = st.columns(2)
            with col_l:
                fig_pie = px.pie(df_e, values='total_price', names='name',
                                 hole=0.42, title="สัดส่วนรายจ่ายสต๊อก")
                fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                                      paper_bgcolor='rgba(0,0,0,0)',
                                      margin=dict(l=0,r=0,t=48,b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_r:
                top = df_e.groupby('name')['total_price'].sum().nlargest(8).reset_index()
                fig_bar = px.bar(top, x='total_price', y='name', orientation='h',
                                 color='total_price', color_continuous_scale='Greens',
                                 title="Top 8 รายจ่าย",
                                 labels={'total_price':'฿','name':''})
                fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)',
                                      paper_bgcolor='rgba(0,0,0,0)',
                                      margin=dict(l=0,r=0,t=48,b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            target   = st.selectbox("เลือกสินค้า:", sorted(df_e['name'].unique()))
            df_item  = df_e[df_e['name'] == target].sort_values('date').copy()
            df_item['u_price'] = df_item['total_price'] / clean_numeric(df_item, 'qty').replace(0, 1)

            if len(df_item) >= 2:
                last, prev = df_item['u_price'].iloc[-1], df_item['u_price'].iloc[-2]
                chg = (last - prev) / prev * 100 if prev > 0 else 0
                ca, cb = st.columns(2)
                ca.metric("ราคาล่าสุด/หน่วย", f"฿{last:.2f}",
                          delta=f"{chg:+.1f}% vs ครั้งก่อน", delta_color="inverse")
                cb.metric("ซื้อทั้งหมด", f"{len(df_item)} ครั้ง",
                          delta=f"รวม ฿{df_item['total_price'].sum():,.0f}")
                if chg >= 10:
                    st.markdown(
                        f"<div class='warn-card'>⚠️ ราคา <b>{target}</b> เพิ่มขึ้น {chg:.1f}% จากครั้งก่อน</div>",
                        unsafe_allow_html=True,
                    )

            fig_l = px.line(df_item, x='date', y='u_price', markers=True,
                            title=f"แนวโน้มราคา {target} ต่อหน่วย",
                            labels={'u_price':'฿/หน่วย'})
            fig_l.update_traces(line_color='#1a6b4a', marker_color='#1a6b4a')
            fig_l.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                                 paper_bgcolor='rgba(0,0,0,0)',
                                 margin=dict(l=0,r=0,t=48,b=0))
            st.plotly_chart(fig_l, use_container_width=True)


# ============================================================
# 6. PAGE — วิเคราะห์รายเดือน (เดิม)
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='page-title'>📈 สรุปยอดและวิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    df_m = load_data("Monthly")

    if not df_m.empty:
        df_m['net_income'] = clean_numeric(df_m, 'net_income')
        df_m['gross']      = clean_numeric(df_m, 'gross')
        df_m['fees']       = clean_numeric(df_m, 'fees')
        df_m['ads']        = clean_numeric(df_m, 'ads')

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 ยอดโอนสุทธิรายเดือน", f"฿{df_m['net_income'].sum():,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)",    f"฿{df_m['gross'].sum():,.0f}")
        m3.metric("📉 ค่า GP/โฆษณารวม",      f"฿{df_m['fees'].sum() + df_m['ads'].sum():,.0f}")

        st.divider()

        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.subheader("เปรียบเทียบยอดขาย vs เงินโอนจริง")
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['gross'],
                                   name='ยอดขายรวม (Gross)', marker_color='#93c5fd'))
            fig_m.add_trace(go.Bar(x=df_m['month_year'], y=df_m['net_income'],
                                   name='เงินโอนสุทธิ (Net)', marker_color='#1a6b4a'))
            fig_m.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0,r=0,t=10,b=0),
            )
            st.plotly_chart(fig_m, use_container_width=True)

        with col_m2:
            st.subheader("สัดส่วนค่าธรรมเนียมแอป")
            fig_pie_m = px.pie(df_m, values='fees', names='platform', title="ค่า GP แยกตามแอป")
            fig_pie_m.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    margin=dict(l=0,r=0,t=48,b=0))
            st.plotly_chart(fig_pie_m, use_container_width=True)

        st.subheader("📋 ตารางสรุปยอดละเอียดรายเดือน")
        df_m['cost_pct'] = ((df_m['fees'] + df_m['ads']) / df_m['gross'].replace(0, pd.NA) * 100).round(2)
        st.dataframe(
            df_m[['month_year','platform','gross','fees','ads','net_income','cost_pct']]
            .sort_values('month_year', ascending=False),
            use_container_width=True,
        )
    else:
        st.info("ยังไม่มีข้อมูลในแท็บ Monthly กรุณาบันทึกรายงานสรุปรายเดือนก่อน")


# ============================================================
# 7. PAGE — บันทึกรายรับ (เดิม)
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)

    rtype  = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"], horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"], horizontal=True)
    res    = None

    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:", height=140,
                           placeholder="วางข้อความจากแอป หรือพิมพ์รายละเอียด...")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI", type="primary"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                res = process_extraction(txt, rtype)

    elif method == "🎙️ บันทึกเสียง":
        st.markdown("<div class='info-card'>🎙️ กดปุ่มไมค์แล้วพูด เช่น Grab วันนี้ 1,500 บาท</div>",
                    unsafe_allow_html=True)
        audio = st.audio_input("กดพูดรายการรายรับ...")
        if audio:
            st.audio(audio)
            if st.button("🚀 แปลงเสียงเป็นข้อมูล", type="primary"):
                with st.spinner("AI กำลังแปลง..."):
                    res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)

    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=['pdf','jpg','png'])
        if file and st.button("🪄 วิเคราะห์ไฟล์", type="primary"):
            with st.spinner("AI กำลังอ่านไฟล์..."):
                res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)

    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
        st.success(f"✅ AI สกัดได้ {len(res)} รายการ")

    if 'tmp_inc' in st.session_state:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบและแก้ไขก่อนบันทึก</div>",
                    unsafe_allow_html=True)
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True,
                                num_rows="dynamic")
        ca, cb = st.columns([1, 5])
        with ca:
            if st.button("💾 บันทึกลงฐานข้อมูล", type="primary"):
                target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
                with st.spinner("กำลังบันทึก..."):
                    if save_to_tab(edited, target_tab):
                        del st.session_state.tmp_inc
                        st.success("✅ บันทึกสำเร็จ!")
                        st.rerun()
        with cb:
            if st.button("🗑️ ล้างข้อมูล"):
                del st.session_state.tmp_inc
                st.rerun()


# ============================================================
# 8. PAGE — บันทึกรายจ่าย (เดิม)
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='page-title'>💸 บันทึกรายจ่ายวัตถุดิบ</div>", unsafe_allow_html=True)

    method = st.radio("เลือกวิธี:",
                      ["📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง"],
                      horizontal=True)
    res_ex = None

    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img = (st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด"
               else st.file_uploader("เลือกรูป", type=['jpg','png','jpeg']))
        if img:
            if sub == "📁 เลือกไฟล์":
                st.image(img, caption="รูปที่เลือก", use_container_width=True)
            if st.button("🪄 วิเคราะห์บิล", type="primary"):
                with st.spinner("AI กำลังอ่านบิล..."):
                    res_ex = process_extraction(
                        Image.open(img) if sub == "📷 ถ่ายรูปสด" else img.read(),
                        "Expense",
                        is_bytes=(sub == "📁 เลือกไฟล์"),
                        mime="image/jpeg",
                    )

    elif method == "🎙️ บันทึกด้วยเสียง":
        st.markdown(
            "<div class='info-card'>🎙️ พูดรายการ เช่น ไก่ 5 กิโล 400 บาท หัวหอม 1 กิโล 30 บาท</div>",
            unsafe_allow_html=True,
        )
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex:
            st.audio(audio_ex)
            if st.button("🚀 แปลงเสียง", type="primary"):
                with st.spinner("AI กำลังแปลง..."):
                    res_ex = process_extraction(audio_ex.read(), "Expense",
                                                is_bytes=True, mime=audio_ex.type)

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
        st.success(f"✅ AI สกัดได้ {len(res_ex)} รายการ")

    if 'tmp_exp' in st.session_state:
        st.markdown("<div class='section-title'>✏️ ตรวจสอบและแก้ไขก่อนบันทึก</div>",
                    unsafe_allow_html=True)
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True,
                                   num_rows="dynamic")
        ca, cb = st.columns([1, 5])
        with ca:
            if st.button("💾 บันทึกลงแท็บ Expense", type="primary"):
                with st.spinner("กำลังบันทึก..."):
                    if save_to_tab(edited_ex, "Expense"):
                        del st.session_state.tmp_exp
                        st.success("✅ บันทึกสำเร็จ!")
                        st.rerun()
        with cb:
            if st.button("🗑️ ล้างข้อมูล"):
                del st.session_state.tmp_exp
                st.rerun()


# ============================================================
# 9. PAGE — AI Agent (เดิม)
# ============================================================
elif page == "🤖 AI Agent":
    st.markdown("<div class='page-title'>🤖 AI ที่ปรึกษาธุรกิจ</div>", unsafe_allow_html=True)

    if "ai_msgs" not in st.session_state:
        st.session_state.ai_msgs = []

    # Quick prompts
    st.markdown("**💡 กดถามได้เลย:**")
    qc = st.columns(3)
    qs = [
        "สรุปภาพรวมธุรกิจให้หน่อย",
        "แอปไหนให้ยอดดีที่สุด?",
        "วัตถุดิบไหนราคาพุ่งมากสุด?",
        "ควรปรับราคาเมนูไหมตอนนี้?",
        "เดือนไหนรายรับสูงสุด?",
        "ต้นทุนที่ควรลดคืออะไร?",
    ]
    for i, q in enumerate(qs):
        with qc[i % 3]:
            if st.button(q, key=f"qb_{i}"):
                st.session_state.ai_pending = q

    st.divider()

    for msg in st.session_state.ai_msgs:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_q = st.chat_input("ปรึกษาเรื่องธุรกิจ...")
    if "ai_pending" in st.session_state:
        user_q = st.session_state.pop("ai_pending")

    if user_q and client:
        st.session_state.ai_msgs.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.write(user_q)

        df_i = load_data("Income")
        df_e = load_data("Expense")
        df_m = load_data("Monthly")
        ctx  = f"Income Daily: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}"

        with st.chat_message("assistant"):
            with st.spinner("กำลังวิเคราะห์..."):
                reply = call_gemini_3_1(
                    f"วิเคราะห์ข้อมูลร้านเนฟ หมี่ไก่ฉีก:\n{ctx}\nคำถาม: {user_q}"
                )
                if reply:
                    st.write(reply)
                    st.session_state.ai_msgs.append({"role": "assistant", "content": reply})

    if st.session_state.ai_msgs and st.button("🗑️ ล้างประวัติ"):
        st.session_state.ai_msgs = []
        st.rerun()


# ============================================================
# 10. PAGE — ข้อมูลทั้งหมด (เดิม)
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='page-title'>📋 ข้อมูลแยกแท็บ</div>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["📥 Income (รายวัน)", "📊 Monthly (รายเดือน)", "📤 Expense (รายจ่าย)"])
    with t1:
        df = load_data("Income")
        st.caption(f"{len(df)} แถว")
        st.dataframe(df, use_container_width=True)
    with t2:
        df = load_data("Monthly")
        st.caption(f"{len(df)} แถว")
        st.dataframe(df, use_container_width=True)
    with t3:
        df = load_data("Expense")
        st.caption(f"{len(df)} แถว")
        st.dataframe(df, use_container_width=True)

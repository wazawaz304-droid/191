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
# 1. PAGE CONFIG & GLOBAL CSS
# ============================================================
st.set_page_config(
    page_title="Nave 304 · AI Business Master",
    layout="wide",
    page_icon="🍜",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Thai', sans-serif !important;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1400px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f4c2e 0%, #1a6b4a 100%);
    border-right: none;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.9) !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 0.45rem 0.8rem;
    border-radius: 8px;
    display: block;
    transition: background 0.15s;
    font-size: 0.875rem;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.12); }
[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div + label,
[data-testid="stSidebar"] .stRadio [aria-checked="true"] ~ label {
    background: rgba(255,255,255,0.18) !important;
    border-left: 3px solid #fff;
}
[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: #fff !important;
    width: 100%;
    border-radius: 8px;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stButton button:hover { background: rgba(255,255,255,0.25); }

/* ── KPI metric cards ── */
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #6b7280 !important; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 600; color: #111827; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── Tab bar ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f3f4f6;
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.85rem;
    color: #6b7280;
    padding: 0.4rem 1rem;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #111827 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px;
    font-weight: 500;
    font-size: 0.875rem;
    transition: all 0.15s;
    border: 1.5px solid transparent;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1a6b4a, #2e8b62);
    color: white;
    border-color: transparent;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0,0,0,0.15); }

/* ── Alert / Info boxes ── */
.nave-alert-danger {
    background: #fef2f2; border-left: 4px solid #ef4444;
    border-radius: 10px; padding: 0.75rem 1rem;
    font-size: 0.875rem; color: #991b1b; margin-bottom: 0.75rem;
}
.nave-alert-warn {
    background: #fffbeb; border-left: 4px solid #f59e0b;
    border-radius: 10px; padding: 0.75rem 1rem;
    font-size: 0.875rem; color: #92400e; margin-bottom: 0.75rem;
}
.nave-alert-success {
    background: #f0fdf4; border-left: 4px solid #22c55e;
    border-radius: 10px; padding: 0.75rem 1rem;
    font-size: 0.875rem; color: #166534; margin-bottom: 0.75rem;
}
.nave-alert-info {
    background: #eff6ff; border-left: 4px solid #3b82f6;
    border-radius: 10px; padding: 0.75rem 1rem;
    font-size: 0.875rem; color: #1e40af; margin-bottom: 0.75rem;
}

/* ── Section header ── */
.section-header {
    font-size: 1.05rem; font-weight: 600; color: #111827;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #e5e7eb;
}

/* ── Food cost meter ── */
.fc-meter-wrap { margin: 0.5rem 0; }
.fc-meter-bar {
    height: 10px; border-radius: 5px;
    background: #e5e7eb; overflow: hidden; margin: 4px 0;
}
.fc-meter-fill { height: 100%; border-radius: 5px; transition: width 0.6s ease; }

/* ── Breakeven card ── */
.be-card {
    background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: 1rem 1.25rem;
}
.be-row {
    display: flex; justify-content: space-between;
    padding: 0.35rem 0; border-bottom: 1px solid #e5e7eb;
    font-size: 0.875rem;
}
.be-row:last-child { border-bottom: none; font-weight: 600; }
.be-label { color: #6b7280; }
.be-value { color: #111827; }

/* ── Page title ── */
.page-title {
    font-size: 1.5rem; font-weight: 700; color: #111827;
    margin-bottom: 0.25rem;
}
.page-subtitle { font-size: 0.875rem; color: #6b7280; margin-bottom: 1.25rem; }

/* ── Mobile responsiveness ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. CONNECTIONS & CACHE
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

@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None:
        return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================
def clean_numeric(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',', '').str.replace('฿', ''),
            errors='coerce'
        ).fillna(0)
    return pd.Series([0] * len(df))

def safe_parse_json(text_response: str):
    if not text_response:
        return []
    try:
        content = text_response.strip()
        if "```" in content:
            content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        return json.loads(content.strip())
    except:
        return []

def call_gemini(prompt, contents=None, is_complex_content=False):
    if client is None:
        return None
    model_name = "models/gemini-2.0-flash"
    try:
        if is_complex_content:
            response = client.models.generate_content(model=model_name, contents=contents)
        else:
            input_parts = [prompt] + contents if contents else [prompt]
            response = client.models.generate_content(model=model_name, contents=input_parts)
        if response.text:
            return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def process_extraction(data, p_type, is_bytes=False, mime=None):
    now_str = datetime.now().strftime("%Y-%m-%d")
    prompts = {
        "Expense": f"สกัดสินค้าเป็น JSON: [{{'date': '{now_str}', 'name': 'สินค้า', 'qty': 1, 'unit': 'หน่วย', 'total_price': 0}}] หากบิลไม่ระบุวันที่ให้ใช้ {now_str}",
        "หน้าร้าน": f"สกัดยอดหน้าร้านจากข้อความหรือเสียง: [{{'date': '{now_str}', 'app': 'หน้าร้าน', 'net_income': ยอดขาย, 'order_count': 0}}] วันนี้คือ {now_str}",
        "สรุปรายเดือน": "สกัดรายงานรายเดือนเป็น JSON: [{'month_year': 'YYYY-MM', 'platform': 'แอป', 'gross': 0, 'fees': 0, 'ads': 0, 'discounts': 0, 'net_income': 0}]",
        "Labor": f"สกัดข้อมูลค่าแรงพนักงานเป็น JSON: [{{'date': '{now_str}', 'name': 'ชื่อพนักงาน', 'role': 'ตำแหน่ง', 'amount': 0, 'note': ''}}] วันนี้คือ {now_str}",
    }
    p = prompts.get(p_type, f"สกัดรายได้เดลิเวอรี่รายวันเป็น JSON: [{{'date': '{now_str}', 'app': 'ชื่อแอป', 'net_income': ยอดโอน, 'order_count': 0}}] วันนี้คือ {now_str}")
    prompt = p + " ตอบเฉพาะ PURE JSON เท่านั้น"
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data, mime_type=mime)
        ])]
        res = call_gemini(prompt, contents=contents, is_complex_content=True)
    else:
        res = call_gemini(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty:
        return False
    try:
        col_map = {
            "Income":   {"type": "Income",   "default_app": "หน้าร้าน"},
            "Expense":  {"type": "Expense"},
            "Monthly":  {"type": "Monthly"},
            "Labor":    {"type": "Labor"},
        }
        df["type"] = col_map[tab]["type"]
        if tab == "Income" and "app" not in df.columns:
            df["app"] = col_map[tab]["default_app"]
        if tab == "Income" and "order_count" not in df.columns:
            df["order_count"] = 0
        if "net" in df.columns:
            df.rename(columns={"net": "net_income"}, inplace=True)

        existing = load_data(tab)
        final = pd.concat([existing, df], ignore_index=True)
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

def alert_html(msg, level="info"):
    cls = f"nave-alert-{level}"
    icons = {"danger": "🚨", "warn": "⚠️", "success": "✅", "info": "ℹ️"}
    return f'<div class="{cls}">{icons.get(level,"ℹ️")} {msg}</div>'

def food_cost_color(pct):
    if pct < 28:   return "#22c55e"   # เขียว
    if pct < 35:   return "#f59e0b"   # เหลือง
    return "#ef4444"                   # แดง

def render_food_cost_meter(pct):
    color = food_cost_color(pct)
    width = min(pct * 2, 100)   # scale: 50% → full bar
    zone = "ดีมาก ✅" if pct < 28 else ("ปกติ ⚠️" if pct < 35 else "อันตราย 🚨")
    st.markdown(f"""
    <div class='fc-meter-wrap'>
      <div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#6b7280;margin-bottom:2px'>
        <span>Food Cost %</span><span style='color:{color};font-weight:600'>{pct:.1f}% — {zone}</span>
      </div>
      <div class='fc-meter-bar'>
        <div class='fc-meter-fill' style='width:{width}%;background:{color}'></div>
      </div>
      <div style='display:flex;justify-content:space-between;font-size:0.7rem;color:#9ca3af'>
        <span>0%</span><span style='color:#22c55e'>28%</span><span style='color:#f59e0b'>35%</span><span>50%+</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 4. SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("### 🍜 Nave 304")
    st.markdown("<small style='opacity:0.7'>AI Business Master</small>", unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "เมนู",
        [
            "📊 Dashboard รายวัน",
            "📈 วิเคราะห์รายเดือน",
            "💰 บันทึกรายรับ",
            "💸 บันทึกรายจ่าย",
            "👷 ค่าแรงพนักงาน",
            "🤖 AI Agent",
            "📋 ข้อมูลทั้งหมด",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # ── ตัวตั้งค่าต้นทุนคงที่ (สำหรับ Break-even) ──
    with st.expander("⚙️ ตั้งค่าต้นทุนคงที่/วัน"):
        rent_day    = st.number_input("ค่าเช่า/วัน (฿)", value=667, step=50)
        utility_day = st.number_input("ค่าน้ำ+ไฟ/วัน (฿)", value=200, step=50)
        pkg_pct     = st.number_input("แพ็คเกจจิ้ง (% ของรายรับ)", value=2.0, step=0.5, format="%.1f")
        target_fc   = st.number_input("เป้า Food Cost สูงสุด (%)", value=35.0, step=1.0, format="%.1f")

    st.divider()
    if st.button("🔄 รีเฟรชข้อมูล"):
        refresh_all_caches()
        st.rerun()


# ============================================================
# 5. PAGE — DASHBOARD รายวัน
# ============================================================
if page == "📊 Dashboard รายวัน":

    st.markdown("<div class='page-title'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>ภาพรวมรายรับ-รายจ่าย และตัวชี้วัดสำคัญวันนี้</div>", unsafe_allow_html=True)

    df_i = load_data("Income")
    df_e = load_data("Expense")
    df_l = load_data("Labor")

    df_i["net_income"]   = clean_numeric(df_i, "net_income")
    df_i["order_count"]  = clean_numeric(df_i, "order_count")
    df_e["total_price"]  = clean_numeric(df_e, "total_price")
    df_l["amount"]       = clean_numeric(df_l, "amount") if not df_l.empty else pd.Series(dtype=float)

    df_i["date"] = pd.to_datetime(df_i["date"], errors="coerce")
    df_e["date"] = pd.to_datetime(df_e["date"], errors="coerce")

    t_inc    = df_i["net_income"].sum()
    t_exp    = df_e["total_price"].sum()
    t_labor  = df_l["amount"].sum() if not df_l.empty else 0
    t_orders = df_i["order_count"].sum()
    aov      = t_inc / t_orders if t_orders > 0 else 0
    food_pct = (t_exp / t_inc * 100) if t_inc > 0 else 0
    pkg_cost = t_inc * pkg_pct / 100
    fixed    = rent_day + utility_day
    net_profit = t_inc - t_exp - t_labor - pkg_cost - fixed

    # ── ระบบแจ้งเตือนอัตโนมัติ ──
    alerts_html = ""

    # เตือน food cost
    if food_pct > target_fc:
        alerts_html += alert_html(
            f"Food Cost สูงถึง <b>{food_pct:.1f}%</b> — เกินเป้าหมาย {target_fc:.0f}% กรุณาตรวจสอบต้นทุนวัตถุดิบ",
            "danger"
        )
    elif food_pct > target_fc * 0.85:
        alerts_html += alert_html(
            f"Food Cost อยู่ที่ {food_pct:.1f}% — ใกล้เป้าหมาย {target_fc:.0f}% ควรระมัดระวัง",
            "warn"
        )

    # เตือนราคาวัตถุดิบพุ่ง
    if not df_e.empty and "name" in df_e.columns:
        df_e_sorted = df_e.sort_values("date")
        for item in df_e_sorted["name"].unique():
            rows = df_e_sorted[df_e_sorted["name"] == item].copy()
            if len(rows) >= 2:
                rows["u_price"] = rows["total_price"] / clean_numeric(rows, "qty").replace(0, 1)
                last2 = rows["u_price"].iloc[-2:]
                if last2.iloc[0] > 0:
                    chg = (last2.iloc[1] - last2.iloc[0]) / last2.iloc[0] * 100
                    if chg >= 10:
                        alerts_html += alert_html(
                            f"ราคา <b>{item}</b> เพิ่มขึ้น <b>{chg:.1f}%</b> จากการซื้อครั้งล่าสุด",
                            "warn"
                        )

    # เตือนไม่มีข้อมูลค่าแรง
    if df_l.empty or t_labor == 0:
        alerts_html += alert_html(
            "ยังไม่มีข้อมูลค่าแรงพนักงาน — กำไรสุทธิที่แสดงอาจสูงกว่าความเป็นจริง",
            "warn"
        )

    # ยอดดี
    if t_inc > 0 and t_inc > (rent_day + utility_day) / (1 - food_pct / 100 - pkg_pct / 100):
        alerts_html += alert_html("ผ่าน Break-even แล้ว 🎉 วันนี้กำลังทำกำไร!", "success")

    if alerts_html:
        st.markdown(alerts_html, unsafe_allow_html=True)

    # ── KPI Cards ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 รายรับรวม",        f"฿{t_inc:,.0f}")
    c2.metric("📦 ต้นทุนวัตถุดิบ",    f"฿{t_exp:,.0f}",
              delta=f"Food Cost {food_pct:.1f}%",
              delta_color="inverse" if food_pct > target_fc else "off")
    c3.metric("👷 ค่าแรงพนักงาน",    f"฿{t_labor:,.0f}")
    c4.metric("📋 จำนวนออเดอร์",     f"{t_orders:,.0f} รายการ",
              delta=f"เฉลี่ย ฿{aov:.0f}/ออเดอร์" if t_orders > 0 else "ยังไม่มีข้อมูล")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("💎 กำไรสุทธิ (Net)",    f"฿{net_profit:,.0f}",
              delta=f"{net_profit/t_inc*100:.1f}% margin" if t_inc > 0 else "N/A")
    c6.metric("🏠 ต้นทุนคงที่/วัน",    f"฿{fixed:,.0f}")
    c7.metric("📦 แพ็คเกจจิ้ง",       f"฿{pkg_cost:,.0f}")
    c8.metric("🎯 Break-even วันนี้",
              f"฿{(fixed + t_labor) / max(1 - food_pct/100 - pkg_pct/100, 0.01):,.0f}")

    st.divider()

    # ── Food Cost Meter ──
    render_food_cost_meter(food_pct)

    st.divider()

    # ── Charts ──
    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ", "🛒 รายจ่ายวัตถุดิบ", "📈 ราคาวัตถุดิบ"])

    with tab_inc:
        zoom_days = st.radio(
            "ดูย้อนหลัง:", [7, 30, 60, 90], horizontal=True,
            format_func=lambda x: f"{x} วัน", key="z_daily"
        )
        cutoff   = pd.Timestamp.now() - pd.Timedelta(days=zoom_days)
        df_filt  = df_i[df_i["date"] >= cutoff].copy()

        if not df_filt.empty:
            daily_total = df_filt.groupby("date")["net_income"].sum().reset_index()
            daily_total["rolling"] = daily_total["net_income"].rolling(window=7, min_periods=1).mean()

            fig = go.Figure()
            color_map = {"Grab": "#00b14f", "Line Man": "#00c300", "Shopee": "#ee4d2d",
                         "foodpanda": "#d70f64", "หน้าร้าน": "#1a6b4a"}
            for app in df_filt["app"].unique():
                d = df_filt[df_filt["app"] == app]
                fig.add_trace(go.Bar(
                    x=d["date"], y=d["net_income"],
                    name=app,
                    marker_color=color_map.get(app, "#6366f1"),
                ))
            fig.add_trace(go.Scatter(
                x=daily_total["date"], y=daily_total["rolling"],
                name="แนวโน้ม (7 วัน)", mode="lines",
                line=dict(color="#f59e0b", dash="dot", width=2)
            ))
            fig.update_layout(
                barmode="stack", hovermode="x unified",
                title=f"ยอดรายวันย้อนหลัง {zoom_days} วัน",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── AOV chart ──
            if "order_count" in df_filt.columns:
                df_aov = df_filt.groupby("date").agg(
                    net_income=("net_income", "sum"),
                    order_count=("order_count", "sum")
                ).reset_index()
                df_aov["aov"] = df_aov["net_income"] / df_aov["order_count"].replace(0, pd.NA)
                fig_aov = px.line(df_aov.dropna(subset=["aov"]), x="date", y="aov",
                                  markers=True, title="ยอดเฉลี่ยต่อออเดอร์ (AOV) รายวัน",
                                  labels={"aov": "฿/ออเดอร์"})
                fig_aov.update_traces(line_color="#6366f1")
                fig_aov.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                      margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_aov, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลรายวันในช่วงนี้")

    with tab_exp:
        if not df_e.empty:
            col_pie, col_bar = st.columns([1, 1])
            with col_pie:
                fig_pie = px.pie(df_e, values="total_price", names="name",
                                 hole=0.45, title="สัดส่วนรายจ่ายวัตถุดิบ")
                fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                      margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_bar:
                top10 = df_e.groupby("name")["total_price"].sum().nlargest(10).reset_index()
                fig_bar = px.bar(top10, x="total_price", y="name", orientation="h",
                                 title="Top 10 รายจ่ายวัตถุดิบ",
                                 color="total_price", color_continuous_scale="Greens",
                                 labels={"total_price": "฿", "name": ""})
                fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                      showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab_price:
        if not df_e.empty and "name" in df_e.columns:
            target_item = st.selectbox("เลือกสินค้า:", sorted(df_e["name"].unique()))
            df_item = df_e[df_e["name"] == target_item].sort_values("date").copy()
            df_item["u_price"] = df_item["total_price"] / clean_numeric(df_item, "qty").replace(0, 1)

            if len(df_item) >= 2:
                last_price = df_item["u_price"].iloc[-1]
                prev_price = df_item["u_price"].iloc[-2]
                chg_pct    = (last_price - prev_price) / prev_price * 100 if prev_price > 0 else 0
                c_p, c_c   = st.columns(2)
                c_p.metric("ราคาล่าสุด/หน่วย", f"฿{last_price:.2f}", delta=f"{chg_pct:+.1f}% vs ครั้งก่อน",
                            delta_color="inverse")
                c_c.metric("ซื้อมาแล้ว", f"{len(df_item)} ครั้ง",
                            delta=f"รวม ฿{df_item['total_price'].sum():,.0f}")

                if chg_pct >= 10:
                    st.markdown(alert_html(f"ราคา {target_item} เพิ่มขึ้น {chg_pct:.1f}% — ควรทบทวนสูตรหรือซัพพลายเออร์", "danger"),
                                unsafe_allow_html=True)

            fig_line = px.line(df_item, x="date", y="u_price", markers=True,
                               title=f"แนวโน้มราคา {target_item} ต่อหน่วย",
                               labels={"u_price": "฿/หน่วย"})
            fig_line.update_traces(line_color="#1a6b4a", marker_color="#1a6b4a")
            fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_line, use_container_width=True)


# ============================================================
# 6. PAGE — วิเคราะห์รายเดือน
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":

    st.markdown("<div class='page-title'>📈 วิเคราะห์รายเดือน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>เปรียบเทียบ Gross vs Net · ค่า GP · แนวโน้มรายเดือน</div>", unsafe_allow_html=True)

    df_m = load_data("Monthly")
    df_e = load_data("Expense")
    df_l = load_data("Labor")

    if not df_m.empty:
        for col in ["net_income", "gross", "fees", "ads", "discounts"]:
            df_m[col] = clean_numeric(df_m, col)

        total_net   = df_m["net_income"].sum()
        total_gross = df_m["gross"].sum()
        total_fees  = df_m["fees"].sum()
        total_ads   = df_m["ads"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 ยอดโอนสุทธิรวม",    f"฿{total_net:,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{total_gross:,.0f}")
        m3.metric("📉 ค่า GP รวม",         f"฿{total_fees:,.0f}")
        m4.metric("📣 ค่าโฆษณารวม",        f"฿{total_ads:,.0f}")

        st.divider()

        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=df_m["month_year"], y=df_m["gross"], name="ยอดขายรวม (Gross)", marker_color="#93c5fd"))
            fig_m.add_trace(go.Bar(x=df_m["month_year"], y=df_m["net_income"], name="เงินโอนสุทธิ (Net)", marker_color="#1a6b4a"))
            fig_m.update_layout(barmode="group", title="Gross vs Net รายเดือน",
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig_m, use_container_width=True)

        with col_m2:
            if total_fees > 0:
                fig_pie_m = px.pie(df_m, values="fees", names="platform",
                                   title="ค่า GP แยกตามแอป", hole=0.4)
                fig_pie_m.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                        margin=dict(l=0, r=0, t=50, b=0))
                st.plotly_chart(fig_pie_m, use_container_width=True)

        # ตาราง + cost %
        st.markdown("<div class='section-header'>📋 ตารางสรุปรายเดือน</div>", unsafe_allow_html=True)
        df_m["cost_pct"] = ((df_m["fees"] + df_m["ads"]) / df_m["gross"].replace(0, pd.NA) * 100).round(2)
        df_m["net_margin_pct"] = (df_m["net_income"] / df_m["gross"].replace(0, pd.NA) * 100).round(2)
        st.dataframe(
            df_m[["month_year", "platform", "gross", "fees", "ads", "discounts", "net_income", "cost_pct", "net_margin_pct"]]
            .sort_values("month_year", ascending=False),
            use_container_width=True,
            column_config={
                "month_year":       "เดือน",
                "platform":         "แอป",
                "gross":            st.column_config.NumberColumn("Gross (฿)", format="฿%.0f"),
                "fees":             st.column_config.NumberColumn("GP (฿)", format="฿%.0f"),
                "ads":              st.column_config.NumberColumn("โฆษณา (฿)", format="฿%.0f"),
                "discounts":        st.column_config.NumberColumn("ส่วนลด (฿)", format="฿%.0f"),
                "net_income":       st.column_config.NumberColumn("Net (฿)", format="฿%.0f"),
                "cost_pct":         st.column_config.NumberColumn("% ต้นทุน", format="%.1f%%"),
                "net_margin_pct":   st.column_config.NumberColumn("% Net Margin", format="%.1f%%"),
            }
        )
    else:
        st.info("ยังไม่มีข้อมูลในแท็บ Monthly กรุณาบันทึกรายงานสรุปรายเดือนก่อน")


# ============================================================
# 7. PAGE — บันทึกรายรับ
# ============================================================
elif page == "💰 บันทึกรายรับ":

    st.markdown("<div class='page-title'>💰 บันทึกรายรับ</div>", unsafe_allow_html=True)

    rtype = st.radio("ประเภท:", ["รายวันเดลิเวอรี่", "สรุปรายเดือน", "หน้าร้าน"],
                     horizontal=True)
    method = st.radio("วิธีบันทึก:", ["⌨️ พิมพ์/วางข้อความ", "🎙️ บันทึกเสียง", "📁 อัปโหลดไฟล์"],
                      horizontal=True)
    res = None

    if method == "⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล (วางข้อความจากแอป หรือพิมพ์รายละเอียด):", height=150)
        if txt and st.button("🪄 วิเคราะห์ด้วย AI", type="primary"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                res = process_extraction(txt, rtype)

    elif method == "🎙️ บันทึกเสียง":
        audio = st.audio_input("กดพูดรายการรายรับ...")
        if audio and st.button("🚀 แปลงเสียงเป็นข้อมูล", type="primary"):
            with st.spinner("AI กำลังแปลงเสียง..."):
                res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)

    else:
        file = st.file_uploader("เลือกไฟล์รายงาน", type=["pdf", "jpg", "png", "jpeg"])
        if file and st.button("🪄 วิเคราะห์ไฟล์", type="primary"):
            with st.spinner("AI กำลังอ่านไฟล์..."):
                res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)

    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
        st.success(f"✅ AI พบข้อมูล {len(res)} รายการ")

    if "tmp_inc" in st.session_state:
        st.markdown("<div class='section-header'>✏️ ตรวจสอบและแก้ไขก่อนบันทึก</div>", unsafe_allow_html=True)
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True,
                                num_rows="dynamic")
        col_save, col_clear = st.columns([1, 4])
        with col_save:
            if st.button("💾 บันทึกลงฐานข้อมูล", type="primary"):
                target_tab = "Monthly" if rtype == "สรุปรายเดือน" else "Income"
                with st.spinner("กำลังบันทึก..."):
                    if save_to_tab(edited.copy(), target_tab):
                        del st.session_state.tmp_inc
                        st.success("✅ บันทึกสำเร็จ!")
                        st.rerun()
        with col_clear:
            if st.button("🗑️ ล้างข้อมูล"):
                del st.session_state.tmp_inc
                st.rerun()


# ============================================================
# 8. PAGE — บันทึกรายจ่าย
# ============================================================
elif page == "💸 บันทึกรายจ่าย":

    st.markdown("<div class='page-title'>💸 บันทึกรายจ่ายวัตถุดิบ</div>", unsafe_allow_html=True)

    method = st.radio("เลือกวิธี:", ["📸 แสกนบิล/อัปโหลดรูป", "🎙️ บันทึกด้วยเสียง", "⌨️ พิมพ์เอง"],
                      horizontal=True)
    res_ex = None

    if method == "📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:", ["📷 ถ่ายรูปสด", "📁 เลือกไฟล์"], horizontal=True)
        img_src = st.camera_input("สแกนบิล") if sub == "📷 ถ่ายรูปสด" \
                  else st.file_uploader("เลือกรูป", type=["jpg", "png", "jpeg", "webp"])
        if img_src and st.button("🪄 วิเคราะห์บิล", type="primary"):
            with st.spinner("AI กำลังอ่านบิล..."):
                if sub == "📷 ถ่ายรูปสด":
                    res_ex = process_extraction(img_src.read(), "Expense", is_bytes=True, mime="image/jpeg")
                else:
                    res_ex = process_extraction(img_src.read(), "Expense", is_bytes=True, mime=img_src.type)

    elif method == "🎙️ บันทึกด้วยเสียง":
        audio_ex = st.audio_input("พูดรายการรายจ่าย...")
        if audio_ex and st.button("🚀 แปลงเสียง", type="primary"):
            with st.spinner("AI กำลังแปลงเสียง..."):
                res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type)

    else:
        with st.form("manual_expense"):
            col_a, col_b, col_c, col_d = st.columns(4)
            e_date  = col_a.date_input("วันที่", value=datetime.now())
            e_name  = col_b.text_input("ชื่อสินค้า")
            e_qty   = col_c.number_input("จำนวน", min_value=0.0, step=0.5)
            e_unit  = col_d.text_input("หน่วย", value="กก.")
            e_price = st.number_input("ราคารวม (฿)", min_value=0.0, step=1.0)
            if st.form_submit_button("➕ เพิ่มรายการ", type="primary"):
                res_ex = [{"date": str(e_date), "name": e_name, "qty": e_qty,
                           "unit": e_unit, "total_price": e_price}]

    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
        st.success(f"✅ พบ {len(res_ex)} รายการ")

    if "tmp_exp" in st.session_state:
        st.markdown("<div class='section-header'>✏️ ตรวจสอบก่อนบันทึก</div>", unsafe_allow_html=True)
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True,
                                   num_rows="dynamic")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 บันทึก", type="primary"):
                with st.spinner("กำลังบันทึก..."):
                    if save_to_tab(edited_ex.copy(), "Expense"):
                        del st.session_state.tmp_exp
                        st.success("✅ บันทึกสำเร็จ!")
                        st.rerun()
        with c2:
            if st.button("🗑️ ล้าง"):
                del st.session_state.tmp_exp
                st.rerun()


# ============================================================
# 9. PAGE — ค่าแรงพนักงาน (ใหม่!)
# ============================================================
elif page == "👷 ค่าแรงพนักงาน":

    st.markdown("<div class='page-title'>👷 บันทึกค่าแรงพนักงาน</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>บันทึกค่าจ้าง เงินเดือน โอที เพื่อคำนวณต้นทุนที่แท้จริง</div>", unsafe_allow_html=True)

    df_l = load_data("Labor")
    if not df_l.empty:
        df_l["amount"] = clean_numeric(df_l, "amount")
        t_labor = df_l["amount"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("💵 ค่าแรงรวมทั้งหมด", f"฿{t_labor:,.0f}")
        if "name" in df_l.columns:
            c2.metric("👥 จำนวนพนักงาน", f"{df_l['name'].nunique()} คน")
        if "role" in df_l.columns:
            c3.metric("📋 จำนวนตำแหน่ง", f"{df_l['role'].nunique()} ตำแหน่ง")

        st.divider()
        if "name" in df_l.columns and "amount" in df_l.columns:
            by_person = df_l.groupby("name")["amount"].sum().reset_index()
            fig_labor = px.bar(by_person, x="name", y="amount",
                               title="ค่าแรงแยกตามพนักงาน",
                               color="amount", color_continuous_scale="Greens",
                               labels={"amount": "฿", "name": "พนักงาน"})
            fig_labor.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                    showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_labor, use_container_width=True)
        st.divider()

    st.markdown("<div class='section-header'>➕ บันทึกค่าแรงใหม่</div>", unsafe_allow_html=True)

    method_l = st.radio("วิธีบันทึก:", ["📝 กรอกแบบฟอร์ม", "🎙️ บันทึกเสียง", "⌨️ พิมพ์ข้อความ"],
                        horizontal=True)
    res_l = None

    if method_l == "📝 กรอกแบบฟอร์ม":
        with st.form("labor_form"):
            c1, c2 = st.columns(2)
            l_date   = c1.date_input("วันที่จ่าย", value=datetime.now())
            l_name   = c2.text_input("ชื่อพนักงาน")
            c3, c4   = st.columns(2)
            l_role   = c3.text_input("ตำแหน่ง", value="พนักงาน")
            l_amount = c4.number_input("จำนวนเงิน (฿)", min_value=0.0, step=100.0)
            l_note   = st.text_input("หมายเหตุ (เช่น เงินเดือน, โอที, รายวัน)")
            if st.form_submit_button("➕ เพิ่ม", type="primary"):
                res_l = [{"date": str(l_date), "name": l_name, "role": l_role,
                          "amount": l_amount, "note": l_note}]

    elif method_l == "🎙️ บันทึกเสียง":
        audio_l = st.audio_input("พูดรายการค่าแรง เช่น 'จ่ายน้องนิด 500 บาท วันที่ 1 พฤษภา'...")
        if audio_l and st.button("🚀 แปลงเสียง", type="primary"):
            with st.spinner("AI กำลังแปลง..."):
                res_l = process_extraction(audio_l.read(), "Labor", is_bytes=True, mime=audio_l.type)

    else:
        txt_l = st.text_area("พิมพ์รายการค่าแรง เช่น 'น้องนิด 500 บาท, พี่ต้น 600 บาท':")
        if txt_l and st.button("🪄 วิเคราะห์", type="primary"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                res_l = process_extraction(txt_l, "Labor")

    if res_l:
        st.session_state.tmp_labor = pd.DataFrame(res_l)

    if "tmp_labor" in st.session_state:
        edited_l = st.data_editor(st.session_state.tmp_labor, use_container_width=True,
                                  num_rows="dynamic")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 บันทึก", type="primary"):
                with st.spinner("กำลังบันทึก..."):
                    if save_to_tab(edited_l.copy(), "Labor"):
                        del st.session_state.tmp_labor
                        st.success("✅ บันทึกสำเร็จ!")
                        st.rerun()
        with c2:
            if st.button("🗑️ ล้าง"):
                del st.session_state.tmp_labor
                st.rerun()


# ============================================================
# 10. PAGE — AI Agent
# ============================================================
elif page == "🤖 AI Agent":

    st.markdown("<div class='page-title'>🤖 AI ที่ปรึกษาธุรกิจ</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>ถามเรื่องธุรกิจ วิเคราะห์ข้อมูล แนะนำกลยุทธ์</div>", unsafe_allow_html=True)

    # Quick prompts
    st.markdown("**💡 คำถามยอดนิยม:**")
    qcols = st.columns(4)
    quick_qs = [
        "วิเคราะห์ food cost ว่าควรปรับราคาเมนูไหนบ้าง?",
        "เดือนไหนยอดขายดีที่สุด เพราะอะไร?",
        "แอปไหนให้กำไรสุทธิดีที่สุด?",
        "ต้นทุนไหนที่ควรลดเพื่อเพิ่มกำไร?",
    ]
    for i, q in enumerate(quick_qs):
        with qcols[i]:
            if st.button(q, key=f"qb_{i}"):
                st.session_state.ai_quick_q = q

    st.divider()

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    for msg in st.session_state.ai_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_q = st.chat_input("ถามอะไรก็ได้เกี่ยวกับธุรกิจร้านเนฟ 304...")

    if "ai_quick_q" in st.session_state:
        user_q = st.session_state.pop("ai_quick_q")

    if user_q:
        st.session_state.ai_messages.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.write(user_q)

        df_i = load_data("Income")
        df_e = load_data("Expense")
        df_m = load_data("Monthly")
        df_l = load_data("Labor")

        ctx = f"""
ข้อมูลร้านเนฟ หมี่ไก่ฉีก (Nave 304):

[รายรับรายวัน 10 วันล่าสุด]
{df_i.tail(10).to_csv(index=False)}

[รายจ่ายวัตถุดิบล่าสุด]
{df_e.tail(10).to_csv(index=False)}

[สรุปรายเดือน]
{df_m.tail(6).to_csv(index=False)}

[ค่าแรงพนักงาน]
{df_l.tail(10).to_csv(index=False) if not df_l.empty else 'ยังไม่มีข้อมูล'}

ต้นทุนคงที่/วัน: ค่าเช่า ฿{rent_day}, ค่าน้ำไฟ ฿{utility_day}, แพ็คเกจจิ้ง {pkg_pct}%
เป้าหมาย Food Cost: ไม่เกิน {target_fc}%
"""
        full_prompt = f"คุณคือที่ปรึกษาธุรกิจร้านอาหารผู้เชี่ยวชาญ ตอบเป็นภาษาไทย กระชับ ใช้ตัวเลขจริงจากข้อมูล\n\n{ctx}\n\nคำถาม: {user_q}"

        with st.chat_message("assistant"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                reply = call_gemini(full_prompt)
                if reply:
                    st.write(reply)
                    st.session_state.ai_messages.append({"role": "assistant", "content": reply})
                else:
                    st.error("ไม่สามารถเชื่อมต่อ AI ได้ในขณะนี้")

    if st.session_state.ai_messages and st.button("🗑️ ล้างประวัติการสนทนา"):
        st.session_state.ai_messages = []
        st.rerun()


# ============================================================
# 11. PAGE — ข้อมูลทั้งหมด
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":

    st.markdown("<div class='page-title'>📋 ข้อมูลทั้งหมด</div>", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        "📥 Income (รายวัน)",
        "📊 Monthly (รายเดือน)",
        "📤 Expense (รายจ่าย)",
        "👷 Labor (ค่าแรง)",
    ])
    with t1:
        df = load_data("Income")
        st.metric("จำนวนแถว", len(df))
        st.dataframe(df, use_container_width=True)
    with t2:
        df = load_data("Monthly")
        st.metric("จำนวนแถว", len(df))
        st.dataframe(df, use_container_width=True)
    with t3:
        df = load_data("Expense")
        st.metric("จำนวนแถว", len(df))
        st.dataframe(df, use_container_width=True)
    with t4:
        df = load_data("Labor")
        st.metric("จำนวนแถว", len(df))
        st.dataframe(df, use_container_width=True)

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
# 1. CONFIG
# ============================================================
st.set_page_config(
    page_title="Nave 304",
    layout="wide",
    page_icon="🍜",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;600;700&display=swap');

html,body,[class*="css"]{font-family:'Sarabun',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}

/* ─── layout ─── */
.block-container{padding:1rem 1.5rem 3rem;max-width:1280px}

/* ─── top nav bar ─── */
.topnav{
  background:linear-gradient(135deg,#064e2e 0%,#1a7a50 100%);
  border-radius:16px;
  padding:12px 16px;
  margin-bottom:1.2rem;
  display:flex;align-items:center;gap:10px;
  box-shadow:0 4px 20px rgba(0,0,0,.15);
}
.topnav-logo{
  font-size:1.15rem;font-weight:700;color:#fff;
  white-space:nowrap;margin-right:6px;
}
.topnav-logo span{opacity:.65;font-weight:400;font-size:.8rem}
.topnav-links{
  display:flex;gap:6px;overflow-x:auto;
  scrollbar-width:none;flex:1;
}
.topnav-links::-webkit-scrollbar{display:none}
.tnav{
  display:inline-flex;align-items:center;gap:5px;
  color:rgba(255,255,255,.72);font-size:.82rem;font-weight:500;
  padding:6px 14px;border-radius:20px;
  border:1px solid rgba(255,255,255,.18);
  white-space:nowrap;cursor:pointer;
  background:transparent;transition:all .15s;
}
.tnav:hover{background:rgba(255,255,255,.12);color:#fff}
.tnav.on{background:rgba(255,255,255,.22);color:#fff;border-color:rgba(255,255,255,.4)}
.nav-refresh{
  color:rgba(255,255,255,.7);font-size:.8rem;white-space:nowrap;
  background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);
  border-radius:20px;padding:5px 12px;cursor:pointer;
}

/* ─── metric cards ─── */
[data-testid="stMetric"]{
  background:#fff;border:1px solid #e8ecef;
  border-radius:14px;padding:.9rem 1.1rem;
  box-shadow:0 2px 8px rgba(0,0,0,.05);
  transition:transform .15s,box-shadow .15s;
}
[data-testid="stMetric"]:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.09)}
[data-testid="stMetricLabel"]{font-size:.7rem!important;color:#7a8694!important;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
[data-testid="stMetricValue"]{font-size:1.45rem!important;font-weight:700;color:#0f1923}

/* ─── tabs ─── */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#f1f4f6;border-radius:10px;padding:4px}
.stTabs [data-baseweb="tab"]{border-radius:8px;font-size:.83rem;color:#6b7280;padding:.38rem .9rem}
.stTabs [aria-selected="true"]{background:#fff!important;color:#0f1923!important;box-shadow:0 1px 6px rgba(0,0,0,.1)}

/* ─── buttons ─── */
.stButton>button{border-radius:10px;font-weight:600;font-size:.84rem;transition:all .15s}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#064e2e,#1a7a50)!important;
  color:#fff!important;border:none!important;
}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.13)}

/* ─── alert boxes ─── */
.box-ok  {background:#f0fdf6;border-left:4px solid #22c55e;border-radius:10px;padding:.75rem 1rem;font-size:.85rem;color:#15622f;margin-bottom:.75rem}
.box-warn{background:#fffbeb;border-left:4px solid #f59e0b;border-radius:10px;padding:.75rem 1rem;font-size:.85rem;color:#8a5000;margin-bottom:.75rem}
.box-info{background:#eff6ff;border-left:4px solid #3b82f6;border-radius:10px;padding:.75rem 1rem;font-size:.85rem;color:#1e3fa0;margin-bottom:.75rem}

/* ─── section title ─── */
.stitle{font-size:.95rem;font-weight:700;color:#0f1923;padding-bottom:.35rem;border-bottom:2px solid #e8ecef;margin:1rem 0 .75rem}

/* ─── mobile ─── */
@media(max-width:768px){
  .block-container{padding:.5rem .5rem 2rem}
  .topnav{border-radius:12px;padding:10px 12px;margin-bottom:.8rem}
  .topnav-logo span{display:none}
  [data-testid="stMetricValue"]{font-size:1.15rem!important}
  [data-testid="stMetric"]{padding:.7rem .8rem}
}

/* ─── hide default sidebar toggle ─── */
[data-testid="collapsedControl"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
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
    st.error(f"⚠️ ไม่พบ API Key: {e}")
    client = None

@st.cache_data(ttl=60)
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except: return pd.DataFrame()

def refresh_all_caches():
    load_data.clear()

# ============================================================
# 3. FUNCTIONS (เดิมทุกอย่าง)
# ============================================================
def clean_numeric(df, col_name):
    if col_name in df.columns:
        return pd.to_numeric(
            df[col_name].astype(str).str.replace(',','').str.replace('฿',''),
            errors='coerce').fillna(0)
    return pd.Series([0]*len(df))

def safe_parse_json(text):
    if not text: return []
    try:
        c = text.strip()
        if "```" in c: c = c.split("```")[1]
        if c.startswith("json"): c = c[4:]
        return json.loads(c.strip())
    except: return []

def call_gemini(prompt, contents=None, is_complex=False):
    if client is None: return None
    model = "models/gemini-3.1-flash-lite-preview"
    try:
        if is_complex:
            r = client.models.generate_content(model=model, contents=contents)
        else:
            parts = [prompt]+(contents or [])
            r = client.models.generate_content(model=model, contents=parts)
        if r.text:
            st.toast("🤖 ประมวลผลสำเร็จ", icon="✅")
            return r.text
    except: return None

def process_extraction(data, p_type, is_bytes=False, mime=None):
    now = datetime.now().strftime("%Y-%m-%d")
    if p_type == "Expense":
        p = f"สกัดสินค้าเป็น JSON: [{{'date':'{now}','name':'สินค้า','qty':1,'unit':'หน่วย','total_price':0}}]. ถ้าไม่มีวันที่ใช้ {now}"
    elif p_type == "หน้าร้าน":
        p = f"สกัดยอดหน้าร้าน: [{{'date':'{now}','app':'หน้าร้าน','net_income':0}}]"
    elif p_type == "สรุปรายเดือน":
        p = "สกัดรายเดือน: [{'month_year':'YYYY-MM','platform':'แอป','gross':0,'fees':0,'ads':0,'discounts':0,'net_income':0}]"
    else:
        p = f"สกัดรายได้เดลิเวอรี่: [{{'date':'{now}','app':'ชื่อแอป','net_income':0}}]"
    prompt = p + " ตอบ PURE JSON เท่านั้น"
    if is_bytes:
        contents = [types.Content(role="user", parts=[
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data, mime_type=mime)])]
        res = call_gemini(prompt, contents=contents, is_complex=True)
    else:
        res = call_gemini(prompt, contents=[data])
    return safe_parse_json(res)

def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        existing = load_data(tab)

        # ── จัดการ column ตาม tab ──
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
            if 'name' not in df.columns: df['name'] = df['app'].astype(str) + " Daily Income"
            if 'qty' not in df.columns: df['qty'] = 1
            if 'unit' not in df.columns: df['unit'] = "วัน"
            if 'net_income' not in df.columns: df['net_income'] = 0
            if 'total_price' not in df.columns: df['total_price'] = df['net_income']
            if 'unit_price' not in df.columns: df['unit_price'] = df['net_income']
            if 'gross_sales' not in df.columns: df['gross_sales'] = df.get('gross', df['net_income'])
            if 'gp_amount' not in df.columns: df['gp_amount'] = df.get('fees', 0)
            # normalize app name ให้ตรงกับ Apps Script
            def norm_app(x):
                s = str(x).lower()
                if 'grab' in s: return 'GrabFood'
                if 'line' in s: return 'LINE MAN'
                if 'shopee' in s: return 'ShopeeFood'
                return x
            df['app'] = df['app'].apply(norm_app)

        elif tab == "Expense":
            df['type'] = 'Expense'
            if 'name' not in df.columns: df['name'] = 'ไม่ได้ระบุ'
            if 'qty' not in df.columns: df['qty'] = 1
            if 'unit' not in df.columns: df['unit'] = 'หน่วย'
            if 'total_price' not in df.columns: df['total_price'] = 0
            if 'unit_price' not in df.columns:
                df['unit_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0) /                                    pd.to_numeric(df['qty'], errors='coerce').replace(0, 1)

        elif tab == "Monthly":
            df['type'] = 'Monthly'
            for c in ['gross','fees','ads','discounts','net_income']:
                if c not in df.columns: df[c] = 0

        # ── fill columns ที่ขาดให้ครบ (ทำก่อน concat เสมอ) ──
        cols = ['name','qty','unit','total_price','date','unit_price',
                'app','net_income','gross_sales','gp_amount','type']
        for c in cols:
            if c not in df.columns: df[c] = ""

        df = df[[c for c in cols if c in df.columns]]

        # ── รวมกับ existing ──
        final = pd.concat([existing, df], ignore_index=True)

        # ── dedup แยกตาม tab ──
        if tab == "Income":
            final['date'] = pd.to_datetime(final['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            final['net_income'] = pd.to_numeric(final['net_income'], errors='coerce').round(2)
            final = final.drop_duplicates(subset=['date','app','net_income'], keep='first')
            final = final.sort_values('date', ascending=False)

        elif tab == "Expense":
            final['date'] = pd.to_datetime(final['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            final['total_price'] = pd.to_numeric(final['total_price'], errors='coerce').round(2)
            final = final.drop_duplicates(subset=['date','name','total_price'], keep='first')
            final = final.sort_values('date', ascending=False)

        elif tab == "Monthly":
            if 'month_year' in final.columns and 'platform' in final.columns:
                final = final.drop_duplicates(subset=['month_year','platform'], keep='last')
                final = final.sort_values('month_year', ascending=False)

        conn.update(worksheet=tab, data=final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ บันทึกล้มเหลว: {e}")
        return False

# ============================================================
# 4. NAV BAR (top bar — ทำงานทั้ง PC และมือถือ)
# ============================================================
MENUS = [
    ("📊","Dashboard","📊 Dashboard รายวัน"),
    ("📈","รายเดือน","📈 วิเคราะห์รายเดือน"),
    ("💰","รายรับ","💰 บันทึกรายรับ"),
    ("💸","รายจ่าย","💸 บันทึกรายจ่าย"),
    ("🤖","AI Agent","🤖 AI Agent"),
    ("📋","ข้อมูล","📋 ข้อมูลทั้งหมด"),
]

st.session_state.setdefault("page", "📊 Dashboard รายวัน")
page = st.session_state["page"]

# render top nav
nav_html = '<div class="topnav"><div class="topnav-logo">🍜 Nave 304 <span>AI Business</span></div><div class="topnav-links">'
for icon, label, key in MENUS:
    cls = "tnav on" if page == key else "tnav"
    nav_html += f'<span class="{cls}">{icon} {label}</span>'
nav_html += '</div></div>'
st.markdown(nav_html, unsafe_allow_html=True)

# ปุ่มเมนูจริง (ซ่อนด้วย CSS แต่ทำงานได้)
st.markdown("""
<style>
.nav-real-btns{
  display:flex;gap:6px;overflow-x:auto;
  margin-bottom:.8rem;scrollbar-width:none;
}
.nav-real-btns::-webkit-scrollbar{display:none}
.nav-real-btns .stButton>button{
  background:rgba(6,78,46,.08)!important;
  border:1px solid rgba(6,78,46,.2)!important;
  color:#064e2e!important;
  border-radius:20px!important;
  font-size:.82rem!important;padding:5px 14px!important;
  white-space:nowrap!important;
}
.nav-real-btns .stButton>button:hover{
  background:rgba(6,78,46,.15)!important;
}
</style>
<div class="nav-real-btns">
""", unsafe_allow_html=True)

_cols = st.columns(len(MENUS))
for _i, (_icon, _label, _key) in enumerate(MENUS):
    with _cols[_i]:
        if st.button(f"{_icon} {_label}", key=f"nb_{_i}"):
            st.session_state["page"] = _key
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# อ่านค่า page ใหม่หลังกด
page = st.session_state["page"]

# break-even settings (popup-style expander ด้านขวา)
with st.expander("⚙️ ตั้งค่าต้นทุนคงที่/เดือน", expanded=False):
    _c1, _c2, _c3, _c4 = st.columns(4)
    st.session_state.setdefault("be_rent",4000)
    st.session_state.setdefault("be_elec",800)
    st.session_state.setdefault("be_water",400)
    st.session_state.setdefault("be_other",0)
    st.session_state["be_rent"]  = _c1.number_input("🏠 ค่าเช่า (฿)", value=st.session_state["be_rent"],  step=500, min_value=0)
    st.session_state["be_elec"]  = _c2.number_input("💡 ค่าไฟ (฿)",   value=st.session_state["be_elec"],  step=100, min_value=0)
    st.session_state["be_water"] = _c3.number_input("🚿 ค่าน้ำ (฿)",  value=st.session_state["be_water"], step=100, min_value=0)
    st.session_state["be_other"] = _c4.number_input("📦 อื่นๆ (฿)",   value=st.session_state["be_other"], step=100, min_value=0)

col_ref, _ = st.columns([1,8])
with col_ref:
    if st.button("🔄 รีเฟรช", type="primary"):
        refresh_all_caches()
        st.rerun()

st.divider()

# ============================================================
# 5. DASHBOARD รายวัน
# ============================================================
if page == "📊 Dashboard รายวัน":
    st.markdown("<div class='stitle'>📊 Dashboard รายวัน</div>", unsafe_allow_html=True)

    df_i = load_data("Income")
    df_e = load_data("Expense")
    df_i['net_income']  = clean_numeric(df_i,'net_income')
    df_e['total_price'] = clean_numeric(df_e,'total_price')
    df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
    df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')

    t_inc  = df_i['net_income'].sum()
    t_exp  = df_e['total_price'].sum()
    profit = t_inc - t_exp

    # break-even
    fixed_mo  = (st.session_state["be_rent"]+st.session_state["be_elec"]
                +st.session_state["be_water"]+st.session_state["be_other"])
    fixed_day = fixed_mo/26
    fc_pct    = (t_exp/t_inc*100) if t_inc>0 else 0
    cm        = 1-fc_pct/100
    be_day    = (fixed_day/cm) if cm>0 else 0
    today     = pd.Timestamp.now().normalize()
    today_inc = df_i[df_i['date']>=today]['net_income'].sum() if not df_i.empty else 0
    passed    = today_inc>=be_day and be_day>0
    gap       = be_day-today_inc

    if be_day>0:
        if passed:
            st.markdown(f"<div class='box-ok'>✅ <b>ผ่าน Break-even แล้ว!</b> วันนี้ ฿{today_inc:,.0f} — เกิน ฿{be_day:,.0f} อยู่ <b>฿{today_inc-be_day:,.0f}</b></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='box-warn'>⚠️ ยังไม่ถึง Break-even — วันนี้ ฿{today_inc:,.0f} ต้องขายเพิ่มอีก <b>฿{gap:,.0f}</b> (เป้า ฿{be_day:,.0f}/วัน)</div>", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💰 รายรับรวม",     f"฿{t_inc:,.0f}")
    c2.metric("📦 รายจ่ายรวม",    f"฿{t_exp:,.0f}")
    c3.metric("⚖️ กำไรขั้นต้น",   f"฿{profit:,.0f}",
              delta=f"{profit/t_inc*100:.1f}% margin" if t_inc>0 else None)
    c4.metric("🎯 Break-even/วัน",
              f"฿{be_day:,.0f}" if be_day>0 else "ตั้งค่าก่อน",
              delta="ผ่านแล้ว ✅" if passed else (f"ขาดอีก ฿{gap:,.0f}" if be_day>0 else None),
              delta_color="normal" if passed else "inverse")

    if be_day>0:
        pct   = min(today_inc/be_day,1.0)
        color = "#22c55e" if passed else "#f59e0b"
        st.markdown(f"""
        <div style="margin:.6rem 0 1rem">
          <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#6b7280;margin-bottom:4px">
            <span>วันนี้ ฿{today_inc:,.0f}</span><span>เป้า ฿{be_day:,.0f}</span>
          </div>
          <div style="background:#e5e7eb;border-radius:8px;height:10px;overflow:hidden">
            <div style="background:{color};width:{pct*100:.1f}%;height:100%;border-radius:8px;transition:width .5s"></div>
          </div>
          <div style="font-size:.72rem;color:#9ca3af;text-align:right;margin-top:2px">{pct*100:.0f}% of break-even</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    tab_inc, tab_exp, tab_price = st.tabs(["📅 แนวโน้มรายรับ","🛒 สรุปรายจ่าย","📈 ราคาวัตถุดิบ"])

    with tab_inc:
        zoom = st.radio("ดูย้อนหลัง:",[7,30,60,90], horizontal=True, format_func=lambda x:f"{x} วัน", key="z")
        cutoff  = pd.Timestamp.now()-pd.Timedelta(days=zoom)
        df_filt = df_i[df_i['date']>=cutoff].copy()
        if not df_filt.empty:
            daily = df_filt.groupby('date')['net_income'].sum().reset_index()
            daily['rolling'] = daily['net_income'].rolling(7,min_periods=1).mean()
            COLORS = {'GrabFood':'#00b14f','Grab':'#00b14f','Line Man':'#0094ff',
                      'Shopee':'#f97316','foodpanda':'#e11d74','หน้าร้าน':'#8b5cf6'}
            FB = ['#06b6d4','#f43f5e','#eab308','#14b8a6','#64748b']
            fig = go.Figure()
            fb_i = 0
            for app in df_filt['app'].unique():
                d = df_filt[df_filt['app']==app]
                if app not in COLORS:
                    COLORS[app]=FB[fb_i%len(FB)]; fb_i+=1
                fig.add_trace(go.Bar(x=d['date'],y=d['net_income'],name=app,
                    marker_color=COLORS[app],marker_line_width=0,opacity=.92))
            fig.add_trace(go.Scatter(x=daily['date'],y=daily['rolling'],
                name='เฉลี่ย 7 วัน',line=dict(color='#fbbf24',dash='dot',width=2.5)))
            fig.update_layout(barmode='stack',hovermode='x unified',
                title=f"รายรับย้อนหลัง {zoom} วัน",
                plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h',yanchor='bottom',y=1.02,xanchor='right',x=1),
                margin=dict(l=0,r=0,t=48,b=0),bargap=.25)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลในช่วงนี้")

    with tab_exp:
        if not df_e.empty:
            cl,cr = st.columns(2)
            with cl:
                fp = px.pie(df_e,values='total_price',names='name',hole=.42,title="สัดส่วนรายจ่าย")
                fp.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=48,b=0))
                st.plotly_chart(fp,use_container_width=True)
            with cr:
                top = df_e.groupby('name')['total_price'].sum().nlargest(8).reset_index()
                fb = px.bar(top,x='total_price',y='name',orientation='h',
                    color='total_price',color_continuous_scale='Greens',title="Top 8 รายจ่าย",
                    labels={'total_price':'฿','name':''})
                fb.update_layout(showlegend=False,plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=48,b=0))
                st.plotly_chart(fb,use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลรายจ่าย")

    with tab_price:
        if not df_e.empty and 'name' in df_e.columns:
            item = st.selectbox("เลือกสินค้า:",sorted(df_e['name'].dropna().unique()))
            di   = df_e[df_e['name']==item].sort_values('date').copy()
            di['u_price'] = di['total_price']/clean_numeric(di,'qty').replace(0,1)
            if len(di)>=2:
                last,prev = di['u_price'].iloc[-1],di['u_price'].iloc[-2]
                chg = (last-prev)/prev*100 if prev>0 else 0
                ca,cb = st.columns(2)
                ca.metric("ราคาล่าสุด/หน่วย",f"฿{last:.2f}",delta=f"{chg:+.1f}%",delta_color="inverse")
                cb.metric("ซื้อทั้งหมด",f"{len(di)} ครั้ง",delta=f"รวม ฿{di['total_price'].sum():,.0f}")
                if chg>=10:
                    st.markdown(f"<div class='box-warn'>⚠️ ราคา <b>{item}</b> เพิ่มขึ้น {chg:.1f}%</div>",unsafe_allow_html=True)
            fl = px.line(di,x='date',y='u_price',markers=True,title=f"แนวโน้มราคา {item} ต่อหน่วย",labels={'u_price':'฿/หน่วย'})
            fl.update_traces(line_color='#064e2e',marker_color='#064e2e')
            fl.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=48,b=0))
            st.plotly_chart(fl,use_container_width=True)

# ============================================================
# 6. วิเคราะห์รายเดือน
# ============================================================
elif page == "📈 วิเคราะห์รายเดือน":
    st.markdown("<div class='stitle'>📈 วิเคราะห์รายเดือน</div>",unsafe_allow_html=True)
    df_m = load_data("Monthly")
    if not df_m.empty:
        for c in ['net_income','gross','fees','ads']:
            df_m[c] = clean_numeric(df_m,c)
        m1,m2,m3 = st.columns(3)
        m1.metric("💰 ยอดโอนสุทธิรวม",   f"฿{df_m['net_income'].sum():,.0f}")
        m2.metric("📊 ยอดขายรวม (Gross)", f"฿{df_m['gross'].sum():,.0f}")
        m3.metric("📉 ค่า GP+โฆษณารวม",   f"฿{(df_m['fees']+df_m['ads']).sum():,.0f}")
        st.divider()
        cl,cr = st.columns([2,1])
        with cl:
            fm = go.Figure()
            fm.add_trace(go.Bar(x=df_m['month_year'],y=df_m['gross'],name='Gross',marker_color='#93c5fd'))
            fm.add_trace(go.Bar(x=df_m['month_year'],y=df_m['net_income'],name='Net',marker_color='#064e2e'))
            fm.update_layout(barmode='group',plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h',yanchor='bottom',y=1.02,xanchor='right',x=1),
                margin=dict(l=0,r=0,t=16,b=0))
            st.plotly_chart(fm,use_container_width=True)
        with cr:
            if df_m['fees'].sum()>0 and 'platform' in df_m.columns:
                fp2 = px.pie(df_m,values='fees',names='platform',hole=.4,title='ค่า GP แยกแอป')
                fp2.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fp2,use_container_width=True)
        df_m['cost_%'] = ((df_m['fees']+df_m['ads'])/df_m['gross'].replace(0,pd.NA)*100).round(1)
        st.dataframe(df_m[['month_year','platform','gross','fees','ads','net_income','cost_%']].sort_values('month_year',ascending=False),use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลรายเดือน")

# ============================================================
# 7. บันทึกรายรับ
# ============================================================
elif page == "💰 บันทึกรายรับ":
    st.markdown("<div class='stitle'>💰 บันทึกรายรับ</div>",unsafe_allow_html=True)
    rtype  = st.radio("ประเภท:",["รายวันเดลิเวอรี่","สรุปรายเดือน","หน้าร้าน"],horizontal=True)
    method = st.radio("วิธีบันทึก:",["⌨️ พิมพ์/วางข้อความ","🎙️ บันทึกเสียง","📁 อัปโหลดไฟล์"],horizontal=True)
    res = None
    if method=="⌨️ พิมพ์/วางข้อความ":
        txt = st.text_area("ระบุข้อมูล:",height=130,placeholder="วางข้อความยอดขายจากแอปได้เลย...")
        if txt and st.button("🪄 วิเคราะห์ด้วย AI",type="primary"):
            with st.spinner("AI กำลังวิเคราะห์..."):
                res = process_extraction(txt, rtype)
    elif method=="🎙️ บันทึกเสียง":
        st.markdown("<div class='box-info'>🎙️ กดปุ่มไมค์แล้วพูด เช่น <b>Grab วันนี้ 1,500 บาท</b></div>",unsafe_allow_html=True)
        audio = st.audio_input("บันทึกเสียง")
        if audio:
            st.audio(audio)
            if st.button("🚀 แปลงเสียงเป็นข้อมูล",type="primary"):
                with st.spinner("AI กำลังแปลง..."):
                    res = process_extraction(audio.read(), rtype, is_bytes=True, mime=audio.type)
    else:
        file = st.file_uploader("เลือกไฟล์",type=['pdf','jpg','png','jpeg'])
        if file and st.button("🪄 วิเคราะห์ไฟล์",type="primary"):
            with st.spinner("AI กำลังอ่าน..."):
                res = process_extraction(file.read(), rtype, is_bytes=True, mime=file.type)
    if res:
        st.session_state.tmp_inc = pd.DataFrame(res)
        st.success(f"✅ AI สกัดได้ {len(res)} รายการ")
    if 'tmp_inc' in st.session_state:
        edited = st.data_editor(st.session_state.tmp_inc, use_container_width=True, num_rows="dynamic")
        ca,cb = st.columns([1,5])
        with ca:
            if st.button("💾 บันทึก",type="primary"):
                target = "Monthly" if rtype=="สรุปรายเดือน" else "Income"
                if save_to_tab(edited, target):
                    del st.session_state.tmp_inc
                    st.success("✅ บันทึกสำเร็จ!")
                    st.rerun()
        with cb:
            if st.button("🗑️ ล้าง"):
                del st.session_state.tmp_inc
                st.rerun()

# ============================================================
# 8. บันทึกรายจ่าย
# ============================================================
elif page == "💸 บันทึกรายจ่าย":
    st.markdown("<div class='stitle'>💸 บันทึกรายจ่ายวัตถุดิบ</div>",unsafe_allow_html=True)
    method = st.radio("เลือกวิธี:",["ยังไม่เลือก","📸 แสกนบิล/อัปโหลดรูป","🎙️ บันทึกด้วยเสียง"],horizontal=True)
    res_ex = None
    if method=="📸 แสกนบิล/อัปโหลดรูป":
        sub = st.radio("ช่องทาง:",["📷 ถ่ายรูปสด","📁 เลือกไฟล์"],horizontal=True)
        img = st.camera_input("สแกนบิล") if sub=="📷 ถ่ายรูปสด" else st.file_uploader("เลือกรูป",type=['jpg','png','jpeg'])
        if img and st.button("🪄 วิเคราะห์บิล",type="primary"):
            with st.spinner("AI กำลังอ่านบิล..."):
                res_ex = process_extraction(
                    Image.open(img) if sub=="📷 ถ่ายรูปสด" else img.read(),
                    "Expense", is_bytes=(sub=="📁 เลือกไฟล์"), mime="image/jpeg")
    elif method=="🎙️ บันทึกด้วยเสียง":
        st.markdown("<div class='box-info'>🎙️ พูดรายการที่ซื้อ เช่น <b>ไก่ 5 กิโล 400 บาท</b></div>",unsafe_allow_html=True)
        audio_ex = st.audio_input("บันทึกเสียงรายจ่าย")
        if audio_ex:
            st.audio(audio_ex)
            if st.button("🚀 แปลงเสียง",type="primary"):
                with st.spinner("AI กำลังแปลง..."):
                    res_ex = process_extraction(audio_ex.read(), "Expense", is_bytes=True, mime=audio_ex.type)
    if res_ex:
        st.session_state.tmp_exp = pd.DataFrame(res_ex)
        st.success(f"✅ AI สกัดได้ {len(res_ex)} รายการ")
    if 'tmp_exp' in st.session_state:
        edited_ex = st.data_editor(st.session_state.tmp_exp, use_container_width=True, num_rows="dynamic")
        ca,cb = st.columns([1,5])
        with ca:
            if st.button("💾 บันทึก",type="primary"):
                if save_to_tab(edited_ex, "Expense"):
                    del st.session_state.tmp_exp
                    st.success("✅ บันทึกสำเร็จ!")
                    st.rerun()
        with cb:
            if st.button("🗑️ ล้าง"):
                del st.session_state.tmp_exp
                st.rerun()

# ============================================================
# 9. AI Agent
# ============================================================
elif page == "🤖 AI Agent":
    st.markdown("<div class='stitle'>🤖 AI ที่ปรึกษาธุรกิจ</div>",unsafe_allow_html=True)
    st.markdown("<div class='box-info'>💡 ถามเรื่องธุรกิจได้เลย เช่น แอปไหนกำไรดีสุด? ควรปรับราคาไหม?</div>",unsafe_allow_html=True)
    q = st.chat_input("ถามเรื่องธุรกิจ...")
    if q:
        df_i = load_data("Income")
        df_e = load_data("Expense")
        df_m = load_data("Monthly")
        ctx  = f"Income: {df_i.tail(5).to_csv()}\nMonthly: {df_m.tail(3).to_csv()}\nExpense: {df_e.tail(5).to_csv()}"
        with st.chat_message("assistant"):
            with st.spinner("กำลังวิเคราะห์..."):
                st.write(call_gemini(f"คุณคือที่ปรึกษาร้านอาหาร ตอบภาษาไทย กระชับ ใช้ตัวเลขจริง\n{ctx}\nคำถาม: {q}"))

# ============================================================
# 10. ข้อมูลทั้งหมด
# ============================================================
elif page == "📋 ข้อมูลทั้งหมด":
    st.markdown("<div class='stitle'>📋 ข้อมูลดิบ Google Sheets</div>",unsafe_allow_html=True)
    t1,t2,t3 = st.tabs(["📥 Income","📊 Monthly","📤 Expense"])
    with t1:
        d = load_data("Income")
        st.caption(f"{len(d)} แถว")
        st.dataframe(d, use_container_width=True)
    with t2:
        d = load_data("Monthly")
        st.caption(f"{len(d)} แถว")
        st.dataframe(d, use_container_width=True)
    with t3:
        d = load_data("Expense")
        st.caption(f"{len(d)} แถว")
        st.dataframe(d, use_container_width=True)

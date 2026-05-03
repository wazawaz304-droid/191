# --- ปรับปรุงฟังก์ชันโหลดข้อมูล (ตัด Cache ออกชั่วคราวเพื่อเช็กข้อมูลจริง) ---
def load_data(sheet_name):
    if conn is None: return pd.DataFrame()
    try:
        # ใช้ ttl=0 เพื่อให้ดึงค่าสดจาก Sheet ทุกครั้งที่ Refresh ป้องกันข้อมูล "หาย" เพราะ Cache
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"❌ โหลดข้อมูลจาก {sheet_name} ไม่ได้: {e}")
        return pd.DataFrame()

# --- ปรับปรุงฟังก์ชันทำความสะอาดตัวเลข (ให้รองรับได้หลายรูปแบบ) ---
def clean_numeric(df, col_name):
    if col_name in df.columns:
        # ลบช่องว่างและสัญลักษณ์ออกก่อนแปลง
        cleaned = df[col_name].astype(str).str.replace(r'[^\d.]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.Series([0.0] * len(df))

# --- ปรับปรุงการบันทึกข้อมูล (เพิ่มระบบตรวจสอบความปลอดภัย) ---
def save_to_tab(df, tab):
    if conn is None or df.empty: return False
    try:
        # โหลดข้อมูลที่มีอยู่เดิมมาสะสมไว้ (Prevent Data Loss)
        existing = load_data(tab)
        
        # จัดการข้อมูลแยกตามประเภท
        if tab == "Income":
            df['type'] = 'Income'
            if 'app' not in df.columns: df['app'] = 'หน้าร้าน'
        elif tab == "Expense":
            df['type'] = 'Expense'
            # คำนวณราคาต่อหน่วยก่อนบันทึก
            df['unit_price'] = clean_numeric(df, 'total_price') / clean_numeric(df, 'qty').replace(0, 1)
        elif tab == "Monthly":
            df['type'] = 'Monthly'

        # รวมข้อมูลเดิมกับข้อมูลใหม่ (Concat)
        final = pd.concat([existing, df], ignore_index=True)
        
        # เขียนทับลงใน Google Sheets ทั้งหมด
        conn.update(worksheet=tab, data=final)
        refresh_all_caches()
        st.success(f"✅ บันทึกลง {tab} เรียบร้อยแล้ว!")
        return True
    except Exception as e:
        st.error(f"❌ ระบบบันทึกมีปัญหา: {e}")
        return False

# --- แก้ไขหน้า Dashboard (ปัญหาที่ข้อมูลมักไม่โชว์) ---
if page == "📊 Dashboard รายวัน":
    st.header("📊 แดชบอร์ดรายรับ-รายจ่ายรายวัน")
    df_i = load_data("Income")
    df_e = load_data("Expense")

    if not df_i.empty:
        # แปลงวันที่และจัดการเรื่องปี พ.ศ./ค.ศ.
        df_i['date'] = pd.to_datetime(df_i['date'], errors='coerce')
        df_i['net_income'] = clean_numeric(df_i, 'net_income')
        
    if not df_e.empty:
        df_e['date'] = pd.to_datetime(df_e['date'], errors='coerce')
        df_e['total_price'] = clean_numeric(df_e, 'total_price')

    # ส่วนแสดงผล Metric (ยอดรวมทั้งหมดแบบไม่สน Filter วันที่ก่อนเพื่อให้เห็นข้อมูล)
    total_inc = df_i['net_income'].sum() if not df_i.empty else 0
    total_exp = df_e['total_price'].sum() if not df_e.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 รายรับรวมทั้งหมด", f"฿{total_inc:,.2f}")
    c2.metric("📦 รายจ่ายรวมทั้งหมด", f"฿{total_exp:,.2f}")
    c3.metric("⚖️ กำไรสะสม", f"฿{total_inc - total_exp:,.2f}")

    # ส่วน Filter วันที่ (ปรับปรุงให้รองรับข้อมูลที่เพิ่งโหลด)
    st.divider()
    days = st.radio("เลือกดูย้อนหลัง:", [7, 30, 90, 365], horizontal=True)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    
    # กรองข้อมูลตามวันที่เลือก
    mask_i = df_i[df_i['date'] >= cutoff] if not df_i.empty else pd.DataFrame()
    
    if not mask_i.empty:
        st.subheader(f"📅 รายรับย้อนหลัง {days} วัน")
        fig = px.bar(mask_i, x='date', y='net_income', color='app', barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ ไม่พบข้อมูลในช่วงวันที่เลือก (ลองเช็กปี พ.ศ. ใน Google Sheets ของพี่ดูครับ)")

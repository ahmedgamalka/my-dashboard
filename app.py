import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import json
from fpdf import FPDF
from hashlib import sha256
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import plotly.io as pio

trading_tips_list = [
    "Always trade with a stop loss — discipline protects your capital.",
    "Don’t overtrade — wait for high-probability setups.",
    "The trend is your friend — don’t fight it.",
    "Stick to your trading plan, don’t improvise mid-trade.",
    "Focus on risk management, not just profits.",
    "Avoid revenge trading after a losing trade.",
    "Trade only what you can afford to lose.",
    "Don’t chase trades — let the trade come to you.",
    "Keep your charts clean and avoid indicator overload.",
    "Master one strategy before trying to learn others.",
    "Pre-market preparation is key for day traders.",
    "Focus on consistency, not on one big win.",
    "Set daily loss limits and stick to them.",
    "Avoid trading based on emotions or FOMO.",
    "Be patient — no trade is better than a bad trade.",
    "Track your trades in your journal to spot mistakes.",
    "Never double down on losing positions.",
    "Remember: capital preservation first, profits second.",
    "Stick to your preferred timeframes, don’t jump around.",
    "If uncertain, step aside — cash is also a position."
]


st.set_page_config(
    page_title="Trading Journal",
    page_icon="https://raw.githubusercontent.com/ahmedgamalka/my-dashboard/refs/heads/main/favicon.ico"
)

# الاتصال بجوجل شيت
def connect_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(st.secrets["service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)
    return client

# الوضع الداكن
def set_dark_theme():
    st.markdown("""
        <style>
        body {background-color: #0E1117; color: white;}
        .stApp {background-color: #0E1117;}
        </style>
    """, unsafe_allow_html=True)

# تشفير كلمة المرور
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# صفحة تسجيل الدخول وإنشاء حساب
def login_signup():
    st.markdown(
        f"""
        <style>
        .center-logo {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 20px;
        }}
        .center-logo img {{
            max-width: 150px;
            height: auto;
        }}
        </style>
        <div class='center-logo'>
            <img src='https://raw.githubusercontent.com/ahmedgamalka/my-dashboard/refs/heads/main/logo.png' alt='Logo'>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown("<h1 style='text-align: center; color: white;'>Trading Risk Management & Journal</h1>", unsafe_allow_html=True)
    st.markdown("---")

    st.title("🔐 Login or Sign Up")
    menu = st.radio("Select:", ["Login", "Sign Up"])
    client = connect_gsheet()

    try:
        sheet = client.open("Trading_Users_DB").worksheet("Users")
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open("Trading_Users_DB").add_worksheet(title="Users", rows="1000", cols="2")
        sheet.append_row(["username", "password_hash"])

    if menu == "Sign Up":
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        if st.button("Create Account"):
            users_data = sheet.get_all_records()
            existing_users = [user["username"] for user in users_data]

            if new_user in existing_users:
                st.warning("Username already exists!")
            else:
                hashed_pw = hash_password(new_password)
                sheet.append_row([new_user, hashed_pw])
                st.success("Account created! You can now login.")

    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            users_data = sheet.get_all_records()
            user_entry = next((u for u in users_data if u["username"] == username), None)

            if user_entry:
                hashed_pw = hash_password(password)
                if user_entry["password_hash"] == hashed_pw:
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Wrong password!")
            else:
                st.warning("Username does not exist.")


# تمييز الصفوف المهمة
def highlight_rows(row):
    highlight = "background-color: yellow; color: black"
    if row["Metric"] in ["Position Size (shares)", "Take Profit Price ($)", "Amount Invested ($)"]:
        return [highlight, highlight]
    return ["", ""]

# صفحة إدارة المخاطر
def risk_management_page():
    st.header("📊 Risk Management")

    # إدخال رصيد الحساب فقط
    acc_bal = st.number_input("Account Balance ($)", min_value=0.0, value=1000.0, step=100.0)

    # استخدام الإعدادات من session_state
    commission = st.session_state.get("commission_per_share", 0.02)
    min_commission = st.session_state.get("min_commission", 3.98)
    risk_pct = st.session_state.get("default_risk_pct", 2.0) / 100
    buffer_pct = st.session_state.get("cash_buffer_pct", 1.0) / 100

    # عرض القيم الحالية للمستخدم
    st.info(f"Commission Per Share: ${commission} - | - Minimum Commission: ${min_commission} - | - Risk % per trade: {risk_pct*100}% - | - Reserved Cash Buffer: {buffer_pct*100}%")

    entry = st.number_input("Entry Price", value=100.0)
    stop = st.number_input("Stop Loss Price", value=90.0)
    rr_ratio = st.number_input("Desired R/R Ratio", value=2.0, step=0.1)

    max_loss = acc_bal * risk_pct
    st.write(f"Max Dollar Loss: ${max_loss:.2f}")

    if st.button("Calculate"):
        risk_per_share = abs(entry - stop)

        if risk_per_share < 0.01:
            st.warning("⚠️ The difference between Entry Price and Stop Loss is too small or zero.")
            return

        pos_size = int(max_loss / risk_per_share)
        take_profit = entry + (risk_per_share * rr_ratio)
        risk_dollar = pos_size * risk_per_share
        total_invested_amount = pos_size * entry

        # ✅ حساب العمولة مع الحد الأدنى
        total_commission = pos_size * commission * 2
        if total_commission < min_commission and pos_size > 0:
            total_commission = min_commission

        # ✅ تعديل تلقائي لو المبلغ المستثمر + العمولة أكبر من رأس المال المتاح بعد الحجز
        available_balance = acc_bal * (1 - buffer_pct)
        if total_invested_amount + total_commission > available_balance:
            st.warning("⚠️ The invested amount + commission exceed the available balance (after reserving buffer). Adjusting position size automatically...")
            pos_size = int((available_balance - min_commission) / entry)  # نحجز الحد الأدنى للعمولة
            total_invested_amount = pos_size * entry
            risk_dollar = pos_size * risk_per_share
            total_commission = pos_size * commission * 2
            if total_commission < min_commission and pos_size > 0:
                total_commission = min_commission

        potential_reward = (take_profit - entry) * pos_size
        actual_rr = (potential_reward - total_commission) / risk_dollar if risk_dollar > 0 else 0
        gain_pct = ((potential_reward - total_commission) / (pos_size * entry)) * 100 if pos_size > 0 else 0

        df = pd.DataFrame({
            "Metric": [
                "Position Size (shares)", 
                "Total Commission ($)", 
                "Risk Amount ($)", 
                "Take Profit Price ($)", 
                "Potential Reward (After Commission) ($)", 
                "Actual R/R Ratio", 
                "Expected Gain (%)",
                "Amount Invested ($)"
            ],
            "Value": [
                pos_size, 
                f"${total_commission:.2f}", 
                f"${risk_dollar:.2f}", 
                f"${take_profit:.2f}", 
                f"${potential_reward - total_commission:.2f}", 
                f"{actual_rr:.2f}", 
                f"{gain_pct:.2f}%", 
                f"${total_invested_amount:.2f}"
            ]
        })

        st.dataframe(df.style.apply(highlight_rows, axis=1))

        if actual_rr < 1:
            st.warning(f"⚠️ The actual R/R ratio is {actual_rr:.2f}, which is below 1.0.")


# صفحة إضافة صفقة جديدة
def add_trade_page():
    st.header("➕ Add Trade")
    client = connect_gsheet()
    
    if "username" in st.session_state:
        user = st.session_state["username"]
        try:
            sheet = client.open("Trading_Journal_Master").worksheet(user)
        except gspread.exceptions.WorksheetNotFound:
            sheet = client.open("Trading_Journal_Master").add_worksheet(title=user, rows="1000", cols="21")
            sheet.append_row([
                "Trade ID", "Ticker Symbol", "Trade Direction", "Entry Price", "Entry Time", 
                "Exit Price", "Exit Time", "Position Size", "Risk", "Trade SL", "Target", 
                "R Multiple", "Commission", "Net P&L", "Used Indicator", "Used Strategy", "Notes"
            ])

        ticker = st.text_input("Ticker Symbol")
        entry = st.number_input("Entry Price", step=0.1)
        exit_price = st.number_input("Exit Price", step=0.1)
        size = st.number_input("Position Size", min_value=1, step=1)
        stop = st.number_input("Stop Loss Price", step=0.1)
        target = st.number_input("Target Price", step=0.1)
        commission = st.number_input("Total Commission ($)", value=3.98, step=0.01)
        used_indicator = st.text_input("Used Indicator")
        used_strategy = st.text_input("Used Strategy")
        notes = st.text_area("Notes")

        if st.button("Save Trade"):
            risk_val = abs(entry - stop) * size
            net_pnl = ((exit_price - entry) * size) - commission
            r_multiple = net_pnl / risk_val if risk_val > 0 else 0

            # Get current max Trade ID
            records = sheet.get_all_records()
            if records:
                trade_id = max(r["Trade ID"] for r in records) + 1
            else:
                trade_id = 1

            trade_row = [
                trade_id, ticker, "Long", entry, 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exit_price,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), size, risk_val, stop, target,
                r_multiple, commission, net_pnl, used_indicator, used_strategy, notes
            ]

            sheet.append_row(trade_row)
            st.success(f"✅ Trade {trade_id} added to journal!")




from fpdf import FPDF
import streamlit as st
import pandas as pd

# دالة حذف الصفقة من Google Sheets
def delete_trade_from_gsheet(user, trade_id):
    client = connect_gsheet()
    sheet = client.open("Trading_Journal_Master").worksheet(user)
    all_data = sheet.get_all_records()
    df_all = pd.DataFrame(all_data)

    # حذف الصف من الداتا فريم
    df_new = df_all[df_all["Trade ID"] != trade_id]

    # مسح الشيت وكتابة البيانات الجديدة
    sheet.clear()
    sheet.append_row(list(df_new.columns))
    for _, record in df_new.iterrows():
        sheet.append_row(record.tolist())

# دالة تصدير الجورنال كـ PDF
def export_journal_to_pdf(filtered_df, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Trading Journal Export for {user}", ln=True, align='C')
    pdf.ln(10)

    # رأس الجدول
    pdf.set_font("Arial", 'B', 10)
    headers = ["Entry Time", "Ticker", "Entry Price", "Exit Price", "Net P&L", "R Multiple"]
    col_widths = [40, 30, 25, 25, 25, 25]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align='C')
    pdf.ln(10)

    # بيانات الجدول
    pdf.set_font("Arial", '', 9)
    for index, row in filtered_df.iterrows():
        row_values = [
            str(row["Entry Time"])[:19],
            row["Ticker Symbol"],
            f"{row['Entry Price']:.2f}",
            f"{row['Exit Price']:.2f}",
            f"{row['Net P&L']:.2f}",
            f"{row['R Multiple']:.2f}"
        ]
        for i, val in enumerate(row_values):
            pdf.cell(col_widths[i], 8, val, border=1, align='C')
        pdf.ln(8)

    pdf_file = f"trading_journal_{user}.pdf"
    pdf.output(pdf_file)
    return pdf_file

# صفحة الجورنال
def trade_journal_page():
    st.header("📁 Trade Journal")
    client = connect_gsheet()

    if "username" in st.session_state:
        user = st.session_state["username"]
        try:
            sheet = client.open("Trading_Journal_Master").worksheet(user)
            df = pd.DataFrame(sheet.get_all_records())
        except gspread.exceptions.WorksheetNotFound:
            st.warning("⚠️ No trades found for this user.")
            return

        if df.empty:
            st.warning("⚠️ No trades recorded yet.")
            return

        st.dataframe(df.reset_index(drop=True), use_container_width=True)

        # التصدير PDF
        if st.button("📥 Export Journal to PDF"):
            pdf_file = export_journal_to_pdf(df, user)
            with open(pdf_file, "rb") as f:
                st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")

        # حذف الصفقة
        st.subheader("🗑️ Delete Trades:")
        for idx, row in df.iterrows():
            summary = f"{row['Trade ID']} | {row['Ticker Symbol']} | Entry: {row['Entry Price']}"
            if st.button(f"❌ Delete {summary}", key=f"delete_{row['Trade ID']}"):
                st.session_state.trade_id_to_delete = row['Trade ID']

        # التأكيد والحذف خارج اللوب
        if "trade_id_to_delete" in st.session_state:
            trade_id = st.session_state.trade_id_to_delete
            st.warning(f"Are you sure you want to delete trade ID: {trade_id}?")
            if st.button("✅ Confirm Delete", key="confirm_delete_button"):
                all_data = sheet.get_all_records()
                df_all = pd.DataFrame(all_data)
                df_new = df_all[df_all["Trade ID"] != trade_id]
                sheet.clear()
                sheet.append_row(list(df_new.columns))
                for i, record in df_new.iterrows():
                    sheet.append_row(record.tolist())
                st.success(f"✅ Deleted trade with ID: {trade_id}")
                del st.session_state.trade_id_to_delete
                st.rerun()   # ✅ استخدم st.rerun() هنا خارج اللوب!

import io
import tempfile

def export_dashboard_summary_to_pdf(summary, user, filtered_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Dashboard Summary for {user}", ln=True, align='C')
    pdf.ln(10)

    # جدول النتائج
    pdf.set_font("Arial", size=10)
    pdf.cell(80, 8, "Metric", border=1)
    pdf.cell(80, 8, "Value", border=1, ln=True)
    for key, value in summary.items():
        pdf.cell(80, 8, key, border=1)
        pdf.cell(80, 8, str(value), border=1, ln=True)  # ✅ حول القيمة إلى نص

    pdf.ln(10)

    # رسم Equity Curve
    filtered_df['Cumulative PnL'] = filtered_df["Net P&L"].cumsum()
    fig = px.line(filtered_df, x="Entry Time", y="Cumulative PnL", title="Cumulative Net P&L Over Time")
    fig.write_image("equity_curve.png")
    pdf.image("equity_curve.png", x=10, y=pdf.get_y(), w=180)
    pdf.ln(85)

    # رسم Performance Bar
    perf = filtered_df.groupby("Ticker Symbol")["Net P&L"].sum().reset_index().sort_values(by="Net P&L", ascending=False)
    fig_bar = px.bar(perf, x="Ticker Symbol", y="Net P&L", title="Net P&L per Ticker")
    fig_bar.write_image("bar_chart.png")
    pdf.image("bar_chart.png", x=10, y=pdf.get_y(), w=180)
    pdf.ln(85)

    # رسم Win/Loss Pie Chart
    win_count = len(filtered_df[filtered_df["Net P&L"] > 0])
    loss_count = len(filtered_df[filtered_df["Net P&L"] <= 0])
    fig_pie = px.pie(
        names=["Wins", "Losses"],
        values=[win_count, loss_count],
        title="Win vs Loss Distribution"
    )
    fig_pie.write_image("pie_chart.png")
    pdf.image("pie_chart.png", x=10, y=pdf.get_y(), w=150)

    pdf_file = f"dashboard_summary_{user}.pdf"
    pdf.output(pdf_file)
    return pdf_file


# صفحة الداشبورد
def dashboard_page():
    st.header("📈 Trading Performance Dashboard")
    client = connect_gsheet()

    if "username" in st.session_state:
        user = st.session_state["username"]
        try:
            sheet = client.open("Trading_Journal_Master").worksheet(user)
            df = pd.DataFrame(sheet.get_all_records())
        except gspread.exceptions.WorksheetNotFound:
            st.warning("⚠️ No data found for this user.")
            return

        if df.empty:
            st.warning("⚠️ No trades recorded yet.")
            return

        df["Entry Time"] = pd.to_datetime(df["Entry Time"], errors="coerce")
        df["Net P&L"] = pd.to_numeric(df["Net P&L"], errors="coerce")
        df = df.dropna(subset=["Entry Time"])

    # فلتر التاريخ
    st.subheader("📅 Filter by Date Range")
    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1))
    end_date = st.date_input("End Date", value=datetime.now())
    end_date_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    filtered = df[
        (df["Entry Time"] >= pd.to_datetime(start_date)) &
        (df["Entry Time"] <= end_date_dt)
    ]

    if filtered.empty:
        st.warning("⚠️ No trades found for the selected period.")
        return

    # حساب الإحصائيات
    total_trades = len(filtered)
    winning_trades = filtered[filtered["Net P&L"] > 0]
    losing_trades = filtered[filtered["Net P&L"] <= 0]
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    avg_win = winning_trades["Net P&L"].mean() if not winning_trades.empty else 0
    avg_loss = losing_trades["Net P&L"].mean() if not losing_trades.empty else 0
    total_pnl = filtered["Net P&L"].sum()
    avg_r = filtered["R Multiple"].mean()
    max_gain = filtered["Net P&L"].max()
    max_loss = filtered["Net P&L"].min()

    # عرض المقاييس
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Trades", total_trades)
        st.metric("Win Rate %", f"{win_rate:.2f}%")
    with col2:
        st.metric("Total Net P&L", f"${total_pnl:.2f}")
        st.metric("Average R Multiple", f"{avg_r:.2f}")
    with col3:
        st.metric("Max Gain", f"${max_gain:.2f}")
        st.metric("Max Loss", f"${max_loss:.2f}")

    # رسم منحنى الربح التراكمي
    st.subheader("📈 Equity Curve")
    filtered['Cumulative PnL'] = filtered["Net P&L"].cumsum()
    fig = px.line(filtered, x="Entry Time", y="Cumulative PnL", title="Cumulative Net P&L Over Time")
    st.plotly_chart(fig)

    # أداء الأسهم حسب Ticker
    st.subheader("🏷️ Performance by Ticker Symbol")
    perf = filtered.groupby("Ticker Symbol")["Net P&L"].sum().reset_index().sort_values(by="Net P&L", ascending=False)
    fig_bar = px.bar(perf, x="Ticker Symbol", y="Net P&L", title="Net P&L per Ticker")
    st.plotly_chart(fig_bar)

        # رسم Pie Chart يوضح نسبة الصفقات الرابحة مقابل الخاسرة
    st.subheader("🥧 Win vs Loss Distribution")
    pie_data = pd.DataFrame({
        "Result": ["Winning Trades", "Losing Trades"],
        "Count": [len(winning_trades), len(losing_trades)]
    })

    fig_pie = px.pie(pie_data, names="Result", values="Count", title="Win vs Loss Breakdown")
    st.plotly_chart(fig_pie)


    # ملخص للـ PDF
    summary = {
        "Total Trades": total_trades,
        "Win Rate %": f"{win_rate:.2f}%",
        "Total Net P&L": f"${total_pnl:.2f}",
        "Average Win": f"${avg_win:.2f}",
        "Average Loss": f"${avg_loss:.2f}",
        "Average R Multiple": f"{avg_r:.2f}",
        "Max Gain": f"${max_gain:.2f}",
        "Max Loss": f"${max_loss:.2f}"
    }

    # زر تصدير الداشبورد كـ PDF
    if st.button("📥 Export Dashboard Summary to PDF"):
        pdf_file = export_dashboard_summary_to_pdf(summary, user, filtered)
        with open(pdf_file, "rb") as f:
            st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")


# صفحة التوثيق
def documentation_page():
    st.header("📚 Documentation — User Guide")

    st.subheader("1️⃣ Risk Management Page")
    st.write("""
    - **Account Balance**: Your total trading capital.
    - **Commission per Share**: The broker's fee per share.
    - **Risk % per Trade**: How much of your capital you're willing to risk in one trade (recommended: 1%–2%).
    - **Entry Price / Stop Loss**: Define entry and exit conditions.
    - **R/R Ratio**: Desired Reward-to-Risk ratio.
    - After calculation, you'll see position size, potential reward, risk amount, and smart tips.
    """)

    st.subheader("2️⃣ Add Trade Page")
    st.write("""
    - Add every trade with its details: entry, exit, size, stop loss, target price.
    - You can also note down the indicator and strategy you used.
    - The trade gets stored automatically in your personal journal file.
    """)

    st.subheader("3️⃣ Trade Journal Page")
    st.write("""
    - View and filter all your saved trades by ticker and date range.
    - Export your trades as a PDF.
    - Delete unwanted trades with confirmation prompts.
    """)

    st.subheader("4️⃣ Dashboard Page")
    st.write("""
    - See key trading stats: Win Rate, Average R, Max Gain/Loss.
    - Visual equity curve to track cumulative performance.
    - Performance by ticker symbols.
    - Export a full dashboard summary (with charts) as a PDF.
    """)

    st.subheader("💡 Key Definitions")
    st.markdown("""
    - **Position Size**: Number of shares you can trade without exceeding your max risk.
    - **R/R Ratio**: Reward-to-Risk ratio — aim for at least 2:1.
    - **Net P&L**: Profit or Loss after fees.
    - **R Multiple**: Profit/Loss relative to initial risk — >1 is good, <1 means loss or small gain.
    - **Equity Curve**: Visual graph of your cumulative trading results.
    """)

    st.subheader("💡 Pro Tips for Traders")
    st.markdown("""
    - Never risk more than 2% of your capital on a single trade.
    - Stick to your plan and avoid revenge trading.
    - Review your journal regularly to learn from mistakes.
    - Trade with discipline — not emotions.
    """)

    st.success("This guide will always be here to help you master your trading dashboard! 🚀")

# ⬇️ هنا أضف:
def settings_page():
    st.header("⚙️ Settings — App Configuration")
    st.write("Here you can set the default values the app will use for all calculations ⬇️")

    commission_per_share = st.number_input("Commission Per Share ($)", value=st.session_state.get("commission_per_share", 0.02), step=0.001)
    st.session_state["commission_per_share"] = commission_per_share

    min_commission = st.number_input("Minimum Total Commission (Buy + Sell) $", value=st.session_state.get("min_commission", 3.98), step=0.01)
    st.session_state["min_commission"] = min_commission

    default_risk_pct = st.number_input("Default Risk % per Trade", value=st.session_state.get("default_risk_pct", 2.0), step=0.1)
    st.session_state["default_risk_pct"] = default_risk_pct

    cash_buffer_pct = st.number_input("Cash Buffer % (Reserve from account balance)", value=st.session_state.get("cash_buffer_pct", 1.0), step=0.1)
    st.session_state["cash_buffer_pct"] = cash_buffer_pct

    if st.button("✅ Save Settings"):
        st.success("Settings saved successfully! 🎯")


# التطبيق الأساسي main
def main():
    set_dark_theme()
    if "username" not in st.session_state:
        login_signup()
    else:
        user = st.session_state["username"]
          # تنبيه في الـ sidebar لو في صفقات فيها R أقل من 1
        client = connect_gsheet()
        try:
            sheet = client.open("Trading_Journal_Master").worksheet(user)
            df = pd.DataFrame(sheet.get_all_records())
            low_r_trades = df[df["R Multiple"] < 1]
            if not low_r_trades.empty:
                st.sidebar.warning(f"⚠️ Attention: You have {len(low_r_trades)} trades with R < 1.0")
        except:
            pass
        st.sidebar.image("logo.png", width=50)
        st.sidebar.title("Trading Risk Management & Journaling")
        st.sidebar.title(f"Welcome, {user}")


        # ✅ Trading Tip of the Day
        tip_index = datetime.now().day % len(trading_tips_list)
        today_tip = trading_tips_list[tip_index]
        st.sidebar.subheader("📅 Trading Tip of the Day")
        st.sidebar.info(f"💡 {today_tip}")


        page = st.sidebar.radio("Go to:", [
            "Risk Management", "Add Trade", "Trade Journal", "Dashboard", "Documentation", "Settings"
        ])


        st.sidebar.markdown(
            '''
            <style>
            .sidebar-footer {
                position: fixed;
                bottom: 20px;
                text-align: left;
                font-size: 16px;
                color: white;
            }
            </style>
            <div class="sidebar-footer">
                Designed & Developed by <strong>Ahmed Gamal</strong>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # زرار اللوج أوت
        if st.sidebar.button("🚪 Logout", key="logout"):
            if "username" in st.session_state:
                del st.session_state["username"]
                st.rerun()

        # الانتقال بين الصفحات
        if page == "Risk Management":
            risk_management_page()
        elif page == "Add Trade":
            add_trade_page()
        elif page == "Trade Journal":
            trade_journal_page()
        elif page == "Dashboard":
            dashboard_page()
        elif page == "Documentation":
            documentation_page()
        elif page == "Settings":
            settings_page()


if __name__ == "__main__":
    main()


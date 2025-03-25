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
import io

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

# تفعيل الوضع الداكن
def set_dark_theme():
    st.markdown("""
        <style>
        body {background-color: #0E1117; color: white;}
        .stApp {background-color: #0E1117;}
        </style>
    """, unsafe_allow_html=True)

# تشفير كلمة السر
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed



# شاشة تسجيل الدخول وإنشاء الحساب باستخدام Google Sheets
def login_signup():
    st.title("🔐 Login or Sign Up")
    menu = st.radio("Select:", ["Login", "Sign Up"])
    client = connect_gsheet()
    
    # تجهيز ورقة العمل لحفظ بيانات المستخدمين
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


# تمييز صفوف معينة في الجداول
def highlight_rows(row):
    highlight = "background-color: yellow; color: black"
    if row["Metric"] in ["Position Size (shares)", "Calculated Take Profit Price ($)"]:
        return [highlight, highlight]
    return ["", ""]

# صفحة إدارة المخاطر
def risk_management_page():
    st.header("📊 Risk Management")
    acc_bal = st.number_input("Account Balance ($)", min_value=0.0, value=1000.0, step=100.0)
    commission = st.number_input("Commission Per Share ($)", value=0.02, step=0.01)
    risk_pct = st.number_input("Risk % per Trade", value=2.0, step=0.1) / 100
    entry = st.number_input("Entry Price", value=100.0)
    stop = st.number_input("Stop Loss Price", value=95.0)
    rr_ratio = st.number_input("Desired R/R Ratio", value=2.0, step=0.1)

    max_loss = acc_bal * risk_pct
    st.write(f"Max Dollar Loss: ${max_loss:.2f}")

    if st.button("Calculate"):
        risk_per_share = abs(entry - stop)

        if risk_per_share < 0.01:
            st.warning("⚠️ The difference between Entry Price and Stop Loss is too small or zero.")
            st.info("💡 Tip: Increase the distance between Entry Price and Stop Loss.")
            return

        pos_size = int(max_loss / risk_per_share)
        take_profit = entry + (risk_per_share * rr_ratio)
        potential_reward = (take_profit - entry) * pos_size
        risk_dollar = pos_size * risk_per_share

        if risk_dollar == 0:
            st.warning("⚠️ Risk amount calculated as zero.")
            st.info("💡 Tip: Adjust your stop loss or entry price.")
            return

        actual_rr = potential_reward / risk_dollar
        gain_pct = (potential_reward / (pos_size * entry)) * 100

        df = pd.DataFrame({
            "Metric": [
                "Position Size (shares)", "Total Trading Fee ($)", "Risk Amount ($)", 
                "Calculated Take Profit Price ($)", "Potential Reward ($)", "Actual R/R Ratio", "Expected Gain (%)"
            ],
            "Value": [
                pos_size, f"${pos_size*commission*2:.2f}", f"${risk_dollar:.2f}", 
                f"${take_profit:.2f}", f"${potential_reward:.2f}", f"{actual_rr:.2f}", f"{gain_pct:.2f}%"
            ]
        })

        st.dataframe(df.style.apply(highlight_rows, axis=1))

        if actual_rr < 1:
            st.warning(f"⚠️ The actual R/R ratio is {actual_rr:.2f}, which is below 1.0.")
            st.info("💡 Tip: Consider improving your stop loss or target.")

# إضافة صفقة جديدة إلى Google Sheets
def add_trade_page():
    st.header("➕ Add Trade")
    client = connect_gsheet()
    
    if "username" in st.session_state:
        user = st.session_state["username"]
        try:
            sheet = client.open("Trading_Journal_Master").worksheet(user)
        except gspread.exceptions.WorksheetNotFound:
            sheet = client.open("Trading_Journal_Master").add_worksheet(title=user, rows="1000", cols="20")
            sheet.append_row([
                "Ticker Symbol", "Trade Direction", "Entry Price", "Entry Time", "Exit Price", "Exit Time",
                "Position Size", "Risk", "Trade SL", "Target", "R Multiple", "Commission", "Net P&L",
                "Used Indicator", "Used Strategy", "Notes"
            ])
        
        ticker = st.text_input("Ticker Symbol")
        entry = st.number_input("Entry Price", step=0.1)
        exit_price = st.number_input("Exit Price", step=0.1)
        size = st.number_input("Position Size", min_value=1, step=1)
        stop = st.number_input("Stop Loss Price", step=0.1)
        target = st.number_input("Target Price", step=0.1)
        commission = st.number_input("Commission ($)", step=0.01)
        used_indicator = st.text_input("Used Indicator")
        used_strategy = st.text_input("Used Strategy")
        notes = st.text_area("Notes")

        if st.button("Save Trade"):
            risk_val = abs(entry - stop) * size
            net_pnl = ((exit_price - entry) * size) - commission
            r_multiple = net_pnl / risk_val if risk_val > 0 else 0

            trade_row = [
                ticker, "Long", entry,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), exit_price,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), size, risk_val, stop, target,
                r_multiple, commission, net_pnl, used_indicator, used_strategy, notes
            ]

            sheet.append_row(trade_row)
            st.success("✅ Trade successfully added to journal!")



from fpdf import FPDF
import io

# تصدير بيانات الجورنال إلى PDF
def export_journal_to_pdf(filtered_df, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Trading Journal Export for {user}", ln=True, align='C')
    pdf.ln(10)

    for index, row in filtered_df.iterrows():
        line = f"{row['Entry Time']} | {row['Ticker Symbol']} | Entry: {row['Entry Price']} | Exit: {row['Exit Price']} | P&L: {row['Net P&L']}"
        pdf.multi_cell(0, 8, line)
        pdf.ln(2)

    pdf_file = f"trading_journal_{user}.pdf"
    pdf.output(pdf_file)
    return pdf_file

# صفحة الجورنال: عرض، تصدير، حذف
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

        ticker_filter = st.text_input("Filter by Ticker Symbol (optional)")
        date_filter_start = st.date_input("From Date", value=datetime(2023, 1, 1))
        date_filter_end = st.date_input("To Date", value=datetime.now())
        date_filter_end_datetime = pd.to_datetime(date_filter_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        df["Entry Time"] = pd.to_datetime(df["Entry Time"], errors="coerce")

        filtered_df = df.copy()
        if ticker_filter:
            filtered_df = filtered_df[filtered_df["Ticker Symbol"].str.contains(ticker_filter, case=False)]

        filtered_df = filtered_df[
            (filtered_df["Entry Time"] >= pd.to_datetime(date_filter_start)) &
            (filtered_df["Entry Time"] <= date_filter_end_datetime)
        ]

        if filtered_df.empty:
            st.warning("⚠️ No trades found for the selected period.")
            return

        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        # تصدير الجورنال إلى PDF
        if st.button("📥 Export Journal to PDF"):
            pdf_file = export_journal_to_pdf(filtered_df, user)
            with open(pdf_file, "rb") as f:
                st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")

        # حذف الصفقات
        st.subheader("🗑️ Delete Trades:")
        for idx, row in filtered_df.iterrows():
            summary = f"{row['Ticker Symbol']} | Entry: {row['Entry Price']} | Exit: {row['Exit Price']} | P&L: {row['Net P&L']}"
            if st.button(f"❌ Delete: {summary}", key=f"del_{idx}"):
                st.warning(f"Are you sure you want to delete this trade?\n{summary}")
                if st.button(f"✅ Confirm Delete: {summary}", key=f"confirm_{idx}"):
                    all_data = sheet.get_all_records()
                    df_all = pd.DataFrame(all_data)
                    df_new = df_all[
                        ~((df_all["Entry Time"] == row["Entry Time"]) & (df_all["Ticker Symbol"] == row["Ticker Symbol"]))
                    ]
                    # إعادة كتابة الشيت
                    sheet.clear()
                    sheet.append_row(list(df_new.columns))
                    for i, record in df_new.iterrows():
                        sheet.append_row(record.tolist())
                    st.success(f"✅ Deleted trade: {summary}")
                    st.experimental_rerun()


import io

# تصدير ملخص الداشبورد إلى PDF
def export_dashboard_summary_to_pdf(summary, user, filtered_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Dashboard Summary Export for {user}", ln=True, align='C')
    pdf.ln(10)

    for key, value in summary.items():
        pdf.cell(0, 10, f"{key}: {value}", ln=True)

    # رسم Equity Curve
    filtered_df['Cumulative PnL'] = filtered_df["Net P&L"].cumsum()
    fig, ax = plt.subplots()
    ax.plot(filtered_df['Entry Time'], filtered_df["Cumulative PnL"], marker='o')
    ax.set_title("Cumulative Net P&L Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative PnL")

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png")
    plt.close(fig)
    img_buf.seek(0)

    pdf.image(img_buf, x=10, y=pdf.get_y(), w=180)
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

        filtered["R Multiple"] = pd.to_numeric(filtered["R Multiple"], errors="coerce")

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

        # رسم Equity Curve
        st.subheader("📈 Equity Curve")
        filtered['Cumulative PnL'] = filtered["Net P&L"].cumsum()
        fig = px.line(filtered, x="Entry Time", y="Cumulative PnL", title="Cumulative Net P&L Over Time")
        st.plotly_chart(fig)

        # أداء حسب الأسهم
        st.subheader("🏷️ Performance by Ticker Symbol")
        perf = filtered.groupby("Ticker Symbol")["Net P&L"].sum().reset_index().sort_values(by="Net P&L", ascending=False)
        fig_bar = px.bar(perf, x="Ticker Symbol", y="Net P&L", title="Net P&L per Ticker")
        st.plotly_chart(fig_bar)

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

        # تصدير الداشبورد PDF
        if st.button("📥 Export Dashboard Summary to PDF"):
            pdf_file = export_dashboard_summary_to_pdf(summary, user, filtered)
            with open(pdf_file, "rb") as f:
                st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")

# صفحة الوثائق (Documentation)
def documentation_page():
    st.header("📚 Documentation — User Guide")

    st.subheader("1️⃣ Risk Management Page")
    st.write("""
    - Define your trading capital, commissions, entry/stop, and target.
    - Calculate position size, risk-reward ratio, and gain expectations.
    """)

    st.subheader("2️⃣ Add Trade Page")
    st.write("""
    - Log every trade with entry/exit prices, size, stop loss, and strategy used.
    """)

    st.subheader("3️⃣ Trade Journal Page")
    st.write("""
    - View, filter, and delete trades.
    - Export your journal as a PDF for your records.
    """)

    st.subheader("4️⃣ Dashboard Page")
    st.write("""
    - See performance metrics, equity curve, and breakdown by ticker.
    - Export a PDF summary including charts and stats.
    """)

    st.subheader("💡 Pro Trading Tips")
    st.markdown("""
    - Never risk more than 2% of your capital per trade.
    - Follow your plan and avoid emotional decisions.
    - Review and learn from your journal regularly.
    """)

    st.success("All the tools you need to become a disciplined trader! 🚀")




# التطبيق الأساسي
def main():
    set_dark_theme()
    if "username" not in st.session_state:
        login_signup()
    else:
        user = st.session_state["username"]
        st.sidebar.image("logo.png", width=100)
        st.sidebar.title("Trading Risk Management & Journaling")
        st.sidebar.title(f"Welcome, {user}")

        page = st.sidebar.radio("Go to:", [
            "Risk Management", "Add Trade", "Trade Journal", "Dashboard", "Documentation"
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

        if st.sidebar.button("🚪 Logout", key="logout"):
            if "username" in st.session_state:
                del st.session_state["username"]
                st.stop()

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


if __name__ == "__main__":
    main()

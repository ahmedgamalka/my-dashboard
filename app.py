import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import os
import io
from fpdf import FPDF
from hashlib import sha256
from datetime import datetime

st.set_page_config(
    page_title="Trading Journal",
    page_icon="https://raw.githubusercontent.com/ahmedgamalka/my-dashboard/refs/heads/main/favicon.ico"
)


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

# شاشة تسجيل الدخول وإنشاء حساب
def login_signup():
    st.title("🔐 Login or Sign Up")
    menu = st.radio("Select:", ["Login", "Sign Up"])
    if menu == "Sign Up":
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        if st.button("Create Account"):
            if new_user and new_password:
                users_df = pd.read_csv("users.csv") if os.path.exists("users.csv") else pd.DataFrame(columns=["username", "password_hash"])
                if new_user in users_df["username"].values:
                    st.warning("Username already exists!")
                else:
                    new_entry = pd.DataFrame([{"username": new_user, "password_hash": hash_password(new_password)}])
                    users_df = pd.concat([users_df, new_entry], ignore_index=True)
                    users_df.to_csv("users.csv", index=False)
                    st.success("Account created! You can now login.")
    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if os.path.exists("users.csv"):
                users_df = pd.read_csv("users.csv")
                if username in users_df["username"].values:
                    hashed = users_df.loc[users_df["username"] == username, "password_hash"].values[0]
                    if verify_password(password, hashed):
                        st.session_state["username"] = username
                        st.rerun()
                    else:
                        st.error("Wrong password!")
                else:
                    st.warning("Username does not exist.")
            else:
                st.warning("No users found. Please sign up first.")

# تمييز صفوف معينة في الجداول
def highlight_rows(row):
    highlight = "background-color: yellow; color: black"
    if row["Metric"] in ["Position Size (shares)", "Calculated Take Profit Price ($)"]:
        return [highlight, highlight]
    return ["", ""]

# صفحة إدارة المخاطر

def risk_management_page(journal_file):
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

        # ✅ التحقق من قيمة الفارق بين الدخول ووقف الخسارة
        if risk_per_share < 0.01:
            st.warning("⚠️ The difference between Entry Price and Stop Loss is too small or zero.")
            st.info("💡 Tip: Increase the distance between Entry Price and Stop Loss to allow proper risk calculations.")
            return

        pos_size = int(max_loss / risk_per_share)
        take_profit = entry + (risk_per_share * rr_ratio)
        potential_reward = (take_profit - entry) * pos_size
        risk_dollar = pos_size * risk_per_share

        # ✅ التحقق من أن المخاطرة بالدولار ليست صفر
        if risk_dollar == 0:
            st.warning("⚠️ Risk amount calculated as zero. Please adjust your stop loss or entry price.")
            st.info("💡 Tip: Make sure there's a meaningful difference between Entry and Stop Loss prices.")
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

        # ✅ نصيحة إضافية لو R/R أقل من 1
        if actual_rr < 1:
            st.warning(f"⚠️ The actual R/R ratio is {actual_rr:.2f}, which is below 1.0.")
            st.info("💡 Tip: Consider adjusting your stop loss or target to improve the reward-to-risk ratio.")


# إضافة صفقة جديدة
def add_trade_page(journal_file):
    st.header("➕ Add Trade")
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

        trade = {
            "Ticker Symbol": ticker, "Trade Direction": "Long", "Entry Price": entry, 
            "Entry Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Exit Price": exit_price, "Exit Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Position Size": size, "Risk": risk_val, "Risk Percentage": "", "Trade SL": stop, 
            "Target": target, "R Multiple": r_multiple, "Commission": commission, "Net P&L": net_pnl, 
            "Custom Close": "", "Used Indicator": used_indicator, "Used Strategy": used_strategy, "Notes": notes
        }

        df = pd.read_csv(journal_file)
        df = pd.concat([df, pd.DataFrame([trade])], ignore_index=True)
        df.to_csv(journal_file, index=False)
        st.success("✅ Trade successfully added to journal!")

# عرض وتصفية وحذف الصفقات
from fpdf import FPDF

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

def trade_journal_page(journal_file):
    st.header("📁 Trade Journal")
    df = pd.read_csv(journal_file)
    df["Entry Time"] = pd.to_datetime(df["Entry Time"], errors="coerce")
    df = df.dropna(subset=["Entry Time"])

    st.write(f"Total Trades Recorded: {len(df)}")
    ticker_filter = st.text_input("Filter by Ticker Symbol (optional)")
    date_filter_start = st.date_input("From Date", value=datetime(2023, 1, 1))
    date_filter_end = st.date_input("To Date", value=datetime.now())
    date_filter_end_datetime = pd.to_datetime(date_filter_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    st.session_state.date_filter_start = date_filter_start
    st.session_state.date_filter_end = date_filter_end
    
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

    # زرار التصدير كـ PDF
    if st.button("📥 Export Journal to PDF"):
        pdf_file = export_journal_to_pdf(filtered_df, st.session_state['username'])
        with open(pdf_file, "rb") as f:
            st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")

    st.subheader("🗑️ Delete Trades:")
    for idx, row in filtered_df.iterrows():
        summary = f"{row['Ticker Symbol']} | Entry: {row['Entry Price']} | Exit: {row['Exit Price']} | P&L: {row['Net P&L']}"
        if st.button(f"❌ Delete: {summary}", key=f"del_{idx}"):
            st.warning(f"Are you sure you want to delete this trade?\n{summary}")
            if st.button(f"✅ Confirm Delete: {summary}", key=f"confirm_{idx}"):
                df = df.drop(row.name).reset_index(drop=True)
                df.to_csv(journal_file, index=False)
                st.success(f"✅ Deleted trade: {summary}")
                st.experimental_rerun()

# داشبورد التحليل
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

def dashboard_page(journal_file):
    st.header("📈 Trading Performance Dashboard")
    df = pd.read_csv(journal_file)
    df["Entry Time"] = pd.to_datetime(df["Entry Time"], errors="coerce")
    df = df.dropna(subset=["Entry Time"])

    if "dash_start" not in st.session_state:
        st.session_state.dash_start = datetime(2023, 1, 1)
    if "dash_end" not in st.session_state:
        st.session_state.dash_end = datetime.now()

    st.subheader("📅 Filter by Date Range")
    start_date = st.date_input("Start Date", value=st.session_state.dash_start)
    end_date = st.date_input("End Date", value=st.session_state.dash_end)
    st.session_state.dash_start = start_date
    st.session_state.dash_end = end_date

    end_date_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    filtered = df[
        (df["Entry Time"] >= pd.to_datetime(start_date)) &
        (df["Entry Time"] <= end_date_dt)
    ]

    if filtered.empty:
        st.warning("⚠️ No trades found for the selected period.")
        return

    # تحويل الأعمدة الرقمية للتأكد من عدم وجود مشاكل
    filtered["Net P&L"] = pd.to_numeric(filtered["Net P&L"], errors="coerce")
    filtered["R Multiple"] = pd.to_numeric(filtered["R Multiple"], errors="coerce")

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
    fig = px.line(filtered, y="Cumulative PnL", title="Cumulative Net P&L Over Time")
    st.plotly_chart(fig)

    # أداء الأسهم حسب Ticker
    st.subheader("🏷️ Performance by Ticker Symbol")
    perf = filtered.groupby("Ticker Symbol")["Net P&L"].sum().reset_index().sort_values(by="Net P&L", ascending=False)
    fig_bar = px.bar(perf, x="Ticker Symbol", y="Net P&L", title="Net P&L per Ticker")
    st.plotly_chart(fig_bar)

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

    # زرار تصدير الـ Dashboard كـ PDF
    if st.button("📥 Export Dashboard Summary to PDF"):
        pdf_file = export_dashboard_summary_to_pdf(summary, st.session_state['username'], filtered)
        with open(pdf_file, "rb") as f:
            st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")

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



# التطبيق الأساسي
def main():
    set_dark_theme()
    if "username" not in st.session_state:
        login_signup()
    else:
        user = st.session_state["username"]
        journal_file = f"trades_journal_{user}.csv"
        if not os.path.exists(journal_file):
            pd.DataFrame(columns=[
                "Ticker Symbol", "Trade Direction", "Entry Price", "Entry Time", "Exit Price", "Exit Time", 
                "Position Size", "Risk", "Risk Percentage", "Trade SL", "Target", "R Multiple", 
                "Commission", "Net P&L", "Custom Close", "Used Indicator", "Used Strategy", "Notes"
            ]).to_csv(journal_file, index=False)

        st.sidebar.image("logo.png", width=100)
        st.sidebar.title("Trading Risk Management & Journaling")
        st.sidebar.title(f"Welcome, {user}")
        page = st.sidebar.radio("Go to:", ["Risk Management", "Add Trade", "Trade Journal", "Dashboard", "Documentation"])

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
            risk_management_page(journal_file)
        elif page == "Add Trade":
            add_trade_page(journal_file)
        elif page == "Trade Journal":
            trade_journal_page(journal_file)
        elif page == "Dashboard":
            dashboard_page(journal_file)
        elif page == "Documentation":
            documentation_page()

if __name__ == "__main__":
    main()

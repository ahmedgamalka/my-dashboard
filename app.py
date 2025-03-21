import streamlit as st
import pandas as pd
import plotly.express as px
import os
from hashlib import sha256
from datetime import datetime

st.set_page_config(page_title="Trading Journal", page_icon="📈")

def set_dark_theme():
    st.markdown("""
        <style>
        body {background-color: #0E1117; color: white;}
        .stApp {background-color: #0E1117;}
        </style>
    """, unsafe_allow_html=True)

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

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

def highlight_rows(row):
    highlight = "background-color: yellow; color: black"
    if row["Metric"] in ["Position Size (shares)", "Calculated Take Profit Price ($)"]:
        return [highlight, highlight]
    return ["", ""]

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
        pos_size = int(max_loss / risk_per_share)
        take_profit = entry + (risk_per_share * rr_ratio)
        potential_reward = (take_profit - entry) * pos_size
        risk_dollar = pos_size * risk_per_share
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

def trade_journal_page(journal_file):
    st.header("📁 Trade Journal")
    df = pd.read_csv(journal_file)
    st.write(f"Total Trades Recorded: {len(df)}")

    ticker_filter = st.text_input("Filter by Ticker Symbol (optional)")
    date_filter_start = st.date_input("From Date", value=datetime(2023, 1, 1))
    date_filter_end = st.date_input("To Date", value=datetime.now())

    filtered_df = df.copy()
    if ticker_filter:
        filtered_df = filtered_df[filtered_df["Ticker Symbol"].str.contains(ticker_filter, case=False)]

    filtered_df["Entry Time"] = pd.to_datetime(filtered_df["Entry Time"], errors="coerce")
    filtered_df = filtered_df[
        (filtered_df["Entry Time"] >= pd.to_datetime(date_filter_start)) &
        (filtered_df["Entry Time"] <= pd.to_datetime(date_filter_end))
    ]

    if filtered_df.empty:
        st.warning("⚠️ No trades found for the selected period.")
        return

    st.dataframe(filtered_df.reset_index(drop=True))

    st.subheader("🗑️ Delete Trades:")
    for idx, row in filtered_df.iterrows():
        summary = f"{row['Ticker Symbol']} | Entry: {row['Entry Price']} | Exit: {row['Exit Price']}"
        if st.button(f"❌ Delete: {summary}", key=f"del_{idx}"):
            df.drop(index=idx, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.to_csv(journal_file, index=False)
            st.success(f"✅ Deleted trade: {summary}")
            st.rerun()

def dashboard_page():
    st.header("📈 Trading Performance Dashboard")

    df = pd.read_csv(journal_file)
    if df.empty:
        st.warning("No trades recorded yet.")
        return

    st.subheader("📅 Filter by Date Range:")
    date_filter_start = st.date_input("From Date", value=datetime(2023, 1, 1), key="dash_start")
    date_filter_end = st.date_input("To Date", value=datetime.now(), key="dash_end")

    df["Entry Time"] = pd.to_datetime(df["Entry Time"], errors="coerce")
    filtered_df = df[
        (df["Entry Time"] >= pd.to_datetime(date_filter_start)) &
        (df["Entry Time"] <= pd.to_datetime(date_filter_end))
    ]

    if filtered_df.empty:
        st.warning("⚠️ No trades found for the selected period.")
        return

    filtered_df["Net P&L"] = pd.to_numeric(filtered_df["Net P&L"], errors="coerce")
    filtered_df["R Multiple"] = pd.to_numeric(filtered_df["R Multiple"], errors="coerce")

    total_trades = len(filtered_df)
    winning_trades = filtered_df[filtered_df["Net P&L"] > 0]
    losing_trades = filtered_df[filtered_df["Net P&L"] <= 0]
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    avg_win = winning_trades["Net P&L"].mean() if not winning_trades.empty else 0
    avg_loss = losing_trades["Net P&L"].mean() if not losing_trades.empty else 0
    total_pnl = filtered_df["Net P&L"].sum()
    avg_r = filtered_df["R Multiple"].mean()
    max_gain = filtered_df["Net P&L"].max()
    max_loss = filtered_df["Net P&L"].min()

    st.metric("Total Trades", total_trades)
    st.metric("Win Rate %", f"{win_rate:.2f}%")
    st.metric("Total Net P&L", f"${total_pnl:.2f}")
    st.metric("Average R Multiple", f"{avg_r:.2f}")
    st.metric("Max Gain", f"${max_gain:.2f}")
    st.metric("Max Loss", f"${max_loss:.2f}")

    st.subheader("📈 Equity Curve")
    filtered_df['Cumulative PnL'] = filtered_df["Net P&L"].cumsum()
    fig = px.line(filtered_df, y="Cumulative PnL", title="Cumulative Net P&L Over Time")
    st.plotly_chart(fig)

    st.subheader("🏷️ Performance by Ticker Symbol")
    ticker_perf = filtered_df.groupby("Ticker Symbol")["Net P&L"].sum().reset_index().sort_values(by="Net P&L", ascending=False)
    fig_bar = px.bar(ticker_perf, x="Ticker Symbol", y="Net P&L", title="Net P&L per Ticker")
    st.plotly_chart(fig_bar)

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

        st.sidebar.image("logo.png", width=150)
        st.sidebar.title(f"Welcome, {user}")
        page = st.sidebar.radio("Go to:", ["Risk Management", "Add Trade", "Trade Journal", "Dashboard"])

        st.sidebar.markdown(
            '''
            <style>
            .sidebar-footer {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                text-align: center;
                font-size: 14px;
                color: white;
            }
            </style>
            <div class="sidebar-footer">
                Designed & Developed by <strong>Ahmed Gamal</strong>
            </div>
            ''',
            unsafe_allow_html=True
        )

        if page == "Risk Management":
            risk_management_page(journal_file)
        elif page == "Add Trade":
            add_trade_page(journal_file)
        elif page == "Trade Journal":
            trade_journal_page(journal_file)
        elif page == "Dashboard":
            dashboard_page(journal_file)

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# ✅ Page config
st.set_page_config(
    page_title="Trading Journal",
    page_icon="favicon.ico"
)

# ✅ Dark Theme
def set_dark_theme():
    st.markdown(
        """
        <style>
        body {background-color: #0E1117; color: white;}
        .stApp {background-color: #0E1117;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ✅ Create CSV if not exists
journal_file = "trades_journal.csv"
if not os.path.exists(journal_file):
    df_empty = pd.DataFrame(columns=[
        "Ticker Symbol", "Trade Direction", "Entry Price", "Entry Time", 
        "Exit Price", "Exit Time", "Position Size", "Risk", "Risk Percentage",
        "Trade SL", "Target", "R Multiple", "Commission", "Net P&L", "Custom Close"
    ])
    df_empty.to_csv(journal_file, index=False)

# ✅ Highlight rows function
def highlight_special_rows(row):
    highlight_style = "background-color: #FFF200; color: black"
    if row["Metric"] in ["Position Size (shares)", "Calculated Take Profit Price ($)"]:
        return [highlight_style, highlight_style]
    else:
        return ["", ""]

# ✅ Risk Management Page
def risk_management_page():
    st.header("📊 Risk Management")

    account_balance = st.number_input("Account Balance ($)", min_value=0.0, value=1000.0, step=100.0)
    commission_per_share = st.number_input("Commission Per Share ($)", min_value=0.0, value=0.02, step=0.01)
    risk_percentage = st.number_input("Risk Percentage per Trade (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1) / 100
    entry_price = st.number_input("Entry Price", min_value=0.0, value=100.0, step=0.1)
    stop_loss_price = st.number_input("Stop Loss Price", min_value=0.0, value=95.0, step=0.1)
    reward_risk_ratio = st.number_input("Desired Reward/Risk Ratio (R/R)", min_value=0.1, value=2.0, step=0.1)

    max_dollar_loss = account_balance * risk_percentage
    st.write(f"📉 Max Dollar Loss Allowed: **${max_dollar_loss:.2f}**")

    if st.button("Calculate"):
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            st.error("❌ Error: Stop loss must be less than entry price.")
        else:
            reserved_capital = account_balance * 0.005
            available_capital = account_balance - reserved_capital
            raw_position_size = max_dollar_loss / risk_per_share
            estimated_commission = raw_position_size * commission_per_share * 2
            adjusted_position_size = (available_capital - estimated_commission) / (entry_price + commission_per_share * 2)
            position_size = int(min(raw_position_size, adjusted_position_size))

            total_invested = position_size * entry_price
            total_commission = position_size * commission_per_share * 2
            take_profit_price = entry_price + (risk_per_share * reward_risk_ratio)
            potential_reward = (take_profit_price - entry_price) * position_size
            actual_risk_dollar = risk_per_share * position_size
            actual_rr_ratio = potential_reward / actual_risk_dollar if actual_risk_dollar > 0 else 0
            gain_percentage = (potential_reward / total_invested) * 100 if total_invested > 0 else 0

            result_data = {
                "Metric": [
                    "Position Size (shares)", 
                    "Total Invested ($)", 
                    "Total Trading Fee ($)", 
                    "Risk Amount ($)", 
                    "Calculated Take Profit Price ($)", 
                    "Potential Reward ($)", 
                    "Actual R/R Ratio", 
                    "Expected Gain (%)"
                ],
                "Value": [
                    f"{position_size}", 
                    f"${total_invested:.2f}", 
                    f"${total_commission:.2f}", 
                    f"${actual_risk_dollar:.2f}", 
                    f"${take_profit_price:.2f}", 
                    f"${potential_reward:.2f}", 
                    f"{actual_rr_ratio:.2f}", 
                    f"{gain_percentage:.2f}%"
                ]
            }

            df = pd.DataFrame(result_data)
            st.subheader("📊 Results:")
            st.dataframe(df.style.apply(highlight_special_rows, axis=1))

            ticker_symbol = st.text_input("Ticker Symbol for this trade")
            if ticker_symbol:
                if st.button("Add Trade to Journal"):
                    trade_data = {
                        "Ticker Symbol": ticker_symbol,
                        "Trade Direction": "Long",
                        "Entry Price": entry_price,
                        "Entry Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Exit Price": "",
                        "Exit Time": "",
                        "Position Size": position_size,
                        "Risk": actual_risk_dollar,
                        "Risk Percentage": risk_percentage * 100,
                        "Trade SL": stop_loss_price,
                        "Target": take_profit_price,
                        "R Multiple": actual_rr_ratio,
                        "Commission": total_commission,
                        "Net P&L": "",
                        "Custom Close": ""
                    }
                    df_old = pd.read_csv(journal_file)
                    df_new = pd.concat([df_old, pd.DataFrame([trade_data])], ignore_index=True)
                    df_new.to_csv(journal_file, index=False)
                    st.success("✅ Trade successfully added to journal!")

# ----------------- Add Trade Page -----------------
def add_trade_page():
    st.header("➕ Add Trade to Journal")
    ticker = st.text_input("Ticker Symbol")
    entry_price = st.number_input("Entry Price", min_value=0.0, step=0.1)
    exit_price = st.number_input("Exit Price", min_value=0.0, step=0.1)
    entry_time = st.date_input("Entry Date")
    exit_time = st.date_input("Exit Date")
    position_size = st.number_input("Position Size (shares)", min_value=1, step=1)
    stop_loss_price = st.number_input("Stop Loss Price", min_value=0.0, step=0.1)
    target_price = st.number_input("Target Price", min_value=0.0, step=0.1)
    commission = st.number_input("Total Commission ($)", min_value=0.0, step=0.01)
    custom_close = st.selectbox("Custom Close?", ["No", "Yes"])

    risk_per_share = abs(entry_price - stop_loss_price)
    total_risk = risk_per_share * position_size
    r_multiple = ((exit_price - entry_price) * position_size - commission) / total_risk if total_risk > 0 else 0
    net_pnl = ((exit_price - entry_price) * position_size) - commission

    if st.button("Save Trade"):
        trade_data = {
            "Ticker Symbol": ticker,
            "Trade Direction": "Long",
            "Entry Price": entry_price,
            "Entry Time": entry_time.strftime("%Y-%m-%d"),
            "Exit Price": exit_price,
            "Exit Time": exit_time.strftime("%Y-%m-%d"),
            "Position Size": position_size,
            "Risk": total_risk,
            "Risk Percentage": "",
            "Trade SL": stop_loss_price,
            "Target": target_price,
            "R Multiple": round(r_multiple, 2),
            "Commission": commission,
            "Net P&L": round(net_pnl, 2),
            "Custom Close": custom_close
        }
        df_old = pd.read_csv(journal_file)
        df_new = pd.concat([df_old, pd.DataFrame([trade_data])], ignore_index=True)
        df_new.to_csv(journal_file, index=False)
        st.success("✅ Trade successfully added to journal!")

# ----------------- Trade Journal Page -----------------
def trade_journal_page():
    st.header("📁 Trade Journal")
    df = pd.read_csv(journal_file)
    st.dataframe(df)

    st.subheader("🗑️ Delete Trades:")
    for idx, row in df.iterrows():
        if st.button(f"❌ Delete Trade ID {idx}", key=f"del_{idx}"):
            df.drop(index=idx, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.to_csv(journal_file, index=False)
            st.success("✅ Trade deleted.")
            st.experimental_rerun()

# ------------------ Dashboard Page ------------------
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


# ----------------- Main & Sidebar -----------------
def main():
    set_dark_theme()

    st.sidebar.image("logo.png", width=140)
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] img {
            display: block;
            width: 100%;
            margin-left: auto;
            margin-right: auto;
            align: center;
            animation: fadeIn 1.5s ease-in-out;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: scale(0.9); }
            100% { opacity: 1; transform: scale(1); }
        }
        .sidebar-footer {
            position: fixed;
            bottom: 20px;
            left: 75%;
            transform: translateX(-50%);
            text-align: center;
            font-size: 15px;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.title("Trading Risk Management & Journaling")
    page = st.sidebar.radio("Go to:", ["Risk Management", "Add Trade", "Trade Journal", "Dashboard"])

    # الملكية مثبتة في أسفل الـ sidebar
    st.sidebar.markdown(
        """
        <style>
        .sidebar-footer {
            position: fixed;
            bottom: 20px;
            text-align: center;
            width: 100%;
            font-size: 15px;
        }
        </style>
        <div class="sidebar-footer">
            Designed & Developed by <strong>Ahmed Gamal</strong>
        </div>
        """, 
        unsafe_allow_html=True
    )


    if page == "Risk Management":
        risk_management_page()
    elif page == "Add Trade":
         add_trade_page()
    elif page == "Trade Journal":
         trade_journal_page()
    elif page == "Dashboard":
         dashboard_page()

if __name__ == "__main__":
    main()

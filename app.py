
import streamlit as st
import pandas as pd
import plotly.express as px
import os
from hashlib import sha256
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Trading Journal", page_icon="📈")

# --- Dark Theme ---
def set_dark_theme():
    st.markdown(
        '''
        <style>
        body {background-color: #0E1117; color: white;}
        .stApp {background-color: #0E1117;}
        </style>
        ''',
        unsafe_allow_html=True,
    )

# --- Hashing Passwords ---
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# --- Login / Signup Page ---
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
                        st.success(f"Welcome {username}!")
                        st.session_state["username"] = username
                        st.rerun()
                    else:
                        st.error("Wrong password!")
                else:
                    st.warning("Username does not exist.")
            else:
                st.warning("No users found. Please sign up first.")

# باقي الوظائف (Risk Management, Add Trade, إلخ.) يمكن إضافتها في نفس الطريقة.

# --- Main Function ---
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
        page = st.sidebar.radio("Go to:", ["Risk Management", "Add Trade"])

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
            pass  # استدعاء الدالة الخاصة بإدارة المخاطر
        elif page == "Add Trade":
            pass  # استدعاء الدالة الخاصة بإضافة الصفقات

if __name__ == "__main__":
    main()

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# பக்கத்தின் அமைப்பு
st.set_page_config(page_title="எரிபொருள் நிலைய மேலாண்மை", page_icon="⛽", layout="centered")

# Database Setup
def init_db():
    conn = sqlite3.connect("fuel_station.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            fuel_type TEXT PRIMARY KEY,
            price_per_liter REAL,
            available_liters REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fuel_type TEXT,
            liters REAL,
            base_amount REAL,
            gst_amount REAL,
            total_amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Petrol, Diesel & Kerosene (மண்ணெண்ணெய்)
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Petrol', 310.0, 5000.0)")
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Diesel', 280.0, 5000.0)")
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Kerosene', 230.0, 5000.0)")
    conn.commit()
    conn.close()

init_db()

st.title("⛽ எரிபொருள் நிலைய மேலாண்மை")
st.write("மொபைல் பயன்பாட்டிற்கான பிரத்யேக மென்பொருள்")

# 1. Stock Display Section
st.subheader("📊 தற்போதைய கையிருப்பு விவரம்")
conn = sqlite3.connect("fuel_station.db")
stock_df = pd.read_sql_query("SELECT fuel_type AS 'எரிபொருள்', price_per_liter AS 'விலை/லிட்டர் (Rs)', available_liters AS 'கையிருப்பு (Liters)' FROM stock", conn)
st.dataframe(stock_df, use_container_width=True)

# 2. Billing Section
st.subheader("💳 புதிய பில்லிங் செய்ய")
with st.form("billing_form"):
    fuel_type = st.selectbox("எரிபொருள் வகையைத் தேர்ந்தெடுக்கவும்", ["Petrol", "Diesel", "Kerosene"])
    total_amount = st.number_input("மொத்த தொகை (LKR - GST உட்பட)", min_value=1.0, step=50.0)
    
    submitted = st.form_submit_button("பில் சேமிக்கவும்")

if submitted:
    cursor = conn.cursor()
    cursor.execute("SELECT price_per_liter, available_liters FROM stock WHERE fuel_type=?", (fuel_type,))
    result = cursor.fetchone()

    if result is None:
        st.error("⚠️ தேர்வு செய்யப்பட்ட எரிபொருள் தரவுத்தளத்தில் இல்லை!")
    else:
        price, stock = result
        liters_needed = total_amount / price

        if liters_needed > stock:
            st.error("⚠️ போதிய கையிருப்பு இல்லை!")
        else:
            gst_rate = 0.05
            base_amount = total_amount / (1 + gst_rate)
            gst_amount = total_amount - base_amount
            new_stock = stock - liters_needed

            cursor.execute("UPDATE stock SET available_liters=? WHERE fuel_type=?", (new_stock, fuel_type))
            cursor.execute(
                "INSERT INTO sales (fuel_type, liters, base_amount, gst_amount, total_amount) VALUES (?, ?, ?, ?, ?)",
                (fuel_type, liters_needed, base_amount, gst_amount, total_amount)
            )
            conn.commit()

            st.success(f"✅ பில் வெற்றிகரமாகப் பதிவானது!\n\n"
                       f"• எரிபொருள்: {fuel_type}\n"
                       f"• அளவு: {liters_needed:.2f} L\n"
                       f"• அடிப்படைத் தொகை: Rs.{base_amount:.2f}\n"
                       f"• GST (5%): Rs.{gst_amount:.2f}\n"
                       f"• மொத்த தொகை: Rs.{total_amount:.2f}")
            st.rerun()

# 3. Report Section
st.subheader("📥 விற்பனை அறிக்கை (Excel)")
sales_df = pd.read_sql_query("SELECT id AS 'Bill ID', date AS 'தேதி', fuel_type AS 'வகை', liters AS 'லிட்டர்', base_amount AS 'அடிப்படை தொகை', gst_amount AS 'GST 5%', total_amount AS 'மொத்த தொகை' FROM sales", conn)

if not sales_df.empty:
    st.dataframe(sales_df.tail(5), use_container_width=True) # கடைசி 5 விற்பனைகள்
    
    # Excel Download
    today_date = datetime.now().strftime("%Y-%m-%d")
    excel_file = f"Daily_Sales_{today_date}.xlsx"
    sales_df.to_excel(excel_file, index=False, engine='openpyxl')
    
    with open(excel_file, "rb") as file:
        st.download_button(
            label="📊 Excel அறிக்கையைப் பதிவிறக்கு",
            data=file,
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("விற்பனைப் பதிவுகள் எதுவும் இல்லை.")

conn.close()

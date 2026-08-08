import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="எரிபொருள் நிலைய மேலாண்மை", page_icon="⛽", layout="centered")

# Database Setup
def init_db():
    conn = sqlite3.connect("fuel_station.db")
    cursor = conn.cursor()
    
    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('gst_rate', 5.0)")
    
    # Stock Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            fuel_type TEXT PRIMARY KEY,
            price_per_liter REAL,
            available_liters REAL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Petrol', 310.0, 5000.0)")
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Diesel', 280.0, 5000.0)")
    cursor.execute("INSERT OR IGNORE INTO stock VALUES ('Kerosene', 230.0, 5000.0)")
    
    # Sales Table
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
    conn.commit()
    conn.close()

init_db()

st.title("⛽ எரிபொருள் நிலைய மேலாண்மை")

# Database Connection
conn = sqlite3.connect("fuel_station.db")
cursor = conn.cursor()

# ----------------------------------------------------
# 1. Admin Control Panel (தகவல்களைத் திருத்தும் பகுதி)
# ----------------------------------------------------
with st.expander("🛠️ அனைத்துத் தகவல்களையும் மாற்றி அமைக்க (Admin Panel)"):
    
    st.markdown("### 1️⃣ விலை & கையிருப்பை மாற்ற")
    stock_data = pd.read_sql_query("SELECT * FROM stock", conn)
    fuel_list = stock_data['fuel_type'].tolist()
    
    with st.form("update_stock_form"):
        selected_fuel = st.selectbox("எரிபொருள் வகை", fuel_list)
        current_row = stock_data[stock_data['fuel_type'] == selected_fuel].iloc[0]
        
        new_price = st.number_input("புதிய விலை (Rs/L)", value=float(current_row['price_per_liter']), step=1.0)
        new_stock = st.number_input("புதிய கையிருப்பு (Liters)", value=float(current_row['available_liters']), step=500.0)
        
        if st.form_submit_button("விவரங்களைப் புதுப்பி"):
            cursor.execute("UPDATE stock SET price_per_liter=?, available_liters=? WHERE fuel_type=?", 
                           (new_price, new_stock, selected_fuel))
            conn.commit()
            st.success(f"✅ {selected_fuel} விவரங்கள் புதுப்பிக்கப்பட்டன!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 2️⃣ புதிய எரிபொருளைச் சேர்க்க")
    with st.form("add_fuel_form"):
        add_name = st.text_input("புதிய எரிபொருள் பெயர் (எ.கா: Octane 95)")
        add_price = st.number_input("விலை (Rs/L)", min_value=1.0, step=1.0)
        add_stock = st.number_input("ஆரம்ப கையிருப்பு (Liters)", min_value=0.0, step=500.0)
        
        if st.form_submit_button("புதிய வகை சேர்"):
            if add_name.strip():
                cursor.execute("INSERT OR REPLACE INTO stock VALUES (?, ?, ?)", (add_name.strip(), add_price, add_stock))
                conn.commit()
                st.success(f"✅ {add_name} வெற்றிகரமாகச் சேர்க்கப்பட்டது!")
                st.rerun()
            else:
                st.error("⚠️ எரிபொருள் பெயரை உள்ளிடவும்!")

    st.markdown("---")
    st.markdown("### 3️⃣ GST வரியை மாற்ற")
    cursor.execute("SELECT value FROM settings WHERE key='gst_rate'")
    current_gst = cursor.fetchone()[0]
    
    with st.form("update_gst_form"):
        new_gst = st.number_input("GST சதவிகிதம் (%)", value=float(current_gst), step=0.5)
        if st.form_submit_button("GST மாற்றுக"):
            cursor.execute("UPDATE settings SET value=? WHERE key='gst_rate'", (new_gst,))
            conn.commit()
            st.success(f"✅ GST {new_gst}% என மாற்றப்பட்டது!")
            st.rerun()

# ----------------------------------------------------
# 2. Stock Display Section
# ----------------------------------------------------
st.subheader("📊 தற்போதைய கையிருப்பு & விலை விவரம்")
stock_df = pd.read_sql_query("SELECT fuel_type AS 'எரிபொருள்', price_per_liter AS 'விலை/லிட்டர் (Rs)', available_liters AS 'கையிருப்பு (Liters)' FROM stock", conn)
st.dataframe(stock_df, use_container_width=True)

# ----------------------------------------------------
# 3. Billing Section
# ----------------------------------------------------
st.subheader("💳 புதிய பில்லிங் செய்ய")
cursor.execute("SELECT value FROM settings WHERE key='gst_rate'")
active_gst_rate = cursor.fetchone()[0] / 100.0

available_fuels = stock_df['எரிபொருள்'].tolist()

with st.form("billing_form"):
    fuel_type = st.selectbox("எரிபொருள் வகையைத் தேர்ந்தெடுக்கவும்", available_fuels)
    total_amount = st.number_input("மொத்த தொகை (LKR - GST உட்பட)", min_value=1.0, step=50.0)
    submitted = st.form_submit_button("பில் சேமிக்கவும்")

if submitted:
    cursor.execute("SELECT price_per_liter, available_liters FROM stock WHERE fuel_type=?", (fuel_type,))
    result = cursor.fetchone()

    if result:
        price, stock = result
        liters_needed = total_amount / price

        if liters_needed > stock:
            st.error("⚠️ போதிய கையிருப்பு இல்லை!")
        else:
            base_amount = total_amount / (1 + active_gst_rate)
            gst_amount = total_amount - base_amount
            new_stock = stock - liters_needed

            cursor.execute("UPDATE stock SET available_liters=? WHERE fuel_type=?", (new_stock, fuel_type))
            cursor.execute(
                "INSERT INTO sales (fuel_type, liters, base_amount, gst_amount, total_amount) VALUES (?, ?, ?, ?, ?)",
                (fuel_type, liters_needed, base_amount, gst_amount, total_amount)
            )
            conn.commit()

            st.success(f"✅ பில் பதிவானது!\n\n"
                       f"• {fuel_type}: {liters_needed:.2f} L\n"
                       f"• அடிப்படை: Rs.{base_amount:.2f}\n"
                       f"• GST ({active_gst_rate*100}%): Rs.{gst_amount:.2f}\n"
                       f"• மொத்தம்: Rs.{total_amount:.2f}")
            st.rerun()

# ----------------------------------------------------
# 4. Report Section
# ----------------------------------------------------
st.subheader("📥 விற்பனை அறிக்கை (Excel)")
sales_df = pd.read_sql_query("SELECT id AS 'Bill ID', date AS 'தேதி', fuel_type AS 'வகை', liters AS 'லிட்டர்', base_amount AS 'அடிப்படை தொகை', gst_amount AS 'GST', total_amount AS 'மொத்த தொகை' FROM sales", conn)

if not sales_df.empty:
    st.dataframe(sales_df.tail(5), use_container_width=True)
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

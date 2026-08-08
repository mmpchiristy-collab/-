import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="எரிபொருள் நிலைய மேலாண்மை", page_icon="⛽", layout="centered")

st.title("⛽ எரிபொருள் நிலைய மேலாண்மை")

# 1. Session State Initialization (தரவுகளைச் சேமிக்க)
if "stock_data" not in st.values:
    st.session_state["stock_data"] = pd.DataFrame({
        "எரிபொருள்": ["Petrol", "Diesel", "Kerosene"],
        "விலை/லிட்டர் (Rs)": [310.0, 280.0, 230.0],
        "கையிருப்பு (Liters)": [5000.0, 5000.0, 5000.0]
    })

if "gst_rate" not in st.session_state:
    st.session_state["gst_rate"] = 5.0

if "sales_history" not in st.session_state:
    st.session_state["sales_history"] = []

# ----------------------------------------------------
# 1. நேரடி அட்டவணை திருத்தம் (Interactive Table)
# ----------------------------------------------------
st.subheader("📊 கையிருப்பு & விலை விவரம் (நேரடியாக மாற்றலாம்)")
st.info("💡 கீழே உள்ள அட்டவணையில் உள்ள எண்களை நேரடியாகக் கிளிக் செய்து மாற்றிக் கொள்ளலாம்!")

# நேரடி அட்டவணை எடிட்டர்
edited_df = st.data_editor(
    st.session_state["stock_data"],
    num_rows="dynamic", # புதிய வரிசைகளைச் சேர்க்கும் வசதி
    use_container_width=True,
    key="editor"
)

# மாற்றங்களைப் புதுப்பித்தல்
st.session_state["stock_data"] = edited_df

# GST வரி மாற்றம்
with st.expander("⚙️ GST வரியை மாற்ற"):
    new_gst = st.number_input("GST சதவிகிதம் (%)", value=float(st.session_state["gst_rate"]), step=0.5)
    st.session_state["gst_rate"] = new_gst

st.markdown("---")

# ----------------------------------------------------
# 2. Billing Section
# ----------------------------------------------------
st.subheader("💳 புதிய பில்லிங் செய்ய")

fuel_options = st.session_state["stock_data"]["எரிபொருள்"].tolist()

with st.form("billing_form"):
    selected_fuel = st.selectbox("எரிபொருள் வகையைத் தேர்ந்தெடுக்கவும்", fuel_options)
    total_amount = st.number_input("மொத்த தொகை (Rs - GST உட்பட)", min_value=1.0, step=50.0)
    submitted = st.form_submit_button("பில் சேமிக்கவும்")

if submitted:
    df = st.session_state["stock_data"]
    fuel_row = df[df["எரிபொருள்"] == selected_fuel]

    if not fuel_row.empty:
        price = fuel_row["விலை/லிட்டர் (Rs)"].values[0]
        current_stock = fuel_row["கையிருப்பு (Liters)"].values[0]

        if price <= 0:
            st.error("⚠️ செல்லுபடியாகும் விலையை உள்ளிடவும்!")
        else:
            liters_needed = total_amount / price

            if liters_needed > current_stock:
                st.error("⚠️ போதிய கையிருப்பு இல்லை!")
            else:
                gst_pct = st.session_state["gst_rate"] / 100.0
                base_amount = total_amount / (1 + gst_pct)
                gst_amount = total_amount - base_amount
                
                # கையிருப்பைச் சரிசெய்தல்
                st.session_state["stock_data"].loc[df["எரிபொருள்"] == selected_fuel, "கையிருப்பு (Liters)"] = current_stock - liters_needed

                # விற்பனையைப் பதிவிடுதல்
                bill_id = len(st.session_state["sales_history"]) + 1
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                st.session_state["sales_history"].append({
                    "Bill ID": bill_id,
                    "தேதி": now_str,
                    "வகை": selected_fuel,
                    "லிட்டர்": round(liters_needed, 2),
                    "அடிப்படை தொகை": round(base_amount, 2),
                    "GST": round(gst_amount, 2),
                    "மொத்த தொகை": round(total_amount, 2)
                })

                st.success(f"✅ பில் பதிவானது!\n\n"
                           f"• {selected_fuel}: {liters_needed:.2f} L\n"
                           f"• அடிப்படை: Rs.{base_amount:.2f}\n"
                           f"• GST ({st.session_state['gst_rate']}%): Rs.{gst_amount:.2f}\n"
                           f"• மொத்தம்: Rs.{total_amount:.2f}")
                st.rerun()

st.markdown("---")

# ----------------------------------------------------
# 3. Report Section
# ----------------------------------------------------
st.subheader("📥 விற்பனை அறிக்கை (Excel)")

if st.session_state["sales_history"]:
    sales_df = pd.DataFrame(st.session_state["sales_history"])
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

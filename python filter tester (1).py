import streamlit as st
import pandas as pd
import ast
import re
from collections import Counter

st.set_page_config(page_title="DC-5 Filter Tester", layout="wide")
st.title("DC-5 Filter Tester")

# --------------------
# Upload CSV of filters
# --------------------
uploaded_file = st.sidebar.file_uploader("Upload filter CSV", type=["csv"])
if uploaded_file:
    filters_df = pd.read_csv(uploaded_file)

# --------------------
# Original Inputs (unchanged)
# --------------------
st.sidebar.markdown("### Main Inputs")
generation_method = st.sidebar.selectbox("Generation Method:", ["1-digit", "other"])
hot_override = st.sidebar.text_input("Hot digits override (comma-separated):")
cold_override = st.sidebar.text_input("Cold digits override (comma-separated):")
due_override = st.sidebar.text_input("Due digits override (comma-separated):")
check_combo = st.sidebar.text_input("Check specific combo:")
hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)

# --------------------
# SAFE Standalone Hot/Cold/Due Calculator
# --------------------
st.sidebar.markdown("### Hot / Cold / Due Calculator")
calc_inputs = []
for i in range(1, 11):
    calc_inputs.append(
        st.sidebar.text_input(
            f"Calculator Draw {i}-back",
            key=f"calc_draw_safe_{i}"
        ).strip()
    )

if all(re.fullmatch(r"\d{5}", d) for d in calc_inputs):
    seq = "".join(calc_inputs)
    cnt = Counter(int(ch) for ch in seq)

    if cnt:
        # HOT: top 3 (include ties)
        sorted_counts = cnt.most_common()
        hot_min = sorted_counts[min(2, len(sorted_counts)-1)][1]
        hot = sorted([n for n, c in cnt.items() if c >= hot_min])

        # COLD: bottom 3 (include ties)
        sorted_asc = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]))
        cold_max = sorted_asc[min(2, len(sorted_asc)-1)][1]
        cold = sorted([n for n, c in cnt.items() if c <= cold_max])

        # DUE: digits missing from last 2 draws
        last2 = "".join(calc_inputs[:2])
        due = [d for d in range(10) if str(d) not in last2]

        st.sidebar.success(f"Hot digits: {hot}")
        st.sidebar.success(f"Cold digits: {cold}")
        st.sidebar.success(f"Due digits: {due}")
else:
    st.sidebar.info("Enter exactly 10 previous 5-digit draws to compute Hot/Cold/Due.")

# --------------------
# Rest of your original filter tester logic goes here
# (reading filters_df, applying filters, showing elimination counts, etc.)
# --------------------

if uploaded_file is not None:
    st.subheader("Filters loaded:")
    st.dataframe(filters_df)
    # TODO: keep your original filter execution & display code here.

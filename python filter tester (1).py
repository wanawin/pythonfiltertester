import streamlit as st
import csv
import pandas as pd
from collections import Counter

# ------------------------------
# EXISTING APP CODE (unchanged)
# ------------------------------

st.set_page_config(page_title="DC-5 Filter Tester", layout="wide")

st.title("DC-5 Filter Tester")

# ===== Existing Inputs =====
uploaded = st.sidebar.file_uploader("Upload filter CSV", type="csv")
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
hot_override = st.sidebar.text_input("Hot digits override (comma-separated):")
cold_override = st.sidebar.text_input("Cold digits override (comma-separated):")
due_override = st.sidebar.text_input("Due digits override (comma-separated):")
check_combo = st.sidebar.text_input("Check specific combo:")

hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=False)

# ===== Load CSV filters safely =====
filters = []
if uploaded is not None:
    reader = csv.DictReader(uploaded)
    for row in reader:
        filters.append(row)

if uploaded is not None:
    st.write(f"Loaded {len(filters)} filters")
    # Original app logic goes here — untouched
    # (manual filter evaluation, display, survivor counts, etc.)

# ------------------------------
# NEW: Hot/Cold/Due Calculator
# ------------------------------

st.markdown("---")
st.subheader("Hot / Cold / Due Calculator")

st.caption("Enter exactly 10 past winning numbers (5 digits each). Calculator waits until all 10 are entered.")

seed_inputs = []
for i in range(10):
    val = st.text_input(f"Draw {i+1}-back (most recent first)", key=f"hotcold_{i}")
    if val.strip():
        seed_inputs.append(val.strip())

# Only run if exactly 10 valid 5-digit entries (digits 0-9)
if len(seed_inputs) == 10 and all(s.isdigit() and len(s) == 5 for s in seed_inputs):
    flat_digits = [int(d) for s in seed_inputs for d in s]

    cnt = Counter(flat_digits)
    # Sort descending for hot, ascending for cold
    hot_sorted = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))
    cold_sorted = sorted(cnt.items(), key=lambda x: (x[1], x[0]))

    # Top 3 hot and cold with ties
    if hot_sorted:
        hot_cut = hot_sorted[min(2, len(hot_sorted)-1)][1]
        hot_digits = [d for d, c in cnt.items() if c >= hot_cut]
    else:
        hot_digits = []

    if cold_sorted:
        cold_cut = cold_sorted[min(2, len(cold_sorted)-1)][1]
        cold_digits = [d for d, c in cnt.items() if c <= cold_cut]
    else:
        cold_digits = []

    # Due digits = digits 0-9 not seen in last 2 draws (most recent two)
    last_two = seed_inputs[:2]
    recent_digits = {int(d) for s in last_two for d in s}
    due_digits = [d for d in range(10) if d not in recent_digits]

    st.success(f"**Hot digits:** {hot_digits}")
    st.info(f"**Cold digits:** {cold_digits}")
    st.warning(f"**Due digits:** {due_digits}")

else:
    st.write("⬆️ Enter 10 valid 5-digit draws to compute Hot/Cold/Due.")

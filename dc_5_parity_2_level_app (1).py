import streamlit as st
import csv
from collections import Counter

st.title("DC5 Parity Prediction (2-Level Model)")

# Input for seed digits
seed_input = st.text_input("Enter the 5 seed digits (e.g. 11323):", "")
if seed_input and len(seed_input) == 5 and seed_input.isdigit():
    seed_digits = [int(d) for d in seed_input]
    seed_sum = sum(seed_digits)
    odd_count = sum(d %2 !=0 for d in seed_digits)

    # Load filters
    filters = []
    with open("final_dc5_parity_filters.csv", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filters.append(row)

    # Level 1: Evaluate filters
    triggered_results = []
    local_vars = {
        'seed_digits': seed_digits,
        'seed_sum': seed_sum,
        'mirror': {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4},
    }

    for filt in filters:
        if eval(filt['applicable_if'], {}, local_vars):
            if eval(filt['expression'], {}, local_vars):
                if 'odd' in filt['name'].lower():
                    triggered_results.append('odd')
                elif 'even' in filt['name'].lower():
                    triggered_results.append('even')

    # Level 2: Decide
    if len(set(triggered_results)) == 1 and triggered_results:
        final_decision = triggered_results[0]
    elif len(set(triggered_results)) > 1 or not triggered_results:
        final_decision = 'odd' if odd_count in (0,2,4) else 'even'

    # Prediction meaning
    predicted_parity = "EVEN" if final_decision == 'odd' else "ODD"

    # Show result
    st.markdown(f"""
    ### Prediction:
    - **Seed Digits:** `{seed_digits}`
    - **Seed Sum:** `{seed_sum}`
    - **Odd Count:** `{odd_count}`
    - **Predicted Next Parity:** 🥇 **{predicted_parity}**
    """)
else:
    st.info("Please enter exactly 5 digits for the seed.")

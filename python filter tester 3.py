import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS

def sum_category(total: int) -> str:
    """Maps a sum to a category bucket."""
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 20:
        return 'Low'
    elif 21 <= total <= 25:
        return 'Mid'
    elif 26 <= total <= 30:
        return 'High'
    else:
        return 'Very High'

def load_filters(csv_path: str = 'lottery_filters_batch10.csv') -> list:
    """Loads filter definitions from a CSV file, tolerating unescaped quotes."""
    filters = []
    with open(csv_path, newline='') as f:
        # Use QUOTE_NONE with a single backslash escape to tolerate unescaped quotes
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONE, escapechar='\\')
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            if not row.get('enabled', '').lower() in ('true', '1'):
                continue
            try:
                expr = row.get('expression', '').strip()
                compiled = compile(expr, '<string>', 'eval')
                filters.append({
                    'id': row['id'],
                    'name': row['name'],
                    'func': compiled,
                    'enabled_default': row.get('enabled_default', 'true').lower() == 'true'
                })
            except Exception:
                st.warning(f"Skipping filter {row['id']}: invalid expression syntax")
    return filters


def apply_filters(filters: list, combos: list, seed_sum: int, **kwargs) -> tuple:
    """Applies filters to combos and returns survivors plus elimination counts."""
    survivors = []
    flt_counts = {f['id']: 0 for f in filters}
    for combo in combos:
        combo_sum = sum(combo)
        context = {**kwargs, 'combo_sum': combo_sum, 'seed_sum': seed_sum}
        passed = True
        for flt in filters:
            if eval(flt['func'], {}, context):
                flt_counts[flt['id']] += 1
                passed = False
                break
        if passed:
            survivors.append(combo)
    return survivors, flt_counts


def generate_combinations(method: str) -> list:
    """Generates digit combinations based on the selected method."""
    digits = range(10)
    if method == '1-digit':
        return [(d,) for d in digits]
    elif method == '2-digit':
        return list(product(digits, repeat=2))
    # Add more methods as needed
    return []


def main():
    st.title("DC-5 Filter Tracker Full")

    select_all = st.checkbox("Select/Deselect All Filters", value=True)
    seed_input = st.text_input("Current 5-digit seed (required):")
    if not seed_input or not seed_input.isdigit() or len(seed_input) != 5:
        st.error("Please enter a valid 5-digit seed.")
        return
    seed_digits = [int(d) for d in seed_input]
    seed_sum = sum(seed_digits)
    
    filters = load_filters()
    st.write(f"Loaded {len(filters)} filters")

    method = st.selectbox("Generation Method:", ['1-digit', '2-digit'])
    combos = generate_combinations(method)
    survivors, flt_counts = apply_filters(filters, combos, seed_sum, seed_digits=seed_digits)

    st.header("Filters")
    for flt in filters:
        key = f"filter_{flt['id']}"
        label = f"{flt['id']}: {flt['name']} — eliminated {flt_counts.get(flt['id'], 0)}"
        st.checkbox(label, key=key, value=(select_all and flt['enabled_default']))

    with st.expander("Show remaining combinations"):
        for combo in survivors:
            st.write(combo)

if __name__ == '__main__':
    main()

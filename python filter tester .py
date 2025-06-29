import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
def get_v_trac_group(d): return V_TRAC_GROUPS.get(d)
def get_mirror(d): return MIRROR_PAIRS.get(d)

filters_list = []
txt_path = 'filter_intent_summary_corrected_only.csv'
if os.path.exists(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            desc = row[0].strip().strip('"')
            if desc:
                filters_list.append(desc)
mirror_desc = "If a combo contains both a digit and its mirror (0/5, 1/6, 2/7, 3/8, 4/9), eliminate combo"
if mirror_desc not in filters_list:
    filters_list.append(mirror_desc)

def generate_combinations(seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    seed_str = str(seed)
    if len(seed_str) < 2:
        return []
    if method == "1-digit":
        for d in seed_str:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed_str[i], seed_str[j]))) for i in range(len(seed_str)) for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

def apply_filter(desc, combo_digits, seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits):
    try:
        d = desc.lower().replace('≥', '>=').replace('≤', '<=')
        sum_combo = sum(combo_digits)
        set_combo = set(combo_digits)
        set_seed = set(seed_digits)
        last2 = set(prev_seed_digits) | set(prev_prev_draw_digits)
        common_to_both = set(prev_seed_digits).intersection(prev_prev_draw_digits)

        m = re.search(r'\{([\d,\s]+)\}\.issubset', d)
        if m:
            subset_digits = set(int(x.strip()) for x in m.group(1).split(','))
            target = set_seed if "seed" in d else set_combo
            if "!= 0" in d:
                return subset_digits.issubset(target) and sum_combo % 2 != 0
            if "== 0" in d:
                return subset_digits.issubset(target) and sum_combo % 2 == 0

        m = re.search(r'≥(\d+)\s+shared.*seed', d)
        if m:
            required_shared = int(m.group(1))
            if "<" in d and "sum" in d:
                m_sum = re.search(r'sum\s*<\s*(\d+)', d)
                if m_sum:
                    sum_limit = int(m_sum.group(1))
                    return len(set_combo & set_seed) >= required_shared and sum_combo < sum_limit
            return len(set_combo & set_seed) >= required_shared

        if "mirror" in d:
            return any(get_mirror(x) in combo_digits for x in combo_digits)
        if d.startswith("v-trac"):
            groups = [get_v_trac_group(digit) for digit in combo_digits]
            return len(set(groups)) == 1
        if "common_to_both" in d:
            return sum(d in common_to_both for d in combo_digits) >= 2
        if "last2" in d:
            if "< 2" in d:
                return len(last2.intersection(combo_digits)) < 2
            if ">= 2" in d:
                return len(last2.intersection(combo_digits)) >= 2
        if "issubset(last2" in d:
            return set(combo_digits).issubset(last2)
        if "new_seed_digits" in d:
            return bool(new_seed_digits) and not new_seed_digits.intersection(combo_digits)
        if "{2, 3}" in d and "seed_counts" in d:
            return set(seed_counts.values()) == {2, 3} and sum_combo % 2 == 0

        return False
    except Exception:
        return False

st.sidebar.header("🔢 DC-5 Filter Tracker Full")
def input_seed(label, required=True):
    v = st.sidebar.text_input(label).strip()
    if required and not v:
        st.sidebar.error(f"Please enter {label.lower()}")
        st.stop()
    if v and (len(v) != 5 or not v.isdigit()):
        st.sidebar.error("Seed must be exactly 5 digits (0–9)")
        st.stop()
    return v

today_seed = input_seed("Current 5-digit seed (required):")
prev_seed = input_seed("Previous 5-digit seed (optional):", required=False)
prev_prev_draw = input_seed("Draw before previous seed (optional):", required=False)
prev_seed_digits = [int(d) for d in prev_seed] if prev_seed else []
prev_prev_draw_digits = [int(d) for d in prev_prev_draw] if prev_prev_draw else []
method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])
combos = generate_combinations(today_seed, method)
if not combos:
    st.sidebar.error("No combos generated. Check current seed.")
    st.stop()
seed_digits = [int(d) for d in today_seed]
seed_counts = Counter(seed_digits)
new_seed_digits = set(seed_digits) - set(prev_seed_digits)

survivors, eliminated_details = [], {}
for combo in combos:
    cd = [int(c) for c in combo]
    eliminated = False
    for i, desc in enumerate(filters_list):
        if st.session_state.get(f"filter_{i}", select_all):
            if apply_filter(desc, cd, seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits):
                eliminated_details[combo] = desc
                eliminated = True
                break
    if not eliminated:
        survivors.append(combo)

st.sidebar.markdown(f"**Total combos:** {len(combos)}  \
**Eliminated:** {len(eliminated_details)}  \
**Remaining:** {len(survivors)}")
query = st.sidebar.text_input("Check a combo (any order):")
if query:
    key = ''.join(sorted(query.strip()))
    if key in eliminated_details:
        st.sidebar.warning(f"Eliminated by: {eliminated_details[key]}")
    elif key in survivors:
        st.sidebar.success("It still survives!")
    else:
        st.sidebar.info("Not generated.")

st.header("🔧 Active Filters")
select_all = st.checkbox("Select/Deselect All Filters", value=False)
for i, desc in enumerate(filters_list):
    count_elim = sum(apply_filter(desc, [int(c) for c in combo], seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits) for combo in combos)
    label = f"{desc} — eliminated {count_elim}"
    st.checkbox(label, value=select_all, key=f"filter_{i}")

with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)

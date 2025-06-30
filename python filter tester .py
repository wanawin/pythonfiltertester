import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}

def get_v_trac_group(d): return V_TRAC_GROUPS.get(d)
def get_mirror(d): return MIRROR_PAIRS.get(d)

# Load filters
filters_list = []
txt_path = 'filter_intent_summary_corrected_only.csv'
if os.path.exists(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            desc = row[0].strip().strip('"')
            if desc:
                filters_list.append(desc)

# Ensure mirror filter present
mirror_desc = "If a combo contains both a digit and its mirror (0/5, 1/6, 2/7, 3/8, 4/9), eliminate combo"
if mirror_desc not in filters_list:
    filters_list.append(mirror_desc)

# Generate combos
def generate_combinations(seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    if len(seed) < 2:
        return []
    if method == "1-digit":
        for d in seed:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed[i], seed[j]))) for i in range(len(seed)) for j in range(i+1, len(seed)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# Apply filters
def apply_filter(desc, combo_digits, seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits):
    sum_combo = sum(combo_digits)
    set_combo = set(combo_digits)
    set_seed = set(seed_digits)
    last2 = set(prev_seed_digits) | set(prev_prev_draw_digits)
    common_to_both = set(prev_seed_digits).intersection(prev_prev_draw_digits)
    if "issubset(set(seed))" in desc:
        nums = set(map(int, re.findall(r'\d', desc)))
        return nums.issubset(set_seed) and ("% 2 != 0" not in desc or sum_combo % 2 != 0)
    if "mirror" in desc:
        return any(get_mirror(x) in combo_digits for x in combo_digits)
    if "v-trac" in desc.lower():
        groups = [get_v_trac_group(x) for x in combo_digits]
        return len(set(groups)) == 1
    if "common_to_both" in desc:
        return sum(x in common_to_both for x in combo_digits) >= 2
    if "< 2" in desc and "last2" in desc:
        return len(last2.intersection(combo_digits)) < 2
    if ">= 2" in desc and "last2" in desc:
        return len(last2.intersection(combo_digits)) >= 2
    if "issubset(last2" in desc:
        return set_combo.issubset(last2)
    if "new_seed_digits" in desc:
        return bool(new_seed_digits) and not new_seed_digits.intersection(combo_digits)
    if "{2, 3}" in desc and "seed_counts" in desc:
        return set(seed_counts.values()) == {2, 3} and sum_combo % 2 == 0
    return False

# Streamlit UI
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)

seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
if len(seed) != 5 or not seed.isdigit():
    st.sidebar.error("Seed must be exactly 5 digits")
    st.stop()

prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):", "").strip()
prev_prev_draw = st.sidebar.text_input("Draw before previous seed (optional):", "").strip()
method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])

prev_seed_digits = [int(d) for d in prev_seed] if prev_seed else []
prev_prev_draw_digits = [int(d) for d in prev_prev_draw] if prev_prev_draw else []
combos = generate_combinations(seed, method)
seed_digits = [int(d) for d in seed]
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

st.sidebar.markdown(f"**Total:** {len(combos)} Elim: {len(eliminated_details)} Remain: {len(survivors)}")
query = st.sidebar.text_input("Check combo:")
if query:
    key = ''.join(sorted(query.strip()))
    if key in eliminated_details:
        st.sidebar.warning(f"Eliminated by: {eliminated_details[key]}")
    elif key in survivors:
        st.sidebar.success("Survives!")
    else:
        st.sidebar.info("Not generated.")

st.header("🔧 Active Filters")
for i, desc in enumerate(filters_list):
    count = sum(apply_filter(desc, [int(c) for c in combo], seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits) for combo in combos)
    st.checkbox(f"{desc} — eliminated {count}", value=select_all, key=f"filter_{i}")

with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)

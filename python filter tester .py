import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter
import pandas as pd  # for diagnostics panel

# ─── V-Trac group definitions ───
# Map each digit (0–9) to its V-Trac group (1–5)
V_TRAC_GROUPS = {
    0: 1, 5: 1,
    1: 2, 6: 2,
    2: 3, 7: 3,
    3: 4, 8: 4,
    4: 5, 9: 5,
}

def get_v_trac_group(digit: int) -> int:
    """Return the V-Trac group number (1–5) for a given digit."""
    return V_TRAC_GROUPS.get(digit)

# ─── Mirror digit definitions ───
# Map each digit (0–9) to its mirror digit
MIRROR_PAIRS = {
    0: 5, 5: 0,
    1: 6, 6: 1,
    2: 7, 7: 2,
    3: 8, 8: 3,
    4: 9, 9: 4,
}

def get_mirror(digit: int) -> int:
    """Return the mirror digit for a given digit (0–9)."""
    return MIRROR_PAIRS.get(digit)

# ─── Read filter intent descriptions from CSV ───
txt_path = 'filter_intent_summary_corrected_only.csv'
filters_list = []
if os.path.exists(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            desc = row[0].strip().strip('"')
            if desc:
                filters_list.append(desc)
else:
    st.sidebar.error(f"Filter intent file not found: {txt_path}")

# ─── Ensure Mirror filter is in the list ───
mirror_desc = "If a combo contains both a digit and its mirror (0/5, 1/6, 2/7, 3/8, 4/9), eliminate combo"
if mirror_desc not in filters_list:
    filters_list.append(mirror_desc)

# ─── Combination Generator ───
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
        pairs = set(''.join(sorted((seed_str[i], seed_str[j])))
                    for i in range(len(seed_str)) for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# ─── Single-filter helper ───
def apply_filter(desc, combo_digits, seed_digits,
                 prev_seed_digits, prev_prev_draw_digits,
                 seed_counts, new_seed_digits):
    # normalize Unicode operators
    d = desc.strip().replace('≥', '>=').replace('≤', '<=')
    sum_combo = sum(combo_digits)
    common_to_both = set(prev_prev_draw_digits).intersection(prev_seed_digits)
    last2 = set(prev_prev_draw_digits) | set(prev_seed_digits)

    # 1. FullHouse on seed (3+2) AND combo sum even
    if d == "if set(seed_counts.values()) == {2, 3} and sum(combo) % 2 == 0: eliminate(combo)":
        return set(seed_counts.values()) == {2, 3} and sum_combo % 2 == 0
    # 2. New seed digit must appear
    if d == "if new_seed_digits and not new_seed_digits.intersection(combo): eliminate(combo)":
        return bool(new_seed_digits) and not new_seed_digits.intersection(combo_digits)
    # 3. ≥2 common to both prev_seed & prev_prev_draw
    if d == "if sum(d in common_to_both for d in combo) >= 2: eliminate(combo)":
        return sum(d in common_to_both for d in combo_digits) >= 2
    # 4. <2 of last2
    if d == "if len(last2.intersection(combo)) < 2: eliminate(combo)":
        return len(last2.intersection(combo_digits)) < 2
    # 5. ≥2 of last2
    if d == "if len(last2.intersection(combo)) >= 2: eliminate(combo)":
        return len(last2.intersection(combo_digits)) >= 2
    # 6. all from last2
    if d == "if set(combo).issubset(last2): eliminate(combo)":
        return set(combo_digits).issubset(last2)
    # V-TRAC: all same group
    if d.lower().startswith("v-trac"):
        groups = [get_v_trac_group(digit) for digit in combo_digits]
        return len(set(groups)) == 1
    # Mirror: any digit with its mirror
    if "mirror" in d.lower():
        return any(get_mirror(digit) in combo_digits for digit in combo_digits)
    return False

# ─── Streamlit UI ───
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

# Inputs
today_seed = input_seed("Current 5-digit seed (required):")
prev_seed = input_seed("Previous 5-digit seed (optional):", required=False)
prev_prev_draw = input_seed("Draw before previous seed (optional):", required=False)

prev_seed_digits = [int(d) for d in prev_seed] if prev_seed else []
prev_prev_draw_digits = [int(d) for d in prev_prev_draw] if prev_prev_draw else []

hot_input = st.sidebar.text_input("Hot digits (optional, comma-separated):")
cold_input = st.sidebar.text_input("Cold digits (optional, comma-separated):")
due_input = st.sidebar.text_input("Due digits (optional, comma-separated):")
hot_digits = [int(d) for d in re.findall(r"\d+", hot_input)] if hot_input else []
cold_digits = [int(d) for d in re.findall(r"\d+", cold_input)] if cold_input else []
due_digits = [int(d) for d in re.findall(r"\d+", due_input)] if due_input else []
method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])

# Generate combos
combos = generate_combinations(today_seed, method)
if not combos:
    st.sidebar.error("No combos generated. Check current seed.")
    st.stop()
seed_digits = [int(d) for d in today_seed]
seed_counts = Counter(seed_digits)
new_seed_digits = set(seed_digits) - set(prev_seed_digits)

# Elimination
survivors = []
eliminated_details = {}
for combo in combos:
    cd = [int(c) for c in combo]
    eliminated = False
    for i, desc in enumerate(filters_list):
        if st.session_state.get(f"filter_{i}", False):
            if apply_filter(desc, cd, seed_digits,
                            prev_seed_digits, prev_prev_draw_digits,
                            seed_counts, new_seed_digits):
                eliminated_details[combo] = desc
                eliminated = True
                break
    if not eliminated:
        survivors.append(combo)

# Metrics
st.sidebar.markdown(f"**Total combos:** {len(combos)}  \
**Eliminated:** {len(eliminated_details)}  \
**Remaining:** {len(survivors)}")

# Combo lookup
st.sidebar.markdown('---')
query = st.sidebar.text_input("Check a combo (any order):")
if query:
    key = ''.join(sorted(query.strip()))
    if key in eliminated_details:
        st.sidebar.warning(f"Eliminated by: {eliminated_details[key]}")
    elif key in survivors:
        st.sidebar.success("It still survives!")
    else:
        st.sidebar.info("Not generated.")

# Active Filters UI
st.header("🔧 Active Filters")
select_all = st.checkbox("Select/Deselect All Filters")
for i, desc in enumerate(filters_list):
    count_elim = sum(
        apply_filter(desc,
                     [int(c) for c in combo],
                     seed_digits,
                     prev_seed_digits,
                     prev_prev_draw_digits,
                     seed_counts,
                     new_seed_digits)
        for combo in combos
    )
    label = f"{desc} — eliminated {count_elim}"
    st.checkbox(label, value=select_all, key=f"filter_{i}")

# Enhanced Diagnostics Panel
st.subheader("🛠️ Filter Diagnostics")
stats = []
for desc in filters_list:
    d_norm = desc.strip().replace('≥', '>=').replace('≤', '<=')
    count = sum(
        apply_filter(
            desc,
            [int(c) for c in combo],
            seed_digits,
            prev_seed_digits,
            prev_prev_draw_digits,
            seed_counts,
            new_seed_digits
        )
        for combo in combos
    )
    first_hit = next(
        (combo for combo in combos if apply_filter(desc, [int(c) for c in combo],
                                                   seed_digits, prev_seed_digits,
                                                   prev_prev_draw_digits,
                                                   seed_counts, new_seed_digits)),
        None
    )
    stats.append((desc, d_norm, count, first_hit))
df = pd.DataFrame(stats, columns=["Original desc", "Normalized desc", "Eliminated count", "First hit combo"])
st.dataframe(df)

# Show remaining combos
with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)

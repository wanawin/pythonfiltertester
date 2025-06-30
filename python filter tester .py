import streamlit as st
from itertools import product
import csv
import os
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}

# Precompute for eval context
MIRROR = MIRROR_PAIRS

# Load filters from CSV
FILTERS_CSV = 'filters.csv'
filters = []
if not os.path.exists(FILTERS_CSV):
    st.error(f"Filter file not found: {FILTERS_CSV}")
else:
    with open(FILTERS_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Compile code
            row['applicable_code'] = compile(row['applicable_if'], '<applicable>', 'eval')
            row['expr_code'] = compile(row['expression'], '<expr>', 'eval')
            row['enabled_default'] = row['enabled'].strip().lower() == 'true'
            filters.append(row)

# Generate combos

def generate_combinations(seed, method):
    all_digits = '0123456789'
    combos = set()
    seed = ''.join(sorted(seed))
    if len(seed) < 2:
        return []
    if method == '1-digit':
        for d in seed:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed[i], seed[j]))) for i in range(len(seed)) for j in range(i+1, len(seed)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# UI Sidebar
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)

# Seed inputs
seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
prev_prev_draw = st.sidebar.text_input("Draw before previous seed (optional):").strip()
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])

# Validate seed
if len(seed) != 5 or not seed.isdigit():
    st.sidebar.error("Seed must be exactly 5 digits")
    st.stop()

# Prepare context values
seed_digits = [int(d) for d in seed]
seed_counts = Counter(seed_digits)
prev_seed_digits = [int(d) for d in prev_seed] if prev_seed.isdigit() else []
prev_prev_draw_digits = [int(d) for d in prev_prev_draw] if prev_prev_draw.isdigit() else []
new_seed_digits = set(seed_digits) - set(prev_seed_digits)

# Generate combos
combos = generate_combinations(seed, method)

# Evaluate filters
survivors = []
eliminated_details = {}
for combo in combos:
    combo_digits = [int(c) for c in combo]
    context = {
        'seed_digits': seed_digits,
        'combo_digits': combo_digits,
        'seed_sum': sum(seed_digits),
        'combo_sum': sum(combo_digits),
        'seed_counts': seed_counts,
        'mirror': MIRROR,
        'new_seed_digits': new_seed_digits,
        'prev_seed_digits': prev_seed_digits,
        'prev_prev_draw_digits': prev_prev_draw_digits
    }
    eliminated = False
    for flt in filters:
        active = st.session_state.get(f"filter_{flt['id']}", flt['enabled_default'] if select_all else False)
        if not active:
            continue
        if not eval(flt['applicable_code'], {}, context):
            continue
        if eval(flt['expr_code'], {}, context):
            eliminated_details[combo] = flt['name']
            eliminated = True
            break
    if not eliminated:
        survivors.append(combo)

# Summary
st.sidebar.markdown(f"**Total:** {len(combos)} &nbsp;&nbsp;Eliminated: {len(eliminated_details)} &nbsp;&nbsp;Survivors: {len(survivors)}")

# Combo checker
query = st.sidebar.text_input("Check specific combo:")
if query:
    key = ''.join(sorted(query.strip()))
    if key in eliminated_details:
        st.sidebar.warning(f"Eliminated by: {eliminated_details[key]}")
    elif key in survivors:
        st.sidebar.success("Survives!")
    else:
        st.sidebar.info("Not generated.")

# Active Filters display
st.header("🔧 Active Filters")
for flt in filters:
    count = sum(
        eval(flt['expr_code'], {}, {
            **{
                'seed_digits': seed_digits,
                'combo_digits': [int(c) for c in combo],
                'seed_sum': sum(seed_digits),
                'combo_sum': sum(int(c) for c in combo),
                'seed_counts': seed_counts,
                'mirror': MIRROR,
                'new_seed_digits': new_seed_digits,
                'prev_seed_digits': prev_seed_digits,
                'prev_prev_draw_digits': prev_prev_draw_digits
            }
        }) for combo in combos if eval(flt['applicable_code'], {}, context)
    )
    st.checkbox(f"{flt['name']} — eliminated {count}", key=f"filter_{flt['id']}", value=select_all)

# Show remaining combos
with st.expander("Show remaining combinations"):
    for combo in survivors:
        st.write(combo)

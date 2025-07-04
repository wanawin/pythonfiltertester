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


def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = row.get('id') or row.get('fid')

            # strip and sanitize fields
            for key in ('name', 'applicable_if', 'expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")

            name_l = row['name'].lower()
            # normalize operators
            if 'expression' in row:
                row['expression'] = row['expression'].replace('!==', '!=')

            # odd/even-sum filters
            if 'eliminate all odd-sum combos' in name_l:
                m = re.search(r'includes ([\d,]+)', name_l)
                if m:
                    digs = [d for d in m.group(1).split(',')]
                    row['applicable_if'] = f"set({digs}).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 != 0'

            elif 'eliminate all even-sum combos' in name_l:
                m = re.search(r'includes ([\d,]+)', name_l)
                if m:
                    digs = [d for d in m.group(1).split(',')]
                    row['applicable_if'] = f"set({digs}).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 == 0'

            # shared-digit filters
            elif 'shared digits' in name_l:
                m = re.search(r'≥?(\d+)', row['name'])
                if m:
                    n = int(m.group(1))
                    expr = f"sum(1 for d in combo_digits if d in seed_digits) >= {n}"
                    m2 = re.search(r'sum <\s*(\d+)', name_l)
                    if m2:
                        t = int(m2.group(1))
                        expr += f" and combo_sum < {t}"
                    row['expression'] = expr

            # keep-range filters: eliminate combos outside the specified sum range
            elif 'keep combo sum' in name_l:
                m = re.search(r'combo sum (\d+)-(\d+)', name_l)
                if m:
                    lo, hi = m.groups()
                    row['expression'] = f"not ({lo} <= combo_sum <= {hi})"

            # compile code
            try:
                row['applicable_code'] = compile(row.get('applicable_if', 'True'), '<applicable>', 'eval')
                row['expr_code'] = compile(row.get('expression', 'False'), '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled', '').lower() == 'true'
            flts.append(row)
    return flts

# Load filters before UI
filters = load_filters()

# Sidebar UI
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
prev_prev_seed = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
hot_input = st.sidebar.text_input("Hot digits (comma-separated):").strip()
cold_input = st.sidebar.text_input("Cold digits (comma-separated):").strip()

# Validate seed
if len(seed) != 5 or not seed.isdigit():
    st.sidebar.error("Seed must be exactly 5 digits")
    st.stop()

# Context values
seed_digits = [int(d) for d in seed]
prev_seed_digits = [int(d) for d in prev_seed if d.isdigit()]
prev_prev_seed_digits = [int(d) for d in prev_prev_seed if d.isdigit()]
new_seed_digits = set(seed_digits) - set(prev_seed_digits)
hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
due_digits = [d for d in range(10) if d not in prev_seed_digits and d not in prev_prev_seed_digits]
seed_counts = Counter(seed_digits)
seed_vtracs = set(V_TRAC_GROUPS[d] for d in seed_digits)

# Generate combos
def generate_combinations(seed, method):
    all_digits = '0123456789'
    combos = set()
    seed_sorted = ''.join(sorted(seed))
    if method == '1-digit':
        for d in seed_sorted:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed_sorted[i], seed_sorted[j]))) for i in range(len(seed_sorted)) for j in range(i+1, len(seed_sorted)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

combos = generate_combinations(seed, method)
eliminated, survivors = {}, []
for combo in combos:
    cdigits = [int(c) for c in combo]
    ctx = {
        'seed_digits': seed_digits,
        'combo_digits': cdigits,
        'seed_sum': sum(seed_digits),
        'combo_sum': sum(cdigits),
        'seed_counts': seed_counts,
        'seed_vtracs': seed_vtracs,
        'combo_vtracs': set(V_TRAC_GROUPS[d] for d in cdigits),
        'mirror': MIRROR,
        'new_seed_digits': new_seed_digits,
        'prev_seed_digits': prev_seed_digits,
        'prev_prev_seed_digits': prev_prev_seed_digits,
        'common_to_both': set(prev_seed_digits) & set(prev_prev_seed_digits),
        'last2': set(prev_seed_digits) | set(prev_prev_seed_digits),
        'hot_digits': hot_digits,
        'cold_digits': cold_digits,
        'due_digits': due_digits,
        'Counter': Counter
    }
    for flt in filters:
        active = st.session_state.get(f"filter_{flt['id']}", select_all and flt['enabled_default'])
        if not active or not eval(flt['applicable_code'], ctx, ctx):
            continue
        if eval(flt['expr_code'], ctx, ctx):
            eliminated[combo] = flt['name']
            break
    else:
        survivors.append(combo)

# Summary
st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

# Active filters
st.header("🔧 Active Filters")
for flt in filters:
    count = 0
    for combo in combos:
        cd = [int(c) for c in combo]
        ctx.update(combo_digits=cd, combo_vtracs=set(V_TRAC_GROUPS[d] for d in cd), combo_sum=sum(cd))
        if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
            count += 1
    label = f"{flt['id']}: {flt['name']} — eliminated {count}"
    st.checkbox(label, key=f"filter_{flt['id']}", value=select_all and flt['enabled_default'])

# Show survivors
with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)

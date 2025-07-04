import os
import csv
import streamlit as st
from itertools import product
from collections import Counter
import re

# V-Trac and mirror mappings\ nV_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS   = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR         = MIRROR_PAIRS

# Load filters from CSV (fixed odd/even and shared-digit logic)
def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()
    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for rawrow in reader:
            row = {k.lower(): v for k, v in rawrow.items()}
            row['id'] = row.get('fid') or row.get('id') or ''
            row['name'] = row.get('name','').strip()
            # strip quotes in CSV fields
            row['applicable_if'] = row.get('applicable_if','').strip().strip('"').strip("'")
            row['expression']    = row.get('expression','').strip().strip('"').strip("'")
            row['expression']    = row['expression'].replace('!==','!=')
            name_l = row['name'].lower()

            # odd/even-sum overrides
            if 'eliminate all odd-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except:
                    pass
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except:
                    pass
                row['expression'] = 'combo_sum % 2 == 0'

            # F054: eliminate combos sharing more than 2 digits common to both previous draws
            if row['id'] == 'F054':
                row['expression'] = 'len(set(combo_digits) & common_to_both) > 2'

            # shared-digit filters override
            elif 'shared digits' in name_l:
                try:
                    # threshold N
                    n = int(re.search(r'≥?(\d+)', row['name']).group(1))
                    # full count of shared digits
                    expr = f"sum(1 for d in combo_digits if d in seed_digits) >= {n}"
                    # optional sum constraint
                    m = re.search(r'sum <\s*(\d+)', row['name'])
                    if m:
                        t = int(m.group(1))
                        expr += f" and combo_sum < {t}"
                    row['expression'] = expr
                except:
                    pass

            # compile expressions
            try:
                row['applicable_code'] = compile(row['applicable_if'], '<applicable>', 'eval')
                row['expr_code']       = compile(row['expression'],   '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts

# Initialize filters
filters = load_filters()

# Generate combinations based on seed and method
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

# Sidebar UI
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
prev_prev_seed = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])
hot_input = st.sidebar.text_input("Hot digits (comma-separated):").strip()
cold_input = st.sidebar.text_input("Cold digits (comma-separated):").strip()

# Validate seed input
if len(seed) != 5 or not seed.isdigit():
    st.sidebar.error("Seed must be exactly 5 digits")
    st.stop()

# Prepare context values
seed_digits = [int(d) for d in seed]
prev_seed_digits = [int(d) for d in prev_seed if d.isdigit()]
prev_prev_seed_digits = [int(d) for d in prev_prev_seed if d.isdigit()]
new_seed_digits = set(seed_digits) - set(prev_seed_digits)
hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
due_digits = [d for d in range(10) if d not in prev_seed_digits and d not in prev_prev_seed_digits]
seed_counts = Counter(seed_digits)
seed_vtracs = set(V_TRAC_GROUPS[d] for d in seed_digits)

# Generate and evaluate combos
combos = generate_combinations(seed, method)
eliminated_details, survivors = {}, []
for combo in combos:
    combo_digits = [int(c) for c in combo]
    combo_vtracs = set(V_TRAC_GROUPS[d] for d in combo_digits)
    common_to_both = set(prev_seed_digits) & set(prev_prev_seed_digits)
    ctx = {
        'seed_digits': seed_digits,
        'combo_digits': combo_digits,
        'seed_sum': sum(seed_digits),
        'combo_sum': sum(combo_digits),
        'seed_counts': seed_counts,
        'seed_vtracs': seed_vtracs,
        'combo_vtracs': combo_vtracs,
        'mirror': MIRROR,
        'new_seed_digits': new_seed_digits,
        'prev_seed_digits': prev_seed_digits,
        'prev_prev_seed_digits': prev_prev_seed_digits,
        'common_to_both': common_to_both,
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
            eliminated_details[combo] = flt['name']
            break
    else:
        survivors.append(combo)

# Summary and combo checker
st.sidebar.markdown(f"**Total:** {len(combos)} &nbsp;&nbsp;Eliminated: {len(eliminated_details)} &nbsp;&nbsp;Survivors: {len(survivors)}")
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
    count, error = 0, None
    for combo in combos:
        combo_digits = [int(c) for c in combo]
        ctx.update({
            'combo_digits': combo_digits,
            'combo_sum': sum(combo_digits),
            'combo_vtracs': set(V_TRAC_GROUPS[d] for d in combo_digits)
        })
        try:
            if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                count += 1
        except Exception as e:
            error = str(e)
            break
    label = f"{flt['id']}: {flt['name']} — eliminated {count}"
    if error:
        label += f" (Error: {error})"
    st.checkbox(label, key=f"filter_{flt['id']}", value=select_all and flt['enabled_default'])

# Show remaining combinations
with st.expander("Show remaining combinations"):
    for combo in survivors:
        st.write(combo)

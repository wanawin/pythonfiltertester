import os
import csv
import streamlit as st
from itertools import product
from collections import Counter
import re

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS   = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR         = MIRROR_PAIRS

# Load filters from CSV (fixed odd/even syntax, unified ID)
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
                except Exception:
                    pass
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except Exception:
                    pass
                row['expression'] = 'combo_sum % 2 == 0'
            # shared-digit filters
            if 'shared digits with seed' in name_l:
                try:
                    n = int(re.search(r'≥?(\d+)',row['name']).group(1))
                    expr = f"len(set(combo_digits)&set(seed_digits)) >= {n}"
                    m = re.search(r'sum <\s*(\d+)', row['name'])
                    if m:
                        expr += f" and combo_sum < {int(m.group(1))}"
                    row['expression'] = expr
                except Exception:
                    pass
            # compile
            try:
                row['applicable_code'] = compile(row['applicable_if'],'<applicable>','eval')
                row['expr_code']       = compile(row['expression'],   '<expr>','eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower()=='true'
            flts.append(row)
    return flts

filters = load_filters()

# combination generation
def generate_combinations(seed,method):
    digits = '0123456789'
    combos = set()
    s = ''.join(sorted(seed))
    if method=='1-digit':
        for d in s:
            for p in product(digits,repeat=4):
                combos.add(''.join(sorted(d+''.join(p))))
    else:
        pairs = set(''.join(sorted((s[i],s[j]))) for i in range(len(s)) for j in range(i+1,len(s)))
        for pair in pairs:
            for p in product(digits,repeat=3):
                combos.add(''.join(sorted(pair+''.join(p))))
    return sorted(combos)

# sidebar inputs
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all = st.sidebar.checkbox("Select/Deselect All Filters",value=True)
seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
prev_prev_seed = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
method = st.sidebar.selectbox("Generation Method:",["1-digit","2-digit pair"])
hot_input = st.sidebar.text_input("Hot digits (comma-separated):").strip()
cold_input = st.sidebar.text_input("Cold digits (comma-separated):").strip()

if len(seed)!=5 or not seed.isdigit(): st.sidebar.error("Seed must be exactly 5 digits"); st.stop()

# context build
seed_digits = [int(d) for d in seed]
prev_seed_digits = [int(d) for d in prev_seed if d.isdigit()]
prev_prev_seed_digits = [int(d) for d in prev_prev_seed if d.isdigit()]
new_seed_digits = set(seed_digits)-set(prev_seed_digits)
hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
due_digits = [d for d in range(10) if d not in prev_seed_digits and d not in prev_prev_seed_digits]
seed_counts = Counter(seed_digits)
seed_vtracs = set(V_TRAC_GROUPS[d] for d in seed_digits)

combos = generate_combinations(seed,method)
eliminated, survivors = {}, []
for combo in combos:
    combo_digits = [int(c) for c in combo]
    combo_vtracs = set(V_TRAC_GROUPS[d] for d in combo_digits)
    ctx = {**locals(),**{'mirror':MIRROR,'Counter':Counter}}
    for flt in filters:
        active = st.session_state.get(f"filter_{flt['id']}", select_all and flt['enabled_default'])
        if not active or not eval(flt['applicable_code'],ctx,ctx): continue
        if eval(flt['expr_code'],ctx,ctx):
            eliminated[combo]=flt['name']; break
    else:
        survivors.append(combo)

# summary & UI
st.sidebar.markdown(f"**Total:**{len(combos)} Elim:{len(eliminated)} Remain:{len(survivors)}")
query = st.sidebar.text_input("Check specific combo:")
if query:
    key=''.join(sorted(query.strip()))
    if key in eliminated: st.sidebar.warning(f"Eliminated by: {eliminated[key]}")
    elif key in survivors: st.sidebar.success("Survives!")
    else: st.sidebar.info("Not generated.")

st.header("🔧 Active Filters")
for flt in filters:
    count=0;err=None
    for combo in combos:
        combo_digits=[int(c) for c in combo]
        ctx.update({'combo_digits':combo_digits,'combo_sum':sum(combo_digits),'combo_vtracs':set(V_TRAC_GROUPS[d] for d in combo_digits)})
        try:
            if eval(flt['applicable_code'],ctx,ctx) and eval(flt['expr_code'],ctx,ctx): count+=1
        except Exception as e:
            err=str(e); break
    label = f"{flt['id']}: {flt['name']} — eliminated {count}" + (f" (Error: {err})" if err else "")
    st.checkbox(label,key=f"filter_{flt['id']}",value=select_all and flt['enabled_default'])

with st.expander("Show remaining combinations"):
    for c in survivors: st.write(c)

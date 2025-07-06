import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# V-Trac and mirror mappings\ nV_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS

def sum_category(s: int) -> str:
    """Categorize sum into buckets."""
    if 0 <= s <= 15:
        return 'Very Low'
    elif 16 <= s <= 24:
        return 'Low'
    elif 25 <= s <= 33:
        return 'Mid'
    else:
        return 'High'

def load_filters(path='lottery_filters_batch10.csv'):
    """Load and compile filter definitions from CSV."""
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = row.get('id') or row.get('fid')
            for key in ('name', 'applicable_if', 'expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
            name_l = (row.get('name') or '').lower()
            row['expression'] = row.get('expression', '').replace('!==', '!=')
            # ... [other filter parsing as before] ...
            a_if = row.get('applicable_if') or 'True'
            expr = row.get('expression')    or 'False'
            try:
                row['applicable_code'] = compile(a_if, '<applicable>', 'eval')
                row['expr_code']       = compile(expr,    '<expr>',       'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled', '').lower() == 'true'
            flts.append(row)
    return flts

def main():
    filters = load_filters()
    # Sidebar input setup...
    # Build context...
    # Generate combos...

    # Apply filters
    eliminated = {}
    survivors  = []
    for combo in combos:
        cdigits = [int(c) for c in combo]
        ctx = generate_context(cdigits)
        for flt in filters:
            key = f"filter_{flt['id']}"
            active = st.session_state.get(key, select_all and flt['enabled_default'])
            if not active:
                continue
            try:
                if not eval(flt['applicable_code'], ctx, ctx):
                    continue
                if eval(flt['expr_code'], ctx, ctx):
                    eliminated[combo] = flt['name']
                    break
            except Exception:
                continue
        else:
            survivors.append(combo)

    # Sidebar summary
    st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

    # Active filters UI
    st.header("🔧 Active Filters")
    for flt in filters:
        # Compute elimination count safely
        count = 0
        for combo in combos:
            cdigits = [int(c) for c in combo]
            ctx = generate_context(cdigits)
            key = f"filter_{flt['id']}"
            active = st.session_state.get(key, select_all and flt['enabled_default'])
            if not active:
                continue
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    count += 1
            except Exception:
                pass
        label = f"{flt['id']}: {flt['name']} — eliminated {count}"
        st.checkbox(label,
                    key=key,
                    value=st.session_state.get(key, select_all and flt['enabled_default']))

    # Show survivors
    with st.expander("Show remaining combinations"):
        for c in survivors:
            st.write(c)

if __name__ == '__main__':
    main()

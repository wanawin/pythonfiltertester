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


def sum_category(s: int) -> str:
    """Categorize sum into buckets."""
    if   0  <= s <= 15: return 'Very Low'
    elif 16 <= s <= 24: return 'Low'
    elif 25 <= s <= 33: return 'Mid'
    else:               return 'High'


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
            for key in ('name','applicable_if','expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
            name_l = row.get('name','').lower()
            row['expression'] = row.get('expression','').replace('!==','!=')

            # existing filter logic...
            # (omitted for brevity)

            # Compile codes
            try:
                row['applicable_code'] = compile(row.get('applicable_if','True'), '<applicable>', 'eval')
                row['expr_code']       = compile(row.get('expression','False'),    '<expr>',       'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts


def main():
    filters = load_filters()

    # Sidebar inputs
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")
    select_all   = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
    seed          = st.sidebar.text_input("Current 5-digit seed (required):").strip()
    prev_seed     = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
    prev_prev_seed= st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
    method        = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])
    hot_input     = st.sidebar.text_input("Hot digits (comma-separated):").strip()
    cold_input    = st.sidebar.text_input("Cold digits (comma-separated):").strip()
    check_combo   = st.sidebar.text_input("Check specific combo:").strip()

    # Validate seed
    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits")
        st.stop()

    # Build context values
    seed_digits        = [int(d) for d in seed]
    prev_seed_digits   = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_seed_digits = [int(d) for d in prev_prev_seed if d.isdigit()]
    hot_digits         = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
    cold_digits        = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
    due_digits         = [d for d in range(10) if d not in prev_seed_digits and d not in prev_prev_seed_digits]
    seed_counts        = Counter(seed_digits)
    seed_vtracs        = set(V_TRAC_GROUPS[d] for d in seed_digits)

    # Precompute seed sum and category
    seed_sum    = sum(seed_digits)
    prev_sum_cat= sum_category(seed_sum)

    # Build prev_pattern
    prev_pattern = []
    for digs in [prev_prev_seed_digits, prev_seed_digits, seed_digits]:
        sc      = sum_category(sum(digs))
        parity  = 'Even' if sum(digs) % 2 == 0 else 'Odd'
        prev_pattern.extend([sc, parity])

    # Context generator
    def generate_context(cdigits):
        combo_sum    = sum(cdigits)
        return {
            'seed_digits':          seed_digits,
            'prev_seed_digits':     prev_seed_digits,
            'prev_prev_seed_digits':prev_prev_seed_digits,
            'prev_pattern':         prev_pattern,
            'hot_digits':           hot_digits,
            'cold_digits':          cold_digits,
            'due_digits':           due_digits,
            'seed_counts':          seed_counts,
            'seed_sum':             seed_sum,
            'prev_sum_cat':         prev_sum_cat,
            'combo_digits':         cdigits,
            'combo_sum':            combo_sum,
            'combo_sum_cat':        sum_category(combo_sum),
            'seed_vtracs':          seed_vtracs,
            'combo_vtracs':         set(V_TRAC_GROUPS[d] for d in cdigits),
            'mirror':               MIRROR,
            'common_to_both':       set(prev_seed_digits) & set(prev_prev_seed_digits),
            'last2':                set(prev_seed_digits) | set(prev_prev_seed_digits),
            'Counter':              Counter
        }

    # Combination generator
    def generate_combinations(seed, method):
        all_d   = '0123456789'
        combos  = set()
        s_sort  = ''.join(sorted(seed))
        if method == '1-digit':
            for d in s_sort:
                for p in product(all_d, repeat=4):
                    combos.add(''.join(sorted(d + ''.join(p))))
        else:
            pairs = set(''.join(sorted((s_sort[i], s_sort[j]))) for i in range(len(s_sort)) for j in range(i+1, len(s_sort)))
            for pair in pairs:
                for p in product(all_d, repeat=3):
                    combos.add(''.join(sorted(pair + ''.join(p))))
        return sorted(combos)

    combos    = generate_combinations(seed, method)
    eliminated= {}
    survivors = []

    # Apply filters
    for combo in combos:
        cdigits= [int(c) for c in combo]
        ctx     = generate_context(cdigits)
        for flt in filters:
            key    = f"filter_{flt['id']}"
            active = st.session_state.get(key, select_all and flt['enabled_default'])
            if not active or not eval(flt['applicable_code'], ctx, ctx):
                continue
            if eval(flt['expr_code'], ctx, ctx):
                eliminated[combo] = flt['name']
                break
        else:
            survivors.append(combo)

    # Sidebar summary
    st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

    # Normalize user-input combo for lookup
    if check_combo:
        norm = ''.join(sorted(check_combo))
        if norm in eliminated:
            st.sidebar.info(f"Combo {check_combo} eliminated by {eliminated[norm]}")
        elif norm in survivors:
            st.sidebar.success(f"Combo {check_combo} survived all filters")
        else:
            st.sidebar.warning(f"Combo {check_combo} not found in generated list")

    # Active filter checkboxes
    st.header("🔧 Active Filters")
    for flt in filters:
        count = sum(
            eval(flt['applicable_code'], generate_context([int(c) for c in combo]), generate_context([int(c) for c in combo]))
            and eval(flt['expr_code'], generate_context([int(c) for c in combo]), generate_context([int(c) for c in combo]))
            for combo in combos
        )
        label = f"{flt['id']}: {flt['name']} — eliminated {count}"
        st.checkbox(label, key=f"filter_{flt['id']}", value=st.session_state.get(f"filter_{flt['id']}", select_all and flt['enabled_default']))

    # Display survivors
    with st.expander("Show remaining combinations"):
        for c in survivors:
            st.write(c)

if __name__ == '__main__':
    main()

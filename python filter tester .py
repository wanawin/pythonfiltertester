import streamlit as st
from itertools import product
import csv
import os
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS

def sum_category(total: int) -> str:
    """Maps a sum to a category bucket."""
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 24:
        return 'Low'
    elif 25 <= total <= 33:
        return 'Mid'
    else:
        return 'High'


def load_filters(path: str = 'lottery_filters_batch10.csv') -> list:
    """Loads filter definitions, compiles code objects for applicability and expression."""
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    filters = []
    # Robust CSV loading: pad rows to header width, then zip into dicts
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        width = len(headers)
        for raw_row in reader:
            # Pad short rows
            if len(raw_row) < width:
                raw_row += [''] * (width - len(raw_row))
            # Create dict from header to value
            raw = dict(zip(headers, raw_row))
            # Normalize keys
            row = {k.lower(): (v or '').strip() for k, v in raw.items()}
            row['id'] = row.get('id', row.get('fid', ''))

            # Strip surrounding quotes from key fields if present
            for key in ('name', 'applicable_if', 'expression'):
                if key in row:
                    row[key] = row[key].strip('"').strip("'")

            # Replace JS-style !== with Python !=
            row['expression'] = row.get('expression', '').replace('!==', '!=')

            applicable = row.get('applicable_if') or 'True'
            expr       = row.get('expression')    or 'False'
            try:
                row['applicable_code'] = compile(applicable, '<applicable>', 'eval')
                row['expr_code']       = compile(expr,       '<expr>',       'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue

            row['enabled_default'] = row.get('enabled', '').lower() == 'true'
            filters.append(row)

    return filters


def generate_combinations(seed: str, method: str) -> list:
    """Generates sorted 5-digit combos by method."""
    all_digits = '0123456789'
    combos_set = set()
    sorted_seed = ''.join(sorted(seed))
    if method == '1-digit':
        for d in sorted_seed:
            for p in product(all_digits, repeat=4):
                combos_set.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(
            ''.join(sorted((sorted_seed[i], sorted_seed[j])))
            for i in range(len(sorted_seed)) for j in range(i+1, len(sorted_seed)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos_set.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos_set)


def main():
    filters = load_filters()

    # Sidebar inputs
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")
    select_all  = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
    seed        = st.sidebar.text_input("Current 5-digit seed (required):").strip()
    prev_seed   = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
    prev_prev   = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
    method      = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
    hot_input   = st.sidebar.text_input("Hot digits (comma-separated):").strip()
    cold_input  = st.sidebar.text_input("Cold digits (comma-separated):").strip()
    check_combo = st.sidebar.text_input("Check specific combo:").strip()

    # Validate seed
    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits")
        return

    # Build context data
    seed_digits      = [int(d) for d in seed]
    prev_digits      = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_digits = [int(d) for d in prev_prev if d.isdigit()]
    new_digits       = set(seed_digits) - set(prev_digits)
    hot_digits       = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
    cold_digits      = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
    due_digits       = [d for d in range(10) if d not in prev_digits and d not in prev_prev_digits]
    seed_counts      = Counter(seed_digits)
    seed_vtracs      = set(V_TRAC_GROUPS[d] for d in seed_digits)
    seed_sum         = sum(seed_digits)
    prev_sum_cat     = sum_category(seed_sum)

    # Build previous pattern as tuple for comparisons
    prev_pattern = []
    for digs in (prev_prev_digits, prev_digits, seed_digits):
        cat = sum_category(sum(digs))
        parity = 'Even' if sum(digs) % 2 == 0 else 'Odd'
        prev_pattern.extend([cat, parity])
    prev_pattern = tuple(prev_pattern)

    def generate_context(cdigits):
        csum = sum(cdigits)
        return {
            'seed_digits':           seed_digits,
            'prev_seed_digits':      prev_digits,
            'prev_prev_seed_digits': prev_prev_digits,
            'new_seed_digits':       new_digits,
            'prev_pattern':          prev_pattern,
            'hot_digits':            hot_digits,
            'cold_digits':           cold_digits,
            'due_digits':            due_digits,
            'seed_counts':           seed_counts,
            'seed_sum':              seed_sum,
            'prev_sum_cat':          prev_sum_cat,
            'combo_digits':          cdigits,
            'combo_sum':             csum,
            'combo_sum_cat':         sum_category(csum),
            'seed_vtracs':           seed_vtracs,
            'combo_vtracs':          set(V_TRAC_GROUPS[d] for d in cdigits),
            'mirror':                MIRROR,
            'common_to_both':        set(prev_digits) & set(prev_prev_digits),
            'last2':                 set(prev_digits) | set(prev_prev_digits),
            'Counter':               Counter
        }

    combos    = generate_combinations(seed, method)
    eliminated = {}
    survivors  = []

    for combo in combos:
        cdigits = [int(c) for c in combo]
        ctx     = generate_context(cdigits)
        for flt in filters:
            key    = f"filter_{flt['id']}"
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

    # Specific combo check
    if check_combo:
        norm = ''.join(sorted(check_combo))
        if norm in eliminated:
            st.sidebar.info(f"Combo {check_combo} eliminated by {eliminated[norm]}")
        elif norm in survivors:
            st.sidebar.success(f"Combo {check_combo} survived all filters")
        else:
            st.sidebar.warning("Combo not found in generated list")

    # Active Filters UI
    st.header("🔧 Active Filters")
    flt_counts = {}  # Compute elimination counts
    for flt in filters:
        cnt = 0
        for combo in combos:
            cdigits = [int(c) for c in combo]
            ctx     = generate_context(cdigits)
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    cnt += 1
            except Exception:
                pass
        flt_counts[flt['id']] = cnt

    sorted_filters = sorted(filters, key=lambda flt: (flt_counts[flt['id']] == 0, -flt_counts[flt['id']]))
    for flt in sorted_filters:
        key   = f"filter_{flt['id']}"
        count = flt_counts[flt['id']]
        label = f"{flt['id']}: {flt['name']} — eliminated {count}"
        st.checkbox(label, key=key, value=st.session_state.get(key, select_all and flt['enabled_default']))

    with st.expander("Show remaining combinations"):
        for combo in survivors:
            st.write(combo)

if __name__ == '__main__':
    main()

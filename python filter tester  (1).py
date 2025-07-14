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
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 24:
        return 'Low'
    elif 25 <= total <= 33:
        return 'Mid'
    else:
        return 'High'


def load_filters(path: str = 'lottery_filters_batch10.csv') -> list:
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()
    filters = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = row.get('id', row.get('fid', '')).strip()
            for key in ('name', 'applicable_if', 'expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
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

    st.sidebar.header("🔢 DC-5 Filter Tracker Sorted")
    select_all    = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
    seed          = st.sidebar.text_input("Current 5-digit seed (required):").strip()
    prev_seed     = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
    prev_prev     = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
    method        = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
    hot_input     = st.sidebar.text_input("Hot digits (comma-separated):").strip()
    cold_input    = st.sidebar.text_input("Cold digits (comma-separated):").strip()
    check_combo   = st.sidebar.text_input("Check specific combo:").strip()

    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits")
        return

    seed_digits       = [int(d) for d in seed]
    prev_digits       = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_digits  = [int(d) for d in prev_prev if d.isdigit()]
    hot_digits        = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
    cold_digits       = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
    seed_counts       = Counter(seed_digits)
    seed_sum          = sum(seed_digits)

    def gen_ctx(cdigits):
        csum = sum(cdigits)
        return {
            'seed_digits':           seed_digits,
            'prev_seed_digits':      prev_digits,
            'prev_prev_seed_digits': prev_prev_digits,
            'hot_digits':            hot_digits,
            'cold_digits':           cold_digits,
            'seed_counts':           seed_counts,
            'seed_sum':              seed_sum,
            'combo_digits':          cdigits,
            'combo_sum':             csum,
            'mirror':                MIRROR,
            'Counter':               Counter,
            'sum_category':          sum_category
        }

    combos     = generate_combinations(seed, method)
    eliminated = {}
    survivors  = []

    # initial elimination pass
    for combo in combos:
        cdigits = [int(c) for c in combo]
        ctx = gen_ctx(cdigits)
        for flt in filters:
            key = f"filter_{flt['id']}"
            active = st.session_state.get(key, select_all and flt['enabled_default'])
            if not active:
                continue
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    eliminated[combo] = flt['name']
                    break
            except Exception:
                continue
        else:
            survivors.append(combo)

    st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

    if check_combo:
        norm = ''.join(sorted(check_combo))
        if norm in eliminated:
            st.sidebar.info(f"Combo {check_combo} eliminated by {eliminated[norm]}")
        elif norm in survivors:
            st.sidebar.success(f"Combo {check_combo} survived all filters")
        else:
            st.sidebar.warning("Combo not found in generated list")

    st.header("🔧 Active Filters")

    # original elimination counts
    orig_counts = {f['id']: 0 for f in filters}
    for flt in filters:
        cnt = 0
        for combo in combos:
            cd = [int(c) for c in combo]
            ctx = gen_ctx(cd)
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    cnt += 1
            except:
                pass
        orig_counts[flt['id']] = cnt

    # sort by original count descending
    sorted_by_orig = sorted(filters, key=lambda f: orig_counts[f['id']], reverse=True)

    # sequential elimination counts
    remaining = list(combos)
    rem_counts = {}
    for flt in sorted_by_orig:
        cnt = 0
        next_rem = []
        for combo in remaining:
            cd = [int(c) for c in combo]
            ctx = gen_ctx(cd)
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    cnt += 1
                else:
                    next_rem.append(combo)
            except:
                next_rem.append(combo)
        rem_counts[flt['id']] = cnt
        remaining = next_rem

    # standalone elimination on survivors
    surv_counts = {f['id']: 0 for f in filters}
    for flt in sorted_by_orig:
        cnt = 0
        for combo in survivors:
            cd = [int(c) for c in combo]
            ctx = gen_ctx(cd)
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    cnt += 1
            except:
                pass
        surv_counts[flt['id']] = cnt

    # display sorted filters
    for flt in sorted_by_orig:
        key   = f"filter_{flt['id']}"
        orig  = orig_counts.get(flt['id'], 0)
        now   = rem_counts.get(flt['id'], 0)
        sv    = surv_counts.get(flt['id'], 0)
        label = f"{flt['id']}: {flt['name']} — originally eliminates {orig}, now eliminates {now}, survivors-target {sv}"
        st.checkbox(label, key=key, value=st.session_state.get(key, select_all and flt['enabled_default']))

    with st.expander("Show remaining combinations"):
        for c in survivors:
            st.write(c)

if __name__ == '__main__':
    main()

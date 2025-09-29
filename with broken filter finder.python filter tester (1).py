import streamlit as st
from itertools import product
import csv
import os
from collections import Counter
import math

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS
mirror = MIRROR  # keep lowercase for CSV expressions

def sum_category(total: int) -> str:
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 24:
        return 'Low'
    elif 25 <= total <= 33:
        return 'Mid'
    else:
        return 'High'

def load_filters(path: str='lottery_filters_batch10.csv') -> list:
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
            expr = row.get('expression') or 'False'
            try:
                row['applicable_code'] = compile(applicable, '<applicable>', 'eval')
                row['expr_code'] = compile(expr, '<expr>', 'eval')
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
        pairs = {''.join(sorted((sorted_seed[i], sorted_seed[j])))
                 for i in range(len(sorted_seed)) for j in range(i+1, len(sorted_seed))}
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos_set.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos_set)

def main():
    filters = load_filters()
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")
    select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
    seed = st.sidebar.text_input("Draw 1-back (required):", help="Enter the draw immediately before the combo to test").strip()
    prev_seed = st.sidebar.text_input("Draw 2-back (optional):", help="Enter the draw two draws before the combo").strip()
    prev_prev = st.sidebar.text_input("Draw 3-back (optional):", help="Enter the draw three draws before the combo").strip()
    prev_prev_prev = st.sidebar.text_input("Draw 4-back (optional):", help="Enter the draw four draws before the combo").strip()
    method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
    hot_input = st.sidebar.text_input("Hot digits (comma-separated):").strip()
    cold_input = st.sidebar.text_input("Cold digits (comma-separated):").strip()
    check_combo = st.sidebar.text_input("Check specific combo:").strip()
    hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)

    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Draw 1-back must be exactly 5 digits")
        return

    # build context
    seed_digits = [int(d) for d in seed]
    prev_digits = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_digits = [int(d) for d in prev_prev if d.isdigit()]
    prev_prev_prev_digits = [int(d) for d in prev_prev_prev if d.isdigit()]
    new_digits = set(seed_digits) - set(prev_digits)
    hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
    cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]
    due_digits = [d for d in range(10) if d not in prev_digits and d not in prev_prev_digits]
    seed_counts = Counter(seed_digits)
    seed_vtracs = set(V_TRAC_GROUPS[d] for d in seed_digits)
    seed_sum = sum(seed_digits)
    prev_sum_cat = sum_category(seed_sum)
    prev_pattern = []
    for digs in (prev_prev_digits, prev_digits, seed_digits):
        parity = 'Even' if sum(digs) % 2 == 0 else 'Odd'
        prev_pattern.extend([sum_category(sum(digs)), parity])
    prev_pattern = tuple(prev_pattern)

    def gen_ctx(cdigits):
        csum = sum(cdigits)
        return {
            'seed_value': int(seed),
            'seed_sum': seed_sum,
            'prev_seed_sum': sum(prev_digits) if prev_digits else None,
            'prev_prev_seed_sum': sum(prev_prev_digits) if prev_prev_digits else None,
            'prev_prev_prev_seed_sum': sum(prev_prev_prev_digits) if prev_prev_prev_digits else None,
            'seed_digits_1': prev_digits,
            'seed_digits_2': prev_prev_digits,
            'seed_digits_3': prev_prev_prev_digits,
            'nan': float('nan'),
            'seed_digits': seed_digits,
            'prev_seed_digits': prev_digits,
            'prev_prev_seed_digits': prev_prev_digits,
            'prev_prev_prev_seed_digits': prev_prev_prev_digits,
            'new_seed_digits': new_digits,
            'prev_pattern': prev_pattern,
            'hot_digits': hot_digits,
            'cold_digits': cold_digits,
            'due_digits': due_digits,
            'seed_counts': seed_counts,
            'combo_digits': cdigits,
            'combo_sum': csum,
            'combo_sum_cat': sum_category(csum),
            'seed_vtracs': seed_vtracs,
            'combo_vtracs': set(V_TRAC_GROUPS[d] for d in cdigits),
            'mirror': MIRROR,
            'common_to_both': set(seed_digits) & set(prev_digits),
            'last2': set(seed_digits) | set(prev_digits),
            'Counter': Counter
        }

    combos = generate_combinations(seed, method)
    eliminated = {}
    survivors = []
    for combo in combos:
        cdigits = [int(c) for c in combo]
        ctx = gen_ctx(cdigits)
        for flt in filters:
            key = f"filter_{flt['id']}"
            if not st.session_state.get(key, select_all and flt['enabled_default']):
                continue
            try:
                if not eval(flt['applicable_code'], ctx, ctx):
                    continue
                if eval(flt['expr_code'], ctx, ctx):
                    eliminated[combo] = flt['name']
                    break
            except:
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

    # initial counts
    init_counts = {flt['id']: 0 for flt in filters}
    for flt in filters:
        for combo in combos:
            cdigits = [int(c) for c in combo]
            ctx = gen_ctx(cdigits)
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    init_counts[flt['id']] += 1
            except:
                pass

    sorted_filters = sorted(filters, key=lambda flt: (init_counts[flt['id']] == 0, -init_counts[flt['id']]))

    if hide_zero:
        display_filters = [flt for flt in sorted_filters if init_counts[flt['id']] > 0]
    else:
        display_filters = sorted_filters

    st.markdown(f"**Initial Manual Filters Count:** {len(display_filters)}")

    pool = list(combos)
    dynamic_counts = {}
    for flt in display_filters:
        key = f"filter_{flt['id']}"
        active = st.session_state.get(key, select_all and flt['enabled_default'])
        dc = 0
        survivors_pool = []
        if active:
            for combo in pool:
                cdigits = [int(c) for c in combo]
                ctx = gen_ctx(cdigits)
                try:
                    if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                        dc += 1
                    else:
                        survivors_pool.append(combo)
                except:
                    survivors_pool.append(combo)
        else:
            survivors_pool = pool.copy()
        dynamic_counts[flt['id']] = dc
        pool = survivors_pool

    st.header("🔧 Active Filters")
    for flt in display_filters:
        key = f"filter_{flt['id']}"
        ic = init_counts[flt['id']]
        dc = dynamic_counts.get(flt['id'], 0)
        label = f"{flt['id']}: {flt['name']} — {dc}/{ic} eliminated"
        st.checkbox(label, key=key, value=st.session_state.get(key, select_all and flt['enabled_default']))

    with st.expander("Show remaining combinations"):
        for c in survivors:
            st.write(c)

    # Diagnostic block
    if check_combo:
        test_digits = [int(c) for c in check_combo if c.isdigit()]
        ctx = gen_ctx(test_digits)
        triggered = []
        failed = []
        for flt in filters:
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    triggered.append(flt['id'])
            except Exception as e:
                failed.append((flt['id'], f"{flt['name']} → {e}"))

        st.subheader("⚡ Filter Diagnostics")
        st.write(f"Triggered filters: {len(triggered)} / {len(filters)}")
        if triggered:
            st.text(", ".join(triggered))
        st.write(f"Filters failed (error → automatically returned False): {len(failed)}")
        if failed:
            for fid, msg in failed:
                st.text(f"{fid}: {msg}")

if __name__ == '__main__':
    main()

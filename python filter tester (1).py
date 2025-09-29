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

def compute_hot_cold(digits_list, hot_n=3, cold_n=3):
    """Return top hot_n and cold_n digits with ties allowed"""
    cnt = Counter(digits_list)
    if not cnt: return [], []
    freqs_desc = cnt.most_common()
    cutoff_hot = freqs_desc[min(hot_n - 1, len(freqs_desc)-1)][1]
    hot = sorted([d for d, c in cnt.items() if c >= cutoff_hot])
    freqs_asc = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]))
    cutoff_cold = freqs_asc[min(cold_n - 1, len(freqs_asc)-1)][1]
    cold = sorted([d for d, c in cnt.items() if c <= cutoff_cold])
    return hot, cold

def main():
    filters = load_filters()
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")

    select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)

    # Accept 10 past draws
    past_draws = []
    for i in range(1, 11):
        val = st.sidebar.text_input(f"Draw {i}-back:", help=f"Enter draw {i} back (required for accurate hot/cold)").strip()
        if val:
            past_draws.append(val)

    method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
    hot_input = st.sidebar.text_input("Hot digits override (comma-separated):").strip()
    cold_input = st.sidebar.text_input("Cold digits override (comma-separated):").strip()
    check_combo = st.sidebar.text_input("Check specific combo:").strip()
    hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)

    if not past_draws or len(past_draws[0]) != 5 or not past_draws[0].isdigit():
        st.sidebar.error("Draw 1-back must be exactly 5 digits")
        return

    seed = past_draws[0]
    seed_digits = [int(d) for d in seed]

    # Hot/Cold auto calculation only if we have 10 draws (50 digits)
    all_digits_flat = [int(d) for draw in past_draws if len(draw)==5 for d in draw if d.isdigit()]
    if len(all_digits_flat) >= 50:
        auto_hot, auto_cold = compute_hot_cold(all_digits_flat)
    else:
        auto_hot, auto_cold = [], []

    # Parse overrides
    hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()] or auto_hot
    cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()] or auto_cold

    # Due digits based on last two draws
    last2_digits = [int(d) for draw in past_draws[:2] if len(draw)==5 for d in draw]
    due_digits = [d for d in range(10) if d not in last2_digits]

    # Display stats
    st.sidebar.markdown(f"**Auto ➜** Hot {auto_hot} | Cold {auto_cold}")
    st.sidebar.markdown(f"**Using ➜** Hot {hot_digits} | Cold {cold_digits} | Due {due_digits}")

    # combos
    combos = generate_combinations(seed, method)

    # Build context generator
    def gen_ctx(cdigits):
        csum = sum(cdigits)
        return {
            'seed_digits': seed_digits,
            'combo_digits': cdigits,
            'combo_sum': csum,
            'combo_sum_cat': sum_category(csum),
            'hot_digits': hot_digits,
            'cold_digits': cold_digits,
            'due_digits': due_digits,
            'V_TRAC_GROUPS': V_TRAC_GROUPS,
            'mirror': MIRROR,
            'Counter': Counter
        }

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

    # Initial counts
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
    display_filters = [flt for flt in sorted_filters if init_counts[flt['id']] > 0] if hide_zero else sorted_filters

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

if __name__ == '__main__':
    main()
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

def compute_hot_cold(digits_list, hot_n=3, cold_n=3):
    """Return top hot_n and cold_n digits with ties allowed"""
    cnt = Counter(digits_list)
    if not cnt: return [], []
    freqs_desc = cnt.most_common()
    cutoff_hot = freqs_desc[min(hot_n - 1, len(freqs_desc)-1)][1]
    hot = sorted([d for d, c in cnt.items() if c >= cutoff_hot])
    freqs_asc = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]))
    cutoff_cold = freqs_asc[min(cold_n - 1, len(freqs_asc)-1)][1]
    cold = sorted([d for d, c in cnt.items() if c <= cutoff_cold])
    return hot, cold

def main():
    filters = load_filters()
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")

    select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)

    # Accept 10 past draws
    past_draws = []
    for i in range(1, 11):
        val = st.sidebar.text_input(f"Draw {i}-back:", help=f"Enter draw {i} back (required for accurate hot/cold)").strip()
        if val:
            past_draws.append(val)

    method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
    hot_input = st.sidebar.text_input("Hot digits override (comma-separated):").strip()
    cold_input = st.sidebar.text_input("Cold digits override (comma-separated):").strip()
    check_combo = st.sidebar.text_input("Check specific combo:").strip()
    hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)

    if not past_draws or len(past_draws[0]) != 5 or not past_draws[0].isdigit():
        st.sidebar.error("Draw 1-back must be exactly 5 digits")
        return

    seed = past_draws[0]
    seed_digits = [int(d) for d in seed]

    # Hot/Cold auto calculation only if we have 10 draws (50 digits)
    all_digits_flat = [int(d) for draw in past_draws if len(draw)==5 for d in draw if d.isdigit()]
    if len(all_digits_flat) >= 50:
        auto_hot, auto_cold = compute_hot_cold(all_digits_flat)
    else:
        auto_hot, auto_cold = [], []

    # Parse overrides
    hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()] or auto_hot
    cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()] or auto_cold

    # Due digits based on last two draws
    last2_digits = [int(d) for draw in past_draws[:2] if len(draw)==5 for d in draw]
    due_digits = [d for d in range(10) if d not in last2_digits]

    # Display stats
    st.sidebar.markdown(f"**Auto ➜** Hot {auto_hot} | Cold {auto_cold}")
    st.sidebar.markdown(f"**Using ➜** Hot {hot_digits} | Cold {cold_digits} | Due {due_digits}")

    # combos
    combos = generate_combinations(seed, method)

    # Build context generator
    def gen_ctx(cdigits):
        csum = sum(cdigits)
        return {
            'seed_digits': seed_digits,
            'combo_digits': cdigits,
            'combo_sum': csum,
            'combo_sum_cat': sum_category(csum),
            'hot_digits': hot_digits,
            'cold_digits': cold_digits,
            'due_digits': due_digits,
            'V_TRAC_GROUPS': V_TRAC_GROUPS,
            'mirror': MIRROR,
            'Counter': Counter
        }

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

    # Initial counts
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
    display_filters = [flt for flt in sorted_filters if init_counts[flt['id']] > 0] if hide_zero else sorted_filters

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

if __name__ == '__main__':
    main()

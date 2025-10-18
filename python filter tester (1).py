import streamlit as st
from itertools import product
import csv
import os
from collections import Counter
import math
import ast
import re

# ---------- Safe built-ins for eval ----------
ALLOWED_BUILTINS = {
    'len': len, 'sum': sum, 'any': any, 'all': all,
    'set': set, 'range': range, 'sorted': sorted,
    'min': min, 'max': max, 'abs': abs, 'round': round,
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'tuple': tuple, 'list': list, 'dict': dict,
    'zip': zip, 'map': map, 'enumerate': enumerate,
    'Counter': Counter, 'math': math,
}

# --------------------------------------------
# === Helper functions and variable pre-definitions for LL filters ===

def combo_has_run(core_digits, run_len=3):
    s = ''.join(str(d) for d in combo_digits)
    for d in core_digits:
        if str(d) * run_len in s:
            return True
    return False

def count_core_digits(*core_digits):
    return sum(1 for d in core_digits if int(d) in combo_digits)

def score_core_digits(*core_digits):
    return sum(1 for d in core_digits if int(d) in combo_digits)

combo_letters = []
core_letters = []

V_TRAC_GROUPS = {0: 1, 5: 1, 1: 2, 6: 2, 2: 3, 7: 3, 3: 4, 8: 4, 4: 5, 9: 5}
MIRROR_PAIRS = {0: 5, 5: 0, 1: 6, 6: 1, 2: 7, 7: 2, 3: 8, 8: 3, 4: 9, 9: 4}
MIRROR = MIRROR_PAIRS
mirror = MIRROR

VTRAC_GROUP = V_TRAC_GROUPS
V_TRAC = V_TRAC_GROUPS
VTRAC_GROUPS = V_TRAC_GROUPS
vtrac = V_TRAC_GROUPS
mirror_pairs = MIRROR_PAIRS
mirrir = MIRROR

def sum_category(total: int) -> str:
    if 0 <= total <= 14:
        return 'Very Low'
    elif 15 <= total <= 20:
        return 'Low'
    elif 21 <= total <= 26:
        return 'Mid'
    else:
        return 'High'

def structure_of(digits):
    counts = sorted(Counter(digits).values(), reverse=True)
    if counts == [1, 1, 1, 1, 1]:
        return 'SINGLE'
    if counts == [2, 1, 1, 1]:
        return 'DOUBLE'
    if counts == [2, 2, 1]:
        return 'DOUBLE-DOUBLE'
    if counts == [3, 1, 1]:
        return 'TRIPLE'
    if counts == [3, 2]:
        return 'TRIPLE-DOUBLE'
    if counts == [4, 1]:
        return 'QUAD'
    if counts == [5]:
        return 'QUINT'
    return f'OTHER-{counts}'

def _enabled_value(val: str) -> bool:
    s = (val or '').strip().lower()
    return s in {'true', '1', 'yes', 'y'}

_leading_zero_int = re.compile(r'(?<![\w])0+(\d+)(?!\s*\.)')

def _sanitize_numeric_literals(code_or_obj):
    if isinstance(code_or_obj, str):
        return _leading_zero_int.sub(r'\1', code_or_obj)
    return code_or_obj

def _eval_code(code_or_obj, ctx):
    g = {'__builtins__': ALLOWED_BUILTINS}
    try:
        return eval(code_or_obj, g, ctx)
    except SyntaxError:
        return eval(_sanitize_numeric_literals(code_or_obj), g, ctx)

def load_filters(path: str = 'lottery_filters_batch10.csv') -> list:
    if not os.path.exists(path):
        st.error(f'Filter file not found: {path}')
        st.stop()

    filters = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = (row.get('id') or row.get('fid') or '').strip()
            for key in ('name', 'applicable_if', 'expression', 'enabled'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")

            applicable = row.get('applicable_if') or 'True'
            expr = row.get('expression') or 'False'

            try:
                ast.parse(f'({applicable})', mode='eval')
                app_code = compile(applicable, '<applicable>', 'eval')
            except SyntaxError:
                app_code = applicable

            try:
                ast.parse(f'({expr})', mode='eval')
                expr_code = compile(expr, '<expr>', 'eval')
            except SyntaxError:
                expr_code = expr

            flt = {
                'id': row['id'],
                'name': row.get('name', ''),
                'enabled_default': _enabled_value(row.get('enabled', '')),
                'applicable_code': app_code,
                'expr_code': expr_code,
            }
            filters.append(flt)

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
                 for i in range(len(sorted_seed)) for j in range(i + 1, len(sorted_seed))}
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos_set.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos_set)

def main():
    filters = load_filters()
    st.sidebar.header('🔎 DC-5 Filter Tracker Full')
    select_all = st.sidebar.checkbox('Select/Deselect All Filters', value=True)

    seed = st.sidebar.text_input('Draw 1-back (required):').strip()
    prev_seed = st.sidebar.text_input('Draw 2-back (optional):').strip()
    prev_prev_seed = st.sidebar.text_input('Draw 3-back (optional):').strip()

    seed_digits = [int(d) for d in seed if d.isdigit()]
    prev_digits = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_digits = [int(d) for d in prev_prev_seed if d.isdigit()]

    due_input = st.sidebar.text_input('Due digits (comma-separated, optional):').strip()

    if due_input:
        due_digits = [int(x) for x in due_input.split(',') if x.strip().isdigit()]
    else:
        due_digits = [d for d in range(10) if d not in prev_digits and d not in prev_prev_digits]

    seed_counts = Counter(seed_digits)
    seed_vtracs = set(V_TRAC_GROUPS[d] for d in seed_digits)
    seed_sum = sum(seed_digits)

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
            'seed_sum_last_digit': seed_sum % 10,
            'prev_seed_sum': sum(prev_digits) if prev_digits else None,
            'prev_prev_seed_sum': sum(prev_prev_digits) if prev_prev_digits else None,
            'seed_digits': seed_digits,
            'prev_seed_digits': prev_digits,
            'prev_prev_seed_digits': prev_prev_digits,
            'due_digits': due_digits,
            'seed_counts': seed_counts,
            'combo_digits': cdigits,
            'combo_sum': csum,
            'combo_sum_cat': sum_category(csum),
            'seed_vtracs': seed_vtracs,
            'combo_vtracs': set(V_TRAC_GROUPS[d] for d in cdigits),
            'sum_category': sum_category,
            'structure_of': structure_of,
        }

    method = '2-digit'
    combos = generate_combinations(seed, method)
    st.session_state['combo_pool'] = [str(c).zfill(5) for c in combos if str(c).isdigit() and len(str(c)) == 5]

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
                ok_if = _eval_code(flt['applicable_code'], ctx)
                if not ok_if:
                    continue
                if _eval_code(flt['expr_code'], ctx):
                    eliminated[combo] = flt['name']
                    break
            except Exception:
                continue
        else:
            survivors.append(combo)

    st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

if __name__ == '__main__':
    main()

try:
    from filter_checker_footer import render_filter_checker
except Exception as _e:
    def render_filter_checker(*args, **kwargs):
        st.error(f"filter_checker_footer.py not found or failed to import: {_e}")

_pool_guess = st.session_state.get('combo_pool', [])
if 'combos' in locals() and locals()['combos']:
    _pool_guess = locals()['combos']

render_filter_checker(combos=_pool_guess, filters_df=None)

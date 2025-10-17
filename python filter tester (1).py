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
    # common funcs
    "len": len, "sum": sum, "any": any, "all": all,
    "set": set, "range": range, "sorted": sorted,
    "min": min, "max": max, "abs": abs, "round": round,

    # types & converters often used in filters
    "int": int, "float": float, "str": str, "bool": bool,
    "tuple": tuple, "list": list, "dict": dict,

    # utilities used in some rows
    "zip": zip, "map": map, "enumerate": enumerate,

    # extras
    "Counter": Counter,
    "math": math,
}
# --------------------------------------------
# === Helper functions and variable pre-definitions for LL filters ===
def combo_has_run(core_digits, run_len=3):
    """Return True if any 3+ consecutive digits from core_digits appear."""
    s = "".join(str(d) for d in combo_digits)
    for d in core_digits:
        if str(d) * run_len in s:
            return True
    return False

def count_core_digits(*core_digits):
    """Count how many unique core digits appear in combo."""
    return sum(1 for d in core_digits if int(d) in combo_digits)

def score_core_digits(*core_digits):
    """Soft filter metric — number of core digits present."""
    return sum(1 for d in core_digits if int(d) in combo_digits)

# Variables referenced by expressions
combo_letters = []  # letters corresponding to digits (if your app defines letter mapping)
core_letters = []   # core letters for the current seed

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS
mirror = MIRROR  # keep lowercase for CSV expressions

# Aliases so older filters keep working
VTRAC_GROUP = V_TRAC_GROUPS
V_TRAC = V_TRAC_GROUPS
VTRAC_GROUPS = V_TRAC_GROUPS
vtrac = V_TRAC_GROUPS
mirror_pairs = MIRROR_PAIRS
mirrir = MIRROR  # common typo alias

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
    if counts == [1,1,1,1,1]:
        return 'SINGLE'
    if counts == [2,1,1,1]:
        return 'DOUBLE'
    if counts == [2,2,1]:
        return 'DOUBLE-DOUBLE'
    if counts == [3,1,1]:
        return 'TRIPLE'
    if counts == [3,2]:
        return 'TRIPLE-DOUBLE'
    if counts == [4,1]:
        return 'QUAD'
    if counts == [5]:
        return 'QUINT'
    return f'OTHER-{counts}'

def _enabled_value(val: str) -> bool:
    s = (val or "").strip().lower()
    return s in {'"""true"""','"true"','true','1','yes','y'}

# --- literal sanitizer for legacy 08/09 style ints ---
_leading_zero_int = re.compile(r'(?<![\w])0+(\d+)(?!\s*\.)')  # 08 -> 8, leaves 0.5 alone
def _sanitize_numeric_literals(code_or_obj):
    if isinstance(code_or_obj, str):
        return _leading_zero_int.sub(r"\1", code_or_obj)
    return code_or_obj

def _eval_code(code_or_obj, ctx):
    """Eval code object or string with safe builtins; retry once after sanitizing legacy ints."""
    g = {"__builtins__": ALLOWED_BUILTINS}
    try:
        return eval(code_or_obj, g, ctx)
    except SyntaxError:
        # If string expression has 08/09 etc., sanitize and retry
        return eval(_sanitize_numeric_literals(code_or_obj), g, ctx)
# === Helper definitions for LL-series filters ===
# These are required by LL001–LL007a and related filters.

# Ensure combo_digits exists before evaluation
try:
    combo_digits
except NameError:
    combo_digits = []

# --- Core helper functions ---
def combo_has_run(core_digits, run_len=3):
    """True if the combo contains ≥run_len consecutive identical digits from core_digits."""
    s = "".join(str(d) for d in combo_digits)
    for d in core_digits:
        seq = str(d) * run_len
        if seq in s:
            return True
    return False

def count_core_digits(*core_digits):
    """Count how many core digits appear in the combo."""
    return sum(int(d) in combo_digits for d in core_digits)

def score_core_digits(*core_digits):
    """Soft filter metric – number of core digits present."""
    return sum(int(d) in combo_digits for d in core_digits)

# --- Letter mapping for B/E/J filters ---
# Hot→cold order (A–J).  Update dynamically if your app provides one;
# otherwise this default keeps filters from erroring.
LETTER_MAP = {
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4,
    'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9
}

# Provide default globals so filters referencing them don’t fail
try:
    combo_letters
except NameError:
    combo_letters = [k for d in combo_digits for k, v in LETTER_MAP.items() if v == int(d)]
try:
    core_letters
except NameError:
    core_letters = []

# === END helper definitions ===

def load_filters(path: str='lottery_filters_batch10.csv') -> list:
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    filters = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = (row.get('id') or row.get('fid') or '').strip()
            # normalize fields
            for key in ('name', 'applicable_if', 'expression', 'enabled'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")

            applicable = row.get('applicable_if') or 'True'
            expr = row.get('expression') or 'False'

            # Try to compile; if that fails, keep raw strings (we'll sanitize at eval time)
            try:
                ast.parse(f"({applicable})", mode='eval')
                app_code = compile(applicable, '<applicable>', 'eval')
            except SyntaxError:
                app_code = applicable  # keep as string

            try:
                ast.parse(f"({expr})", mode='eval')
                expr_code = compile(expr, '<expr>', 'eval')
            except SyntaxError:
                expr_code = expr  # keep as string

            flt = {
                "id": row['id'],
                "name": row.get('name',''),
                "enabled_default": _enabled_value(row.get('enabled','')),
                "applicable_code": app_code,
                "expr_code": expr_code,
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

    # manual due digits override
    due_input = st.sidebar.text_input("Due digits (comma-separated, optional):").strip()

    check_combo = st.sidebar.text_input("Check specific combo:").strip()
    hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)

    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Draw 1-back must be exactly 5 digits")
        return

    seed_digits = [int(d) for d in seed]
    prev_digits = [int(d) for d in prev_seed if d.isdigit()]
    prev_prev_digits = [int(d) for d in prev_prev if d.isdigit()]
    prev_prev_prev_digits = [int(d) for d in prev_prev_prev if d.isdigit()]
    new_digits = set(seed_digits) - set(prev_digits)
    hot_digits = [int(x) for x in hot_input.split(',') if x.strip().isdigit()]
    cold_digits = [int(x) for x in cold_input.split(',') if x.strip().isdigit()]

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
            'seed_sum_last_digit': seed_sum % 10,  # convenience
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

            # mappings & aliases many filters use
            'MIRROR': MIRROR, 'mirror': MIRROR, 'mirrir': MIRROR, 'MIRROR_PAIRS': MIRROR_PAIRS,
            'V_TRAC_GROUPS': V_TRAC_GROUPS, 'VTRAC_GROUPS': V_TRAC_GROUPS,
            'V_TRAC': V_TRAC_GROUPS, 'VTRAC_GROUP': V_TRAC_GROUPS, 'vtrac': V_TRAC_GROUPS,

            'common_to_both': set(seed_digits) & set(prev_digits),
            'last2': set(seed_digits) | set(prev_digits),
            'Counter': Counter,
            'combo_structure': structure_of(cdigits),
            'winner_structure': structure_of(seed_digits),

            # helpers callable from expressions
            'sum_category': sum_category,
            'structure_of': structure_of,
        }

    # ----- Generate pool -----
    combos = generate_combinations(seed, method)
    # Save to session so the footer can see it (normalize defensively)
    st.session_state['combo_pool'] = [str(c).zfill(5) for c in combos if str(c).isdigit() and len(str(c)) == 5]

    # ----- Run filters (initial elimination pass) -----
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
                # treat as not firing for the initial pass
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
# =============================
# Define shared variables needed for LL filters
# =============================

# Convert combo and seed into lists of digits
combo_digits = list(str(combo)) if 'combo' in locals() else []
seed_digits = list(str(seed)) if 'seed' in locals() else []

# Convenience: establish variable name aliases
combo_has_run = True
info = {}
rankings = {}

# Safety: ensure ord() is available for numeric checks
# (Already built-in, but we redefine to suppress “ord not defined” errors)
def ord(x): 
    try:
        return __builtins__.ord(x)
    except Exception:
        return 0

    # ----- “initial eliminations” counts for UI -----
    init_counts = {flt['id']: 0 for flt in filters}
    for flt in filters:
        for combo in combos:
            cdigits = [int(c) for c in combo]
            ctx = gen_ctx(cdigits)
            try:
                if _eval_code(flt['applicable_code'], ctx) and _eval_code(flt['expr_code'], ctx):
                    init_counts[flt['id']] += 1
            except Exception:
                pass

    sorted_filters = sorted(filters, key=lambda flt: (init_counts[flt['id']] == 0, -init_counts[flt['id']]))

    if hide_zero:
        display_filters = [flt for flt in sorted_filters if init_counts[flt['id']] > 0]
    else:
        display_filters = sorted_filters

    st.markdown(f"**Initial Manual Filters Count:** {len(display_filters)}")

    # ----- Dynamic apply based on toggles -----
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
                    if _eval_code(flt['applicable_code'], ctx) and _eval_code(flt['expr_code'], ctx):
                        dc += 1
                    else:
                        survivors_pool.append(combo)
                except Exception:
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

    # ----- Per-combo diagnostics (on demand) -----
    if check_combo:
        test_digits = [int(c) for c in check_combo if c.isdigit()]
        ctx = gen_ctx(test_digits)
        triggered = []
        failed = []
        for flt in filters:
            try:
                if _eval_code(flt['applicable_code'], ctx) and _eval_code(flt['expr_code'], ctx):
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

    # ----- Hot / Cold / Due calculator -----
    st.sidebar.markdown("---")
    st.sidebar.subheader("Hot / Cold / Due Calculator")

    calc_draws = []
    for i in range(1, 11):
        calc_draws.append(
            st.sidebar.text_input(
                f"Draw {i}-back (for calculator)",
                key=f"calc_draw_{i}"
            ).strip()
        )

    if all(len(d) == 5 and d.isdigit() for d in calc_draws):
        seq = "".join(calc_draws)
        cnt = Counter(int(ch) for ch in seq)

        auto_hot, auto_cold, auto_due = [], [], []
        if cnt:
            hot_cutoff = cnt.most_common(3)[-1][1] if len(cnt) >= 3 else cnt.most_common()[-1][1]
            auto_hot = sorted([d for d, c in cnt.items() if c >= hot_cutoff])

            sorted_asc = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]))
            cold_cutoff = sorted_asc[min(2, len(sorted_asc)-1)][1] if len(sorted_asc) >= 3 else sorted_asc[-1][1]
            auto_cold = sorted([d for d, c in cnt.items() if c <= cold_cutoff])

        last2 = "".join(calc_draws[:2])
        seen = {int(x) for x in last2}
        auto_due = [d for d in range(10) if d not in seen]

        st.sidebar.write(f"**Hot:** {auto_hot}")
        st.sidebar.write(f"**Cold:** {auto_cold}")
        st.sidebar.write(f"**Due:** {auto_due}")
    else:
        st.sidebar.info("Enter all **10** past draws (5 digits each) to calculate Hot/Cold/Due.")

if __name__ == '__main__':
    main()

# --- Diagnostics footer import + call ---
try:
    from filter_checker_footer import render_filter_checker
except Exception as _e:  # ModuleNotFoundError or any import error
    _FOOTER_ERR = f"filter_checker_footer.py not found or failed to import: {_e}"
    def render_filter_checker(*args, **kwargs):
        st.error(_FOOTER_ERR)

# Pool for footer: prefer current combos, else session_state
_pool_guess = st.session_state.get('combo_pool', [])
if 'combos' in locals() and locals()['combos']:
    _pool_guess = locals()['combos']

render_filter_checker(combos=_pool_guess, filters_df=None)

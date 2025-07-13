import streamlit as st
from itertools import product
import csv, os
from collections import Counter

# Define sum_category to categorize seed and combo sums
def sum_category(total: int) -> str:
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 20:
        return 'Low'
    elif 21 <= total <= 25:
        return 'Mid'
    elif 26 <= total <= 30:
        return 'High'
    else:
        return 'Very High'

# Load filters from CSV, tolerating backslashes and unescaped quotes
def load_filters(csv_path='lottery_filters_batch10.csv'):
    filters = []
    if not os.path.exists(csv_path):
        st.error(f"Filter file not found: {csv_path}")
        st.stop()
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONE, escapechar='\\')
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            if row.get('enabled','').strip().lower() not in ('true','1'):
                continue
            applicable = row.get('applicable_if','').strip() or 'True'
            expr = row.get('expression','').strip() or 'False'
            expr = expr.replace('!==','!=')
            try:
                filters.append({
                    'id': row['id'].strip(),
                    'name': row['name'].strip(),
                    'applicable_code': compile(applicable, '<applicable>', 'eval'),
                    'expr_code': compile(expr, '<expr>', 'eval'),
                    'enabled_default': row.get('enabled').lower() == 'true'
                })
            except SyntaxError as e:
                st.warning(f"Skipping filter {row.get('id')}: {e}")
    return filters

# Generate all 5-digit combos based on method
def generate_combinations(seed, method):
    all_digits = '0123456789'
    combos = set()
    sorted_seed = ''.join(sorted(seed))

    if method == '1-digit':
        for d in sorted_seed:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = {''.join(sorted((sorted_seed[i], sorted_seed[j])))
                 for i in range(5) for j in range(i+1, 5)}
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))

    return sorted(combos)

# Main Streamlit app
def main():
    # Load and build
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")
    select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True)
    seed = st.sidebar.text_input("Current 5-digit seed (required):").strip()
    prev_seed = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
    prev_prev_seed = st.sidebar.text_input("Prev Prev 5-digit seed (optional):").strip()

    # Validate current seed
    if len(seed) != 5 or not seed.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits")
        return
    method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])

    # Build history digits, sums, and categories
    history = [prev_prev_seed, prev_seed, seed]
    history_digits = [([int(d) for d in h] if len(h)==5 and h.isdigit() else None)
                      for h in history]
    history_sums = [sum(d) if d else None for d in history_digits]
    history_cats = [sum_category(s) if s is not None else None for s in history_sums]

    # Generate combos and prepare counts
    combos = generate_combinations(seed, method)
    eliminated = {}
    survivors = []
    seed_digits = [int(d) for d in seed]
    seed_sum = sum(seed_digits)

    filters = load_filters()
    # Apply filters to each combo
    for combo in combos:
        cdigits = [int(c) for c in combo]
        combo_sum = sum(cdigits)
        ctx = {
            'seed_digits': seed_digits,
            'combo_digits': cdigits,
            'seed_sum': seed_sum,
            'combo_sum': combo_sum,
            'prev_seed_sum': history_sums[1],
            'prev_prev_seed_sum': history_sums[0],
            'seed_cats': history_cats
        }
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

    # Summary
    st.sidebar.markdown(f"**Total:** {len(combos)}  Elim: {len(eliminated)}  Remain: {len(survivors)}")

    # Active filters UI
    st.header("🔧 Active Filters")
    flt_counts = Counter()
    for flt in filters:
        for combo in combos:
            cd = [int(c) for c in combo]
            ctx = {
                'seed_sum': seed_sum,
                'combo_sum': sum(cd),
                'prev_seed_sum': history_sums[1],
                'prev_prev_seed_sum': history_sums[0],
                'seed_cats': history_cats
            }
            try:
                if eval(flt['applicable_code'], ctx, ctx) and eval(flt['expr_code'], ctx, ctx):
                    flt_counts[flt['id']] += 1
            except:
                pass

    # Sort and render filter checkboxes
    sorted_filters = sorted(filters, key=lambda f: (flt_counts[f['id']] == 0, -flt_counts[f['id']]))
    for flt in sorted_filters:
        key = f"filter_{flt['id']}"
        label = f"{flt['id']}: {flt['name']} — eliminated {flt_counts[flt['id']]}"
        st.checkbox(label, key=key, value=st.session_state.get(key, select_all and flt['enabled_default']))

    # Show survivors
    with st.expander("Show remaining combinations"):
        for combo in survivors:
            st.write(combo)

if __name__ == '__main__':
    main()

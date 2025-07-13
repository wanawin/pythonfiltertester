import streamlit as st
from itertools import product
import csv, os
from collections import Counter

# Define sum_category to categorize sums
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

# Define parity helper
def parity(n: int) -> str:
    return 'Even' if n % 2 == 0 else 'Odd'

# Load filters from CSV, tolerating unescaped quotes by disabling quoting and using escapechar
def load_filters(csv_path='lottery_filters_batch10.csv'):
    filters = []
    if not os.path.exists(csv_path):
        st.error(f"Filter file not found: {csv_path}")
        st.stop()

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONE, escapechar='\\')
        for raw in reader:
            if not raw or raw.get('id') is None:
                continue
            row = {k.lower(): (v or '').strip() for k, v in raw.items()}
            if row.get('enabled', '').lower() not in ('true', '1'):
                continue

            applicable = row.get('applicable_if') or 'True'
            expr = (row.get('expression') or 'False').replace('!==', '!=')
            try:
                filters.append({
                    'id': row['id'],
                    'name': row['name'],
                    'applicable_code': compile(applicable, '<applicable>', 'eval'),
                    'expr_code': compile(expr, '<expr>', 'eval'),
                    'enabled_default': row.get('enabled', '').lower() == 'true'
                })
            except SyntaxError as e:
                st.warning(f"Skipping filter {row.get('id')}: {e}")
    return filters

# -- UI and evaluation context --
def main():
    st.sidebar.title('DC-5 Filter Tracker')
    current_seed = st.sidebar.text_input('Current 5-digit seed (required):')
    prev_seed = st.sidebar.text_input('Previous 5-digit seed (optional):')
    prev_prev_seed = st.sidebar.text_input('Prev Prev 5-digit seed (optional):')
    gen_method = st.sidebar.selectbox('Generation Method:', ['1-digit', '2-digit'])
    hot = st.sidebar.text_input('Hot digits (comma-separated):')
    cold = st.sidebar.text_input('Cold digits (comma-separated):')
    track_combo = st.sidebar.text_input('Track specific combo (optional):')

    # Validate seeds
    # ... validation code ...

    filters = load_filters()
    results = []

    # Generate combinations based on method
    for combo in product(range(10), repeat=1 if gen_method=='1-digit' else 2):
        seed_digits = [int(d) for d in current_seed]
        prev_digits = [int(d) for d in prev_seed] if prev_seed else []
        prev_prev_digits = [int(d) for d in prev_prev_seed] if prev_prev_seed else []

        seed_sum = sum(seed_digits)
        prev_seed_sum = sum(prev_digits) if prev_digits else None
        prev_prev_seed_sum = sum(prev_prev_digits) if prev_prev_digits else None
        combo_sum = sum(combo)

        # Build last_three tuple: (category, parity) pairs for prev_prev, prev, current
        last_three = ()
        if prev_prev_seed_sum is not None:
            last_three += (sum_category(prev_prev_seed_sum), parity(prev_prev_seed_sum))
        if prev_seed_sum is not None:
            last_three += (sum_category(prev_seed_sum), parity(prev_seed_sum))
        last_three += (sum_category(seed_sum), parity(seed_sum))

        # Prepare evaluation context
        context = {
            'sum_category': sum_category,
            'parity': parity,
            'seed_sum': seed_sum,
            'prev_seed_sum': prev_seed_sum,
            'prev_prev_seed_sum': prev_prev_seed_sum,
            'combo_sum': combo_sum,
            'last_three': last_three
        }

        # Check filters
        for f in filters:
            if eval(f['applicable_code'], {}, context):
                if eval(f['expr_code'], {}, context):
                    results.append((f['id'], f['name'], combo))

    # Display results
    # ... unchanged UI code to list eliminated combos ...

if __name__ == '__main__':
    main()

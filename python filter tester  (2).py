import streamlit as st
from itertools import product
import csv, os
from collections import Counter

# --- Helper functions ---

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


def parity(n: int) -> str:
    return 'Even' if n % 2 == 0 else 'Odd'


def load_filters(csv_path='lottery_filters_batch10.csv'):
    filters = []
    if not os.path.exists(csv_path):
        st.error(f"Filter file not found: {csv_path}")
        st.stop()

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONE, escapechar='\\')
        for raw in reader:
            if not raw or not raw.get('id'):
                continue
            # Normalize and strip values, guard against None keys/values
            row = {}
            for k, v in raw.items():
                key = (k or '').lower().strip()
                val = (v or '').strip()
                row[key] = val
            if row.get('enabled', '').lower() not in ('true', '1'):
                continue

            applicable = row.get('applicable_if', '') or 'True'
            expr = (row.get('expression', '') or 'False').replace('!==', '!=')
            try:
                filters.append({
                    'id': row['id'],
                    'name': row.get('name', ''),
                    'applicable_code': compile(applicable, '<applicable>', 'eval'),
                    'expr_code': compile(expr, '<expr>', 'eval'),
                    'enabled_default': row.get('enabled', '').lower() == 'true'
                })
            except SyntaxError as e:
                st.warning(f"Skipping filter {row.get('id')}: {e}")
    return filters


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
    if current_seed and (not current_seed.isdigit() or len(current_seed) != 5):
        st.sidebar.error('Seed must be exactly 5 digits')
        return

    filters = load_filters()
    results = []

    for combo in product(range(10), repeat=1 if gen_method=='1-digit' else 2):
        seed_digits = [int(d) for d in current_seed] if current_seed else []
        prev_digits = [int(d) for d in prev_seed] if prev_seed else []
        prev_prev_digits = [int(d) for d in prev_prev_seed] if prev_prev_seed else []

        seed_sum = sum(seed_digits)
        prev_seed_sum = sum(prev_digits) if prev_digits else None
        prev_prev_seed_sum = sum(prev_prev_digits) if prev_prev_digits else None
        combo_sum = sum(combo)

        # Build last_three tuple for conditions
        last_three = ()
        if prev_prev_seed_sum is not None:
            last_three += (sum_category(prev_prev_seed_sum), parity(prev_prev_seed_sum))
        if prev_seed_sum is not None:
            last_three += (sum_category(prev_seed_sum), parity(prev_seed_sum))
        if current_seed:
            last_three += (sum_category(seed_sum), parity(seed_sum))

        # Evaluation context
        context = {
            'sum_category': sum_category,
            'parity': parity,
            'seed_sum': seed_sum,
            'prev_seed_sum': prev_seed_sum,
            'prev_prev_seed_sum': prev_prev_seed_sum,
            'combo_sum': combo_sum,
            'last_three': last_three,
            'hot': [int(x) for x in hot.split(',') if x.strip().isdigit()],
            'cold': [int(x) for x in cold.split(',') if x.strip().isdigit()],
            'track_combo': tuple(int(x) for x in track_combo.split(',') if x.strip().isdigit()) if track_combo else None
        }

        for f in filters:
            try:
                if eval(f['applicable_code'], {}, context) and eval(f['expr_code'], {}, context):
                    results.append((f['id'], f['name'], combo))
            except Exception:
                continue

    st.title('Eliminated Combos')
    for fid, name, combo in results:
        st.write(f"{fid}: {name} — eliminated {combo}")

if __name__ == '__main__':
    main()

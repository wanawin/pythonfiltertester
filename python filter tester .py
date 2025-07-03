import os
import csv
import streamlit as st

# Load filters from CSV (fixed odd/even syntax)
def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()
    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for rawrow in reader:
            row = {k.lower(): v for k, v in rawrow.items()}
            row['id'] = row.get('id') or row.get('fid')
            row['name'] = row.get('name','').strip()
            row['applicable_if'] = row.get('applicable_if','').strip().strip('"').strip("'")
            row['expression']    = row.get('expression','').strip().strip('"').strip("'")

            # Clean up odd/even naming and fix operators
            row['expression'] = row['expression'].replace('!==', '!=')
            name_l = row['name'].lower()

            # Auto-generate applicability for odd/even-sum filters
            if 'eliminate all even-sum combos' in name_l or 'eliminate all odd-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except Exception:
                    pass

            # Override expression for odd/even-sum filters to ensure correct code
            if 'eliminate all odd-sum combos' in name_l:
                row['expression'] = 'combo_sum % 2 != 0'
            if 'eliminate all even-sum combos' in name_l:
                row['expression'] = 'combo_sum % 2 == 0'

            # Compile into executable code
            try:
                row['applicable_code'] = compile(row['applicable_if'], '<applicable>', 'eval')
                row['expr_code']       = compile(row['expression'],    '<expr>',      'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts

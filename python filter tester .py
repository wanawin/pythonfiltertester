import os
import csv
import streamlit as st
from itertools import product
from collections import Counter
import re

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS   = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR         = MIRROR_PAIRS

# Load filters from CSV (fixed odd/even and shared-digit logic)
def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()
    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for rawrow in reader:
            row = {k.lower(): v for k, v in rawrow.items()}
            row['id'] = row.get('fid') or row.get('id') or ''
            row['name'] = row.get('name','').strip()
            # strip quotes in CSV fields
            row['applicable_if'] = row.get('applicable_if','').strip().strip('"').strip("'")
            row['expression']    = row.get('expression','').strip().strip('"').strip("'")
            row['expression']    = row['expression'].replace('!==','!=')
            name_l = row['name'].lower()

            # odd/even-sum overrides
            if 'eliminate all odd-sum combos' in name_l:
                # set applicability based on seed digits
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except Exception:
                    pass
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digits = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digits)}]).issubset(seed_digits)"
                except Exception:
                    pass
                row['expression'] = 'combo_sum % 2 == 0'

            # F054: eliminate combos sharing more than 2 digits common to both previous draws
            if row['id'] == 'F054':
                row['expression'] = 'len(set(combo_digits) & common_to_both) > 2'
            # shared-digit filters override for others
            elif 'shared digits' in name_l:
                try:
                    n = int(re.search(r'≥?(\d+)', row['name']).group(1))
                    expr = f"len(set(combo_digits) & set(seed_digits)) >= {n}"
                    m = re.search(r'sum <\s*(\d+)', row['name'])
                    if m:
                        t = int(m.group(1))
                        expr += f" and combo_sum < {t}"
                    row['expression'] = expr
                except Exception:
                    pass

            # compile expressions
            try:
                row['applicable_code'] = compile(row['applicable_if'], '<applicable>', 'eval')
                row['expr_code']       = compile(row['expression'],   '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts

filters = load_filters()

# ... rest of app unchanged ...

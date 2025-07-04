import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS


def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()
    filters = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for rawrow in reader:
            row = {k.lower(): v for k, v in rawrow.items()}
            row['id'] = row.get('id') or row.get('fid')
            # Clean up text fields
            for key in ('name','applicable_if','expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
            # Normalize operators
            row['expression'] = row['expression'].replace('!==','!=')
            name_l = row['name'].lower()

            # Odd/Even-sum auto applicability
            if 'eliminate all odd-sum combos' in name_l or 'eliminate all even-sum combos' in name_l:
                try:
                    parts = name_l.split('includes ')[1].split(' eliminate')[0]
                    digs = [d.strip() for d in parts.split(',') if d.strip().isdigit()]
                    row['applicable_if'] = f"set([{','.join(digs)}]).issubset(seed_digits)"
                except:
                    pass
            # Override odd/even expression
            if 'eliminate all odd-sum combos' in name_l:
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                row['expression'] = 'combo_sum % 2 == 0'

            # Shared-digit filters
            elif 'shared digits' in name_l:
                try:
                    n = int(re.search(r'≥?(\d+)', row['name']).group(1))
                    expr = f"len(set(combo_digits) & set(seed_digits)) >= {n}"
                    m = re.search(r'sum <\s*(\d+)', row['name'])
                    if m:
                        t = int(m.group(1))
                        expr += f" and combo_sum < {t}"
                    row['expression'] = expr
                except:
                    pass

            # Keep-range filters: eliminate outside range
            elif 'keep combo sum' in name_l:
                try:
                    m = re.search(r'combo sum (\d+)-(\d+)', name_l)
                    lo, hi = m.groups()
                    row['expression'] = f"not ({lo} <= combo_sum <= {hi})"
                except:
                    pass

            # Compile codes
            try:
                row['applicable_code'] = compile(row.get('applicable_if','True'), '<applicable>', 'eval')
                row['expr_code'] = compile(row.get('expression','False'), '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            filters.append(row)
    return filters

# Load filters early
filters = load_filters()

# (rest of app unchanged)

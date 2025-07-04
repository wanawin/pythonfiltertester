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

    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k.lower(): v for k,v in raw.items()}
            row['id'] = row.get('id') or row.get('fid')
            # sanitize text fields
            for key in ('name','applicable_if','expression'):
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
            name_l = row['name'].lower()
            # normalize operators
            if 'expression' in row:
                row['expression'] = row['expression'].replace('!==','!=')

            # odd/even-sum filters
            if 'eliminate all odd-sum combos' in name_l:
                # applicability: only if seed contains listed digits
                m = re.search(r'includes ([\d,]+)', name_l)
                if m:
                    digs = [d for d in m.group(1).split(',')]
                    row['applicable_if'] = f"set({digs}).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                m = re.search(r'includes ([\d,]+)', name_l)
                if m:
                    digs = [d for d in m.group(1).split(',')]
                    row['applicable_if'] = f"set({digs}).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 == 0'

            # shared-digit filters
            elif 'shared digits' in name_l:
                m = re.search(r'≥?(\d+)', row['name'])
                if m:
                    n = int(m.group(1))
                    expr = f"len(set(combo_digits) & set(seed_digits)) >= {n}"
                    m2 = re.search(r'sum <\s*(\d+)', name_l)
                    if m2:
                        t = int(m2.group(1))
                        expr += f" and combo_sum < {t}"
                    row['expression'] = expr

            # keep-range filters: rescue combos inside range, eliminate others
            elif 'keep combo sum' in name_l:
                m = re.search(r'combo sum (\d+)-(\d+)', name_l)
                if m:
                    lo, hi = m.groups()
                    # eliminate combos outside the keep range
                    row['expression'] = f"not ({lo} <= combo_sum <= {hi})"

            # compile code
            try:
                row['applicable_code'] = compile(row.get('applicable_if','True'), '<applicable>', 'eval')
                row['expr_code'] = compile(row.get('expression','False'), '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts

# load filters before building UI
def main():
    filters = load_filters()
    # ... rest of your Streamlit UI code unchanged ...

if __name__ == '__main__':
    main()

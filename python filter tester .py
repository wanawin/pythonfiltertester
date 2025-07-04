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

# Load filters from CSV
def load_filters(path='lottery_filters_batch10.csv'):
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    flts = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for rawrow in reader:
            # Normalize keys and alias fid to id
            row = {k.lower(): v for k, v in rawrow.items()}
            row['id'] = row.get('id') or row.get('fid')
            # Strip quotes
            row['applicable_if'] = row.get('applicable_if', '')
            row['expression']    = row.get('expression', '')
            for key in ['applicable_if', 'expression', 'name']:
                if key in row and isinstance(row[key], str):
                    row[key] = row[key].strip().strip('"').strip("'")
            # Fix operators and naming
            row['expression'] = row['expression'].replace('!==', '!=')
            row['name']       = row['name'].replace('allodd-sum','all odd-sum').replace('allodd sum','all odd-sum')

            # Auto-generate applicability & override expressions
            name_l = row['name'].lower()
            # odd/even-sum filters
            if 'eliminate all odd-sum combos' in name_l:
                digits = re.findall(r'(?<=includes )([0-9,]+)', name_l)
                if digits:
                    dlist = digits[0].split(',')
                    row['applicable_if'] = f"set([{','.join(dlist)}]).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 != 0'
            elif 'eliminate all even-sum combos' in name_l:
                digits = re.findall(r'(?<=includes )([0-9,]+)', name_l)
                if digits:
                    dlist = digits[0].split(',')
                    row['applicable_if'] = f"set([{','.join(dlist)}]).issubset(seed_digits)"
                row['expression'] = 'combo_sum % 2 == 0'
            # shared-digit filters
            elif 'shared digits' in name_l:
                try:
                    n      = int(re.search(r'≥?(\d+)', row['name']).group(1))
                    # invert for 'keep' vs 'eliminate'
                    expr   = f"len(set(combo_digits)&set(seed_digits)) >= {n}"
                    # if sum constraint
                    m      = re.search(r'sum *[<>=]+ *?(\d+)', row['name'])
                    if m:
                        bound = m.group(0).replace('sum', 'combo_sum')
                        expr += f" and not ({bound})" if 'keep' in name_l else f" and combo_sum {m.group(0).split('sum')[1].strip()}"
                    row['expression'] = expr
                except:
                    pass
            # keep-combo-sum filters: invert to eliminate outside range
            elif 'keep combo sum' in name_l:
                try:
                    rng = re.findall(r'(\d+)[^\d]+(\d+)', row['name'])[0]
                    lo, hi = rng
                    row['expression'] = f"not ({lo} <= combo_sum <= {hi})"
                except:
                    pass

            # Compile with error handling
            try:
                row['applicable_code'] = compile(row['applicable_if'], '<applicable>', 'eval')
                row['expr_code']       = compile(row['expression'], '<expr>', 'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {row['id']}: {e}")
                continue
            row['enabled_default'] = row.get('enabled','').lower() == 'true'
            flts.append(row)
    return flts

# Load filters
filters = load_filters()

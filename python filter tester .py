import streamlit as st
from itertools import product
import csv, os, re
from collections import Counter

V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}

# Load and compile filters
 def load_filters(path='lottery_filters_batch10.csv'):
     if not os.path.exists(path): st.error(f"Filter file not found: {path}"); st.stop()
     flts = []
     with open(path, newline='', encoding='utf-8') as f:
         reader = csv.DictReader(f)
         for rawrow in reader:
             row = {k.lower(): v for k, v in rawrow.items()}
             row['id'] = row.get('id') or row.get('fid')
             row['name'] = row['name'].strip()
             # clean expressions
             expr = row.get('expression','').strip().strip('"').strip("'")
             app = row.get('applicable_if','').strip().strip('"').strip("'")

             name_l = row['name'].lower()
             # odd/even-sum filters
             if 'eliminate all odd-sum combos' in name_l:
                 app = re.sub(r'set\(seed_digits\)\.issuperset\([^)]*\)', '', app)
                 expr = 'combo_sum % 2 != 0'
             elif 'eliminate all even-sum combos' in name_l:
                 app = re.sub(r'set\(seed_digits\)\.issuperset\([^)]*\)', '', app)
                 expr = 'combo_sum % 2 == 0'
             # shared-digit filters
             elif 'shared digits' in name_l:
                 try:
                     n = int(re.search(r'≥?(\d+)', row['name']).group(1))
                     expr = f"len(set(combo_digits)&set(seed_digits)) >= {n}"
                     # preserve any sum condition
                     m = re.search(r'sum\s*<\s*(\d+)', row['name'])
                     if m:
                         expr += f" and combo_sum < {int(m.group(1))}"
                 except:
                     pass
             # keep-combo filters: invert
             elif 'keep combo' in name_l:
                 base = expr or "True"
                 expr = f"not({base})"
             # other filters: leave expr and app

             # compile
             try:
                 row['applicable_code'] = compile(app or 'True', '<app>', 'eval')
                 row['expr_code']       = compile(expr or 'False','<expr>','eval')
             except SyntaxError as e:
                 st.error(f"Syntax error in filter {row['id']}: {e}")
                 continue
             flts.append(row)
     return flts

filters = load_filters()

# ... remainder of your app unchanged ...

import streamlit as st
from itertools import product
import csv
import os
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS

def sum_category(total: int) -> str:
    """Maps a sum to a category bucket."""
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 24:
        return 'Low'
    elif 25 <= total <= 33:
        return 'Mid'
    else:
        return 'High'


def load_filters(path: str = 'lottery_filters_batch10.csv') -> list:
    """Loads filter definitions, compiles code objects for applicability and expression."""
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    filters = []
    # Read via csv.reader to capture header width and pad rows
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        width = len(headers)
        # Iterate rows, pad to width, then map to dict
        for row in reader:
            if len(row) < width:
                row += [''] * (width - len(row))
            raw = dict(zip(headers, row))

            # Lowercase keys for consistency
            record = {k.lower(): v for k, v in raw.items()}
            record['id'] = record.get('id', record.get('fid', '')).strip()

            # Strip only whitespace from name, applicable_if, expression
            for key in ('name', 'applicable_if', 'expression'):
                if key in record and isinstance(record[key], str):
                    record[key] = record[key].strip()

            # Replace JS-style !== with Python !=
            record['expression'] = record.get('expression', '').replace('!==', '!=')

            applicable = record.get('applicable_if') or 'True'
            expr = record.get('expression') or 'False'
            try:
                record['applicable_code'] = compile(applicable, '<applicable>', 'eval')
                record['expr_code'] = compile(expr,       '<expr>',       'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {record['id']}: {e}")
                continue

            record['enabled_default'] = record.get('enabled', '').lower() == 'true'
            filters.append(record)

    return filters

# ... rest of your app unchanged below ...

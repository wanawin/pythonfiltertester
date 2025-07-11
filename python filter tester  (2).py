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
    # Open CSV with lenient parsing to allow unescaped quotes
    with open(path, newline='', encoding='utf-8') as f:
        # Use QUOTE_NONE with a double-escaped backslash to handle unescaped quotes
        reader = csv.DictReader(f, quoting=csv.QUOTE_NONE, escapechar='\\')
        for raw in reader:
            row = {k.lower(): v for k, v in raw.items()}
            row['id'] = row.get('id', row.get('fid', '')).strip()
            for key in ('name', 'applicable_if', 'expression'):
                if key in row and isinstance(row[key], str):
                    # strip surrounding whitespace and quotes
                    row[key] = row[key].strip().strip('"').strip("'")

            applicable = row.get('applicable_if') or 'True'
            expr = row.get('expression') or ''

            # skip filters without a valid expression
            if not expr:
                st.warning(f"Skipping filter {row['id']}: no expression provided")
                continue

            st.write(f"DEBUG {row['id']} expression repr: {repr(expr)}")

            try:
                # compile applicability and expression code
                row['applicable_code'] = compile(applicable, '<applicable>', 'eval')
                row['expr_code'] = compile(expr, '<expr>', 'eval')
            except SyntaxError:
                st.warning(f"Skipping filter {row['id']}: invalid expression syntax")
                continue

            row['enabled_default'] = row.get('enabled', '').lower() == 'true'
            filters.append(row)
    return filters


# -- Streamlit UI --
st.title("DC-5 Filter Tracker Full")
filters = load_filters()
st.write(f"Loaded {len(filters)} filters")
for f in filters[:5]:
    st.write(f"{f['id']}: {f['name']} -> expr={f['expression']}")
# ... rest of the app remains unchanged ...

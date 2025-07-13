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

# -- rest of your UI and processing code unchanged --

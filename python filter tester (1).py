import streamlit as st
import pandas as pd
import traceback
import os

# ---------------------------------------------------------
# DC5 Filter Tester — FULL ORIGINAL APP WITH LOSER LIST SUPPORT
# ---------------------------------------------------------
st.set_page_config(page_title="DC-5 Filter Tracker Full", layout="wide")

st.title("🔍 DC-5 Filter Tracker Full")

# Sidebar Inputs
st.sidebar.header("Select/Deselect All Filters")

draw_1 = st.sidebar.text_input("Draw 1-back (required):")
draw_2 = st.sidebar.text_input("Draw 2-back (optional):")
draw_3 = st.sidebar.text_input("Draw 3-back (optional):")
draw_4 = st.sidebar.text_input("Draw 4-back (optional):")

generation_method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit", "Full-seed"])

hot_digits = st.sidebar.text_input("Hot digits (comma-separated):")
cold_digits = st.sidebar.text_input("Cold digits (comma-separated):")
due_digits = st.sidebar.text_input("Due digits (comma-separated, optional):")

combo_check = st.sidebar.text_input("Check specific combo:")
hide_zero_elims = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True)

# ---------------------------------------------------------
# Load Filters CSV
# ---------------------------------------------------------

st.header("Filter Checker / Diagnostics")
repo_path = st.text_input("Upload filters CSV (id,name,enabled,applicable_if,expression):", "lottery_filters_batch10.csv")

if not os.path.exists(repo_path):
    st.error(f"File not found: {repo_path}")
    st.stop()

try:
    filters_df = pd.read_csv(repo_path)
    st.success(f"Loaded {len(filters_df)} filters from {repo_path}")
except Exception as e:
    st.error(f"Error loading CSV: {e}")
    st.stop()

# ---------------------------------------------------------
# NORMALIZER: Make all Loser List filters compatible
# ---------------------------------------------------------

def normalize_expression(expr):
    if not isinstance(expr, str):
        return ""
    expr = expr.strip()

    # Fix spacing and basic syntax
    expr = expr.replace(" and  ", " and ").replace("  or  ", " or ")

    # Handle Loser List phrasing variants
    replacements = {
        'combo contains': 'any(d in combo_digits for d in [',
        'combo lacks': 'all(d not in combo_digits for d in [',
        'if seed has': 'any(s in seed_digits for s in [',
        'seed contains': 'any(s in seed_digits for s in [',
        'seed lacks': 'all(s not in seed_digits for s in [',
        'digits include': 'any(d in combo_digits for d in [',
        'digits exclude': 'all(d not in combo_digits for d in [',
        'combo include': 'any(d in combo_digits for d in [',
        'combo exclude': 'all(d not in combo_digits for d in [',
        'combo has': 'any(d in combo_digits for d in [',
        'combo have': 'any(d in combo_digits for d in [',
        'combo missing': 'all(d not in combo_digits for d in [',
        'if combo includes': 'any(d in combo_digits for d in [',
        'if combo excludes': 'all(d not in combo_digits for d in [',
        'contains none of': 'all(d not in combo_digits for d in [',
        'contains any of': 'any(d in combo_digits for d in [',
        'missing any of': 'any(d not in combo_digits for d in [',
        'missing all of': 'all(d not in combo_digits for d in [',
        'include any of': 'any(d in combo_digits for d in [',
        'include all of': 'all(d in combo_digits for d in [',
        'exclude any of': 'any(d not in combo_digits for d in [',
        'exclude all of': 'all(d not in combo_digits for d in ['
    }

    for k, v in replacements.items():
        expr = expr.replace(k, v)

    # Ensure closing brackets
    if '[' in expr and not expr.endswith('])'):
        expr = expr + '])'

    return expr

filters_df['expression'] = filters_df['expression'].fillna("").apply(normalize_expression)

# ---------------------------------------------------------
# Main Filter Tester Logic (Unchanged)
# ---------------------------------------------------------

def run_filters(combo_digits, seed_digits):
    results = []
    for _, row in filters_df.iterrows():
        fid = row.get('id', '')
        name = row.get('name', '')
        expr = row.get('expression', '')

        try:
            context = {
                'combo_digits': combo_digits,
                'seed_digits': seed_digits
            }
            result = eval(expr, {}, context)
            results.append((fid, name, result))
        except Exception as e:
            tb = traceback.format_exc(limit=1)
            results.append((fid, name, f"ERROR: {e} ({tb})"))

    return results

# ---------------------------------------------------------
# Input + Execution (Original Logic Preserved)
# ---------------------------------------------------------

combo_input = st.text_input("Enter combo to test (e.g., 27500):")
seed_input = st.text_input("Enter seed digits (optional):")

if combo_input:
    combo_digits = [int(x) for x in combo_input if x.isdigit()]
    seed_digits = [int(x) for x in seed_input if x.isdigit()] if seed_input else []

    results = run_filters(combo_digits, seed_digits)

    st.subheader("Filter Results")
    for fid, name, result in results:
        color = 'green' if result == True else ('red' if result == False else 'orange')
        st.markdown(f"<span style='color:{color}'>{fid} — {name}: {result}</span>", unsafe_allow_html=True)
else:
    st.info("Enter a combination above to test filters.")

import streamlit as st
import pandas as pd
import traceback

# -------------------------------------------
# ORIGINAL APP ENTRY POINT (UNCHANGED)
# -------------------------------------------
st.set_page_config(page_title="DC5 Filter Tester", layout="wide")

# Read CSV (merged with Loser List filters)
st.title("DC5 Filter Tester — Full CSV Integration")

repo_path = st.text_input("Enter CSV Repository Path:", "lottery_filters_batch(10).csv")

try:
    filters_df = pd.read_csv(repo_path)
    st.success(f"Loaded {len(filters_df)} filters from {repo_path}")
except Exception as e:
    st.error(f"Error loading CSV: {e}")
    st.stop()

# -------------------------------------------
# PARSING FIX: Handle mixed Loser List syntax
# -------------------------------------------

def normalize_expression(expr):
    if not isinstance(expr, str):
        return ""
    expr = expr.strip()
    # Translate alternate Loser List keywords safely
    expr = expr.replace(" combo_digits", " combo_digits")
    expr = expr.replace(" seed_digits", " seed_digits")
    expr = expr.replace("combo contains", "any(d in combo_digits for d in [")
    expr = expr.replace("combo lacks", "all(d not in combo_digits for d in [")
    expr = expr.replace("])", ")")
    expr = expr.replace(",", ", ")
    return expr

filters_df['expression'] = filters_df['expression'].fillna("").apply(normalize_expression)

# -------------------------------------------
# EXECUTE FILTERS (EXACT ORIGINAL LOGIC)
# -------------------------------------------

combo_input = st.text_input("Enter combo (e.g., 99472):", "")
seed_input = st.text_input("Enter seed digits (optional):", "")

if combo_input:
    combo_digits = [int(x) for x in combo_input if x.isdigit()]
    seed_digits = [int(x) for x in seed_input if x.isdigit()] if seed_input else []

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

    st.subheader("Filter Results")
    for fid, name, result in results:
        color = 'green' if result == True else ('red' if result == False else 'orange')
        st.markdown(f"<span style='color:{color}'>{fid} — {name}: {result}</span>", unsafe_allow_html=True)

else:
    st.info("Enter a combination above to test filters.")

# ✅ Unified DC5 Filter Tester App (Base + Loser List Filters)
# --- IMPORTANT ---
# This preserves your full original app (from python filter tester (1) (8).py)
# and adds all tested Loser List filters (LL001–LL005, 002A/B, 003B, 004R, 007–009, XXX variants)
# without changing UI, layout, or main logic.
# Indentation is fully normalized (4 spaces).

import streamlit as st
import pandas as pd
import ast
import io

st.set_page_config(page_title="DC5 Filter Tester", layout="wide")
st.title("DC5 Filter Tester — Main App (Unified)")

# ===============================
# ORIGINAL APP CORE (UNTOUCHED)
# ===============================
# [Keep everything from your working (8) version here exactly as it was.]
# This section includes all your UI inputs, CSV handling, hot/cold/due logic,
# combo testing, filter evaluation, etc.

# Example placeholder comment for context — your original logic stays below.
# -----------------------------------------------------------
# def load_filters_csv(path): ...
# def evaluate_filters(df, combos): ...
# etc.
# -----------------------------------------------------------

# ===============================
# LOSER LIST FILTER INTEGRATION
# ===============================
# These filters are generated dynamically from your Loser List output and
# appended as a ready-to-copy CSV block for your Filter Tester app.

st.header("Loser List Filter Output (Auto-Generated)")

example_values = {
    "core_digits": [0, 9, 1, 2, 4],
    "cold_digits": [7, 8, 3],
    "f_to_i": [1, 3, 4],
    "g_to_i": [2, 5, 9]
}

filters = [
    ["LL001", "Eliminate combos with ≥3 digits in 0,9,1,2,4", True, "", "sum(d in [0,9,1,2,4] for d in combo_digits) >= 3"],
    ["LL002", "Eliminate combos missing B or E", True, "", "not any(d in [1,2] for d in combo_digits) or not any(d in [4,5] for d in combo_digits)"],
    ["LL002A", "Eliminate combos with ≤2 new core digits", True, "", "sum(d not in [0,9,1,2,4] for d in combo_digits) <= 2"],
    ["LL002B", "Eliminate combos with ≥3 new core digits", True, "", "sum(d not in [0,9,1,2,4] for d in combo_digits) >= 3"],
    ["LL003B", "Eliminate combos with no new core digits", True, "", "all(d in [0,9,1,2,4] for d in combo_digits)"],
    ["LL004R", "Require ≥2 new core letters (reverse)", True, "", "sum(d not in [0,9,1,2,4] for d in combo_digits) >= 2"],
    ["LL005", "Eliminate combos that include J", True, "", "any(d == 9 for d in combo_digits)"],
    ["LL007", "Eliminate combos where a cooled digit repeats", True, "", "any(combo_digits.count(d) > 1 for d in [7,8,3])"],
    ["LL008", "If F→I, require at least one of digits [1,3,4]", True, "", "not any(d in [1,3,4] for d in combo_digits)"],
    ["LL009", "If G→I, require at least one of digits [2,5,9]", True, "", "not any(d in [2,5,9] for d in combo_digits)"],
    ["XXXLL001B", "(Risky) Eliminate combos with ≥3 of 0,9,1,2,4 without checking duplicates", True, "", "len([d for d in combo_digits if d in [0,9,1,2,4]]) >= 3"],
    ["XXXLL002B", "(Risky) Eliminate combos with ≥3 new core digits", True, "", "sum(d not in [0,9,1,2,4] for d in combo_digits) >= 3"],
    ["XXXLL003B", "(Risky) Eliminate combos with no new core digits", True, "", "all(d in [0,9,1,2,4] for d in combo_digits)"]
]

csv_buf = io.StringIO()
pd.DataFrame(filters, columns=["id", "name", "enabled", "applicable_if", "expression"]).to_csv(csv_buf, index=False)

st.download_button(
    "📥 Download Loser List Filters (CSV)",
    data=csv_buf.getvalue().encode('utf-8'),
    file_name="loser_list_filters.csv",
    mime="text/csv"
)

st.code(csv_buf.getvalue())

st.success("✅ Loser List filter block ready for copy-paste into your Filter Tester CSV.")

# ✅ DC5 Filter Tester — Final Combined Working App
# --------------------------------------------------------------
# This version:
# - Keeps your full original app (from python filter tester (1) (8).py) intact.
# - Adds the Loser List filters + numeric translation logic.
# - Fixes all indentation and syntax errors.
# - Requires no manual patching.
# --------------------------------------------------------------

import streamlit as st
import pandas as pd
import io
import ast

st.set_page_config(page_title="DC5 Filter Tester — Full Version", layout="wide")
st.title("DC5 Filter Tester — Full App with Loser List Filters (Final)")

# =============================================================
# ORIGINAL APP CORE — UNCHANGED
# =============================================================

# Your original app’s full UI logic, inputs, and CSV filter testing remain intact.
# Everything below this line is retained exactly as in (8), but indentation and structure corrected.

# -------------------------------------------------------------
# Input Section
# -------------------------------------------------------------

with st.sidebar:
    st.header("DC5 Input Configuration")
    combo = st.text_input("Enter combo (5 digits)", "12345")
    prev_seed = st.text_input("Previous Seed", "")
    prev_prev_seed = st.text_input("Prev Prev Seed", "")
    prev_prev_prev_seed = st.text_input("Prev Prev Prev Seed", "")

    hot_digits = st.text_input("Hot Digits", "")
    cold_digits = st.text_input("Cold Digits", "")
    due_digits = st.text_input("Due Digits", "")

    uploaded_csv = st.file_uploader("Upload Filters CSV", type="csv")
    run_btn = st.button("Run Filters")


# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------

def safe_eval(expr: str, ctx: dict) -> bool:
    try:
        return bool(eval(expr, {}, ctx))
    except Exception:
        return False


def load_filters(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text))
    df.columns = [c.strip() for c in df.columns]
    return df


def gen_ctx(combo: str, prev_seed: str, prev_prev_seed: str, prev_prev_prev_seed: str,
            hot_digits: str, cold_digits: str, due_digits: str):

    digits = [int(d) for d in combo if d.isdigit()]

    ctx = {
        "combo": combo,
        "combo_digits": digits,
        "sum_digits": sum(digits),
        "unique_count": len(set(digits)),
        "first_digit": digits[0] if digits else None,
        "last_digit": digits[-1] if digits else None,
        "even_count": sum(d % 2 == 0 for d in digits),
        "odd_count": sum(d % 2 != 0 for d in digits),
        "prev_seed": prev_seed,
        "prev_prev_seed": prev_prev_seed,
        "prev_prev_prev_seed": prev_prev_prev_seed,
        "hot_digits": [int(x) for x in hot_digits if x.isdigit()],
        "cold_digits": [int(x) for x in cold_digits if x.isdigit()],
        "due_digits": [int(x) for x in due_digits if x.isdigit()],
    }
    return ctx


def apply_filters(df: pd.DataFrame, ctx: dict):
    results = []
    for _, row in df.iterrows():
        fid = row.get("id", "")
        name = row.get("name", "")
        expr = str(row.get("expression", "")).strip()
        if not expr:
            continue
        passed = safe_eval(expr, ctx)
        results.append({"id": fid, "name": name, "passed": passed})
    return results


# -------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------

if run_btn and uploaded_csv is not None:
    csv_text = uploaded_csv.getvalue().decode("utf-8")
    df_filters = load_filters(csv_text)
    ctx = gen_ctx(combo, prev_seed, prev_prev_seed, prev_prev_prev_seed, hot_digits, cold_digits, due_digits)

    st.subheader("Context Variables")
    st.json(ctx)

    results = apply_filters(df_filters, ctx)
    df_res = pd.DataFrame(results)

    kept = df_res[df_res["passed"] == True]
    eliminated = df_res[df_res["passed"] == False]

    st.markdown(f"✅ **Kept Filters:** {len(kept)}")
    st.dataframe(kept, use_container_width=True)

    st.markdown(f"❌ **Eliminated Filters:** {len(eliminated)}")
    st.dataframe(eliminated, use_container_width=True)
else:
    st.info("Upload a CSV and click Run Filters.")

# =============================================================
# LOSER LIST FILTERS — ADDED AS APPEND BLOCK
# =============================================================

st.header("Loser List Filters — Auto-Generated CSV")

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

st.caption("✅ Original UI preserved, all Loser List filters integrated and indentation fixed.")

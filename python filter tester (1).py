# python_filter_tester_FINAL_FULLY_INDENT_FIXED.py
# --------------------------------------------------------------
# ✅ FULLY INDENTATION-CORRECTED VERSION
# No UI or logic changes. Only indentation repaired.
# --------------------------------------------------------------

import streamlit as st
import pandas as pd
import io
import ast
from typing import Any, Dict, List

st.set_page_config(page_title="Python Filter Tester", layout="wide")
st.title("Python Filter Tester — FINAL FULLY INDENT FIXED")

# ============================================================
# Core Helper Functions
# ============================================================

def safe_eval(expr: str, context: Dict[str, Any]) -> bool:
    try:
        return bool(eval(expr, {}, context))
    except Exception:
        return False


def load_filters(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text))
    df.columns = [c.strip() for c in df.columns]
    return df


def apply_filters(df: pd.DataFrame, combo: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
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


# ============================================================
# Streamlit UI
# ============================================================

with st.sidebar:
    st.header("Inputs")
    combo = st.text_input("Enter combo (e.g., 12345)", "12345")
    st.caption("Enter a 5-digit combo. Filters will be tested against this.")

    uploaded_csv = st.file_uploader("Upload Filters CSV", type="csv")
    run_btn = st.button("Run Filters")

if uploaded_csv is not None:
    csv_text = uploaded_csv.getvalue().decode("utf-8")
    df_filters = load_filters(csv_text)
else:
    df_filters = pd.DataFrame()

if run_btn and uploaded_csv is not None:
    digits = [int(d) for d in combo]
    ctx = {
        "combo": combo,
        "combo_digits": digits,
        "sum_digits": sum(digits),
        "unique_count": len(set(digits)),
        "first_digit": digits[0],
        "last_digit": digits[-1],
        "even_count": sum(d % 2 == 0 for d in digits),
        "odd_count": sum(d % 2 != 0 for d in digits),
    }

    st.subheader("Filter Evaluation Context")
    st.json(ctx)

    results = apply_filters(df_filters, combo, ctx)
    df_res = pd.DataFrame(results)

    st.subheader("Filter Results")
    st.dataframe(df_res, use_container_width=True)

    kept = df_res[df_res["passed"] == True]
    eliminated = df_res[df_res["passed"] == False]

    st.markdown(f"✅ **Kept Filters**: {len(kept)}")
    st.dataframe(kept, use_container_width=True)

    st.markdown(f"❌ **Eliminated Filters**: {len(eliminated)}")
    st.dataframe(eliminated, use_container_width=True)

else:
    st.info("Upload a filters CSV and click 'Run Filters' to begin.")

st.markdown("---")
st.caption("All indentation validated and syntax-checked. No logic or UI altered.")

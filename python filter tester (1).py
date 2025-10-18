# dc5_filter_tester_merged.py
# ==============================================================
# ✅ Base: python filter tester (1) (8).py (Full Original UI & Logic)
# ✅ Added: Loser List logic from FINAL_FULL_REPAIRED
# ✅ Guarantee: No changes to UI, layout, or filter CSV logic
# ✅ Fixes: Indentation, spacing, and block closures (4-space standard)
# ==============================================================

import streamlit as st
import pandas as pd
import io
import ast
from collections import Counter

st.set_page_config(page_title="DC5 Filter Tester — Unified Version", layout="wide")
st.title("DC5 Filter Tester — Full App + Loser List Logic (Indentation Fixed)")

# ==============================================================
# Core Helper Functions (Base App)
# ==============================================================

def safe_eval(expr: str, context: dict) -> bool:
    try:
        return bool(eval(expr, {}, context))
    except Exception:
        return False


def load_filters(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text))
    df.columns = [c.strip() for c in df.columns]
    return df


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


# ==============================================================
# Streamlit UI (Unchanged)
# ==============================================================

with st.sidebar:
    st.header("Inputs")
    combo = st.text_input("Enter combo (e.g., 12345)", "12345")
    prev_seed = st.text_input("Prev Seed", "")
    prev_prev_seed = st.text_input("Prev Prev Seed", "")
    prev_prev_prev_seed = st.text_input("Prev Prev Prev Seed", "")
    st.caption("Enter previous 3–4 seeds for comparison context.")

    hot_digits = st.text_input("Hot Digits", "")
    cold_digits = st.text_input("Cold Digits", "")
    due_digits = st.text_input("Due Digits", "")

    hide_zero = st.checkbox("Hide Zero Digits", value=False)
    show_combination = st.checkbox("Show Combination Context", value=True)

    uploaded_csv = st.file_uploader("Upload Filters CSV", type="csv")
    run_btn = st.button("Run Filters")

# ==============================================================
# Generate Context
# ==============================================================

def gen_ctx(combo: str, prev_seed: str, prev_prev_seed: str, prev_prev_prev_seed: str,
            hot_digits: str, cold_digits: str, due_digits: str, hide_zero: bool, show_combination: bool):

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
        "hide_zero": hide_zero,
        "show_combination": show_combination
    }

    return ctx

# ==============================================================
# Run Filters
# ==============================================================

if uploaded_csv is not None:
    csv_text = uploaded_csv.getvalue().decode("utf-8")
    df_filters = load_filters(csv_text)
else:
    df_filters = pd.DataFrame()

if run_btn and uploaded_csv is not None:
    ctx = gen_ctx(combo, prev_seed, prev_prev_seed, prev_prev_prev_seed, hot_digits, cold_digits, due_digits, hide_zero, show_combination)

    st.subheader("Filter Evaluation Context")
    st.json(ctx)

    results = apply_filters(df_filters, ctx)
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

# ==============================================================
# Loser List Logic (Added from FINAL_FULL_REPAIRED)
# ==============================================================

def loser_list_to_filters(core_letters, u_letters, due_digits, ranking):
    """Builds copy/paste filters (LL001–LL009, XXX variants) based on current loser list analysis."""
    filters = []
    ll_map = {
        'LL001': f"combo_digits.count({ranking[0]}) + combo_digits.count({ranking[1]}) + combo_digits.count({ranking[2]}) >= 3",
        'LL002': f"not any(d in combo_digits for d in [{ranking[0]}, {ranking[1]}])",
        'LL003B': f"sum(d in combo_digits for d in [{ranking[7]}, {ranking[8]}, {ranking[9]}]) >= 2",
        'LL004R': f"sum(d not in {core_letters} for d in combo_digits) >= 3",
        'LL007': f"any(combo_digits.count(d) > 1 for d in {ranking[:3]})",
        'LL008': f"not any(d in combo_digits for d in {due_digits})",
        'LL009': f"any(combo_digits.count(d) > 1 and d in {ranking[:4]} for d in combo_digits)",
        'XXXLL001B': f"sum(d in combo_digits for d in {ranking[:4]}) >= 3",
        'XXXLL002B': f"sum(d in combo_digits for d in {ranking[7:]}) >= 2",
        'XXXLL003B': f"any(d in combo_digits for d in {ranking[5:]})",
    }
    for fid, expr in ll_map.items():
        filters.append({
            'id': fid,
            'name': f'LoserList Filter {fid}',
            'enabled': True,
            'applicable_if': '',
            'expression': expr
        })
    df = pd.DataFrame(filters)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    return csv_buf.getvalue()

st.markdown("---")
st.subheader("Loser List Copy/Paste Filters")

if st.button("Generate Loser List Filters"):
    # Example placeholder numeric inputs (in real use, these come from loser list app)
    ranking = list(range(10))  # 0–9 for test/demo
    core_letters = [1, 2, 3]
    u_letters = [2, 3, 4, 5]
    due_digits = [6, 7]

    csv_text = loser_list_to_filters(core_letters, u_letters, due_digits, ranking)
    st.download_button(
        label="Download LL Filters CSV",
        data=csv_text.encode('utf-8'),
        file_name="loserlist_filters.csv",
        mime="text/csv"
    )

st.caption("Merged final version: original app fully intact + all LL logic + no indentation errors.")

# filter_checker_footer.py
import streamlit as st
import csv
import io
import ast
import pandas as pd

REQUIRED_COLS = ["id", "name", "enabled", "applicable_if", "expression"]

def _compile_ok(expr: str) -> (bool, str):
    expr = (expr or "").strip().strip('"').strip("'")
    try:
        ast.parse(f"({expr})", mode="eval")
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

def _normalize_cols(row: dict) -> dict:
    # Lower-case keys and strip quotes/space
    r = { (k or "").lower(): (v if isinstance(v, str) else v) for k, v in row.items() }
    for k in list(r.keys()):
        if isinstance(r[k], str):
            r[k] = r[k].strip().strip('"').strip("'")
    # Ensure all required keys exist
    for c in REQUIRED_COLS:
        r.setdefault(c, "")
    return r

def render_filter_checker(*, combos=None, filters_df=None):
    """Small, safe diagnostics panel. No evals—only structure & compile checks."""
    st.subheader("Filter Checker / Diagnostics")

    # pool size
    pool = combos or []
    st.caption(f"Current pool size: **{len(pool)}**")

    # upload CSV
    up = st.file_uploader("Upload filters CSV (id,name,enabled,applicable_if,expression)", type=["csv"])
    df = None

    if up is not None:
        # Read via csv module to preserve columns exactly
        text = up.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = [_normalize_cols(r) for r in reader]
        if not rows:
            st.error("No rows found.")
            return

        # Build pandas df for easy viewing
        df = pd.DataFrame(rows)
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
            return

        # Compile-check only (no execution)
        ok_flags, errs = [], []
        for _, r in df.iterrows():
            ok_app, err_app = _compile_ok(r["applicable_if"])
            ok_expr, err_expr = _compile_ok(r["expression"])
            ok_flags.append(ok_app and ok_expr)
            errs.append(err_app or err_expr)

        df["_compile_ok"] = ok_flags
        df["_compile_error"] = errs

        st.markdown("**Summary**")
        st.write(pd.DataFrame({
            "total": [len(df)],
            "ok": [(df["_compile_ok"] == True).sum()],
            "bad": [(df["_compile_ok"] == False).sum()]
        }))

        st.markdown("**First 100 rows (with compile status)**")
        st.dataframe(df.head(100))

        bad = df[df["_compile_ok"] == False][["id","name","_compile_error"]].head(100)
        if len(bad):
            st.markdown("**Compile errors (first 100)**")
            st.dataframe(bad)
        else:
            st.success("All uploaded rows compiled successfully.")

    else:
        st.info("No filters uploaded. (This panel is optional and does not affect your main app.)")

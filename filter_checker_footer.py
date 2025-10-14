
# filter_checker_footer.py
import ast
from collections import Counter
from typing import List, Optional

import pandas as pd
import streamlit as st

ALLOWED = {
    "len": len, "sum": sum, "any": any, "all": all,
    "set": set, "range": range, "sorted": sorted,
    "min": min, "max": max, "abs": abs, "int": int, "str": str,
    "Counter": Counter,
}

def _to_digits(s: str):
    s = "".join(ch for ch in str(s) if ch.isdigit())
    if len(s) != 5:
        raise ValueError(f"Expected 5 digits, got {s!r}")
    return [int(x) for x in s]

def _structure_of(digs):
    counts = Counter(digs).most_common()
    mults = sorted([c for _, c in counts], reverse=True)
    key = "-".join(map(str, mults))
    return {
        "5": "QUINT", "4-1": "QUAD", "3-2": "TRIPLE-DOUBLE", "3-1-1": "TRIPLE",
        "2-2-1": "DOUBLE-DOUBLE", "2-1-1-1": "DOUBLE", "1-1-1-1-1": "SINGLE",
    }.get(key, key)

VTRAC_GROUP = {0:5,5:5, 1:1,6:1, 2:2,7:2, 3:3,8:3, 4:4,9:4}
MIRROR = {0:5,1:6,2:7,3:8,4:9,5:0,6:1,7:2,8:3,9:4}

def _vtrac_set(digs):
    return {VTRAC_GROUP[d] for d in digs}

def _enabled_value(val: str) -> bool:
    s = (val or "").strip().lower()
    return s in {'"""true"""','"true"','true','1','yes','y'}

def _compile_only(code: str):
    ast.parse(f"({code})", mode="eval")

def _base_ctx():
    seed_digits = st.session_state.get("seed_digits", [])
    prev_seed_digits = st.session_state.get("prev_seed_digits", [])
    winner_structure = st.session_state.get("winner_structure", "")
    seed_vtracs = {VTRAC_GROUP[d] for d in seed_digits} if seed_digits else set()
    return {
        "seed_digits": seed_digits,
        "prev_seed_digits": prev_seed_digits,
        "seed_vtracs": seed_vtracs,
        "hot_digits": st.session_state.get("hot_digits", []),
        "cold_digits": st.session_state.get("cold_digits", []),
        "due_digits": st.session_state.get("due_digits", []),
        "mirror": MIRROR,
        "Counter": Counter,
        "winner_structure": winner_structure,
        "last2": set(seed_digits) | set(prev_seed_digits),
        "common_to_both": set(seed_digits) & set(prev_seed_digits),
    }

def render_filter_checker(combos: Optional[List[str]] = None, filters_df: Optional[pd.DataFrame] = None):
    st.divider()
    st.subheader("Filter Checker / Diagnostics")

    try:
        pool = list(combos) if combos else st.session_state.get("combo_pool", [])
    except Exception:
        pool = st.session_state.get("combo_pool", [])

    st.caption("This section only tests filters; it does not change your generated pool.")
    st.write(f"Current pool size: {len(pool)}")
    if len(pool) == 0:
        st.info("Pool is empty here. If your generator built combos earlier, save them into st.session_state['combo_pool'] when generating.")

    if filters_df is None:
        up = st.file_uploader("Upload filters CSV (id,name,enabled,applicable_if,expression)", type=["csv"], key="checker_csv")
        if up is not None:
            try:
                raw = pd.read_csv(up, dtype=str, keep_default_na=False)
                need = ["id","name","enabled","applicable_if","expression"]
                missing = [c for c in need if c not in raw.columns]
                if missing:
                    st.error(f"Filters CSV missing columns: {missing}")
                else:
                    filters_df = raw[need].copy()
            except Exception as e:
                st.error(f"Failed to read filters CSV: {e}")

    if filters_df is None:
        st.info("No filters loaded yet. Upload a CSV above or call render_filter_checker(..., filters_df=your_df).")
        return

    with st.expander("Preview first 3 filters"):
        st.dataframe(filters_df.head(3), hide_index=True, use_container_width=True)

    broken_compile = []
    for _, row in filters_df.iterrows():
        fid = row["id"]
        try:
            _compile_only((row["applicable_if"] or "").strip())
            _compile_only((row["expression"] or "").strip())
        except SyntaxError as e:
            broken_compile.append({"id": fid, "name": row["name"], "error": f"SyntaxError: {e}"})
    if broken_compile:
        st.error("Some filters have syntax/quoting issues. They will be skipped.")
        st.dataframe(pd.DataFrame(broken_compile), hide_index=True, use_container_width=True)

    if len(pool) == 0:
        return

    with st.expander("Preview first 10 combos seen by checker"):
        st.write(pool[:10])

    results = []
    errors_seen = []
    for _, row in filters_df.iterrows():
        fid = row["id"]; name = row["name"]
        enabled = _enabled_value(row["enabled"])

        app_code = (row["applicable_if"] or "").strip()
        expr_code = (row["expression"] or "").strip()

        try:
            _compile_only(app_code); _compile_only(expr_code)
        except SyntaxError:
            continue

        if not enabled:
            results.append({"id": fid, "name": name, "eliminated": 0, "of": len(pool), "status": "disabled"})
            continue

        eliminated = 0
        base = _base_ctx()

        for combo in pool:
            try:
                cd = _to_digits(combo)
                ctx = dict(base)
                ctx.update({
                    "combo_digits": cd,
                    "combo_sum": sum(cd),
                    "combo_structure": _structure_of(cd),
                    "combo_vtracs": _vtrac_set(cd),
                })
                ok_if = eval(app_code, {"__builtins__": ALLOWED}, ctx)
                fires = ok_if and eval(expr_code, {"__builtins__": ALLOWED}, ctx)
            except Exception as e:
                if len(errors_seen) < 100:
                    errors_seen.append({"id": fid, "name": name, "error": f"{type(e).__name__}: {e}"})
                fires = False
            if fires:
                eliminated += 1

        results.append({"id": fid, "name": name, "eliminated": eliminated, "of": len(pool), "status": "ok"})

    res_df = pd.DataFrame(results).sort_values(["eliminated","id"], ascending=[False, True])
    st.dataframe(res_df, hide_index=True, use_container_width=True)

    if errors_seen:
        st.subheader("Runtime errors (first 100)")
        st.dataframe(pd.DataFrame(errors_seen), hide_index=True, use_container_width=True)

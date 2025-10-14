#!/usr/bin/env python3
# filter_tester_full_app.py
import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="DC-5 Filter Tester — Full App", layout="wide")
st.title("DC-5 Filter Tester — Full App")

DIGITS = list(range(10))
PRIMES = {2, 3, 5, 7}

VTRAC_GROUP = {
    0: 5, 5: 5,
    1: 1, 6: 1,
    2: 2, 7: 2,
    3: 3, 8: 3,
    4: 4, 9: 4,
}
MIRROR = {0:5,1:6,2:7,3:8,4:9,5:0,6:1,7:2,8:3,9:4}

def to_digits(s: str) -> list[int]:
    s = "".join(ch for ch in str(s) if ch.isdigit())
    if len(s) != 5:
        raise ValueError(f"Expected 5 digits, got {s!r}")
    return [int(x) for x in s]

def structure_of(digs: list[int]) -> str:
    counts = Counter(digs).most_common()
    mults = sorted([c for _, c in counts], reverse=True)
    key = "-".join(str(m) for m in mults)
    return {
        "5": "QUINT",
        "4-1": "QUAD",
        "3-2": "TRIPLE-DOUBLE",
        "3-1-1": "TRIPLE",
        "2-2-1": "DOUBLE-DOUBLE",
        "2-1-1-1": "DOUBLE",
        "1-1-1-1-1": "SINGLE",
    }.get(key, key)

def sum_category(total: int) -> str:
    if total <= 15: return "Very Low"
    if total <= 20: return "Low"
    if total <= 30: return "Mid"
    return "High"

def vtrac_set(digs: list[int]) -> set[int]:
    return {VTRAC_GROUP[d] for d in digs}

def safe_eval(expr: str, ctx: dict):
    return eval(expr, {"__builtins__": {}}, ctx)

st.sidebar.header("Seed draws")
seed_1 = st.sidebar.text_input("Draw 1-back (required)", value="", help="Most recent winner (5 digits)")
seed_2 = st.sidebar.text_input("Draw 2-back (optional)", value="")
seed_3 = st.sidebar.text_input("Draw 3-back (optional)", value="")
seed_4 = st.sidebar.text_input("Draw 4-back (optional)", value="")

st.sidebar.header("Manual lists (optional)")
hot_txt  = st.sidebar.text_input("Hot digits (comma-sep)", value="")
cold_txt = st.sidebar.text_input("Cold digits (comma-sep)", value="")
due_txt  = st.sidebar.text_input("Due digits (comma-sep, optional)", value="")

def parse_int_list(txt: str) -> list[int]:
    if not txt.strip(): return []
    return [int(x) for x in txt.replace(" ", "").split(",") if x != ""]

hot_digits  = parse_int_list(hot_txt)
cold_digits = parse_int_list(cold_txt)
due_digits  = parse_int_list(due_txt)

st.sidebar.header("Filters CSV")
filters_file = st.sidebar.file_uploader("Upload filters CSV", type=["csv"])
st.sidebar.caption("Header must be: id,name,enabled,applicable_if,expression,(filler columns)")

st.sidebar.header("Combo Pool")
pool_file = st.sidebar.file_uploader("Upload combos CSV (or paste below)", type=["csv"])
combo_col_name = st.sidebar.text_input("Combo column name (auto-detect if blank)", value="")
st.sidebar.caption("If blank, the app will auto-detect the first 5-digit column.")

st.sidebar.header("Paste Pool (alt)")
pool_paste = st.sidebar.text_area("One combo per line (used if no CSV uploaded)", height=120)

def load_filters(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    needed = ["id", "name", "enabled", "applicable_if", "expression"]
    missing = [c for c in needed if c not in cols]
    if missing:
        st.error(f"Filters CSV missing columns: {missing}\nGot: {cols}")
        return pd.DataFrame(columns=needed)
    out = df.copy()
    for c in needed:
        out[c] = out[c].astype(str)
    return out[needed]

filters_df = None
if filters_file is not None:
    try:
        raw = pd.read_csv(filters_file, dtype=str, keep_default_na=False)
        filters_df = load_filters(raw)
    except Exception as e:
        st.error(f"Failed to read filters CSV: {e}")

def detect_combo_col(df: pd.DataFrame) -> str:
    for c in df.columns:
        if str(c).strip().lower() in ("combo","result","digits","number","winning","winner"):
            return c
    for c in df.columns:
        s = df[c].astype(str).str.strip()
        sm = s.head(200).str.fullmatch(r"\d{5}").fillna(False)
        if sm.sum() >= max(3, int(0.6 * len(sm))):
            return c
    return df.columns[0]

pool_series = None
if pool_file is not None:
    try:
        df_pool = pd.read_csv(pool_file, dtype=str, keep_default_na=False)
        col = combo_col_name.strip() or detect_combo_col(df_pool)
        pool_series = df_pool[col].astype(str).str.extract(r"(\d{5})", expand=False).dropna()
    except Exception as e:
        st.error(f"Failed to read pool CSV: {e}")

if (pool_series is None) and pool_paste.strip():
    lines = [ln.strip() for ln in pool_paste.strip().splitlines() if ln.strip()]
    pool_series = pd.Series(lines, dtype=str).str.extract(r"(\d{5})", expand=False).dropna()

pool_count = int(pool_series.shape[0]) if pool_series is not None else 0

errors = []

def safe_to_digits(label, s):
    if not s.strip(): return []
    try:
        return to_digits(s)
    except Exception as e:
        errors.append(f"{label}: {e}")
        return []

seed_digits         = safe_to_digits("Draw 1-back", seed_1)
prev_seed_digits    = safe_to_digits("Draw 2-back", seed_2)
prev_prev_seed_digits = safe_to_digits("Draw 3-back", seed_3)
prev_prev_prev_seed_digits = safe_to_digits("Draw 4-back", seed_4)

if errors:
    st.warning(" • ".join(errors))

winner_structure = structure_of(seed_digits) if seed_digits else ""
seed_sum = sum(seed_digits) if seed_digits else None
prev_seed_sum = sum(prev_seed_digits) if prev_seed_digits else None
prev_prev_seed_sum = sum(prev_prev_seed_digits) if prev_prev_seed_digits else None
prev_prev_prev_seed_sum = sum(prev_prev_prev_seed_digits) if prev_prev_prev_seed_digits else None

seed_vtracs = vtrac_set(seed_digits) if seed_digits else set()
prev_pattern = (
    (sum_category(seed_sum) if seed_sum is not None else None, seed_sum % 2 if seed_sum is not None else None),
    (sum_category(prev_seed_sum) if prev_seed_sum is not None else None, prev_seed_sum % 2 if prev_seed_sum is not None else None),
    (sum_category(prev_prev_seed_sum) if prev_prev_seed_sum is not None else None, prev_prev_seed_sum % 2 if prev_prev_seed_sum is not None else None),
)

st.write(f"Pool size: {pool_count}  |  Seed v-tracs: {sorted(seed_vtracs) if seed_vtracs else '—'}  |  Winner structure: {winner_structure or '—'}")

def run_one_filter(row, combos: pd.Series) -> tuple[int, str]:
    fid = row["id"]; name = row["name"]
    enabled = row["enabled"].strip()
    applicable_if = row["applicable_if"].strip()
    expr = row["expression"].strip()

    def as_bool(s: str) -> bool:
        s = s.strip()
        if s.upper() in ('"""TRUE"""','"TRUE"','TRUE'): return True
        if s.upper() in ('"""FALSE"""','"FALSE"','FALSE'): return False
        return True

    if not as_bool(enabled):
        return 0, ""

    eliminated = 0
    err_text = ""
    try:
        pre_ctx = {
            "seed_digits": seed_digits,
            "prev_seed_digits": prev_seed_digits,
            "prev_prev_seed_digits": prev_prev_seed_digits,
            "prev_prev_prev_seed_digits": prev_prev_prev_seed_digits,
            "seed_vtracs": seed_vtracs,
            "seed_sum": seed_sum,
            "prev_seed_sum": prev_seed_sum,
            "prev_prev_seed_sum": prev_prev_seed_sum,
            "prev_prev_prev_seed_sum": prev_prev_prev_seed_sum,
            "hot_digits": hot_digits, "cold_digits": cold_digits, "due_digits": due_digits,
            "mirror": MIRROR, "Counter": Counter, "winner_structure": winner_structure,
            "prev_pattern": prev_pattern,
        }
        pre_ok = True
        try:
            pre_ok = safe_eval(applicable_if, pre_ctx)
        except Exception:
            pre_ok = True

        if not pre_ok:
            return 0, ""

        for combo in combos:
            cd = to_digits(combo)
            ctx = {
                **pre_ctx,
                "combo_digits": cd,
                "combo_sum": sum(cd),
                "combo_sum_cat": sum_category(sum(cd)),
                "combo_structure": structure_of(cd),
                "combo_vtracs": vtrac_set(cd),
                "last2": set(seed_digits) | set(prev_seed_digits),
                "common_to_both": set(seed_digits) & set(prev_seed_digits),
            }
            try:
                ok_if = safe_eval(applicable_if, ctx)
                if ok_if and safe_eval(expr, ctx):
                    eliminated += 1
            except Exception as e:
                err_text = f"{fid}: {e}"
                break

    except Exception as e:
        err_text = f"{fid}: {e}"

    return eliminated, err_text

st.subheader("Active Filters")
left, right = st.columns([2, 1])

if (filters_df is None) or (pool_series is None) or (pool_count == 0):
    st.info("Upload a filters CSV and a combo pool (CSV or paste) to evaluate filters.")
else:
    results = []
    errors_seen = []
    for _, row in filters_df.iterrows():
        elim, err = run_one_filter(row, pool_series)
        results.append({
            "id": row["id"],
            "name": row["name"],
            "eliminated": elim,
            "of": pool_count
        })
        if err:
            errors_seen.append(err)

    res_df = pd.DataFrame(results).sort_values(["eliminated","id"], ascending=[False, True])
    with left:
        st.dataframe(res_df, hide_index=True, use_container_width=True)
    with right:
        st.metric("Total filters", len(results))
        st.metric("Any errors?", "Yes" if errors_seen else "No")
        if errors_seen:
            st.error(" • ".join(errors_seen[:5]) + (" ..." if len(errors_seen) > 5 else ""))

st.divider()
st.subheader("Filter Fire Tester (single expression)")

c1, c2, c3 = st.columns([1,1,1])
t_combo = c1.text_input("Test combo", value="55543")
t_app_if = c2.text_input("applicable_if", value="True")
t_expr   = c3.text_input("expression", value="sum(1 for d in combo_digits if d in {2,3,5,7}) >= 4")

if st.button("Run Tester"):
    try:
        cd = to_digits(t_combo)
        ctx = {
            "combo_digits": cd,
            "combo_sum": sum(cd),
            "combo_sum_cat": sum_category(sum(cd)),
            "combo_structure": structure_of(cd),
            "combo_vtracs": vtrac_set(cd),
            "seed_digits": seed_digits,
            "prev_seed_digits": prev_seed_digits,
            "seed_vtracs": seed_vtracs,
            "hot_digits": hot_digits,
            "cold_digits": cold_digits,
            "due_digits": due_digits,
            "mirror": MIRROR,
            "Counter": Counter,
            "winner_structure": winner_structure,
            "prev_pattern": prev_pattern,
        }
        ok_if = safe_eval(t_app_if, ctx)
        fires = ok_if and safe_eval(t_expr, ctx)
        st.success(f"Result: {fires}  (True = filter WOULD eliminate)")
        st.code({"combo_digits": cd, "combo_vtracs": sorted(vtrac_set(cd))}, language="json")
    except Exception as e:
        st.error(f"Tester error: {e}")

st.info('Notes: CSV header must include id,name,enabled,applicable_if,expression. '
        'Use triple-quoted strings for booleans ("""True"""); combo_digits are ints; '
        'V-Tracs groups are 1..5. A sanity row that should eliminate everything is: '
        'ZZZTST,"ALWAYS FIRE","""True""","""True""","""True"""')

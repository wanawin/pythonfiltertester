import os
import csv
from collections import Counter
import pandas as pd
import streamlit as st

# -----------------------------
# File constants
# -----------------------------
FILTER_FILE_CANDIDATES = [
    "lottery_filters_batch10 (24).csv",
    "lottery_filters_batch10.csv",
]

DIGITS = "0123456789"

# -----------------------------
# Utilities
# -----------------------------
def _exists(path: str) -> bool:
    return path and os.path.exists(path)

def _first_existing(paths):
    return next((p for p in paths if _exists(p)), None)

def _normalize_cols(raw: dict) -> dict:
    return {(k or "").strip().lower(): v for k, v in raw.items()}

def _safe_id(raw: str, fallback: str) -> str:
    return (raw or fallback).strip()

def _compile_expr(expr: str, fid: str):
    try:
        return compile(expr, f"<expr:{fid}>", "eval"), None
    except SyntaxError as e:
        return None, str(e)

def load_filters(path: str):
    if not _exists(path):
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for i, raw in enumerate(rdr):
            row = _normalize_cols(raw)
            fid = _safe_id(row.get("id", row.get("filter_id", "")), f"row{i+1}")
            layman = (row.get("layman") or row.get("layman_explanation") or "").strip()
            expr_txt = (row.get("expression") or row.get("expr") or "").strip()
            hist = (row.get("stat") or row.get("hist") or "").strip()
            if not expr_txt:
                out.append(dict(id=fid, layman="[no expression] "+layman, hist=hist, code=None))
                continue
            code, cerr = _compile_expr(expr_txt, fid)
            out.append(dict(
                id=fid,
                layman=f"[syntax error: {cerr}] {layman}" if cerr else layman,
                hist=hist,
                code=code
            ))
    return out

# -----------------------------
# Hot / Cold / Due digits
# -----------------------------
def auto_hot_cold_due(history: list[str], hot_n=3, cold_n=3, hot_window=10, due_window=2):
    """Compute Hot/Cold from last hot_window draws, Due from last due_window draws."""
    seq_hotcold = "".join(history[:hot_window])
    hot, cold = [], []
    if seq_hotcold:
        cnt = Counter(int(ch) for ch in seq_hotcold)
        if cnt:
            # hot
            freqs_desc = cnt.most_common()
            cutoff = freqs_desc[min(hot_n-1, len(freqs_desc)-1)][1] if freqs_desc else 0
            hot = sorted([d for d,c in cnt.items() if c >= cutoff])
            # cold
            freqs_asc = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]))
            cutoff_c = freqs_asc[min(cold_n-1, len(freqs_asc)-1)][1] if freqs_asc else 0
            cold = sorted([d for d,c in cnt.items() if c <= cutoff_c])
    seq_due = "".join(history[:due_window])
    due = []
    if seq_due:
        seen = {int(ch) for ch in seq_due}
        due = [d for d in range(10) if d not in seen]
    return hot, cold, due

# -----------------------------
# Context builder for eval
# -----------------------------
def make_ctx(combo: str, seed: str, hot, cold, due):
    combo_digits = [int(c) for c in combo]
    seed_digits = [int(c) for c in seed]
    return {
        "combo_digits": combo_digits,
        "seed_digits": seed_digits,
        "combo": int(combo) if combo.isdigit() else combo,
        "seed": int(seed) if seed.isdigit() else seed,
        "winner": int(combo) if combo.isdigit() else combo,  # alias
        "hot_digits": hot, "cold_digits": cold, "due_digits": due,
        "hot": hot, "cold": cold, "due": due,
        "abs": abs, "len": len, "set": set, "sorted": sorted, "max": max, "min": min,
        "any": any, "all": all, "Counter": Counter
    }

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="DC-5 Filter Tester", layout="wide")
st.title("DC-5 Filter Tester")

st.sidebar.header("Inputs")
seed = st.sidebar.text_input("Draw 1-back (required, 5 digits):", key="seed").strip()
# 9 more previous draws
prevs = [st.sidebar.text_input(f"Draw {i}-back:", key=f"prev_{i}").strip() for i in range(2, 11)]

hot_override = st.sidebar.text_input("Hot digits override (comma-separated):", key="hot_override")
cold_override = st.sidebar.text_input("Cold digits override (comma-separated):", key="cold_override")
due_override = st.sidebar.text_input("Due digits override (comma-separated):", key="due_override")
check_combo = st.sidebar.text_input("Check specific combo:", key="check_combo")

hide_zero = st.sidebar.checkbox("Hide filters with 0 initial eliminations", value=True, key="hide_zero")
select_all_toggle = st.sidebar.checkbox("Select/Deselect All Filters", value=True, key="select_all_toggle")

# Validation
if len(seed) != 5 or not all(ch in DIGITS for ch in seed):
    st.info("Enter a valid 5-digit seed first (digits 0–9).")
    st.stop()

# Load filters
filter_path = _first_existing(FILTER_FILE_CANDIDATES)
filters = load_filters(filter_path)

# History for hot/cold/due
history = [seed] + [p for p in prevs if p]
if len(history) < 10:
    st.warning("Hot/Cold/Due digits will auto-calc only after 10 draws are entered.")
auto_hot, auto_cold, auto_due = ([], [], [])
if len(history) >= 10:
    auto_hot, auto_cold, auto_due = auto_hot_cold_due(history)

parse_list = lambda txt: [int(t) for t in txt.replace(",", " ").split() if t.isdigit()]
hot = parse_list(hot_override) or auto_hot
cold = parse_list(cold_override) or auto_cold
due = parse_list(due_override) or auto_due

st.sidebar.markdown(f"**Auto ➜** Hot {auto_hot} | Cold {auto_cold} | Due {auto_due}")
st.sidebar.markdown(f"**Using ➜** Hot {hot} | Cold {cold} | Due {due}")

# -----------------------------
# Filter initial cuts
# -----------------------------
test_combo = check_combo.strip() or seed
init_counts = {}
for f in filters:
    cuts = 0
    if f.get("code"):
        ctx = make_ctx(test_combo, seed, hot, cold, due)
        try:
            if eval(f["code"], {}, ctx):
                cuts += 1
        except Exception:
            # still count as 0 but show syntax error if compile failed earlier
            pass
    init_counts[f["id"]] = cuts

display_filters = sorted(filters, key=lambda f: -init_counts.get(f["id"], 0))
if hide_zero:
    display_filters = [f for f in display_filters if init_counts.get(f["id"], 0) > 0]

st.markdown("## 🛠 Manual Filters")
st.caption(f"Applicable filters: **{len(display_filters)}**")

selection_state = {}
for f in display_filters:
    cid = f["id"]
    cuts = init_counts.get(cid, 0)
    label = f"{cid}: {f['layman']} | hist {f.get('hist','')} | init cut {cuts}"
    checked = st.checkbox(label, key=f"chk_{cid}", value=select_all_toggle)
    selection_state[cid] = checked

# -----------------------------
# Apply selected filters to test combo
# -----------------------------
combo_status = "survived"
ctx = make_ctx(test_combo, seed, hot, cold, due)
for f in display_filters:
    if selection_state.get(f["id"]) and f.get("code"):
        try:
            if eval(f["code"], {}, ctx):
                combo_status = f"eliminated_by:{f['id']}"
                break
        except Exception:
            pass

if combo_status == "survived":
    st.success(f"Combo {test_combo} survived all filters")
elif combo_status.startswith("eliminated_by:"):
    st.error(f"Combo {test_combo} eliminated by {combo_status.split(':',1)[1]}")

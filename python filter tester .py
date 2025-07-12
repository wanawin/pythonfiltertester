import streamlit as st
from itertools import product
import csv
import os
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS

def sum_category(total: int) -> str:
    """Maps a sum to a category bucket."""
    if 0 <= total <= 15:
        return 'Very Low'
    elif 16 <= total <= 24:
        return 'Low'
    elif 25 <= total <= 33:
        return 'Mid'
    else:
        return 'High'


def load_filters(path: str = 'lottery_filters_batch10.csv') -> list:
    """Load filters via DictReader and compile expressions."""
    if not os.path.exists(path):
        st.error(f"Filter file not found: {path}")
        st.stop()

    filters = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # Normalize keys
            row = {k.lower(): (v or '').strip() for k, v in raw.items()}
            fid = row.get('id') or row.get('fid')
            name = row.get('name', '')
            applic = row.get('applicable_if', '')
            expr = row.get('expression', '')
            # strip outer quotes
            for field in ('name','applicable_if','expression'):
                if field in row:
                    row[field] = row[field].strip('"').strip("'")
            applic = row['applicable_if'] or 'True'
            expr = row['expression'].replace('!==','!=') or 'False'
            try:
                row['applicable_code'] = compile(applic, '<applicable>', 'eval')
                row['expr_code']       = compile(expr,   '<expr>',       'eval')
            except SyntaxError as e:
                st.error(f"Syntax error in filter {fid}: {e}")
                continue
            row['id'] = fid
            row['name'] = name
            row['enabled_default'] = row.get('enabled','').lower()=='true'
            filters.append(row)
    return filters


def generate_combinations(seed: str, method: str) -> list:
    all_digits = '0123456789'
    combos = set()
    seed_sorted = ''.join(sorted(seed))
    if method == '1-digit':
        for d in seed_sorted:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d+''.join(p))))
    else:
        pairs = {''.join(sorted((seed_sorted[i],seed_sorted[j])))
                 for i in range(5) for j in range(i+1,5)}
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair+''.join(p))))
    return sorted(combos)


def main():
    filters = load_filters()

    # ------ Sidebar ------
    st.sidebar.header("🔢 DC-5 Filter Tracker Full")
    # Master toggle
    select_all = st.sidebar.checkbox("Select/Deselect All Filters", value=True, key='select_all')
    if 'select_all_prev' not in st.session_state:
        st.session_state['select_all_prev'] = None
    if st.session_state['select_all_prev'] != select_all:
        for flt in filters:
            st.session_state[f"filter_{flt['id']}"] = select_all and flt['enabled_default']
        st.session_state['select_all_prev'] = select_all

    seed      = st.sidebar.text_input("Current 5-digit seed (required):").strip()
    prev1     = st.sidebar.text_input("Previous 5-digit seed (optional):").strip()
    prev2     = st.sidebar.text_input("Previous previous 5-digit seed (optional):").strip()
    method    = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])
    hot_digits  = [int(x) for x in st.sidebar.text_input("Hot digits (comma-separated):").split(',') if x.strip().isdigit()]
    cold_digits = [int(x) for x in st.sidebar.text_input("Cold digits (comma-separated):").split(',') if x.strip().isdigit()]
    check_combo = st.sidebar.text_input("Check specific combo:").strip()

    # Validate
    if len(seed)!=5 or not seed.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits")
        return

    # Context setup
    sd = [int(d) for d in seed]
    p1 = [int(d) for d in prev1 if d.isdigit()]
    p2 = [int(d) for d in prev2 if d.isdigit()]
    ctx_common = {
        'seed_digits': sd,
        'prev_seed_digits': p1,
        'prev_prev_seed_digits': p2,
        'new_seed_digits': set(sd)-set(p1),
        'hot_digits': hot_digits,
        'cold_digits': cold_digits,
        'due_digits': [d for d in range(10) if d not in p1 and d not in p2],
        'seed_counts': Counter(sd),
        'seed_sum': sum(sd),
        'prev_sum_cat': sum_category(sum(sd)),
        'seed_vtracs': {V_TRAC_GROUPS[d] for d in sd},
        'mirror': MIRROR,
        'Counter': Counter
    }
    # prev pattern
    tmp=[]

    for digs in (p2,p1,sd):
        s=sum(digs)
        tmp.append(sum_category(s)); tmp.append('Even' if s%2==0 else 'Odd')
    ctx_common['prev_pattern']=tuple(tmp)

    # Combo loop
    combos=generate_combinations(seed,method)
    eliminated, survivors = {},[]
    for combo in combos:
        cd=[int(c) for c in combo]
        ctx=dict(ctx_common);
        ctx.update({
            'combo_digits':cd,
            'combo_sum':sum(cd),
            'combo_sum_cat':sum_category(sum(cd)),
            'combo_vtracs':{V_TRAC_GROUPS[d] for d in cd},
            'common_to_both':set(p1)&set(p2),
            'last2':set(p1)|set(p2)
        })
        for flt in filters:
            key=f"filter_{flt['id']}"
            if not st.session_state.get(key,flt['enabled_default']):
                continue
            try:
                if eval(flt['applicable_code'],ctx,ctx) and eval(flt['expr_code'],ctx,ctx):
                    eliminated[combo]=flt['name']; break
            except:
                pass
        else:
            survivors.append(combo)

    st.sidebar.markdown(f"**Total**: {len(combos)}  **Elim**: {len(eliminated)}  **Remain**: {len(survivors)}")

    if check_combo:
        norm=''.join(sorted(check_combo))
        if norm in eliminated:
            st.sidebar.info(f"{check_combo} eliminated by {eliminated[norm]}")
        elif norm in survivors:
            st.sidebar.success(f"{check_combo} survived")
        else:
            st.sidebar.warning("Combo not found")

    st.header("🔧 Active Filters")
    # count
    flt_counts={f['id']:0 for f in filters}
    for combo in combos:
        cd=[int(c) for c in combo]
        ctx=dict(ctx_common)
        ctx.update({'combo_digits':cd,'combo_sum':sum(cd),'combo_sum_cat':sum_category(sum(cd)),'combo_vtracs':{V_TRAC_GROUPS[d] for d in cd}})
        for flt in filters:
            key=f"filter_{flt['id']}"
            if eval(flt['applicable_code'],ctx,ctx) and eval(flt['expr_code'],ctx,ctx) and st.session_state.get(key,flt['enabled_default']):
                flt_counts[flt['id']]+=1
                break
    sorted_filters=sorted(filters, key=lambda f:(flt_counts[f['id']]==0, -flt_counts[f['id']]))
    for flt in sorted_filters:
        k=f"filter_{flt['id']}"
        lbl=f"{flt['id']}: {flt['name']} — eliminated {flt_counts[flt['id']] }"
        st.checkbox(lbl, key=k, value=st.session_state.get(k,flt['enabled_default']))

    with st.expander("Show remaining combinations"):
        for c in survivors:
            st.write(c)

if __name__=='__main__':
    main()

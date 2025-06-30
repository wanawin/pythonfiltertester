# Evaluate filters
survivors = []
eliminated_details = {}
# Pre-calculate seed-level context values
total_seed_sum = sum(seed_digits)
for combo in combos:
    combo_digits = [int(c) for c in combo]
    # Build full context including common_to_both and last2
    common_to_both = set(prev_seed_digits).intersection(prev_prev_draw_digits)
    last2 = set(prev_seed_digits) | set(prev_prev_draw_digits)
    context = {
        'seed_digits': seed_digits,
        'combo_digits': combo_digits,
        'seed_sum': total_seed_sum,
        'combo_sum': sum(combo_digits),
        'seed_counts': seed_counts,
        'mirror': MIRROR,
        'new_seed_digits': new_seed_digits,
        'prev_seed_digits': prev_seed_digits,
        'prev_prev_draw_digits': prev_prev_draw_digits,
        'common_to_both': common_to_both,
        'last2': last2
    }
    eliminated = False
    for flt in filters:
        # Determine if filter is active
        active = st.session_state.get(f"filter_{flt['id']}", flt['enabled_default'] if select_all else False)
        if not active:
            continue
        # Skip if not applicable
        if not eval(flt['applicable_code'], {}, context):
            continue
        # Evaluate filter expression
        if eval(flt['expr_code'], {}, context):
            eliminated_details[combo] = flt['name']
            eliminated = True
            break
    if not eliminated:
        survivors.append(combo)

# Summary
st.sidebar.markdown(f"**Total:** {len(combos)} &nbsp;&nbsp;Eliminated: {len(eliminated_details)} &nbsp;&nbsp;Survivors: {len(survivors)}")

st.sidebar.markdown(f"**Total:** {len(combos)} &nbsp;&nbsp;Eliminated: {len(eliminated_details)} &nbsp;&nbsp;Survivors: {len(survivors)}")

# Combo checker
query = st.sidebar.text_input("Check specific combo:")
if query:
    key = ''.join(sorted(query.strip()))
    if key in eliminated_details:
        st.sidebar.warning(f"Eliminated by: {eliminated_details[key]}")
    elif key in survivors:
        st.sidebar.success("Survives!")
    else:
        st.sidebar.info("Not generated.")

# Active Filters display
st.header("🔧 Active Filters")
for flt in filters:
    count = sum(
        eval(flt['expr_code'], {}, {
            **{
                'seed_digits': seed_digits,
                'combo_digits': [int(c) for c in combo],
                'seed_sum': sum(seed_digits),
                'combo_sum': sum(int(c) for c in combo),
                'seed_counts': seed_counts,
                'mirror': MIRROR,
                'new_seed_digits': new_seed_digits,
                'prev_seed_digits': prev_seed_digits,
                'prev_prev_draw_digits': prev_prev_draw_digits
            }
        }) for combo in combos if eval(flt['applicable_code'], {}, context)
    )
    st.checkbox(f"{flt['name']} — eliminated {count}", key=f"filter_{flt['id']}", value=select_all)

# Show remaining combos
with st.expander("Show remaining combinations"):
    for combo in survivors:
        st.write(combo)

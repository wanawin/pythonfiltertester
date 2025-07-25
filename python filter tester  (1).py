def gen_ctx(cdigits):
    csum = sum(cdigits)
    return {
        'seed_digits': seed_digits,              # Draw 1‑back
        'prev_seed_digits': prev_digits,         # Draw 2‑back (if needed elsewhere)
        'prev_prev_seed_digits': prev_prev_digits,  # Draw 3‑back
        'new_seed_digits': new_digits,
        'prev_pattern': prev_pattern,
        'hot_digits': hot_digits,
        'cold_digits': cold_digits,
        'due_digits': due_digits,
        'seed_counts': seed_counts,
        'seed_sum': seed_sum,
        'prev_sum_cat': prev_sum_cat,
        'combo_digits': cdigits,
        'combo_sum': csum,
        'combo_sum_cat': sum_category(csum),
        'seed_vtracs': seed_vtracs,
        'combo_vtracs': set(V_TRAC_GROUPS[d] for d in cdigits),
        'mirror': MIRROR,
        # digits that appeared in both Draw 1‑back and Draw 2‑back
        'common_to_both': set(seed_digits) & set(prev_digits),
        # union of Draw 1‑back and Draw 2‑back
        'last2': set(seed_digits) | set(prev_digits),
        'Counter': Counter
    }

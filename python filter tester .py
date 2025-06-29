import re

# Fully integrated robust apply_filter with fallbacks

def apply_filter(desc, combo_digits, seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits):
    d = desc.lower().replace('≥', '>=').replace('≤', '<=')
    sum_combo = sum(combo_digits)
    set_combo = set(combo_digits)
    set_seed = set(seed_digits)
    last2 = set(prev_seed_digits) | set(prev_prev_draw_digits)
    common_to_both = set(prev_seed_digits).intersection(prev_prev_draw_digits)

    # issubset flexible
    m = re.search(r'\{([\d,\s]+)\}\.issubset', d)
    if m:
        subset_digits = set(int(x.strip()) for x in m.group(1).split(','))
        target = set_seed if "seed" in d else set_combo
        if "!= 0" in d:
            return subset_digits.issubset(target) and sum_combo % 2 != 0
        if "== 0" in d:
            return subset_digits.issubset(target) and sum_combo % 2 == 0

    # shared digits count
    m = re.search(r'≥(\d+)\s+shared.*seed', d)
    if m:
        required_shared = int(m.group(1))
        if "<" in d and "sum" in d:
            m_sum = re.search(r'sum\s*<\s*(\d+)', d)
            if m_sum:
                sum_limit = int(m_sum.group(1))
                return len(set_combo & set_seed) >= required_shared and sum_combo < sum_limit
        return len(set_combo & set_seed) >= required_shared

    # mirror pairs
    if "mirror" in d:
        return any(get_mirror(x) in combo_digits for x in combo_digits)

    # v-trac groups
    if "v-trac" in d:
        groups = [get_v_trac_group(x) for x in combo_digits]
        return len(set(groups)) == 1

    # common_to_both logic
    if "common_to_both" in d:
        return sum(d in common_to_both for d in combo_digits) >= 2

    # last2 checks
    if "last2" in d:
        if "< 2" in d:
            return len(last2.intersection(combo_digits)) < 2
        if ">= 2" in d:
            return len(last2.intersection(combo_digits)) >= 2

    # subset of last2
    if "issubset(last2" in d:
        return set(combo_digits).issubset(last2)

    # new_seed_digits
    if "new_seed_digits" in d:
        return bool(new_seed_digits) and not new_seed_digits.intersection(combo_digits)

    # seed_counts full house check
    if "{2, 3}" in d and "seed_counts" in d:
        return set(seed_counts.values()) == {2, 3} and sum_combo % 2 == 0

    return False

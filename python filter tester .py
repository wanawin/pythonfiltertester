import re

# Drop-in improved apply_filter with robust issubset and shared digits parsing
def apply_filter(desc, combo_digits, seed_digits, prev_seed_digits, prev_prev_draw_digits, seed_counts, new_seed_digits):
    d = desc.lower().replace('≥', '>=').replace('≤', '<=')
    sum_combo = sum(combo_digits)
    set_combo = set(combo_digits)
    set_seed = set(seed_digits)
    last2 = set(prev_seed_digits) | set(prev_prev_draw_digits)
    common_to_both = set(prev_seed_digits).intersection(prev_prev_draw_digits)

    m = re.search(r'\{([\d,\s]+)\}\.issubset', d)
    if m:
        subset_digits = set(int(x.strip()) for x in m.group(1).split(','))
        is_seed = "seed" in d
        is_combo = "combo" in d and "seed" not in d
        odd = "!= 0" in d
        even = "== 0" in d
        if is_seed and odd:
            return subset_digits.issubset(set_seed) and sum_combo % 2 != 0
        if is_seed and even:
            return subset_digits.issubset(set_seed) and sum_combo % 2 == 0
        if is_combo and odd:
            return subset_digits.issubset(set_combo) and sum_combo % 2 != 0
        if is_combo and even:
            return subset_digits.issubset(set_combo) and sum_combo % 2 == 0

    m = re.search(r'≥(\d+)\s+shared.*seed', d)
    if m:
        required_shared = int(m.group(1))
        if "<" in d and "sum" in d:
            m_sum = re.search(r'sum\s*<\s*(\d+)', d)
            if m_sum:
                sum_limit = int(m_sum.group(1))
                return len(set_combo & set_seed) >= required_shared and sum_combo < sum_limit
        else:
            return len(set_combo & set_seed) >= required_shared

    if "mirror" in d:
        return any(get_mirror(x) in combo_digits for x in combo_digits)
    if d.startswith("v-trac"):
        groups = [get_v_trac_group(x) for x in combo_digits]
        return len(set(groups)) == 1
    if "common_to_both" in d:
        return sum(d in common_to_both for d in combo_digits) >= 2
    if "last2" in d:
        return len(last2.intersection(combo_digits)) >= 2
    return False

import csv
import streamlit as st

# Function to categorize sums

def sum_category(val):
    if val > 30:
        return "High"
    elif val > 20:
        return "Mid"
    elif val > 10:
        return "Low"
    else:
        return "Very Low"

# Load filter definitions from CSV

def load_filters():
    filters = []
    with open('lottery_filters_batch10.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)  # default quoting to allow commas in expressions
        for raw in reader:
            row = {k.lower(): (v or '').strip() for k, v in raw.items()}
            expr = row.get('expression')
            if expr:
                # wrap expression in triple-quotes to preserve internal quotes/commas
                wrapped = f'''{expr}'''
                try:
                    compiled = compile(wrapped, '<filter>', 'eval')
                    filters.append({
                        'id': row.get('f'),
                        'name': row.get('description'),
                        'expr': compiled,
                        'sum_category': sum_category,
                    })
                except Exception as e:
                    st.warning(f"Skipping filter {row.get('f')}: {e}")
    return filters

# Main Streamlit app

def main():
    st.sidebar.title('DC-5 Filter Tracker')
    seed = st.sidebar.text_input('Current 5-digit seed (required):')
    prev = st.sidebar.text_input('Previous 5-digit seed (optional):')
    prev2 = st.sidebar.text_input('Prev Prev 5-digit seed (optional):')
    method = st.sidebar.selectbox('Generation Method:', ['1-digit', '2-digit'])
    hot = st.sidebar.text_input('Hot digits (comma-separated):')
    cold = st.sidebar.text_input('Cold digits (comma-separated):')
    combo = st.sidebar.text_input('Track specific combo (optional):')

    st.sidebar.checkbox('Select/Deselect All Filters', key='all')

    filters = load_filters()

    if len(seed) == 5 and seed.isdigit():
        seed_vals = list(map(int, list(seed)))
        seed_sum = sum(seed_vals)
        prev_sum = sum(map(int, list(prev))) if prev.isdigit() else None
        prev2_sum = sum(map(int, list(prev2))) if prev2.isdigit() else None
        combo_sum = seed_sum + (prev_sum or 0)

        results = []
        for f in filters:
            try:
                keep = eval(f['expr'], {}, {
                    'seed_sum': seed_sum,
                    'prev_seed_sum': prev_sum,
                    'prev_prev_seed_sum': prev2_sum,
                    'combo_sum': combo_sum,
                    'sum_category': f['sum_category'],
                })
            except Exception:
                keep = False
            results.append((f['id'], f['name'], keep))

        st.write('### Filter Results')
        for fid, name, keep in results:
            st.write(f"{fid}: {name} — {'PASSED' if keep else 'ELIMINATED'}")
    else:
        st.error('Seed must be exactly 5 digits')

if __name__ == '__main__':
    main()

# ✅ Updated app with unique keys
# (This prevents DuplicateElementKey errors in Streamlit)

import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# Dummy filter groups for demonstration (replace with CSV reading logic)
filter_groups = [
    {"name": "Subset Filters", "filters": ["Subset filter A", "Subset filter B"]},
    {"name": "Mirror Filters", "filters": ["Mirror filter A"]},
    {"name": "V-Trac Filters", "filters": ["V-Trac filter A"]},
]

# Streamlit UI
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
select_all_groups = st.sidebar.checkbox("Select/Deselect All Groups", value=True)

for i, group in enumerate(filter_groups):
    group_name = group["name"]
    filters = group["filters"]
    # Ensure unique key for group checkbox
    if st.sidebar.checkbox(f"{group_name} ({len(filters)} filters)", value=select_all_groups, key=f"group_{i}"):
        for j, filter_desc in enumerate(filters):
            # Ensure unique key for each filter checkbox
            st.sidebar.checkbox(f"{filter_desc}", value=True, key=f"filter_{i}_{j}")

st.write("✔ App loaded with unique keys. Ready for processing.")

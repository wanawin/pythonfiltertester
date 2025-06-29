# filter_translator_app.py
# Streamlit Web App: Filter Translator Utility

import streamlit as st
import re

st.set_page_config(page_title="Filter Translator", layout="centered")

st.title("📝 Filter Translator Utility")
st.write("Enter a filter description below to see how Python normalizes and interprets it.")

# Normalization function
def normalize(desc: str) -> str:
    """
    Convert Unicode comparison operators to ASCII equivalents.
    """
    return desc.replace('≥', '>=').replace('≤', '<=').replace('–', '-')

# Translation function
def translate(desc: str) -> str:
    """
    Turn a Python-like filter string into a plain-English explanation.
    """
    t = desc
    # operators to words
    t = t.replace('>=', ' greater than or equal to ')
    t = t.replace('<=', ' less than or equal to ')
    t = t.replace('==', ' equals ')
    t = t.replace('!=', ' not equal to ')
    t = t.replace('%', ' modulo ')
    # sum() patterns
    t = re.sub(r'sum\(([^()]+)\)', r'the sum of (\1)', t)
    # intersection & subset
    t = t.replace('.intersection(', ' intersecting with ')
    t = t.replace('.issubset(', ' is a subset of ')
    # logical connectors
    t = t.replace(' and ', ' AND ')
    t = t.replace(' or ', ' OR ')
    return t.strip()

# Input area
user_input = st.text_area("Filter description:", height=150)

if user_input:
    norm = normalize(user_input)
    st.subheader("🔧 Normalized Filter")
    st.code(norm, language='python')

    trans = translate(norm)
    st.subheader("🗣️ Translation")
    st.write(trans)

    st.info("Copy the normalized code above for your app, and use the translation as a guide.")

st.sidebar.markdown("---")
st.sidebar.write("Version: 1.0")

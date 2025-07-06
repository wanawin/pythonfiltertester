import streamlit as st
from itertools import product
import csv
import os
import re
from collections import Counter

# V-Trac and mirror mappings
V_TRAC_GROUPS = {0:1,5:1,1:2,6:2,2:3,7:3,3:4,8:4,4:5,9:5}
MIRROR_PAIRS = {0:5,5:0,1:6,6:1,2:7,7:2,3:8,8:3,4:9,9:4}
MIRROR = MIRROR_PAIRS


def sum_category(s: int) -> str:
    """Categorize sum into buckets."""
    if   0  <= s <= 15: return 'Very Low'
    elif 16 <= s <= 24: return 'Low'
    elif 25 <= s <= 33: return 'Mid'
    else:               return 'High'


def load_filters(path='lottery_filters_batch11_complete.csv'):

# filter_translator.py
# A simple CLI utility to normalize and translate filter descriptions

import re
import sys

def normalize(desc: str) -> str:
    """
    Convert Unicode comparison operators to ASCII equivalents.
    """
    return desc.replace('≥', '>=').replace('≤', '<=').replace('–', '-')


def translate(desc: str) -> str:
    """
    Turn a Python-like filter string into a plain-English explanation.
    """
    t = desc
    # Replace comparison operators with words
    t = t.replace('>=', ' greater than or equal to ')
    t = t.replace('<=', ' less than or equal to ')
    t = t.replace('==', ' equals ')
    t = t.replace('!=', ' not equal to ')
    t = t.replace('%', ' modulo ')
    # Summation patterns
    t = re.sub(r'sum\(([^()]+)\)', r'the sum of (\1)', t)
    # Intersection and subset patterns
    t = t.replace('.intersection(', ' intersecting with ')
    t = t.replace('.issubset(', ' is a subset of ')
    # Logical connectors
    t = t.replace(' and ', ' AND ')
    t = t.replace(' or ', ' OR ')
    return t.strip()


def main():
    print("Filter Translator Utility")
    print("Enter your filter description (or 'exit' to quit):")
    while True:
        desc = input('> ').strip()
        if not desc or desc.lower() in ('exit', 'quit'):
            print("Exiting translator.")
            break
        norm = normalize(desc)
        print(f"\nNormalized: {norm}")
        print(f"Translated: {translate(norm)}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting translator.")
        sys.exit(0)

#!/usr/bin/env python3
import sys
from pathlib import Path

import requests
import xlrd

def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/inspect_excel.py <url>")
        raise SystemExit(1)

    url = sys.argv[1]
    cache = Path("cache/inspect.xls")
    cache.parent.mkdir(exist_ok=True)

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    cache.write_bytes(r.content)

    book = xlrd.open_workbook(str(cache))

    print("Sheets:")
    for name in book.sheet_names():
        print("-", name)

    for sheet in book.sheets():
        print(f"\n=== {sheet.name} ===")
        for r in range(min(sheet.nrows, 30)):
            values = [sheet.cell_value(r, c) for c in range(min(sheet.ncols, 12))]
            print(r + 1, values)

if __name__ == "__main__":
    main()

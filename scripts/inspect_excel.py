#!/usr/bin/env python3

import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests


def open_excel_source(arg: str) -> Path:
    if arg.startswith("http://") or arg.startswith("https://"):
        r = requests.get(
            arg,
            # headers={
            #     "User-Agent": "Mozilla/5.0",
            #     "Referer": "https://tokei.pref.nagano.lg.jp/",
            # },
            timeout=60,
        )
        r.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        tmp.write(r.content)
        tmp.close()

        return Path(tmp.name)

    path = Path(arg)

    if not path.exists():
        raise FileNotFoundError(path)

    return path


def inspect_sheet(path: Path):
    xls = pd.ExcelFile(path)

    print("=" * 80)
    print(f"FILE: {path}")
    print("=" * 80)

    print("\nSHEETS:")
    for i, name in enumerate(xls.sheet_names):
        print(f"  [{i}] {name}")

    print("\n" + "=" * 80)

    for name in xls.sheet_names:
        print(f"\n### SHEET: {name}")

        try:
            df = pd.read_excel(path, sheet_name=name, header=None)

            print(f"shape = {df.shape}")
            print()

            preview = df.head(15).fillna("")
            print(preview.to_string(index=False, header=False))

        except Exception as e:
            print(f"ERROR: {e}")

        print("\n" + "-" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python inspect_excel.py <xlsx path or url>")
        sys.exit(1)

    source = sys.argv[1]

    path = open_excel_source(source)

    inspect_sheet(path)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
from pathlib import Path
import json
import re
import urllib.request

import xlrd


SOURCE_URL = "https://www.city.shiojiri.lg.jp/uploaded/attachment/40337.xls"
CACHE_PATH = Path("cache/finance_expenditure_nature.xls")
OUTPUT_PATH = Path("public/data/finance_expenditure_nature.json")
SHEET_NAME = "15-4【歳出】"


def parse_year(value):
    if value is None:
        return None
    match = re.search(r"(\d{4})", str(value))
    if match:
        return int(match.group(1))
    return None


def to_int(value):
    if value in (None, "", "***"):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def to_float(value):
    if value in (None, "", "***"):
        return None
    try:
        return float(value)
    except Exception:
        return None


def download():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE_PATH.exists():
        print(f"download: {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, CACHE_PATH)
    return CACHE_PATH


def build_records(path):
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_name(SHEET_NAME)
    grouped = {}

    for row_index in range(4, sheet.nrows):
        row = sheet.row_values(row_index)
        year = parse_year(row[1])
        category = str(row[2]).strip() if row[2] else ""
        if not year:
            continue

        grouped.setdefault(year, {
            "year": year,
            "construction_amount": None,
            "construction_ratio": None,
            "support_amount": None,
            "support_ratio": None,
            "personnel_amount": None,
            "personnel_ratio": None,
            "debt_amount": None,
            "debt_ratio": None,
            "total_amount": None,
        })

        amount = to_int(row[3])
        ratio = to_float(row[4])

        if category == "普通建設事業費":
            grouped[year]["construction_amount"] = amount
            grouped[year]["construction_ratio"] = ratio
        elif category == "扶助費":
            grouped[year]["support_amount"] = amount
            grouped[year]["support_ratio"] = ratio
        elif category == "人件費":
            grouped[year]["personnel_amount"] = amount
            grouped[year]["personnel_ratio"] = ratio
        elif category == "公債費":
            grouped[year]["debt_amount"] = amount
            grouped[year]["debt_ratio"] = ratio
        elif category == "合計":
            grouped[year]["total_amount"] = amount

    return sorted(grouped.values(), key=lambda row: row["year"])


def main():
    path = download()
    records = build_records(path)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"created: {OUTPUT_PATH}")
    print(f"rows: {len(records)}")


if __name__ == "__main__":
    main()

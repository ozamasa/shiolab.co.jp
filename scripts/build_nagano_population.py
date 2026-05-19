#!/usr/bin/env python3

import json
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE = PROJECT_ROOT / "cache" / "nagano" / "population_age_structure.xlsx"
OUTPUT = PROJECT_ROOT / "public" / "sites" / "nagano" / "data" / "population_age_groups.json"


def to_int(value):
    if pd.isna(value):
        return None

    s = str(value)
    # "1980年" → "1980"
    s = s.replace("年", "").replace(",", "").strip()
    return int(float(s))


def to_float(value):
    if pd.isna(value):
        return None
    return float(value)


def normalize_sheet_name(name: str) -> str:
    return str(name).replace(" ", "").replace("　", "").strip()


def should_use_sheet(name: str) -> bool:
    n = normalize_sheet_name(name)

    if "原数値" in n:
        return False

    return (
        n in {
            "昭和55年",
            "昭和60年",
            "平成2年",
            "平成7年",
            "平成12年",
            "平成17年",
            "平成22年",
            "平成27年_不詳補完値",
            "令和2年_不詳補完値",
        }
    )


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    xls = pd.ExcelFile(SOURCE)

    print("Sheets:")
    for name in xls.sheet_names:
        print(f"- {name}")

    records = []

    for sheet in xls.sheet_names:
        if not should_use_sheet(sheet):
            continue

        df = pd.read_excel(SOURCE, sheet_name=sheet, header=None)

        row = df[df[2] == 20000.0]

        if row.empty:
            # 念のため文字列化でも探す
            row = df[df[2].astype(str).str.replace(".0", "", regex=False) == "20000"]

        if row.empty:
            print(f"[skip] {sheet}: 長野県行が見つかりません")
            continue

        r = row.iloc[0]

        year = to_int(r[0])
        total = to_int(r[4])
        young = to_int(r[5])
        working = to_int(r[6])
        elderly = to_int(r[7])

        young_ratio = to_float(r[16])
        working_ratio = to_float(r[17])
        elderly_ratio = to_float(r[18])

        aging_index = elderly / young * 100 if young else None
        dependency_index = (young + elderly) / working * 100 if working else None

        records.append({
            "year": year,
            "total": total,
            "young": young,
            "working": working,
            "elderly": elderly,
            "young_ratio": young_ratio,
            "working_age_ratio": working_ratio,
            "elderly_ratio": elderly_ratio,
            "aging_index": aging_index,
            "dependency_index": dependency_index,
        })

    if not records:
        raise RuntimeError("対象シートからデータを作成できませんでした")

    records.sort(key=lambda x: x["year"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[ok] {OUTPUT}")
    print(f"rows: {len(records)}")
    print(f"years: {records[0]['year']} - {records[-1]['year']}")


if __name__ == "__main__":
    main()
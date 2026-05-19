#!/usr/bin/env python3

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

AGE_GROUPS = PROJECT_ROOT / "public" / "sites" / "nagano" / "data" / "population_age_groups.json"
OUTPUT = PROJECT_ROOT / "public" / "sites" / "nagano" / "data" / "population_summary.json"


def main():
    rows = json.loads(AGE_GROUPS.read_text(encoding="utf-8"))

    records = []

    for row in rows:
        total = row["total"]

        # 世帯数は未取得なので null
        households = None

        records.append({
            "year": row["year"],
            "total": total,
            "households": households,
            "people_per_household": None,
        })

    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[ok] {OUTPUT}")
    print(f"rows: {len(records)}")


if __name__ == "__main__":
    main()
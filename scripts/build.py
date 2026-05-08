#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable

import requests
import yaml
import xlrd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "datasets.yml"
METADATA_PATH = PROJECT_ROOT / "public" / "data" / "metadata.json"
SUPPORTED_DATASET_TYPES = {"table_by_columns", "row_blocks_by_year"}
SUPPORTED_COLUMN_TYPES = {"raw", "text", "year", "int", "float", "number"}

ValidationHandler = Callable[[str, list[dict[str, Any]], dict[str, Any]], list[str]]

def now_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def excel_col_to_index(col: str) -> int:
    col = col.strip().upper()
    value = 0
    for ch in col:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"invalid Excel column: {col}")
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value - 1

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()

def normalize_number(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "").replace("　", "")
    if text in {"-", "－", "―", "…", "—", "***"}:
        return None
    text = re.sub(r"[人世帯％%千円億円]+$", "", text)
    try:
        num = float(text)
    except ValueError:
        return None
    if num.is_integer():
        return int(num)
    return num

def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        year = int(value)
        if 1800 <= year <= 2200:
            return year
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(\d{4})", text)
    if match:
        return int(match.group(1))
    era_match = re.search(r"(令和|平成|昭和|大正|明治)\s*(\d+|元)\s*年", text)
    if era_match:
        era, n_text = era_match.groups()
        n = 1 if n_text == "元" else int(n_text)
        base = {"令和": 2018, "平成": 1988, "昭和": 1925, "大正": 1911, "明治": 1867}[era]
        return base + n
    return None

def convert_value(value: Any, value_type: str | None) -> Any:
    value_type = value_type or "number"
    if value_type == "raw":
        return value
    if value_type == "text":
        return clean_text(value)
    if value_type == "year":
        return parse_year(value)
    if value_type == "int":
        number = normalize_number(value)
        return None if number is None else int(number)
    if value_type == "float":
        number = normalize_number(value)
        return None if number is None else float(number)
    if value_type == "number":
        return normalize_number(value)
    raise ValueError(f"unknown column type: {value_type}")

def validate_dataset_config(dataset_key: str, cfg: dict[str, Any]) -> None:
    if not cfg.get("enabled", True):
        return
    required = ["type", "source_url", "cache_file", "data_start_row", "columns", "output"]
    missing = [field for field in required if field not in cfg]
    if missing:
        raise ValueError(f"{dataset_key}: required config fields are missing: {missing}")
    if cfg["type"] not in SUPPORTED_DATASET_TYPES:
        raise ValueError(f"{dataset_key}: unsupported type: {cfg['type']}")
    if not isinstance(cfg["columns"], dict) or "year" not in cfg["columns"]:
        raise ValueError(f"{dataset_key}: columns must include year")
    columns_cfg = normalize_columns_config(cfg["columns"])
    for field, spec in columns_cfg.items():
        if "column" not in spec:
            raise ValueError(f"{dataset_key}: columns.{field}.column is required")
        excel_col_to_index(spec["column"])
        value_type = spec.get("type", "number")
        if value_type not in SUPPORTED_COLUMN_TYPES:
            raise ValueError(f"{dataset_key}: columns.{field}.type is unsupported: {value_type}")
    for rule in cfg.get("validations", []) or []:
        rule_type = rule.get("type")
        if rule_type not in VALIDATION_HANDLERS:
            raise ValueError(f"{dataset_key}: unsupported validation type: {rule_type}")

def safe_eval_formula(formula: str, row: dict[str, Any]) -> Any:
    allowed_builtins = {"abs": abs, "round": round, "min": min, "max": max}
    return eval(formula, {"__builtins__": allowed_builtins}, row)

def apply_derived_fields(row: dict[str, Any], derived: dict[str, Any] | None) -> None:
    if not derived:
        return
    for field, spec in derived.items():
        try:
            value = safe_eval_formula(spec["formula"], row)
        except Exception:
            value = None
        if value is not None and spec.get("digits") is not None:
            value = round(value, int(spec["digits"]))
        row[field] = value

def download_source(dataset_key: str, cfg: dict[str, Any], force: bool = False) -> dict[str, Any]:
    url = cfg.get("source_url")
    if not url:
        raise ValueError(f"{dataset_key}: source_url が空です")
    cache_file = PROJECT_ROOT / cfg["cache_file"]
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if cache_file.exists() and not force:
        return {
            "source_url": url,
            "cache_file": str(cache_file.relative_to(PROJECT_ROOT)),
            "downloaded_at": None,
            "used_cached_file": True,
            "last_modified": None,
            "etag": None,
            "sha256": sha256_file(cache_file),
        }
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    cache_file.write_bytes(response.content)
    return {
        "source_url": url,
        "cache_file": str(cache_file.relative_to(PROJECT_ROOT)),
        "downloaded_at": now_iso(),
        "used_cached_file": False,
        "last_modified": response.headers.get("Last-Modified"),
        "etag": response.headers.get("ETag"),
        "content_length": response.headers.get("Content-Length"),
        "sha256": sha256_file(cache_file),
    }

def get_sheet(book: xlrd.book.Book, sheet_name: str | None, dataset_key: str) -> xlrd.sheet.Sheet:
    if sheet_name:
        try:
            return book.sheet_by_name(sheet_name)
        except xlrd.biffh.XLRDError as exc:
            raise ValueError(
                f"{dataset_key}: sheet '{sheet_name}' が見つかりません。 available={book.sheet_names()}"
            ) from exc
    return book.sheet_by_index(0)

def normalize_columns_config(columns: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = {}
    for field, spec in columns.items():
        if isinstance(spec, str):
            normalized[field] = {"column": spec, "type": "number" if field != "year" else "year"}
        elif isinstance(spec, dict):
            normalized[field] = spec
        else:
            raise ValueError(f"invalid column spec for {field}: {spec}")
    return normalized

def row_matches_filters(sheet: xlrd.sheet.Sheet, row_index: int, filters: list[dict[str, Any]] | dict[str, Any] | None) -> bool:
    if not filters:
        return True
    filters_iter = list(filters.values()) if isinstance(filters, dict) else filters
    for f in filters_iter:
        col_idx = excel_col_to_index(f["column"])
        text = clean_text(sheet.cell_value(row_index, col_idx))
        if "equals" in f and text != str(f["equals"]).strip():
            return False
        if "not_equals" in f and text == str(f["not_equals"]).strip():
            return False
        if "contains" in f and str(f["contains"]).strip() not in text:
            return False
        if f.get("not_empty") and text == "":
            return False
        if f.get("empty") and text != "":
            return False
    return True

def read_table_by_columns(dataset_key: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / cfg["cache_file"]
    if not path.exists():
        raise FileNotFoundError(f"{dataset_key}: cache file not found: {path}")
    book = xlrd.open_workbook(str(path))
    sheet = get_sheet(book, cfg.get("sheet"), dataset_key)
    start_row = int(cfg["data_start_row"]) - 1
    columns_cfg = normalize_columns_config(cfg["columns"])
    col_indexes = {field: excel_col_to_index(spec["column"]) for field, spec in columns_cfg.items()}
    rows = []
    blank_year_count = 0
    max_blank_years = int(cfg.get("max_blank_years", 30))
    for r in range(start_row, sheet.nrows):
        raw_year = sheet.cell_value(r, col_indexes["year"])
        year = convert_value(raw_year, columns_cfg["year"].get("type", "year"))
        if year is None:
            blank_year_count += 1
            if cfg.get("stop_when_year_blank", True):
                break
            if blank_year_count >= max_blank_years:
                break
            continue
        blank_year_count = 0
        if not row_matches_filters(sheet, r, cfg.get("filters")):
            continue
        item = {}
        for field, spec in columns_cfg.items():
            raw_value = sheet.cell_value(r, col_indexes[field])
            item[field] = convert_value(raw_value, spec.get("type"))
        apply_derived_fields(item, cfg.get("derived"))
        rows.append(item)
    if not rows:
        raise ValueError(f"{dataset_key}: データ行を抽出できませんでした。 sheet={sheet.name}, start_row={cfg['data_start_row']}")
    if "year" in rows[0]:
        rows.sort(key=lambda x: x["year"])
    return rows

def read_row_blocks_by_year(dataset_key: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """複数行で1年分を表す統計表を、年単位にマージして読む。

    例：
      1960 / 事業所数 / 総数
      1960 / 従業者数 / 総数
    を
      {year: 1960, businesses: ..., employees: ...}
    に変換する。
    """
    path = PROJECT_ROOT / cfg["cache_file"]
    if not path.exists():
        raise FileNotFoundError(f"{dataset_key}: cache file not found: {path}")

    book = xlrd.open_workbook(str(path))
    sheet = get_sheet(book, cfg.get("sheet"), dataset_key)

    blocks = cfg["row_blocks"]
    columns_cfg = normalize_columns_config(cfg["columns"])
    start_row = int(cfg["data_start_row"]) - 1
    grouped: dict[int, dict[str, Any]] = {}

    for row_idx in range(start_row, sheet.nrows):
        matched_block = None

        for block in blocks:
            col_idx = excel_col_to_index(block["match"]["column"])
            cell = clean_text(sheet.cell_value(row_idx, col_idx))

            if cell == str(block["match"]["equals"]).strip():
                matched_block = block["key"]
                break

        if not matched_block:
            continue

        row_data: dict[str, Any] = {}
        for field, spec in columns_cfg.items():
            col_idx = excel_col_to_index(spec["column"])
            raw_value = sheet.cell_value(row_idx, col_idx)
            row_data[field] = convert_value(raw_value, spec.get("type"))

        year = row_data.get("year")
        if year is None:
            continue

        mapping = cfg["merge_by_year"].get(matched_block, {})
        if not mapping:
            continue

        # 値が欠損（*** 等）の行は採用しない。
        has_any_value = any(row_data.get(source_field) is not None for source_field in mapping.keys())
        if not has_any_value:
            continue

        if year not in grouped:
            grouped[year] = {"year": year}

        for source_field, target_field in mapping.items():
            grouped[year][target_field] = row_data.get(source_field)

    rows = [grouped[year] for year in sorted(grouped.keys())]

    for row in rows:
        apply_derived_fields(row, cfg.get("derived"))

    if not rows:
        raise ValueError(f"{dataset_key}: データ行を抽出できませんでした。 sheet={sheet.name}, start_row={cfg['data_start_row']}")

    return rows

def validate_sum_equals(dataset_key: str, rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    errors = []
    name = rule.get("name", rule["type"])
    left = rule["left"]
    rights = rule["rights"]
    tolerance = float(rule.get("tolerance", 0))
    for row in rows:
        left_value = row.get(left)
        right_sum = sum((row.get(k) or 0) for k in rights)
        if left_value is None or abs(left_value - right_sum) > tolerance:
            errors.append(f"{dataset_key}:{name}: {row.get('year')} {left}={left_value}, sum({rights})={right_sum}")
    return errors

def validate_range(dataset_key: str, rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    errors = []
    name = rule.get("name", rule["type"])
    field = rule["field"]
    min_v = rule.get("min")
    max_v = rule.get("max")
    for row in rows:
        value = row.get(field)
        if value is None:
            errors.append(f"{dataset_key}:{name}: {row.get('year')} {field} が空です")
            continue
        if min_v is not None and value < min_v:
            errors.append(f"{dataset_key}:{name}: {row.get('year')} {field}={value} < {min_v}")
        if max_v is not None and value > max_v:
            errors.append(f"{dataset_key}:{name}: {row.get('year')} {field}={value} > {max_v}")
    return errors

def validate_unique(dataset_key: str, rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    field = rule["field"]
    values = [row.get(field) for row in rows]
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        name = rule.get("name", rule["type"])
        return [f"{dataset_key}:{name}: {field} に重複があります: {sorted(duplicates)}"]
    return []

def validate_ascending(dataset_key: str, rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    field = rule["field"]
    values = [row.get(field) for row in rows]
    if values != sorted(values):
        name = rule.get("name", rule["type"])
        return [f"{dataset_key}:{name}: {field} が昇順ではありません"]
    return []

def validate_not_null(dataset_key: str, rows: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    errors = []
    name = rule.get("name", rule["type"])
    fields = rule.get("fields") or [rule["field"]]
    for row in rows:
        for field in fields:
            if row.get(field) is None:
                errors.append(f"{dataset_key}:{name}: {row.get('year')} {field} が空です")
    return errors

VALIDATION_HANDLERS: dict[str, ValidationHandler] = {
    "sum_equals": validate_sum_equals,
    "range": validate_range,
    "unique": validate_unique,
    "ascending": validate_ascending,
    "not_null": validate_not_null,
}

def validate_rows(dataset_key: str, rows: list[dict[str, Any]], validations: list[dict[str, Any]]) -> list[str]:
    errors = []
    for rule in validations or []:
        errors.extend(VALIDATION_HANDLERS[rule["type"]](dataset_key, rows, rule))
    return errors

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def build_dataset(dataset_key: str, cfg: dict[str, Any], force_download: bool = False) -> dict[str, Any]:
    validate_dataset_config(dataset_key, cfg)
    if not cfg.get("enabled", True):
        return {"dataset": dataset_key, "enabled": False, "skipped": True}
    source_meta = download_source(dataset_key, cfg, force=force_download)
    data_type = cfg.get("type")
    if data_type == "table_by_columns":
        rows = read_table_by_columns(dataset_key, cfg)
    elif data_type == "row_blocks_by_year":
        rows = read_row_blocks_by_year(dataset_key, cfg)
    else:
        raise ValueError(f"{dataset_key}: 未対応の type: {data_type}")
    validation_errors = validate_rows(dataset_key, rows, cfg.get("validations", []))
    if validation_errors:
        message = "\n".join(validation_errors[:30])
        more = "" if len(validation_errors) <= 30 else f"\n... and {len(validation_errors) - 30} more"
        raise ValueError(f"Validation failed for {dataset_key}:\n{message}{more}")
    output_path = PROJECT_ROOT / cfg["output"]
    write_json(output_path, rows)
    years = [row.get("year") for row in rows if row.get("year") is not None]
    return {
        "dataset": dataset_key,
        "enabled": True,
        "source_name": cfg.get("source_name"),
        **source_meta,
        "generated_at": now_iso(),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "row_count": len(rows),
        "years": {"min": min(years) if years else None, "max": max(years) if years else None},
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--dataset")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    metadata = {"generated_at": now_iso(), "datasets": {}}
    targets = [args.dataset] if args.dataset else list(config.keys())
    for key in targets:
        if key not in config:
            raise SystemExit(f"dataset not found: {key}")
        result = build_dataset(key, config[key], force_download=args.force_download)
        metadata["datasets"][key] = result
        if result.get("skipped"):
            print(f"[skip] {key}")
        else:
            year_info = result.get("years", {})
            print(f"[ok] {key}: {result['row_count']} rows ({year_info.get('min')} - {year_info.get('max')}) -> {result['output']}")
    write_json(METADATA_PATH, metadata)
    print(f"[ok] metadata -> {METADATA_PATH.relative_to(PROJECT_ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

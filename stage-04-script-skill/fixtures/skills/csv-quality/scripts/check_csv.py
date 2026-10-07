#!/usr/bin/env python3
"""Kiểm tra chất lượng CSV công việc (task_id, owner, hours), tính tổng giờ theo owner và in JSON ra stdout.

Cách chạy (cwd là workspace):
    python skills/csv-quality/scripts/check_csv.py --input data/tasks.csv --max-hours 8

Exit 0: phân tích thành công, kể cả khi dữ liệu có lỗi chất lượng hoặc có người quá tải.
Exit 1: file không tồn tại/không đọc được, thiếu cột bắt buộc hoặc lỗi parse CSV; thông báo ra stderr.
Exit 2: thiếu --max-hours hoặc giá trị không phải số hữu hạn không âm; thông báo ra stderr.
Script chỉ đọc, không sửa CSV. Tổng giờ chỉ cộng các dòng hợp lệ; dòng bị loại nằm trong excluded_rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys

REQUIRED_COLUMNS = ("task_id", "owner", "hours")
# Thứ tự cố định của lý do loại dòng trong excluded_rows[].reasons
REASON_ORDER = ("wrong_field_count", "missing_task_id", "duplicate_id", "missing_owner", "invalid_hours")


class InputError(Exception):
    pass


def parse_hours(raw: str | None) -> float | None:
    """Số giờ hợp lệ: số hữu hạn, không âm. Trả None nếu không hợp lệ."""
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def parse_max_hours(raw: str) -> float:
    """Kiểu cho argparse: ngưỡng phải là số hữu hạn không âm, cùng quy tắc với hours."""
    value = parse_hours(raw)
    if value is None:
        raise argparse.ArgumentTypeError(f"phải là số hữu hạn không âm, nhận được '{raw}'")
    return value


def analyze(path: str, max_hours: float) -> dict:
    try:
        handle = open(path, encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise InputError(f"Không đọc được file {path}: {exc.strerror or exc}") from exc
    with handle:
        reader = csv.reader(handle, strict=True)
        try:
            header = next(reader, None)
            if header is None:
                raise InputError(f"File {path} rỗng, không có header.")
            columns = [c.strip() for c in header]
            missing = [c for c in REQUIRED_COLUMNS if c not in columns]
            if missing:
                raise InputError(f"Thiếu cột bắt buộc: {', '.join(missing)}. Header hiện có: {', '.join(columns)}")
            index = {name: columns.index(name) for name in REQUIRED_COLUMNS}

            row_count = 0
            missing_owner = 0
            invalid_hours = 0
            first_seen: dict[str, int] = {}
            duplicate_ids: list[str] = []
            issues: list[dict] = []
            hours_by_owner: dict[str, float] = {}
            excluded_rows: list[dict] = []
            for row in reader:
                line = reader.line_num
                if not any(cell.strip() for cell in row):
                    continue  # bỏ qua dòng trống
                row_count += 1

                def cell(name: str) -> str:
                    position = index[name]
                    return row[position].strip() if position < len(row) else ""

                task_id, owner, hours = cell("task_id"), cell("owner"), cell("hours")
                reasons: list[str] = []
                if len(row) != len(columns):
                    reasons.append("wrong_field_count")
                    issues.append({"line": line, "column": None, "type": "wrong_field_count", "task_id": task_id or None,
                                   "message": f"Có {len(row)} trường, header có {len(columns)} cột."})
                if not task_id:
                    reasons.append("missing_task_id")
                    issues.append({"line": line, "column": "task_id", "type": "missing_task_id", "task_id": None,
                                   "message": "task_id trống."})
                elif task_id in first_seen:
                    # Lần đầu xuất hiện luôn được giữ, kể cả khi dòng đó không hợp lệ; lần sau luôn bị loại
                    reasons.append("duplicate_id")
                    if task_id not in duplicate_ids:
                        duplicate_ids.append(task_id)
                    issues.append({"line": line, "column": "task_id", "type": "duplicate_id", "task_id": task_id,
                                   "message": f"task_id {task_id} đã xuất hiện ở line {first_seen[task_id]}."})
                else:
                    first_seen[task_id] = line
                if not owner:
                    reasons.append("missing_owner")
                    missing_owner += 1
                    issues.append({"line": line, "column": "owner", "type": "missing_owner", "task_id": task_id or None,
                                   "message": "owner trống."})
                value = parse_hours(hours)
                if value is None:
                    reasons.append("invalid_hours")
                    invalid_hours += 1
                    issues.append({"line": line, "column": "hours", "type": "invalid_hours", "task_id": task_id or None,
                                   "value": hours, "message": f"hours '{hours}' không phải số hữu hạn không âm."})

                if reasons:
                    reasons.sort(key=REASON_ORDER.index)
                    excluded_rows.append({"line": line, "task_id": task_id or None, "reasons": reasons})
                else:
                    hours_by_owner[owner] = hours_by_owner.get(owner, 0.0) + value
        except csv.Error as exc:
            raise InputError(f"Lỗi parse CSV ở line {reader.line_num}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise InputError(f"File {path} không phải UTF-8: {exc}") from exc

    return {
        "input": path,
        "row_count": row_count,
        "missing_owner_count": missing_owner,
        "invalid_hours_count": invalid_hours,
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids,
        "issues": sorted(issues, key=lambda item: item["line"]),
        "max_hours": max_hours,
        "hours_by_owner": dict(sorted(hours_by_owner.items())),
        # Quá tải khi tổng giờ lớn hơn ngưỡng; bằng ngưỡng không tính
        "overloaded_owners": [
            {"owner": owner, "total_hours": total}
            for owner, total in sorted(hours_by_owner.items())
            if total > max_hours
        ],
        "excluded_rows": sorted(excluded_rows, key=lambda item: item["line"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng CSV công việc (task_id, owner, hours).")
    parser.add_argument("--input", required=True, help="Đường dẫn CSV, ví dụ data/tasks.csv")
    parser.add_argument("--max-hours", required=True, type=parse_max_hours,
                        help="Ngưỡng quá tải (số hữu hạn không âm). Tổng giờ lớn hơn ngưỡng là quá tải.")
    args = parser.parse_args(argv)  # thiếu/sai --max-hours: argparse ghi stderr và exit 2
    try:
        result = analyze(args.input, args.max_hours)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

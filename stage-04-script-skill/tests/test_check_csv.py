"""csv-quality script: thống kê fixture, lỗi input/schema/parse exit 1, lỗi dữ liệu exit 0, tổng giờ và quá tải."""

import json
import subprocess
import sys

import pytest

import paths

SCRIPT = paths.FIXTURES_DIR / "skills" / "csv-quality" / "scripts" / "check_csv.py"


def run(path, *extra, max_hours="8"):
    args = [sys.executable, str(SCRIPT), "--input", str(path), *extra]
    if max_hours is not None:
        args += ["--max-hours", max_hours]
    return subprocess.run(args, capture_output=True, text=True, timeout=10)


def write_csv(tmp_path, text):
    path = tmp_path / "t.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_fixture_statistics():
    result = run(paths.FIXTURES_DIR / "data" / "tasks.csv")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["row_count"] == 6
    assert data["missing_owner_count"] == 1
    assert data["invalid_hours_count"] == 1
    assert data["duplicate_id_count"] == 1
    assert data["duplicate_ids"] == ["T02"]
    assert [(i["line"], i["column"], i["type"]) for i in data["issues"]] == [
        (4, "owner", "missing_owner"),
        (5, "hours", "invalid_hours"),
        (6, "task_id", "duplicate_id"),
    ]
    assert "total_hours" not in data


@pytest.mark.parametrize("hours", ["NaN", "nan", "Infinity", "-inf", "-1", ""])
def test_non_finite_negative_or_empty_hours_rejected(tmp_path, hours):
    data = json.loads(run(write_csv(tmp_path, f"task_id,owner,hours\nT01,Lan,{hours}\n")).stdout)
    assert data["invalid_hours_count"] == 1
    assert data["issues"][0]["line"] == 2


def test_clean_data_exit_0_without_issues(tmp_path):
    result = run(write_csv(tmp_path, "task_id,owner,hours\nT01,Lan,4\nT02,Minh,2.5\n"))
    assert result.returncode == 0
    assert json.loads(result.stdout)["issues"] == []


def test_missing_file_exit_1(tmp_path):
    result = run(tmp_path / "khong-co.csv")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Không đọc được file" in result.stderr


def test_missing_column_exit_1(tmp_path):
    result = run(write_csv(tmp_path, "task_id,owner\nT01,Lan\n"))
    assert result.returncode == 1
    assert "Thiếu cột bắt buộc: hours" in result.stderr


def test_parse_error_exit_1(tmp_path):
    result = run(write_csv(tmp_path, 'task_id,owner,hours\nT01,"La"n,4\n'))
    assert result.returncode == 1
    assert "Lỗi parse CSV" in result.stderr


def test_script_does_not_modify_input():
    source = paths.FIXTURES_DIR / "data" / "tasks.csv"
    before = source.read_bytes()
    run(source)
    assert source.read_bytes() == before


def excluded(data):
    return [(r["line"], r["task_id"], r["reasons"]) for r in data["excluded_rows"]]


WORKLOAD_EXCLUDED = [(5, "T04", ["invalid_hours"]), (6, "T02", ["duplicate_id"]), (7, "T05", ["missing_owner"])]


def test_workload_threshold_8_lan_overloaded():
    result = run(paths.FIXTURES_DIR / "data" / "workload.csv", max_hours="8")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["max_hours"] == 8
    assert data["hours_by_owner"] == {"Lan": 9, "Minh": 3}  # dòng 6 trùng T02 không được cộng
    assert data["overloaded_owners"] == [{"owner": "Lan", "total_hours": 9}]
    assert excluded(data) == WORKLOAD_EXCLUDED
    assert data["row_count"] == 6 and data["duplicate_ids"] == ["T02"]  # trường cũ vẫn giữ


def test_workload_threshold_equal_is_not_overloaded():
    data = json.loads(run(paths.FIXTURES_DIR / "data" / "workload.csv", max_hours="9").stdout)
    assert data["hours_by_owner"] == {"Lan": 9, "Minh": 3}
    assert data["overloaded_owners"] == []
    assert excluded(data) == WORKLOAD_EXCLUDED


def test_first_id_with_invalid_hours_still_blocks_later_duplicate():
    result = run(paths.FIXTURES_DIR / "data" / "workload-edge.csv", max_hours="0")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["hours_by_owner"] == {"Minh": 0}  # E01 dòng 3 hợp lệ nhưng vẫn bị loại vì trùng
    assert data["overloaded_owners"] == []
    assert excluded(data) == [(2, "E01", ["invalid_hours"]), (3, "E01", ["duplicate_id"])]


def test_excluded_row_lists_all_reasons_in_fixed_order(tmp_path):
    path = write_csv(tmp_path, "task_id,owner,hours\nT01,Lan,4\nT01,,abc\n,,-1,x\n")
    data = json.loads(run(path).stdout)
    assert excluded(data) == [
        (3, "T01", ["duplicate_id", "missing_owner", "invalid_hours"]),
        (4, None, ["wrong_field_count", "missing_task_id", "missing_owner", "invalid_hours"]),
    ]
    assert data["hours_by_owner"] == {"Lan": 4}


@pytest.mark.parametrize("value", [None, "-1", "abc", "nan", "inf", ""])
def test_missing_or_invalid_max_hours_rejected(value):
    result = run(paths.FIXTURES_DIR / "data" / "workload.csv", max_hours=value)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "--max-hours" in result.stderr

---
name: csv-quality
description: Kiểm tra chất lượng file CSV danh sách công việc (cột task_id, owner, hours), tính tổng giờ theo owner và xác định người quá tải theo ngưỡng giờ, bằng script có sẵn, rồi ghi báo cáo Markdown dưới output/. Dùng khi người dùng yêu cầu kiểm tra, rà soát chất lượng dữ liệu CSV công việc, tính tổng giờ theo người hoặc kiểm tra ai quá tải.
---

# CSV quality

Kiểm tra chất lượng CSV công việc và tính tổng giờ theo owner bằng script, không tự đếm hay tự cộng bằng mắt.

## Xác định ngưỡng quá tải

Script bắt buộc có ngưỡng giờ `--max-hours` (số hữu hạn không âm).

- Người dùng đã nêu ngưỡng (ví dụ "ngưỡng 8 giờ", "quá 8 giờ là quá tải") → truyền **đúng giá trị đó** vào `--max-hours`.
- Người dùng chưa nêu ngưỡng → **hỏi lại ngưỡng và dừng**. Không tự chọn ngưỡng mặc định, không chạy script với ngưỡng đoán, không kết luận ai quá tải.
- Ngưỡng là số âm hoặc không phải số → báo không hợp lệ và hỏi lại.

## Chạy script

Dùng tool `bash` (cwd là workspace). Lệnh đầy đủ:

```
python skills/csv-quality/scripts/check_csv.py --input <đường dẫn CSV> --max-hours <ngưỡng>
```

Ví dụ: `python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 8`

Không cần đọc source script để chạy. Chỉ đọc `scripts/check_csv.py` khi cần hiểu một hành vi mà phần dưới không mô tả.

## Kiểm tra kết quả

- `exit_code` 0: phân tích thành công. `stdout` là JSON gồm:
  - Chất lượng dữ liệu: `row_count`, `missing_owner_count`, `invalid_hours_count`, `duplicate_id_count`, `duplicate_ids`, `issues`.
  - Tổng giờ: `max_hours` (ngưỡng đã dùng), `hours_by_owner` (owner → tổng giờ, chỉ cộng dòng hợp lệ), `overloaded_owners` (owner có tổng giờ **lớn hơn** ngưỡng; bằng ngưỡng không phải quá tải), `excluded_rows` (dòng không được cộng, mỗi dòng kèm `line`, `task_id`, `reasons`).
  - Dữ liệu có lỗi chất lượng hoặc có người quá tải vẫn là exit 0.
- `exit_code` 1: **lỗi thực thi** (file không tồn tại, thiếu cột bắt buộc, lỗi parse). Đọc `stderr`, báo lỗi cho người dùng. Không bịa thống kê, không ghi báo cáo như thể đã phân tích.
- `exit_code` 2: **lỗi tham số** (thiếu hoặc sai `--max-hours`). Đọc `stderr`; kiểm tra lại lệnh hoặc hỏi lại ngưỡng hợp lệ.
- `timed_out` true hoặc `ok` false: lệnh không chạy xong; báo lỗi, không suy đoán kết quả.
- Phân biệt rõ **lỗi dữ liệu** (nằm trong `issues`/`excluded_rows`, script vẫn chạy thành công) với **lỗi thực thi** (exit khác 0).

## Viết báo cáo

1. Đọc template `references/report-template.md` trong thư mục skill này, tức `skills/csv-quality/references/report-template.md`.
2. Lấy mọi con số từ JSON của script, kể cả tổng giờ. Không tự cộng lại, không cộng thêm dòng trong `excluded_rows`, không tự so sánh lại với ngưỡng.
3. Ghi rõ ngưỡng đã dùng (`max_hours`), tổng giờ từng owner, danh sách người quá tải (hoặc "Không có"), và từng dòng bị loại kèm **tất cả** lý do theo bảng mã lý do trong template. Line number tính header là line 1.
4. Nêu rõ tổng giờ chỉ tính trên các dòng hợp lệ; các dòng bị loại cần sửa dữ liệu nguồn trước khi được tính.
5. Không sửa file CSV khi người dùng chỉ yêu cầu kiểm tra. Có thể đề xuất cách sửa trong mục khuyến nghị.
6. Ghi báo cáo bằng `write_file` vào đường dẫn người dùng yêu cầu (mặc định `output/csv-quality.md`), rồi trả lời đường dẫn và tóm tắt ngắn: ngưỡng, tổng giờ từng người, ai quá tải.

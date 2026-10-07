# Báo cáo chất lượng dữ liệu và khối lượng công việc: `{đường dẫn CSV}`

Công cụ: `skills/csv-quality/scripts/check_csv.py` | ngưỡng `--max-hours`: {max_hours} | exit code: {exit_code}

## Tổng quan
| Chỉ số | Giá trị |
|---|---|
| Số dòng dữ liệu (không tính header) | {row_count} |
| Dòng thiếu owner | {missing_owner_count} |
| Dòng hours không hợp lệ | {invalid_hours_count} |
| Số task_id bị lặp (distinct) | {duplicate_id_count} ({duplicate_ids}) |
| Số dòng bị loại khỏi tổng giờ | {số phần tử excluded_rows} |

## Tổng giờ theo owner
Chỉ cộng các dòng hợp lệ (không nằm trong mục "Dòng bị loại").

| Owner | Tổng giờ | Quá tải (> {max_hours} giờ)? |
|---|---|---|
| {owner} | {total_hours} | {Có / Không} |

## Người quá tải
- {owner}: {total_hours} giờ (ngưỡng {max_hours} giờ)
- Nếu `overloaded_owners` rỗng: "Không có ai quá tải (tổng giờ bằng ngưỡng không tính là quá tải)."

## Dòng bị loại
| Line | task_id | Lý do |
|---|---|---|
| {line} | {task_id hoặc "(trống)"} | {tất cả lý do, theo bảng mã bên dưới} |

Bảng mã lý do:
| Mã | Ý nghĩa |
|---|---|
| `wrong_field_count` | Số trường khác số cột của header |
| `missing_task_id` | task_id trống |
| `duplicate_id` | task_id đã xuất hiện ở dòng trước (chỉ giữ lần đầu, kể cả khi lần đầu không hợp lệ) |
| `missing_owner` | owner trống |
| `invalid_hours` | hours không phải số hữu hạn không âm |

## Chi tiết lỗi chất lượng
| Line | Cột | Loại | task_id | Mô tả |
|---|---|---|---|---|
| {line} | {column} | {type} | {task_id} | {message} |

## Đánh giá
- Tổng giờ ở trên chỉ phản ánh các dòng hợp lệ. Nêu rõ số dòng bị loại và ảnh hưởng có thể có tới kết luận quá tải (ví dụ owner trống chưa được tính cho ai).

## Khuyến nghị
- {Cách sửa đề xuất cho từng nhóm lỗi; không tự sửa file nguồn}

# Analysis Block 2: Workload Check by Person

Model dùng khi chạy: `openai/gpt-oss-120b` qua Groq (OpenAI-compatible endpoint). Ngày chạy: 2026-10-07.
Môi trường: stage-03 và stage-04 chạy trong WSL2 Ubuntu (tool `bash` cần môi trường POSIX theo README của lab).

## 1. Thay đổi đã thực hiện

| File (trong `stage-04-script-skill/`) | Thay đổi |
|---|---|
| `fixtures/skills/csv-quality/scripts/check_csv.py` | Thêm tham số bắt buộc `--max-hours` (số hữu hạn không âm, sai/thiếu → stderr + exit 2). Thêm `max_hours`, `hours_by_owner`, `overloaded_owners`, `excluded_rows` vào JSON; giữ nguyên các trường cũ (`row_count`, `issues`, …) và cách báo lỗi exit 1 |
| `fixtures/skills/csv-quality/SKILL.md` | Mô tả trigger thêm "tổng giờ / quá tải"; mục mới "Xác định ngưỡng" (thiếu ngưỡng → hỏi lại và dừng); lệnh có `--max-hours`; mô tả 4 trường JSON mới và exit 2; bỏ quy tắc cũ "không tính tổng giờ khi còn dữ liệu lỗi", thay bằng "lấy tổng giờ từ JSON, không tự cộng lại" |
| `fixtures/skills/csv-quality/references/report-template.md` | Thêm mục ngưỡng, tổng giờ theo owner, người quá tải, dòng bị loại kèm lý do và bảng giải nghĩa mã lý do |
| `workspace/skills/csv-quality/` | Bản đồng bộ y hệt `fixtures/skills/csv-quality/` (`diff -r` không khác biệt) |
| `fixtures/data/workload.csv`, `fixtures/data/workload-edge.csv` (+ bản trong `workspace/data/`) | Dữ liệu đầu vào theo đề |
| `tests/test_check_csv.py` | `run()` truyền `--max-hours`; thêm 4 test + 6 case tham số sai (xem mục 2) |
| `tests/test_agent.py` | Lệnh mẫu thêm `--max-hours 8` |

`stage-03-bash`: chỉ thêm `data/workload.csv` vào `fixtures/` và `workspace/`, không sửa code.

Quy tắc cài trong script:
- Một dòng được cộng khi: đúng số trường, `task_id` không rỗng, không trùng, `owner` không rỗng, `hours` là số hữu hạn không âm.
- Mỗi `task_id` chỉ giữ lần xuất hiện đầu tiên trong file, **kể cả khi lần đầu không hợp lệ**. Biến `first_seen` ghi nhận ID ngay lần gặp đầu tiên, trước khi xét các lỗi khác.
- Mỗi dòng bị loại xuất hiện một lần trong `excluded_rows`, kèm tất cả lý do theo thứ tự `wrong_field_count`, `missing_task_id`, `duplicate_id`, `missing_owner`, `invalid_hours`.
- Quá tải khi tổng giờ **lớn hơn** ngưỡng (`total > max_hours`); bằng ngưỡng không phải quá tải.

## 2. Kết quả kiểm thử tự động

Lệnh: `uv run pytest` trong từng stage (WSL, mock model, không gọi API).

| Stage | Kết quả |
|---|---|
| stage-03-bash | 48 passed |
| stage-04-script-skill | 71 passed (trong đó `tests/test_check_csv.py`: 22 passed) |

Test mới trong `tests/test_check_csv.py`:

| Test | Kiểm tra |
|---|---|
| `test_workload_threshold_8_lan_overloaded` | Lan 9, Minh 3; chỉ Lan quá tải; loại dòng 5/6/7; trường cũ vẫn còn |
| `test_workload_threshold_equal_is_not_overloaded` | Ngưỡng 9: Lan = 9 không quá tải |
| `test_first_id_with_invalid_hours_still_blocks_later_duplicate` | **Trường hợp đặc biệt**: `workload-edge.csv`, ngưỡng 0 → chỉ Minh 0 giờ; dòng 2 `invalid_hours`, dòng 3 `duplicate_id` |
| `test_excluded_row_lists_all_reasons_in_fixed_order` | Một dòng nhiều lỗi xuất hiện một lần, đủ lý do, đúng thứ tự |
| `test_missing_or_invalid_max_hours_rejected` (6 case) | Thiếu, `-1`, `abc`, `nan`, `inf`, rỗng → exit khác 0, stdout rỗng, stderr nhắc `--max-hours` |

## 3. JSON khi chạy script trực tiếp

Lưu tại `block2-evidence/`:

| File | Lệnh | Kết quả chính |
|---|---|---|
| `workload-max8.json` | `--input data/workload.csv --max-hours 8` | `hours_by_owner` = {Lan: 9, Minh: 3}; `overloaded_owners` = [Lan 9]; `excluded_rows` = dòng 5 `invalid_hours`, dòng 6 `duplicate_id`, dòng 7 `missing_owner` |
| `workload-max9.json` | `--input data/workload.csv --max-hours 9` | Tổng giờ như trên; `overloaded_owners` = [] |
| `workload-edge-max0.json` | `--input data/workload-edge.csv --max-hours 0` | `hours_by_owner` = {Minh: 0}; `overloaded_owners` = []; dòng 2 E01 `invalid_hours`, dòng 3 E01 `duplicate_id` |

Lỗi tham số và lỗi file (chạy trực tiếp):

| Lệnh | Exit | stderr |
|---|---|---|
| không có `--max-hours` | 2 | `the following arguments are required: --max-hours` |
| `--max-hours -1` / `abc` / `nan` | 2 | `argument --max-hours: phải là số hữu hạn không âm, nhận được '…'` |
| `--input data/khong-co.csv --max-hours 8` | 1 | `ERROR: Không đọc được file data/khong-co.csv: No such file or directory` |

## 4. Kết quả từng trường hợp

Mỗi dòng trong trace là một event có `sequence` (#). Trace không lưu nội dung câu trả lời cuối; nội dung xem ở ảnh trong `screenshots/`. Mã conversation trên ảnh trùng với phần thứ hai trong tên file trace.

### Stage 03: Model tự viết Python qua Bash

- Lượt 1: `stage-03-bash/traces/20261007-162623_4fbf4381_turn01_1c783460.jsonl`
  - #2 → #4: 1 model call, **0 tool call**. Model được cấp tool `bash` nhưng chỉ viết code ra câu trả lời, không chạy, không đọc file. Mọi con số trong câu trả lời là suy đoán.
- Lượt 2 (nhắc "hãy thực sự chạy code"): `stage-03-bash/traces/20261007-162917_4fbf4381_turn02_3a210fc5.jsonl`
  - #4 `bash` chạy một đoạn Python inline; #5 `exit_code` 0, stdout `Lan: 14.00 hours`, `Minh: 3.00 hours`.
- Các dòng được cộng: 2 (T01 Lan 4), 3 (T02 Lan 5), 4 (T03 Minh 3) và **dòng 6 (T02 Lan 5, trùng)**. Dòng 5 (`abc`) và dòng 7 (owner trống) bị bỏ qua đúng.
- **Lan = 14 là sai, đúng phải là 9. Dòng bị cộng trùng là dòng 6** (`T02,Lan,5`). Đoạn lệnh của model phát hiện được ID trùng nhưng vẫn cộng:
  ```python
  if task_id in seen_task:
      sys.stderr.write(f"[INFO] Dòng {i}: task_id {task_id} đã xuất hiện → cộng thêm hours\n")
  seen_task.add(task_id)
  owner_hours[owner] += hrs   # thiếu `continue` sau khi phát hiện trùng
  ```
- Kết luận: khi model tự viết code, quy tắc nghiệp vụ (ID trùng có được cộng không) do model tự quyết, nên có thể sai và không ổn định giữa các lần chạy.

### Ngưỡng 8

- Trace: `stage-04-script-skill/traces/20261007-163836_ef110d79_turn01_1a73bf0b.jsonl` | Ảnh: `screenshots/b2-max8.png` (conversation `ef110d79`)
- Bằng chứng: #4 đọc `SKILL.md`; #8 đọc `report-template.md`; #12 `bash`: `python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 8`; #13 `exit_code` 0; #16 `write_file output/workload-max8.md`.
- Báo cáo agent: `block2-evidence/workload-max8.md`. Lan 9 giờ (quá tải), Minh 3 giờ; loại dòng 5 `invalid_hours`, 6 `duplicate_id`, 7 `missing_owner`.
- Kết luận: **đúng**.

### Ngưỡng 9

- Trace: `stage-04-script-skill/traces/20261007-164016_593887ed_turn01_11182a4c.jsonl` | Ảnh: `screenshots/b2-max9.png` (conversation `593887ed`)
- Bằng chứng: #4 đọc `SKILL.md`; #8 `bash` với `--max-hours 9`; #9 `exit_code` 0; #12 đọc template; #16 `write_file output/workload-max9.md`.
- Báo cáo agent: `block2-evidence/workload-max9.md`. Lan 9, Minh 3; không ai quá tải ("tổng giờ bằng ngưỡng không tính là quá tải"); cùng 3 dòng bị loại.
- Kết luận: **đúng**.

### Thiếu ngưỡng

- Trace: `stage-04-script-skill/traces/20261007-164142_75bccae8_turn01_076f0d2f.jsonl` | Ảnh: `screenshots/b2-no-threshold.png` (conversation `75bccae8`)
- Input: "Kiểm tra xem ai bị quá tải trong data/workload.csv."
- Bằng chứng: #4 đọc `SKILL.md`, rồi #8 kết thúc. **Không có lệnh bash nào**, nên script không được chạy với ngưỡng tự đoán.
- Câu trả lời: agent hỏi người dùng muốn đặt ngưỡng bao nhiêu giờ (`--max-hours`) trước khi kiểm tra.
- Kết luận: **đúng** theo mục "Xác định ngưỡng" của skill.

### File không tồn tại

- Trace: `stage-04-script-skill/traces/20261007-164351_96382cf9_turn01_75a4a923.jsonl` | Ảnh: `screenshots/b2-missing-file.png` (conversation `96382cf9`)
- Bằng chứng: #4 đọc `SKILL.md`; #8 `bash`: `check_csv.py --input data/khong-ton-tai.csv --max-hours 8`; #9 `exit_code` **1**, `stdout` rỗng, stderr `ERROR: Không đọc được file data/khong-ton-tai.csv: No such file or directory`.
- Câu trả lời: báo lỗi file không tồn tại, không đưa ra số liệu, không ghi báo cáo.
- Kết luận: **đúng**.
- Lần chạy trước của cùng input: `stage-04-script-skill/traces/20261007-164201_f60ec3fc_turn01_729d9f1b.jsonl` (ảnh `screenshots/b2-missing-file-shortcut.png`). Model **không nạp skill**: #4 `read_file data/khong-ton-tai.csv`, #5 `FILE_NOT_FOUND`, rồi trả lời. Kết quả vẫn an toàn (không bịa số liệu) nhưng bỏ qua quy trình của skill. Chạy lại 3 lần sau đó (1 lần trên app là trace ở trên, 2 lần gọi agent trực tiếp nên không ghi trace), cả 3 lần agent đều nạp skill và chạy script. Vậy đây là hành vi không ổn định của model, không phải lỗi script.

## 5. Phần nào do script tính, phần nào do model diễn giải?

| Script tính (máy, xác định) | Model diễn giải (LLM) |
|---|---|
| Đọc CSV, kiểm tra số trường, ID rỗng, ID trùng, owner rỗng, hours hợp lệ | Hiểu yêu cầu, nhận ra cần skill `csv-quality` |
| Quyết định dòng nào được cộng, dòng nào bị loại và vì sao (`excluded_rows`) | Xác định người dùng đã cho ngưỡng chưa; thiếu thì hỏi lại |
| Cộng tổng giờ theo owner (`hours_by_owner`) | Đưa đúng ngưỡng vào `--max-hours` |
| So sánh với ngưỡng, lập danh sách quá tải (`overloaded_owners`) | Đọc `exit_code`/`stderr` để phân biệt lỗi thực thi với lỗi dữ liệu |
| Kiểm tra tham số `--max-hours`, báo lỗi file/cột/parse bằng exit code | Điền JSON vào template, dịch mã lý do sang lời giải thích, viết đánh giá và khuyến nghị sửa dữ liệu |

Stage 03 cho thấy lý do phải chia như vậy. Khi model tự viết code, nó tự quyết định quy tắc ID trùng và cộng sai (Lan 14). Ở lượt đầu, nó còn không chạy code. Sau khi đưa quy tắc vào script, cả 4 trường hợp đều cho cùng con số với test tự động.

## 6. Nếu sửa script nhưng không cập nhật skill và reference

- **Lệnh chạy sai:** `SKILL.md` cũ chỉ có `--input`. Agent làm theo sẽ gọi script thiếu `--max-hours`, nhận exit 2 và không có kết quả. Skill cũ chỉ mô tả exit 0/1, nên agent có thể hiểu nhầm lỗi tham số là lỗi file.
- **Không hỏi ngưỡng:** skill cũ không có quy tắc hỏi lại ngưỡng. Agent có thể tự chọn một ngưỡng (8, 40…) và kết luận quá tải dựa trên con số người dùng chưa từng đưa ra.
- **Bỏ qua hoặc tính lại tổng giờ:** skill cũ ghi "Không tính tổng giờ hay KPI khi còn dữ liệu lỗi". Agent sẽ từ chối báo cáo tổng giờ dù script đã tính đúng, hoặc tự cộng lại từ CSV và có thể lặp lại lỗi của Stage 03 (cộng trùng dòng 6).
- **Báo cáo thiếu thông tin:** template cũ không có mục ngưỡng, tổng giờ theo owner, người quá tải, dòng bị loại. Báo cáo sẽ thiếu đúng những phần người dùng hỏi; mã lý do như `duplicate_id` không được giải nghĩa; quy tắc "bằng ngưỡng không phải quá tải" không được nêu nên người đọc dễ hiểu nhầm Lan (9 giờ, ngưỡng 9) là quá tải.
- **Mô tả trigger lỗi thời:** `description` cũ chỉ nói "kiểm tra chất lượng CSV". Câu hỏi "ai bị quá tải" có thể không kích hoạt skill, khiến model tự viết code như Stage 03.

Script chỉ đảm bảo **con số** đúng. Skill và reference đảm bảo agent **gọi script đúng cách và trình bày đầy đủ, đúng nghĩa** những con số đó. Thiếu một trong hai thì báo cáo vẫn có thể sai.

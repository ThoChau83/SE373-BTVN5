# Analysis: Policy Document Retrieval

Model dùng khi chạy: `openai/gpt-oss-120b` qua Groq (OpenAI-compatible endpoint). Ngày chạy: 2026-10-07.

## 1. Thay đổi đã thực hiện

| Stage | File | Thay đổi |
|---|---|---|
| 01, 02 | `tools/files.py` | Thêm `_list()` và tool `list_files(path)` |
| 01, 02 | `tools/__init__.py`, `agent.py` | Export và đăng ký: `TOOLS = [read_file, write_file, list_files]` |
| 01, 02 | `prompts.py`, `config.py` | Mô tả `list_files` trong system prompt và trên UI |
| 01, 02 | `tests/test_files.py` | 8 test mới cho `list_files` |
| 01, 02 | `tests/test_agent.py`, `tests/test_app.py` | Cập nhật số tool 2 → 3 |
| 02 | `fixtures/data/policies/`, `workspace/data/policies/` | `policy-before-oct.md`, `policy-from-oct.md` |
| 02 | `fixtures/skills/refund-policy/`, `workspace/skills/refund-policy/` | `SKILL.md`, `references/answer-template.md` |
| 02 | `tests/test_skill_catalog.py`, `tests/test_project.py`, `tests/test_app.py` | Cập nhật catalog 1 → 2 skill |

`list_files` tái sử dụng `_resolve()` có sẵn nên dùng chung quy tắc chặn đường dẫn với `read_file`: đường dẫn tuyệt đối, `~`, `..` và symlink trỏ ra ngoài workspace đều bị chặn.

## 2. Kết quả kiểm tra tool

Lệnh: `uv run pytest` trong từng stage (dùng mock model, không gọi API).

| Stage | Kết quả |
|---|---|
| stage-01-files | 40 passed, 2 failed |
| stage-02-skills | 47 passed, 2 failed |

2 test fail ở cả hai stage là `test_read_symlink_escape_blocked` và `test_write_absolute_and_symlink_escape_rejected`. Hai test này có sẵn trong repo và đã fail trước khi sửa code. Nguyên nhân: tạo symlink trên Windows cần quyền admin (`OSError: [WinError 1314] A required privilege is not held by the client`). Hai test này không liên quan đến `list_files`.

Test mới cho `list_files`:

| Test | Kiểm tra |
|---|---|
| `test_list_direct_children_sorted_without_recursion` | Trả `name`, `path`, `type`; sắp xếp theo tên; không liệt kê `data/sub/deep.md` (không đệ quy) |
| `test_list_workspace_root` | `"."` liệt kê gốc workspace |
| `test_list_missing_path_and_file_path` | Thư mục không tồn tại → `PATH_NOT_FOUND`; truyền vào file → `NOT_A_DIRECTORY` |
| `test_list_outside_workspace_blocked` (5 case) | `..`, `../`, `data/../..`, `/etc`, `~` → `PATH_OUTSIDE_WORKSPACE` |
| `test_tools_return_json_against_project_workspace` | Tool `list_files` trả JSON trên workspace thật của project |

Kiểm tra với model thật:

| Trace | Bằng chứng |
|---|---|
| `stage-01-files/traces/20261007-155821_3fb7e13a_turn01_1a3aad14.jsonl` | Câu hỏi "Trong thư mục data có những file nào?". #4 `list_files {"path": "data"}`, #5 `ok: true`, trả `weekly_notes.md` |
| `stage-01-files/traces/20261007-155855_3fb7e13a_turn02_b7fd1454.jsonl` | Câu hỏi "Liệt kê thư mục ../". Model từ chối theo system prompt, không gọi tool (#2 → #4). Việc chặn ở tầng tool được chứng minh bằng `test_list_outside_workspace_blocked` |

## 3. Kết luận từng trường hợp

Ghi chú về trace: mỗi dòng trong trace là một event có `sequence` (#). Trace ghi tool call, arguments và result, nhưng không lưu nội dung câu trả lời cuối (chỉ có `answer_chars`). Nội dung câu trả lời xem ở ảnh chụp màn hình trong `screenshots/`. Mã conversation trên ảnh trùng với 8 ký tự thứ hai trong tên file trace.

### Stage 00: Agent chưa có tool

- Trace: `stage-00-chat/traces/20261007-161519_73e74cc9_turn01_353f3070.jsonl`
- Ảnh: `screenshots/stage00.png` (conversation `73e74cc9`)
- Input: Case A (mua 28/09/2026, yêu cầu 06/10/2026, chưa kích hoạt), không kèm nội dung chính sách.
- Bằng chứng: 1 model call, 0 tool call; #3 `model_response` có `tool_calls_requested: []`.
- Câu trả lời: agent nói cần biết quy định hoàn tiền của công ty ("trong vòng X ngày…") và yêu cầu người dùng cung cấp chính sách.
- Kết luận: agent không có cách nào tự đọc chính sách nên không kết luận được. Người dùng phải dán chính sách vào prompt. Đây là giới hạn cần khắc phục.

### Case A: Mua 28/09/2026, yêu cầu 06/10/2026, chưa kích hoạt

- Trace: `stage-02-skills/traces/20261007-161555_ca6b3120_turn01_1592943c.jsonl`
- Ảnh: `screenshots/case-a.png` (conversation `ca6b3120`)
- Bằng chứng (6 model call, 5 tool call):
  - #4 `list_files {"path": "data/policies"}`, #5 → `policy-before-oct.md`, `policy-from-oct.md`
  - #8 `read_file skills/refund-policy/SKILL.md` (nạp skill)
  - #12, #16 đọc cả 2 chính sách; #20 đọc `answer-template.md`
- Câu trả lời: chính sách `data/policies/policy-before-oct.md`; 8 ngày, thời hạn 7 ngày; chưa kích hoạt; **không được hoàn tiền**; phí: không áp dụng.
- Kết luận: **đúng**.

### Case B: Mua 02/10/2026, yêu cầu 12/10/2026, chưa kích hoạt

- Trace: `stage-02-skills/traces/20261007-161633_88e3b0b0_turn01_2d229d93.jsonl`
- Ảnh: `screenshots/case-b.png` (conversation `88e3b0b0`)
- Bằng chứng (6 model call, 5 tool call): chuỗi tool call giống Case A (#4 `list_files`, #8 SKILL.md, #12/#16 hai chính sách, #20 template).
- Câu trả lời: chính sách `data/policies/policy-from-oct.md` vì ngày mua thuộc "Áp dụng cho ngày mua từ 2026-10-01, bao gồm ngày này"; 10 ngày, thời hạn 14 ngày; **được hoàn tiền, không thu phí**.
- Kết luận: **đúng**.

### Case C: Thiếu thông tin

- Trace: `stage-02-skills/traces/20261007-161707_d44f1cac_turn01_871bce15.jsonl`
- Ảnh: `screenshots/case-c.png` (conversation `d44f1cac`)
- Input: "Khách mua ngày 02/10/2026, muốn hoàn tiền. Được không?" (thiếu ngày yêu cầu và trạng thái kích hoạt).
- Bằng chứng (3 model call, 2 tool call): #4 `list_files data/policies`, #8 đọc `SKILL.md`, sau đó #11 trả lời mà không đọc chính sách nào.
- Câu trả lời: agent yêu cầu bổ sung (1) ngày yêu cầu hoàn tiền, (2) sản phẩm đã kích hoạt chưa; không đưa ra kết luận.
- Kết luận: **đúng** theo bước 1 của skill ("thiếu thông tin thì hỏi lại và dừng; không tự giả định").

### Case D: Đổi tên file chính sách

- Thao tác: đổi `policy-before-oct.md` thành `chinhsachcu.md`, `policy-from-oct.md` thành `chinhsachmoi.md`, rồi chạy lại input Case B.
- Trace: `stage-02-skills/traces/20261007-161847_78965cf7_turn01_e986ddbb.jsonl`
- Ảnh: `screenshots/case-d.png` (conversation `78965cf7`)
- Bằng chứng (7 model call, 6 tool call):
  - #8 đọc `SKILL.md`
  - #12 `list_files {"path": "data/policies"}`, #13 → `chinhsachcu.md`, `chinhsachmoi.md` (tên mới)
  - #16, #20 đọc đúng 2 file tên mới; không có lần `read_file` nào dùng tên cũ, không có lỗi `FILE_NOT_FOUND`
- Câu trả lời: chính sách `data/policies/chinhsachmoi.md` (tiêu đề "Chính sách hoàn tiền từ tháng 10"); 10 ngày, thời hạn 14 ngày; **được hoàn tiền, không thu phí**. Kết quả giống hệt Case B.
- Kết luận: **đúng**. Agent thích nghi được vì skill yêu cầu khám phá file bằng `list_files` và chọn chính sách theo nội dung ("Áp dụng cho ngày mua ..."), không theo tên file.
- Lần chạy trước (không có ảnh) với bộ tên khác `chinh-sach-cu.md` / `chinh-sach-moi.md` cũng cho chuỗi tool call tương tự: `stage-02-skills/traces/20261007-161003_96620556_turn01_42fff88b.jsonl` (#8 `list_files` → tên mới, #12/#16 đọc đúng 2 file).
- Sau test, tên file đã được khôi phục về `policy-before-oct.md`, `policy-from-oct.md`.

## 4. Vì sao cần cả tool khám phá file lẫn skill chọn chính sách?

Hai thành phần giải quyết hai vấn đề khác nhau:

- **Tool `list_files` cho agent khả năng.** Trước khi có tool, agent chỉ có `read_file`, mà `read_file` cần biết trước tên file. Agent hoặc phải được người dùng báo tên file, hoặc phải đoán. Có `list_files`, agent tự xem trong `data/policies/` đang có gì tại thời điểm chạy.
- **Skill `refund-policy` cho agent quy trình.** Biết có những file nào chưa đủ. Agent còn cần biết phải tìm ở đâu, chọn chính sách theo tiêu chí gì (ngày mua, đọc từ nội dung file), thiếu thông tin thì làm gì, tính số ngày ra sao, trả lời theo mẫu nào và tự kiểm tra gì trước khi trả lời. Skill chỉ nạp khi câu hỏi liên quan đến hoàn tiền (Case C, D cho thấy agent đọc `SKILL.md` khi cần), nên không làm phình system prompt.

**Chỉ sửa prompt có xử lý được việc đổi tên file không? Không.** Nếu prompt ghi "đọc `policy-before-oct.md` khi ngày mua trước 01/10", thì khi file đổi tên (Case D), `read_file` sẽ trả `FILE_NOT_FOUND` và agent không biết tên mới. Mỗi lần đổi tên hoặc thêm chính sách lại phải sửa prompt. Prompt chỉ là văn bản tĩnh, không quan sát được trạng thái hiện tại của thư mục. Chỉ có tool mới làm được việc đó, và chỉ khi quy tắc chọn dựa vào nội dung thay vì tên file thì kết quả mới đúng dù tên file thay đổi.

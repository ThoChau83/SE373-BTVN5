---
name: refund-policy
description: Trả lời yêu cầu hoàn tiền của khách hàng bằng cách tìm các chính sách hoàn tiền trong data/policies/, chọn đúng chính sách theo ngày mua, tính số ngày đã qua và kết luận có được hoàn tiền không, phí bao nhiêu. Dùng khi người dùng hỏi về hoàn tiền, trả hàng lấy lại tiền hoặc refund.
---

# Refund policy

Hướng dẫn chọn chính sách hoàn tiền và kết luận một yêu cầu hoàn tiền.

## Các bước

1. Kiểm tra người dùng đã cung cấp đủ 3 thông tin: **ngày mua**, **ngày yêu cầu hoàn tiền**, **sản phẩm đã kích hoạt hay chưa**. Nếu thiếu, hỏi lại đúng những thông tin còn thiếu và dừng; không tự giả định.
2. Gọi `list_files` với `data/policies` để biết hiện có những file chính sách nào. Không đoán tên file; tên file có thể thay đổi.
3. Đọc từng file chính sách bằng `read_file`. Chọn chính sách theo **phạm vi ngày mua ghi trong nội dung file** (dòng "Áp dụng cho ngày mua ..."), không theo tên file. Nếu không có chính sách nào khớp hoặc có nhiều hơn một chính sách khớp, báo cho người dùng và dừng.
4. Tính số ngày đã qua = ngày yêu cầu hoàn tiền − ngày mua, đếm theo lịch. Ví dụ: mua 28/09/2026, yêu cầu 06/10/2026 → 2 ngày còn lại của tháng 9 (29, 30) + 6 ngày tháng 10 = 8 ngày. Ngày người dùng nhập thường theo dạng dd/mm/yyyy, ngày trong chính sách theo dạng yyyy-mm-dd.
5. Kết luận theo đúng chính sách đã chọn:
   - Sản phẩm đã kích hoạt → **không được hoàn tiền**.
   - Số ngày đã qua lớn hơn thời hạn → **không được hoàn tiền**.
   - Còn lại → **được hoàn tiền**, kèm mức phí theo chính sách.
6. Đọc `references/answer-template.md` trong thư mục skill này, tức `skills/refund-policy/references/answer-template.md`, và trả lời đúng các mục của template.
7. Trước khi trả lời, tự kiểm tra: file chính sách nêu trong câu trả lời là file đã đọc thành công ở bước 3; tính lại số ngày lần hai và khớp với bước 4; kết luận khớp với thời hạn và trạng thái kích hoạt; nếu không được hoàn tiền thì mục phí ghi "Không áp dụng". Chỉ trả lời khi mọi mục đều khớp.

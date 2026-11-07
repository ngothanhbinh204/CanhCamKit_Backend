# Bàn giao page: [page-slug]

> Kit version: `2.2.0`. Copy thành `handoffs/[page-slug].md` tại gốc theme. Main agent ghi Đầu vào, Mapping đã duyệt và Review từ stdout. ACF builder/coder chỉ ghi mục được giao. Lệch `KIT_VERSION` thì dừng page để đồng bộ.

## Đầu vào và phạm vi

- HTML nguồn: `UI/[TenTrang].html`
- Loại page: [Page Template / Archive / Single / Taxonomy / Tiện ích]
- Template và ACF dự kiến: [đường dẫn hoặc “không áp dụng”]
- ACF key namespace: [`group_page_{page_key}`; tiền tố field `field_{page_key}_{section}_*`]
- Phụ thuộc chung đã có (Tầng 1–3): [CPT, taxonomy, helper, shared section, atomic card]
- Overlay/biến thể đã đọc: [`PROJECT_OVERRIDES.md`; mã VAR đã duyệt hoặc “không có”]
- File được phép sửa trong bước hiện tại: [danh sách]
- File chung cần main agent phân công: [danh sách hoặc “không có”]

## Mapping — `wp-architect`

| Section (CSS class đầu tiên) | Tầng component | ACF Tab / không áp dụng | File dự kiến | Nguồn dữ liệu |
|---|---|---|---|---|
| [section] | [global/shared/card/page] | [tab] | [path] | [ACF/query/options] |

- DOM & JS hooks cần bảo toàn: [Swiper, Fancybox, GSAP, Tabs, `data-*` quan sát từ HTML]
- Câu hỏi còn mở: [đánh số, chỉ các quyết định ảnh hưởng triển khai]
- Quyết định đã có từ dự án: [liên kết hoặc mô tả ngắn]
- Kết quả duyệt mapping: [Chưa duyệt / Đã duyệt bởi người dùng, ngày / Cần sửa]
- Bàn giao cho ACF: [tên field, tiền tố key `field_{page_key}_*`, nguồn dữ liệu, vị trí binding và ngoại lệ cần lưu ý]

## ACF — `acf-builder`

- Đầu vào đã duyệt: [mapping và quyết định]
- File JSON tạo/sửa: [đường dẫn hoặc “không áp dụng”]
- Tiền tố `field_key` đã áp dụng: [`field_{page_key}_{section}_*`]
- Field quan trọng và return format: [tên, kiểu, định dạng]
- Kiểm tra đã chạy và output (`verify_theme.py --acf`): [lệnh + output thật; nếu chưa chạy ghi `[NOT RUN]`]
- Điểm còn mở / cần main xử lý: [nếu có]
- Bàn giao cho coder: [JSON, tên field và cấu trúc repeater/relationship]

## Code — `wp-coder`

- File tạo/sửa: [danh sách]
- File chung đã được main phân quyền: [danh sách hoặc “không có”]
- Hành vi dữ liệu rỗng/fallback & bảo toàn DOM/JS: [mô tả ngắn]
- Kiểm tra đã chạy và output (`php -l` & `verify_theme.py --html ... --php ...`): [lệnh + output thật; nếu chưa chạy ghi `[NOT RUN]`]
- Điểm còn mở / cần main xử lý: [nếu có]
- Bàn giao cho reviewer: [file, hành vi và trường hợp cần kiểm tra]

## Review — `wp-reviewer`

- Phạm vi và biến thể áp dụng: [file và mã VAR đã ghi nhận, nếu có]
- Kết quả: `[PASS]` / `[ACTION REQUIRED]` / `[BLOCKED]` / `[NOT RUN]`
- Bằng chứng kiểm tra: [mỗi lệnh `php -l`, `verify_theme.py`, `rg` và output thật; phạm vi file đã quét]
- Edge cases cần WordPress runtime: [đã chạy + output / `[NOT RUN]` + lý do]
- Lỗi cần sửa: [mã ZTR-01..18, file:dòng, cách tái hiện, hướng sửa]
- Bước kế tiếp: [DONE / REWORK / chờ điều kiện cụ thể]

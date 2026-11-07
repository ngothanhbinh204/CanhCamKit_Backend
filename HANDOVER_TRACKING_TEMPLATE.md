# Theo dõi pipeline nhiều page

> **Dự án:** [Tên dự án]
> **Theme:** `canhcamtheme`
> **Cập nhật:** [YYYY-MM-DD HH:mm]
> **Chủ sở hữu file:** Main agent. ACF builder/coder chỉ cập nhật mục được giao trong `handoffs/{page-slug}.md`; architect/reviewer trả stdout để main ghi.
> **Kit version:** `2.2.0`. Main đối chiếu `KIT_VERSION` và version trong từng handoff trước khi giao bước tiếp.

## 1. Cross-Page Inventory & Hợp đồng dùng chung (Wave 0 & Wave 1)

Chạy `python canhcam-agents-kit/scripts/verify_theme.py --inventory` trên `UI/*.html` để khóa danh sách bên dưới trước khi chạy song song từng page (Wave 2).

| Thành phần (Tầng 1–3) | Quyết định / file nguồn | Chủ sở hữu khi cần sửa | Page phụ thuộc | Trạng thái Foundation |
|---|---|---|---|---|
| CPT và taxonomy | [tên, slug, file đăng ký `inc/function-post-types.php`] | [main/worker được giao] | [page] | [Đã khóa / Chờ] |
| Global Modules (Tầng 1) | [`modules/common/banner.php`, `breadcrumb.php`, `popup-*.php`] | [main/worker được giao] | [page] | [Đã khóa / Chờ] |
| Shared Sections (Tầng 2, $\ge 2$ page) | [`template-parts/shared/section-*.php` + `wp_parse_args`] | [main/worker được giao] | [page] | [Đã khóa / Chờ] |
| Atomic Cards (Tầng 3, 1 CPT = 1 Card) | [`template-parts/cards/card-*.php`] | [main/worker được giao] | [page] | [Đã khóa / Chờ] |
| ACF options / group chung | [tên field, file `acf-json/group_*.json`] | [main/worker được giao] | [page] | [Đã khóa / Chờ] |

Chỉ coi hợp đồng là đã chốt khi quyết định có trong code hoặc đã được người dùng duyệt. Page có phụ thuộc chưa chốt có thể tiếp tục mapping, nhưng chưa được tạo ACF hoặc code cần hợp đồng đó.

## 2. Hàng đợi và trạng thái page (Wave 2)

Trạng thái hợp lệ: `TODO`, `MAPPING`, `WAITING_APPROVAL`, `READY_ACF`, `ACF`, `READY_CODING`, `CODING`, `READY_REVIEW`, `REVIEW`, `REWORK`, `BLOCKED`, `DONE`. `READY_*` nghĩa là bước trước đã bàn giao đủ đầu vào và page có thể được giao ngay. `BLOCKED` phải ghi điều kiện mở khóa. `DONE` chỉ sau review `[PASS]` và output của mọi kiểm tra bắt buộc; `[NOT RUN]` không đủ để `DONE`.

| Ưu tiên | Page / HTML nguồn | Loại page | Trạng thái | Agent đang làm | Phụ thuộc / file chung | Handoff | Bước kế tiếp / điều kiện mở khóa |
|---|---|---|---|---|---|---|---|
| [1] | `UI/[Page].html` | [Page Template / Archive / Single / Taxonomy] | `TODO` | — | [chỉ phụ thuộc đã xác minh] | `handoffs/[page-slug].md` | Giao mapping |

Khi agent xong một bước, main cập nhật hàng đợi và giao tác vụ sẵn sàng tiếp theo. Page `WAITING_APPROVAL` không chặn page độc lập. Main đối chiếu diff với allowlist trước khi nhận bàn giao.

## 3. Tác vụ đang chạy và quyền sở hữu file chung

| Agent / vai trò | Page | Bước | File được phép sửa | Bắt đầu | Trạng thái |
|---|---|---|---|---|---|
| [agent] | [page] | [MAPPING/ACF/CODING/REVIEW] | [danh sách] | [giờ] | [đang làm/chờ] |

Không để hai agent cùng sửa một file chung. Nếu cần đổi chủ sở hữu, main chờ tác vụ hiện tại bàn giao và kiểm tra thay đổi trước khi giao tiếp.

## 4. Quyết định cần người dùng duyệt

| Page | Câu hỏi / lựa chọn | Ảnh hưởng | Trạng thái quyết định |
|---|---|---|---|
| [page] | [câu hỏi cụ thể] | [field, URL, taxonomy...] | [chờ / đã duyệt + nội dung] |

Main có thể gom câu hỏi của nhiều page vào một lượt. Chỉ chuyển page sang `READY_ACF` sau khi mapping và các quyết định bắt buộc đã được duyệt, hoặc có ủy quyền trước rõ ràng cho mapping không có câu hỏi mở. Ghi nguồn ủy quyền trong handoff.

## 5. Bàn giao phiên làm việc

- Đã hoàn tất: [page, file, bằng chứng review]
- Đang làm: [agent, page, bước, file đang sở hữu]
- Đang chờ: [page, câu hỏi hoặc phụ thuộc, người cần xử lý]
- Tác vụ sẵn sàng giao tiếp: [page và bước theo ưu tiên]
- Thay đổi ngoài pipeline cần bảo toàn: [file hoặc “không có”]

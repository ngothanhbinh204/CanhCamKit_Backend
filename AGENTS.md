# CanhCam agent rules

> Kit version: `2.2.0`. Khi cài hoặc nâng cấp, chạy `python canhcam-agents-kit/scripts/install_kit.py` (hoặc `--upgrade`) để tự động bung file ra **gốc theme/git root** cùng `KIT_VERSION`; thư mục `canhcam-agents-kit/` chỉ là nguồn phân phối. Nếu version trong handoff khác `KIT_VERSION`, dừng page đó và nhờ main chạy `install_kit.py --upgrade` để đồng bộ tài liệu.

## Nguồn sự thật và phạm vi đọc

- Code/theme hiện tại, HTML nguồn và quyết định người dùng là nguồn sự thật. Đọc `PROJECT_OVERRIDES.md` trước Blueprint; nếu thiếu quyết định cần cho bước hiện tại thì hỏi, không lấy giá trị ví dụ trong Blueprint làm cấu hình dự án.
- `CANHCAM_THEME_BLUEPRINT.md` chứa **một** schema mapping/ACF, chuẩn code, bảo toàn DOM và bảng ZTR. Đọc đúng mục: architect §2 (nhất là §2.3), §3.1 khi có taxonomy phân cấp, §6.2; ACF builder §6–7; coder §2.1, §8–9 và mục khác khi liên quan; reviewer §11 cùng `PROJECT_VARIANTS.md` nếu có. Không chép Blueprint vào prompt hay file agent.
- `HANDOVER_TRACKING.md` là bảng tổng, **chỉ main sửa**. Mỗi page có `handoffs/{page-slug}.md` theo `PAGE_HANDOFF_TEMPLATE.md`. Main ghi đầu vào, mapping đã duyệt và Review từ stdout; ACF builder/coder chỉ ghi đúng mục của mình sau khi được giao.

## Quy trình 3 Wave & State machine đa trang

1. **Wave 0 — Cross-Page Inventory:** Trước khi bóc tách từng page lẻ, main chạy `python canhcam-agents-kit/scripts/verify_theme.py --inventory` (hoặc quét `<section` toàn bộ `UI/*.html`) để nhận diện các khối xuất hiện ở $\ge 2$ trang (Tầng 1 Global / Tầng 2 Shared) và danh sách CPT/Taxonomy/Card (Tầng 3). Ghi vào bảng **Hợp đồng dùng chung** trong `HANDOVER_TRACKING.md`.
2. **Wave 1 — Foundation First:** Chốt và triển khai trước các thành phần dùng chung (`inc/function-post-types.php`, Options, `header.php`, `footer.php`, `modules/common/`, `template-parts/shared/`, `template-parts/cards/`, ACF group chung) để khóa interface contract (`wp_parse_args`).
3. **Wave 2 — Multi-Page Parallel Pipeline:** Từng page chạy theo state machine:
   `TODO → MAPPING → WAITING_APPROVAL → READY_ACF → ACF → READY_CODING → CODING → READY_REVIEW → REVIEW → DONE`; `BLOCKED` ghi điều kiện mở khóa, `REWORK` quay về owner của lỗi rồi review lại.

Chỉ main đổi state; chỉ chuyển khi handoff đã có đầu ra tương ứng. Không coi im lặng là duyệt. Chỉ bỏ `WAITING_APPROVAL` khi người dùng đã duyệt mapping hoặc đã ủy quyền trước rõ ràng cho đúng loại mapping không có câu hỏi mở.

Khi architect xong Page A, main giao ngay page chưa mapping tiếp theo nếu có; Page A đi tiếp khi đủ điều kiện. Tương tự cho ACF, coder, reviewer. Page chờ duyệt không khóa page khác. Khởi đầu với 2–3 worker theo sức chứa thực tế, tối đa **hai worker ghi code/JSON** cùng lúc. Không tạo worker rảnh chỉ để đủ vai trò.

File chung (`functions.php`, `inc/`, `modules/common/`, `template-parts/shared/`, `template-parts/cards/`, header/footer, ACF group chung) chỉ có một owner tại một thời điểm. Worker không sửa file ngoài allowlist; nếu cần, dừng phần đó và báo main. Sau mỗi worker, main đối chiếu **diff và file mới chưa track** với allowlist, không hợp nhất âm thầm file ngoài phạm vi.

## Hợp đồng spawn bắt buộc

Worker có thể bắt đầu từ ngữ cảnh riêng; **mỗi lệnh giao việc phải tự đủ thông tin**. Thiếu một mục dưới đây thì main bổ sung trước khi spawn, hoặc tự xử lý trong cùng luồng. Không dùng isolated Git worktree/Antigravity `branch` cho pipeline chia sẻ handoff này; Antigravity dùng workspace `inherit` hoặc `share`, Codex dùng cùng theme workspace. Cấu hình native nằm trong `.codex/agents/` hoặc `.agents/agents/`.

```text
Kit version: [đọc KIT_VERSION]
Vai trò và bước: [tên native; MAPPING/ACF/CODING/REVIEW]
Page và HTML: [slug; UI/....html]
Handoff: handoffs/[slug].md; mục [Mapping/ACF/Code/Review]; ghi file hay stdout-only
Được sửa: [danh sách path chính xác hoặc “không file”]
Cấm: [file/nhóm file ngoài allowlist, nhất là HANDOVER_TRACKING.md và file chung]
Quyết định đã duyệt: [nội dung hoặc “chưa, chỉ phân tích”]
Phụ thuộc chung: [CPT/taxonomy/banner/card/shared section đã chốt, file nguồn]
ACF namespace: [group_page_{page_key}; tiền tố field_{page_key}_{section}_*]
Đọc Blueprint: [mục cụ thể] và PROJECT_OVERRIDES.md
Xong: [đầu ra, lệnh kiểm tra thực tế, 5–8 dòng tóm tắt cho main]
```

Codex gọi tên TOML `wp_architect`, `acf_builder`, `wp_coder`, `wp_reviewer`; Antigravity gọi tên dấu gạch nối tương ứng bằng `invoke_subagent`. Architect và reviewer **stdout-only**, main chép kết quả vào handoff sau khi kiểm tra. ACF builder và coder được ghi file đã giao cùng mục handoff tương ứng.

## Bằng chứng và hoàn tất

Reviewer đối chiếu §11, chạy `php -l` trên từng PHP đã đụng, chạy `python canhcam-agents-kit/scripts/verify_theme.py` (kiểm tra cú pháp JSON, trùng lặp `field_key`/`group_key` toàn cục, ZTR JSON và đối chiếu section HTML ↔ PHP) và quét các mẫu cấm theo `PROMPT_PLAYBOOK.md`. Ghi lệnh, output và phạm vi. Không có output lệnh thì ghi `[NOT RUN]`, không `[PASS]`; edge case cần WordPress runtime mà chưa chạy cũng ghi `[NOT RUN]`. Main không đánh `DONE` khi kiểm tra bắt buộc còn `[NOT RUN]`.

Chỉ main đổi `UI/{name}.html` thành `UI/Done-{name}.html` sau review `[PASS]` có bằng chứng và khi không worker nào còn đọc file đó. Không đổi tên chỉ để báo tiến độ.

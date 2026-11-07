# CanhCam Pipeline Playbook

> Kit version `2.3.0`. State machine, Wave 0/1/2, quyền sửa file và cổng duyệt nằm trong `AGENTS.md`; schema mapping, ACF, DOM Parity và 18 ZTR nằm trong Blueprint. Prompt dưới đây dùng cho **main agent** ở gốc theme sau khi cài kit.

## 0.1 — Khởi tạo, build Code Graph, quét Cross-Page Inventory & migrate tracking (Wave 0)

```text
Đọc AGENTS.md, KIT_VERSION, PROJECT_OVERRIDES.md, PROJECT_VARIANTS.md, code hiện có và UI/. Kiểm tra HANDOVER_TRACKING.md.
Chạy `python canhcam-agents-kit/scripts/codemap.py build` và `python canhcam-agents-kit/scripts/verify_theme.py --inventory` để sinh CODEMAP.md + .ai-map/, thống kê toàn bộ `<section class="...">` trên các file UI/*.html và kiểm tra hiện trạng `acf-json/`.
Nếu tracking đang là bảng cũ/essay với nhãn “PASS 100%”, migrate vào một bảng trạng thái theo HANDOVER_TRACKING_TEMPLATE.md; giữ nguyên dữ kiện và ghi rõ trạng thái nào chưa có bằng chứng. Không duy trì hai bảng trạng thái song song, không mặc định “PASS 100%” là DONE.
Từ kết quả inventory và CODEMAP.md, chốt bảng Hợp đồng dùng chung (CPT/Taxonomy, Global Modules Tầng 1, Shared Sections Tầng 2 xuất hiện ở >=2 trang, Atomic Cards Tầng 3) và lập danh sách page còn việc cùng handoffs/{page-slug}.md.
Chốt hoặc hỏi các giá trị chưa rõ trong PROJECT_OVERRIDES.md trước khi ACF/code phụ thuộc. Chưa sửa PHP hay ACF JSON ở bước này.
```

## 0.2 — Xây dựng Foundation (Wave 1) & Chạy pipeline nhiều page (Wave 2)

```text
Bước 1 (Wave 1 - Foundation): Hoàn thiện và khóa interface (`wp_parse_args`) cho các file chung đang thiếu trong bảng Hợp đồng dùng chung (`inc/function-post-types.php`, Options, `modules/common/`, `template-parts/shared/`, `template-parts/cards/`) trước khi mở rộng song song cho các page phụ thuộc; chạy `python canhcam-agents-kit/scripts/codemap.py build` sau khi khóa Foundation.
Bước 2 (Wave 2 - Multi-Page): Điều phối [danh sách page] theo AGENTS.md; tối đa [2–3] worker và tối đa 2 writer cùng lúc.
Sau mỗi worker, kiểm tra kết quả, diff so với allowlist và mục handoff tương ứng; main chạy `python canhcam-agents-kit/scripts/codemap.py build` sau mỗi worker acf-builder/wp-coder được nhận bàn giao; đổi state nếu đủ bằng chứng. Cấp việc sẵn sàng kế tiếp ngay, kể cả page khác; page WAITING_APPROVAL không khóa page độc lập.
Chế độ duyệt mapping: [từng page / theo lô / ủy quyền trước rõ ràng cho mapping không có câu hỏi mở]. Câu hỏi nghiệp vụ mới vẫn phải hỏi.
Codex spawn theo tên wp_architect, acf_builder, wp_coder, wp_reviewer. Antigravity invoke_subagent tên wp-architect, acf-builder, wp-coder, wp-reviewer với workspace inherit/share, không branch. Nếu không có subagent, main tự xử lý cùng state machine.
```

## Block spawn bắt buộc cho từng worker

Main điền **đủ tất cả dòng** từ file thực tế; không gửi toàn bộ chat cha. Worker thiếu đầu vào thì dừng và hỏi main.

```text
Kit version: 2.3.0 (đối chiếu KIT_VERSION và handoff)
Vai trò và bước: [tên native]; [MAPPING/ACF/CODING/REVIEW]
Page và HTML: [slug]; UI/[TenTrang].html
Handoff: handoffs/[slug].md; mục [Mapping/ACF/Code/Review]; [stdout-only hoặc ghi mục]
Được sửa: [danh sách path chính xác hoặc “không file”]
Cấm: [HANDOVER_TRACKING.md, CODEMAP.md, .ai-map/; file chung/ngoài allowlist]
Quyết định đã duyệt: [nội dung + nguồn hoặc “chưa, chỉ phân tích”]
Phụ thuộc chung: [CPT/taxonomy/banner/options/shared section/card + file nguồn, đã chốt/chưa]
ACF namespace: [group_page_{page_key}; tiền tố field_{page_key}_{section}_*]
Bản đồ: CODEMAP.md và .ai-map/shards/[architecture|acf-schema|php-contracts].md
Đọc Blueprint: [mục cụ thể] và PROJECT_OVERRIDES.md; PROJECT_VARIANTS.md nếu review biến thể
Xong: [đầu ra đúng mục, lệnh kiểm tra thực tế, 5–8 dòng tóm tắt cho main]
```

### Điều kiện giao bước

| Vai trò | Chỉ nhận khi | Đầu ra | Quyền ghi |
|---|---|---|---|
| Architect | `MAPPING`, HTML tồn tại | Bảng 5 cột Blueprint §2.3, DOM/JS hooks, câu hỏi, dependency | stdout-only; main ghi Mapping |
| ACF builder | `READY_ACF`, mapping đã duyệt, overlay đủ | JSON (key có tiền tố `field_{page_key}_*`) + output `verify_theme.py --acf` | JSON được giao và mục ACF |
| Coder | `READY_CODING`, ACF contract có hoặc ghi không áp dụng | PHP/JS + output `php -l` & `verify_theme.py --html ... --php ...` | file được giao và mục Code |
| Reviewer | `READY_REVIEW`, diff và handoff đủ | kết quả 18 ZTR + output lệnh + `[NOT RUN]` khi cần | stdout-only; main ghi Review |

## Evidence gate của reviewer

Chạy trên **file PHP/JSON đã đụng**; báo chính xác phạm vi. Quét rộng toàn repo khi cần tìm ảnh hưởng nhưng phân biệt lỗi mới với lỗi có sẵn. Bản đồ chỉ dùng để định hướng; không dùng `CODEMAP.md` hay `.ai-map/` làm bằng chứng `[PASS]`. Nếu thiếu binary hoặc WordPress runtime, ghi `[NOT RUN]` cùng lý do, không tự nhận `[PASS]`.

```powershell
php -l <mỗi-file-PHP-đã-đụng>
python canhcam-agents-kit/scripts/verify_theme.py --acf
python canhcam-agents-kit/scripts/verify_theme.py --html <UI/Page.html> --php <các-file-PHP-của-page>
python canhcam-agents-kit/scripts/codemap.py check
rg 'query_posts\(' -g '*.php' <phạm-vi>
rg '<img ' -g '*.php' <phạm-vi>
rg 'the_post_thumbnail' -g '*.php' <phạm-vi>
```

`rg` exit 1 nghĩa là không thấy mẫu; `codemap.py check` ghi cả output và exit code (exit 1/2 chỉ cảnh báo bản đồ cũ/chưa build, không chặn `DONE`). Kiểm tra Cold Start, media bị xóa, URL `?paged=999999`, taxonomy rỗng hoặc AJAX cần WordPress runtime: chỉ ghi đã chạy nếu có bước tái hiện và output thực tế. Nếu còn `[NOT RUN]` ở kiểm tra bắt buộc, main giữ `BLOCKED`/`REVIEW`, không `DONE`.

## Bàn giao và hoàn tất

Main ghi kết quả stdout của architect/reviewer vào handoff sau khi đối chiếu file và version. ACF/coder ghi mục của mình; mục trống thì không đổi state. Review `[ACTION REQUIRED]` quay về owner sửa, rồi review lại. Sau `[PASS]` có bằng chứng đầy đủ, main đổi tên HTML thành `Done-*.html` khi không worker nào còn đọc file nguồn, cập nhật tracking và giao tác vụ tiếp theo.

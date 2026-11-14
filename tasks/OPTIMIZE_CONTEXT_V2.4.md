# TASK: Optimize CanhCam Agents Kit — Context-Aware WordPress Development

## ROLE

Bạn là Senior AI Agent Architect, Context Engineering Specialist và WordPress Developer.

Nhiệm vụ: **Tối ưu CanhCam Agents Kit v2.3.0 hiện tại, ưu tiên giúp AI hiểu đúng phạm vi code và giảm lượng context không liên quan khi mapping HTML → WordPress hoặc sửa PHP + ACF.**

Nguyên tắc xuyên suốt:

> Đừng dùng một con dao lớn để mổ xẻ một con chim nhỏ.

Không over-engineering. Không thêm architecture hoặc dependencies chỉ vì chúng phổ biến. Ưu tiên giải pháp nhỏ, deterministic, dễ bảo trì, có kiểm thử và tận dụng mã nguồn hiện hữu.

## 1. PROJECT CONTEXT

Kit hiện có:

- `AGENTS.md`
- `CANHCAM_THEME_BLUEPRINT.md`
- `PROMPT_PLAYBOOK.md`
- `PROJECT_OVERRIDES_TEMPLATE.md`
- `PROJECT_VARIANTS_TEMPLATE.md`
- `HANDOVER_TRACKING_TEMPLATE.md`
- `PAGE_HANDOFF_TEMPLATE.md`
- `scripts/codemap.py`
- `scripts/kitlib.py`
- `scripts/verify_theme.py`
- `scripts/install_kit.py`
- `scripts/validate_kit.py`
- Bốn native agents: `wp_architect`, `acf_builder`, `wp_coder`, `wp_reviewer`.

CODEMAP sinh ra:

- `CODEMAP.md`
- `.ai-map/graph.json`
- `.ai-map/meta.json`
- `.ai-map/shards/architecture.md`
- `.ai-map/shards/acf-schema.md`
- `.ai-map/shards/php-contracts.md`

Các file trên có thể nằm trong theme được cài kit. Không giả định chúng có sẵn trong repository phân phối.

### Mục tiêu chính

Khi user yêu cầu:

**Case A:** Mapping một file HTML thành WordPress.

AI cần xác định:

- HTML nguồn.
- Template PHP tương ứng.
- Các component hiện hữu có thể tái sử dụng.
- ACF groups và fields liên quan.
- Shared/global components.
- JS hooks hoặc DOM contracts cần bảo toàn.

**Case B:** Chỉnh sửa một PHP component cụ thể.

AI cần biết:

- Component thuộc page/template nào.
- File nào trực tiếp gọi component.
- ACF group/field có liên quan.
- Helper hoặc dependency cần kiểm tra.
- Những file khác có thể bị ảnh hưởng bởi thay đổi.

**Case C:** Sửa một ACF field/group.

AI cần tìm những PHP files thực sự đọc field đó, phân biệt field cấp cao và subfield trong repeater/group/flexible content.

Ở cả ba case, AI không được tự động đọc toàn bộ source theme.

Đích đến: **Relevant Context First — Read Real Source Before Editing.**

## 2. NON-NEGOTIABLE CONSTRAINTS

1. Giữ tương thích với WordPress theme `canhcamtheme` và các cấu trúc theme hiện hữu.
2. Giữ hỗ trợ Codex và Antigravity.
3. Không viết lại toàn bộ kit.
4. Không thêm agent mới nếu bốn agent hiện tại đã đáp ứng được.
5. Không đưa vector database, embeddings, LangChain, RAG server hay external API vào hệ thống.
6. Ưu tiên Python standard library.
7. CODEMAP chỉ là navigation index, không phải source of truth.
8. Không tự động sửa mã nguồn WordPress của các dự án khách hàng trong nhiệm vụ này.
9. Không làm mất dữ liệu trong `PROJECT_OVERRIDES.md`, `HANDOVER_TRACKING.md` hoặc handoffs.
10. Không tự động gán PASS cho bài kiểm tra chưa thực sự chạy.
11. Không tự động đổi version handoff để giả vờ schema đã được migrate.
12. Không nâng KIT_VERSION trước khi đạt acceptance criteria.

Không tự động copy code từ repository bên ngoài. Chỉ tham khảo kiến trúc và patterns phù hợp, nếu cần.

## 3. PHASE 0 — AUDIT EXISTING IMPLEMENTATION

Trước khi sửa code:

- Đọc các script và cấu hình hiện hữu có liên quan.
- Kiểm tra trạng thái Git.
- Đọc tests hiện có nếu có.
- Kiểm tra cấu trúc CODEMAP và parser.
- Xác định hành vi CLI hiện tại.
- Xác định các contract cần giữ tương thích.

Không cần đọc toàn bộ Blueprint ngay từ đầu. Chỉ đọc các mục thực sự ảnh hưởng đến phần code đang triển khai.

Đặc biệt xác minh các vấn đề đã được phát hiện trước đó:

**A. `codemap.py`**

- `query` và `impact` chưa có implementation hữu dụng.
- Quan hệ `uses_field` có thể sai vì các subfields trùng tên như `image`, `title`, `description`.
- Một số edges có source/target không phải graph nodes.
- `renders` có thể suy đoán sai từ chuỗi văn bản hoặc comment.
- `queries` có thể phát hiện nhầm `post_type` ngoài WP_Query.
- CODEMAP có thể bị cắt theo số dòng, làm mất cấu trúc bảng.

**B. `verify_theme.py`**

- ZTR-18 có thể PASS chỉ vì section class xuất hiện trong comment hoặc string.
- Kiểm tra section marker chưa chứng minh DOM/JS parity.

**C. `install_kit.py`**

- Cần phân biệt nâng cấp version với migration schema.
- Build CODEMAP thất bại không được bị che giấu bởi thông báo thành công chung.

Với mỗi vấn đề, xác nhận lại bằng source hiện tại và test tái hiện. Không mặc định tất cả nhận định cũ đều còn đúng.

Kết quả Phase 0: một báo cáo ngắn, gồm lỗi đã xác nhận, severity, file liên quan và đề xuất sửa tối thiểu.

## 4. PHASE 1 — IMPLEMENT P0: RELIABLE CODE GRAPH

Ưu tiên sửa graph hiện tại, không tạo graph engine mới.

### 4.1. ACF Field Resolution

Khắc phục trường hợp hai repeater có cùng subfield name nhưng thuộc các cấu trúc khác nhau.

Ví dụ:

`about_goal_list.image`

không được tự động coi là cùng field với:

`about_history_list.image`.

Ưu tiên resolve theo:

- ACF group.
- Parent field/repeater path.
- Field key khi xác định được.
- Context sử dụng trong PHP.

Nếu chỉ thấy `get_sub_field('image')` mà không xác định được parent repeater, đánh dấu ambiguous/unresolved thay vì tạo nhiều cạnh static chắc chắn.

Không đưa ra kết luận chính xác giả tạo.

### 4.2. Graph Integrity

- Chuẩn hóa source/target node.
- Giữ tương thích graph schema khi có thể.
- Phân biệt dependency confirmed/inferred/dynamic/unresolved.
- Lưu file nguồn và bằng chứng suy luận ở mức vừa đủ.
- Không biến suy đoán thành quan hệ chắc chắn.

### 4.3. Parser Reliability

Giảm false positives trong:

- `uses_field`
- `renders`
- `queries`
- `includes`

Không yêu cầu xây dựng PHP AST parser hoàn chỉnh.

Nếu regex không phân tích an toàn được một cấu trúc, hãy đánh dấu unresolved. Ưu tiên độ tin cậy hơn số lượng edges.

### 4.4. Tests

Tạo hoặc cập nhật tests cho:

- ACF subfields trùng tên.
- Dynamic template parts.
- PHP comments chứa section class.
- Unresolved dependencies.
- Graph node/edge integrity.

Giữ fixtures nhỏ và dễ đọc.

## 5. PHASE 2 — IMPLEMENT P0: CONTEXT RETRIEVAL

Hoàn thiện hai lệnh hiện có:

`codemap.py query`

`codemap.py impact`

Không tạo một framework retrieval mới nếu có thể triển khai trực tiếp trên graph hiện tại.

### 5.1. Query

Hỗ trợ truy vấn theo:

- Page.
- File path.
- ACF field/group.

Đầu ra phải ưu tiên:

1. Exact target.
2. Direct dependencies.
3. Direct consumers.
4. Relevant ACF contracts.
5. Unresolved dependencies cần xác minh.

Không mặc định traverse toàn graph.

### 5.2. Impact

Khi một file PHP hoặc ACF JSON thay đổi:

- Xác định direct consumers.
- Xác định shared components bị ảnh hưởng.
- Nêu các kiểm tra nên chạy.
- Phân biệt ảnh hưởng đã xác minh và có thể xảy ra.

Không mặc định tất cả quan hệ là transitive.

### 5.3. Bounded Output

Thêm cơ chế giới hạn output, ví dụ `--max-tokens` hoặc `--max-items`.

Không cần tokenizer dependency mới. Nếu sử dụng ước lượng token, phải ghi rõ đó là ước lượng.

Khi output bị cắt:

- Không tạo JSON hỏng.
- Không cắt giữa một cấu trúc.
- Có `truncated` và số lượng kết quả bị lược bỏ.
- Ưu tiên giữ các dependency quan trọng.

### 5.4. Freshness

Trước khi truy vấn, xác minh CODEMAP có còn phù hợp với source hiện tại hay không.

Nếu stale:

- Cảnh báo rõ.
- Không trả kết quả stale như dữ liệu chắc chắn.
- Chỉ rebuild khi được phép trong workflow.
- Agent read-only không tự sửa CODEMAP.

### 5.5. CLI Contract

Giữ CLI gọn và nhất quán.

Ví dụ mong muốn:

```bash
python scripts/codemap.py query --page about --format json
python scripts/codemap.py query --file template-parts/about/section-history.php
python scripts/codemap.py query --field about_history_list
python scripts/codemap.py impact --file template-parts/about/section-history.php
```

Có thể điều chỉnh cú pháp sau khi kiểm tra CLI hiện tại.

Lệnh chưa hỗ trợ hoặc tham số không hợp lệ phải trả exit code thất bại, không được báo thành công.

## 6. PHASE 3 — FIX VERIFICATION

Sửa lỗi false positive ZTR-18.

Ít nhất cần phân biệt:

- Section class thật trong markup.
- Class chỉ xuất hiện trong comments/strings.
- JS hook hoặc DOM structure chưa được xác minh.

Không tuyên bố full DOM parity chỉ dựa trên static section marker check.

Nếu chưa có WordPress runtime/browser:

- Ghi rõ phạm vi kiểm tra static.
- Báo `NOT RUN` với runtime tests.
- Không tạo PASS giả.

Bổ sung test tái hiện: HTML có `<section class="home-2">`, PHP chỉ có comment chứa `home-2` và không render section. Trường hợp này bắt buộc không được PASS.

Ưu tiên sửa verifier hiện tại, không xây dựng ngay một visual regression framework.

## 7. PHASE 4 — CONTEXT-AWARE AGENT WORKFLOW

Chỉ triển khai sau khi P0 ổn định.

Mục tiêu: thay đổi cách agents đọc tài liệu, không tăng số lượng agents.

### 7.1. Progressive Context Loading

Đề xuất trình tự:

1. Đọc task và project overrides.
2. Kiểm tra CODEMAP freshness.
3. Query đúng page/file/ACF.
4. Đọc source thật thuộc phạm vi cần thiết.
5. Chỉ đọc phần Blueprint liên quan đến nhiệm vụ.
6. Mở thêm dependency khi phát hiện bằng chứng cần thiết.

Không nạp toàn bộ các shards hoặc Blueprint theo mặc định.

### 7.2. Minimal Context Package

Nếu thực sự cần, bổ sung một output hoặc helper nhỏ để tạo context package cho một task.

Nên chứa:

- Target.
- Related files.
- Relevant rules/skills.
- Known decisions.
- Unresolved dependencies.
- Recommended checks.

Không copy toàn bộ code vào package.

Không tạo `context_router.py` riêng nếu logic có thể được xử lý đơn giản trong `codemap.py` và AGENTS instructions.

### 7.3. Adaptive Workflow

Giữ nguyên bốn vai trò chuyên trách nhưng cho phép:

- FAST: sửa nhỏ, phạm vi rõ, kiểm tra trực tiếp.
- STANDARD: mapping/ACF/code/review thông thường.
- STRICT: shared architecture, CPT/taxonomy, AJAX hoặc thay đổi ảnh hưởng nhiều page.

Không spawn đủ bốn agents cho mọi tác vụ.

Việc chọn workflow phải dựa trên dependency, rủi ro và yêu cầu người dùng; không chỉ đếm số section.

Không được bỏ qua approval bắt buộc hoặc verification liên quan đến bảo mật.

### 7.4. Resume Context

Đánh giá việc bổ sung compact snapshot vào handoff hiện có.

Chỉ triển khai khi snapshot giải quyết được vấn đề rõ ràng mà handoff chưa giải quyết tốt.

Không tạo thêm nhiều loại state files hoặc decision database nếu chưa cần.

Thông tin cần thiết khi tiếp tục phiên:

- Current state.
- Approved decisions.
- Current target.
- Related files.
- Last verified status.
- Blockers.
- Next action.

### 7.5. Skill Architecture

Tham khảo Progressive Disclosure từ Anthropic Skills và Context Engineering patterns.

Không copy toàn bộ 17 skills từ repo ngoài.

Chỉ tách Blueprint thành skills khi xác định có lợi ích cụ thể về retrieval/context. Nếu chưa cần, giữ Blueprint và cải thiện cách đọc theo mục trước.

Tránh duplicated instructions giữa AGENTS, Blueprint và SKILL.md.

## 8. PHASE 5 — TEST & EVALUATION

Tạo bộ kiểm tra tối thiểu để chứng minh thay đổi hữu ích.

Các tình huống bắt buộc:

1. Query đúng About page.
2. Query một PHP component.
3. Query ACF repeater subfield trùng tên.
4. Impact khi sửa shared component.
5. Dynamic dependency không bị báo chắc chắn.
6. CODEMAP stale.
7. Missing target.
8. Output bị giới hạn nhưng vẫn hợp lệ.
9. DOM parity false-positive regression.
10. Existing installer/validator không bị phá.

Nếu có snapshot CODEMAP thật trong repo, sử dụng để kiểm tra. Nếu không, dùng fixtures nhỏ; không tự ý thay đổi source của dự án khách hàng.

Đo khi có thể:

- Số file được đề xuất đọc.
- Precision của related-file retrieval.
- Số false dependencies.
- Kích thước context output.
- Thời gian chạy query.
- Regression pass rate.

Không tự tuyên bố tiết kiệm X% token khi chưa có benchmark thực tế trên Codex/Antigravity.

## 9. IMPLEMENTATION RULES

- Ưu tiên minimal diff.
- Không refactor code không liên quan.
- Không đổi tên hàng loạt file chỉ vì muốn tổ chức lại.
- Không cài dependencies mới nếu chưa thực sự cần.
- Không ghi đè state của dự án.
- Mỗi phase phải có test và kết quả thật.
- Không che giấu lỗi bằng fallback giả.
- Không tự thay đổi behavior của WordPress theme.
- Giữ compatibility với quy trình cũ hoặc tài liệu hóa migration cần thiết.
- Nếu một cải tiến phức tạp hơn lợi ích nó mang lại, ghi nhận và bỏ qua.

## 10. EXECUTION STRATEGY

Thực hiện theo các bước:

**STEP 1 — ANALYZE**

Đọc source liên quan, xác nhận lỗi, lập kế hoạch ngắn và xác định file cần sửa.

**STEP 2 — IMPLEMENT P0**

Ưu tiên Reliable Graph, Query/Impact và Verification. Chia commit hoặc diff theo nhóm thay đổi nếu phù hợp.

**STEP 3 — RECHECK**

Chạy tests độc lập và kiểm tra regression. Không sửa code trong lúc đang thực hiện bước recheck.

**STEP 4 — FIX**

Nếu phát hiện lỗi, sửa đúng phạm vi rồi chạy lại tests.

**STEP 5 — SELECTIVE P1**

Chỉ triển khai các cải tiến context workflow nhỏ, có tác động trực tiếp và không đòi hỏi kiến trúc nặng.

**STEP 6 — FINAL REVIEW**

Đối chiếu toàn bộ diff với yêu cầu và đảm bảo không có thay đổi ngoài phạm vi.

## 11. EXPECTED DELIVERABLES

Sau khi thực hiện, báo cáo bằng tiếng Việt:

1. Các lỗi đã xác nhận.
2. Các file đã sửa/tạo.
3. Những chức năng mới.
4. Các lệnh CLI mẫu và output thực tế.
5. Tests đã chạy cùng PASS/FAIL.
6. Các giới hạn còn lại.
7. Những cải tiến đã cố ý không triển khai và lý do.
8. Cách nâng cấp kit hiện tại mà không mất dữ liệu project.
9. Những lợi ích đã chứng minh và những lợi ích vẫn cần benchmark.

Không dùng những câu như “tối ưu hoàn toàn”, “giảm 70% token”, “PASS 100%” khi không có số liệu.

## 12. DEFINITION OF DONE

Nhiệm vụ đạt yêu cầu khi:

- AI có thể truy xuất relevant files cho một page/component/ACF cụ thể.
- `query` và `impact` trả kết quả hữu dụng, có giới hạn phạm vi và độ tin cậy.
- Repeater subfields trùng tên không bị liên kết sai thành quan hệ chắc chắn.
- ZTR-18 không PASS giả khi chỉ xuất hiện section name trong comments.
- Các tests P0 chạy thành công.
- Workflow hiện hữu không bị phá vỡ.
- Không phải đọc toàn source để thực hiện một thay đổi nhỏ.
- Không bổ sung framework hoặc complexity không cần thiết.

**Final principle: Smallest Reliable Context, Smallest Safe Change.**
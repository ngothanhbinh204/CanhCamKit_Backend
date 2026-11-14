# Báo cáo triển khai Context V2.4

Ngày kiểm tra: 2026-11-14. Kit giữ `KIT_VERSION=2.3.0`; graph có `schema_version=2`. Đây là thay đổi source của kit, chưa cài lên theme reviewgolf và chưa phát hành version mới.

Đã thực hiện ANALYZE → IMPLEMENT → RECHECK → FIX → cập nhật P1 chọn lọc → kiểm tra cuối. Không thêm package, framework, agent hoặc dịch vụ bên ngoài. Không thay đổi PHP/ACF/state/handoff của khách hàng. Thư mục `tasks/` đã untracked trước khi làm; file nhiệm vụ gốc không bị sửa.

## 1. Audit và lỗi đã xác nhận

Đã đọc `AGENTS.md`, nhiệm vụ, source của năm script, cấu hình tám file native agent, project overrides ở theme cha và CLI hiện tại. Repo phân phối chưa có tests hoặc CODEMAP snapshot. Validator ban đầu chạy thành công.

| Mức | Lỗi | Bằng chứng | Sửa tối thiểu |
|---|---|---|---|
| P0 | `query`/`impact` placeholder trả thành công | Test truy vấn page và test tham số không hỗ trợ thất bại trên bản cũ | Xử lý selector trên graph hiện hữu; exit code rõ ràng |
| P0 | Subfield `image` nối cả History và Goal | Test `test_duplicate_subfields` thất bại | Dùng group/key/parent path và scope `while(have_rows)`; giữ ambiguous/unresolved |
| P0 | Edge trỏ endpoint không có node | Test integrity thất bại | Node file/schema/reference đầy đủ; thiếu declaration không coi confirmed |
| P0 | Comment/string tạo include/field giả | Test comments/strings thất bại | Lexer nhỏ tách PHP, comment, string và HTML literal |
| P0 | Mọi `post_type` bị coi là query | Test query scope thất bại | Chỉ nhận đối số trực tiếp của `new WP_Query`/`get_posts` |
| P0 | ZTR-18 PASS khi PHP không render section | Test comment regression trả PASS sai trên bản cũ | So marker HTML literal bằng HTMLParser; runtime/JS ghi NOT RUN |
| P0 | Upgrade tự đổi version handoff | Chạy installer từ Git HEAD trong thư mục tạm: `1.0.0` thành `2.3.0` | Giữ nguyên state/handoff kể cả version |
| P0 | Installer nuốt lỗi build map | Chạy installer HEAD với subprocess build giả lập exit 1: installer exit 0 | Trả exit 1, báo cài đặt chưa hoàn tất |
| P1 | CODEMAP cắt tại dòng 150, shard cắt bảng | Source `cm[:150]`, chia chunk theo dòng; test bảng lớn sau sửa | Giữ toàn bộ CODEMAP; chia shard theo block, giới hạn mềm |

Lệnh tái hiện ban đầu:

```text
python -B -m unittest discover -s tests -v
Ran 7 tests in 0.897s
FAILED (failures=7)
```

Trong RECHECK mở rộng, phát hiện hai template call động cùng dòng bị gộp ID. Đã FIX theo vị trí ký tự và file nguồn; test variant/dynamic hiện qua. Kiểm tra cuối bổ sung chặn nhận nhầm variable function và namespace khác thành lời gọi WordPress.

## 2. File đã thay đổi hoặc tạo

| File | Nội dung |
|---|---|
| `scripts/codemap.py` | Graph integrity, ACF resolution, call extraction, query/impact, freshness/schema/hash, output có giới hạn, giữ cấu trúc Markdown |
| `scripts/kitlib.py` | Lexer/call scanner nhỏ, string literal, balanced delimiters, template references, section parser dùng chung |
| `scripts/verify_theme.py` | ZTR-18 phân biệt static marker với DOM/JS runtime |
| `scripts/install_kit.py` | Bảo toàn state/version, không che lỗi CODEMAP |
| `AGENTS.md` | Context theo từng bước; FAST/STANDARD/STRICT giữ nguyên approval/verification |
| `README.md` | CLI, exit codes, phạm vi parser, upgrade và migration |
| `codex-agents/wp_architect.toml` | Query trước, mở shard khi cần |
| `codex-agents/acf_builder.toml` | Query group trước, đọc JSON thật |
| `codex-agents/wp_coder.toml` | Query/impact theo file, đọc source thật |
| `codex-agents/wp_reviewer.toml` | Freshness và evidence read-only; static không thay runtime |
| `custom-agents/wp-architect.md` | Chính sách tương ứng cho Antigravity |
| `custom-agents/acf-builder.md` | Chính sách tương ứng cho Antigravity |
| `custom-agents/wp-coder.md` | Chính sách tương ứng cho Antigravity |
| `custom-agents/wp-reviewer.md` | Chính sách tương ứng cho Antigravity |
| `tests/test_context.py` — mới | 31 test, tạo theme nhỏ trong TemporaryDirectory |
| `tasks/OPTIMIZE_CONTEXT_V2.4_REPORT.md` — mới | Báo cáo này |

Không sửa Blueprint, validator, template state/handoff hoặc `KIT_VERSION`. Bốn vai trò chuyên trách vẫn giữ nguyên; không spawn worker cho nhiệm vụ sửa kit này.

## 3. Chức năng và CLI

Các lệnh chạy từ kit với `--root <theme-fixture>`; từ theme đã cài thay `scripts/` bằng `canhcam-agents-kit/scripts/`.

```bash
python scripts/codemap.py build --root <theme>
python scripts/codemap.py check --root <theme>
python scripts/codemap.py query --page about --format json --root <theme>
python scripts/codemap.py query --file template-parts/about/history.php --root <theme>
python scripts/codemap.py query --field about_history_list.image --max-items 3 --root <theme>
python scripts/codemap.py query --field group_about:about_history_list.image --root <theme>
python scripts/codemap.py query --group group_about --root <theme>
python scripts/codemap.py impact --file template-parts/shared/cta.php --root <theme>
python scripts/codemap.py impact --file acf-json/group_about.json --root <theme>
```

Output build thực tế trên fixture: `15 nodes, 16 edges, 6 files hashed, 3 shards written`.

Trích output thực tế của `query --page about` (bỏ các dòng hướng dẫn check chung):

```text
[OK] about
- exact_target: UI/About.html (target)
- exact_target: templates/template-about.php (target)
- direct_dependency: UISection:about-1 (confirmed)
- direct_dependency: template-parts/about/history.php (confirmed)
- direct_dependency: template-parts/shared/cta.php (confirmed)
- direct_consumer: ACFGroup:group_about (confirmed)
- acf_contract: ACFField:field_about_history_list (confirmed)
- acf_contract: ACFField:field_about_history_list_image (confirmed)
- acf_contract: ACFGroup:group_about (confirmed)
- acf_contract: ACFGroup:group_about (target)
- matching_component: template-parts/about/history.php (inferred)
- unresolved_dependency: dynamic:get_template_part@116:template-parts/about/history.php (dynamic)
- unresolved_dependency: unresolved:template-parts/about/history.php:92:field (unresolved)
truncated=False; omitted_count=0
```

Trích output `impact --file template-parts/shared/cta.php`:

```text
[OK] template-parts/shared/cta.php
- exact_target: template-parts/shared/cta.php (target)
- direct_consumer: templates/template-about.php (confirmed)
- direct_consumer: templates/template-home.php (confirmed)
- acf_contract: ACFGroup:group_about (confirmed)
truncated=False; omitted_count=0
```

Trích output `query --field about_history_list.image --max-items 3`:

```text
[OK] about_history_list.image
- exact_target: ACFField:field_about_history_list_image (target)
- direct_consumer: ACFGroup:group_about (confirmed)
- direct_consumer: template-parts/about/history.php (confirmed)
truncated=True; omitted_count=5
```

`confirmed` là quan hệ cú pháp trong source, không chứng minh runtime. `matching_component` theo HTML marker được ghi `inferred`. Dependency động hoặc thiếu parent không nối bừa vào field/component chắc chắn. Ownership của ACFGroup → field được trả kèm loại edge để phân biệt với PHP đọc field.

Query/impact mặc định một hop, cộng ownership ACF/helper và contract liên quan. Không tự đi qua toàn bộ cây consumer. `--max-items` giới hạn item; không phải giới hạn token. JSON có `truncated`, `omitted_count`, `related_files`, `shared_components`, `recommended_checks`, `limitations` và `ambiguous_target` khi tên field/group không duy nhất.

Exit code: 0 = kết quả hợp lệ; 1 = stale; 2 = map thiếu/hỏng, schema/CLI không hợp lệ hoặc lỗi build; 3 = target không tồn tại. Schema map cũ được báo stale (1). Query/check/impact không ghi map. Hash kiểm tra source thêm/sửa/xóa và tính toàn vẹn graph.

## 4. Bằng chứng kiểm thử

Lần chạy cuối:

```text
python -B -m unittest discover -s tests -v
Ran 31 tests in 31.968s
OK

python -B scripts/validate_kit.py
CanhCam kit 2.3.0: 4 Antigravity + 4 Codex agents + install_kit.py + verify_theme.py + codemap.py validated

compile() từng file Python trong scripts/ và tests/, không ghi bytecode
[PASS] Python syntax: 6 files

git -c core.whitespace=blank-at-eol diff --check
exit 0; không có whitespace error (Git chỉ cảnh báo LF/CRLF)
```

31 test bao phủ: About page, PHP component, ACF key/path/group và tên trùng; parent lồng nhau; shared component/ACF JSON/helper impact; dynamic template variants; comment/string/heredoc; graph integrity; literal section/static-only output; query ngoài WP_Query và mảng lồng; stale thêm/sửa/xóa; schema cũ/graph hỏng/map thiếu; target thiếu; bounded JSON; CLI root/tham số sai; installer dry-run/upgrade giữ state; installer lỗi build; Markdown không mất bảng; variable/namespaced calls không bị coi là WordPress call.

Lệnh verifier thực sự chạy trên fixture (cwd là theme tạm):

```text
python <kit>/scripts/verify_theme.py --acf --html UI/About.html --php templates/template-about.php
exit 0
[PASS] ACF verification: 1 JSON groups, 4 fields checked (0 duplicate keys, ZTR-11/12/14/17 clean).
[NOT RUN] [ZTR-18] Runtime DOM structure / JS hooks / browser parity; static markers only.
[PASS] [ZTR-18 static markers only] 1/1 section(s) from About.html verified across 3 PHP file(s) (about-1).
```

Không sửa file PHP thực của dự án nên `php -l` không áp dụng cho diff này. WordPress/browser runtime, visual parity, JS interaction: **[NOT RUN]**. Không dùng các test Python để kết luận page khách hàng DONE.

## 5. Đo trên fixture và giới hạn

Một lần đo `query --file template-parts/about/history.php --format json`:

- Đề xuất 4 file trên fixture có 6 file được index: HTML About, ACF About, History component và template About.
- So với tập kỳ vọng xác định trước: 4/4 file đúng, 0 file thừa. Đây chỉ là precision của fixture nhỏ, chưa đại diện theme thực tế.
- Output JSON UTF-8: 7.498 byte.
- Median 5 lần chạy CLI (gồm Python startup và freshness): 116,32 ms trên môi trường này; không phải benchmark production.
- Test loại bỏ dependency giả ở những mẫu comment/string/query/subfield đã liệt kê. Chưa đo recall trên toàn bộ canhcamtheme.

Parser là scanner bảo thủ, không phải PHP AST/interpreter. Không giải dataflow của biến, foreach/mảng ACF, clone fields, layout flexible content phức tạp hoặc query args động; phần không phân giải giữ unresolved khi nhận diện được call. Các lời gọi namespaced/method/variable không được coi tự động là API WordPress. Không thực thi PHP để suy DOM; section được echo vẫn cần kiểm tra runtime. Không kiểm tra nesting, số lần render, thứ tự, CSS hay JS hooks bằng static marker.

Freshness vẫn đọc/hash các file thuộc scan scope trên đĩa; lợi ích context là agent nhận kết quả theo phạm vi, không phải đưa toàn bộ source vào prompt. Chưa đo số token, chi phí hay chất lượng trên phiên Codex/Antigravity thực. Không tuyên bố phần trăm tiết kiệm token.

## 6. P1 chọn lọc và phần không triển khai

Đã đồng bộ progressive context loading trong AGENTS, tám file native agent và phần hướng dẫn CODEMAP sinh ra: task/override → check → query → source thật → đúng mục Blueprint → mở dependency khi có bằng chứng. Giữ các gate mapping approval, quyền ghi file chung và verification.

Không thêm context router, vector DB, embeddings, framework retrieval, agent mới hoặc skill mới. Query JSON đã đủ làm context package nhỏ. Không tạo snapshot/state database mới vì handoff hiện có đã chứa state, quyết định, file, evidence, blocker và bước tiếp theo. Không tách Blueprint thành nhiều skills khi chưa có benchmark chứng minh lợi ích. Không xây visual regression framework trong nhiệm vụ này.

## 7. Nâng cấp an toàn

Tại theme đã đặt source kit:

```bash
python canhcam-agents-kit/scripts/install_kit.py --upgrade --dry-run
python canhcam-agents-kit/scripts/install_kit.py --upgrade
python canhcam-agents-kit/scripts/codemap.py check
```

Chỉ chạy lệnh thứ hai sau khi kiểm tra dry-run theo workflow dự án. `--upgrade` cập nhật rule/agent/KIT_VERSION cài đặt và map nhưng giữ nguyên nội dung/version trong overrides, variants, tracking và handoffs. Không dùng `--force-reset` khi cần giữ state. Nếu version handoff khác kit, main phải review migration và bằng chứng tương thích riêng; không đổi số tự động để bỏ gate.

Map schema 1 phải rebuild có chủ đích để dùng retrieval mới; không cần migrate ACF/PHP của khách hàng. Nếu build thất bại, installer trả lỗi và nêu core có thể đã copy; sửa nguyên nhân rồi chạy lại. Việc cài lên theme thật không được thực hiện trong nhiệm vụ này.

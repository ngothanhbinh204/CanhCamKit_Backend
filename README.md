# CanhCam Agents Kit

**Version:** `2.3.0` (`KIT_VERSION`). Kit là **repo nguồn phân phối**, đi kèm bộ cài đặt tự động 1 lệnh (`install_kit.py`) và bộ sinh Bản đồ cấu trúc cho AI (`codemap.py` + `kitlib.py`) để bung toàn bộ cấu hình runtime vào gốc theme WordPress mà không cần copy thủ công.

---

## 1. Quick Start — Khởi tạo dự án mới chỉ với 2 lệnh

Đứng tại thư mục gốc của theme (`wp-content/themes/<ten-theme>/`):

```powershell
# Bước 1: Clone bộ kit về thư mục gốc của theme
git clone <url-git-canhcam-agents-kit> canhcam-agents-kit

# Bước 2: Chạy lệnh tự động cài đặt và build CODEMAP ra gốc theme (Windows / macOS / Linux)
python canhcam-agents-kit/scripts/install_kit.py
# Hoặc trên PowerShell: .\canhcam-agents-kit\install.ps1
# Hoặc trên macOS/Linux: ./canhcam-agents-kit/install.sh
```

### Cập nhật bộ Kit khi dự án đang chạy (Không mất dữ liệu dự án)

```powershell
git -C canhcam-agents-kit pull
python canhcam-agents-kit/scripts/install_kit.py --upgrade
```

### Các tham số CLI của `install_kit.py` và `codemap.py`

| Lệnh / Cờ (Flag) | Tác dụng |
|---|---|
| `python canhcam-agents-kit/scripts/install_kit.py` | Cài đặt chuẩn (cả Antigravity & Codex), thêm `canhcam-agents-kit/`, `.ai-map/`, `CODEMAP.md` vào `.gitignore`, sinh `CODEMAP.md` + `.ai-map/` và quét `UI/*.html` |
| `--tool antigravity` / `--tool codex` | Chỉ cài `.agents/agents/*.md` hoặc `.codex/agents/*.toml` |
| `--upgrade` | Cập nhật Rule/Blueprint/Agents và build lại `CODEMAP`; giữ nguyên từng byte của state/handoff hiện có, bao gồm version. Migration schema phải được review riêng |
| `--dry-run` | Xem trước danh sách file sẽ `[CREATE]`, `[UPDATE]`, `[SKIP]` và `[WOULD BUILD] CODEMAP` mà không ghi xuống ổ cứng |
| `--force-reset` | Khởi tạo lại toàn bộ từ đầu (kể cả `PROJECT_OVERRIDES.md` và `HANDOVER_TRACKING.md`) và build lại `CODEMAP` |
| `python canhcam-agents-kit/scripts/codemap.py build` | Quét theme và ghi `CODEMAP.md`, `.ai-map/graph.json`, `.ai-map/meta.json`, `.ai-map/shards/*.md` (chỉ Main gọi) |
| `python canhcam-agents-kit/scripts/codemap.py check` | Chỉ đọc: kiểm tra độ tươi của bản đồ theo SHA-256 (`exit 0` = tươi, `exit 1` = cũ, `exit 2` = chưa có map) |
| `codemap.py query --page about --format json` | Exact target, dependency/consumer trực tiếp, ACF contract, component gợi ý theo marker và dependency chưa phân giải |
| `codemap.py query --file template-parts/about/section-history.php` | Phạm vi component; mở source thật trước khi sửa |
| `codemap.py query --field about_history_list.image` | Field theo key/path; dùng `group_about:about_history_list.image` để phân biệt group; `--group group_about` để chọn group |
| `codemap.py impact --file acf-json/group_about.json` | Consumer của field thuộc JSON; cũng hỗ trợ `--file <PHP>` và `--field <key-or-path>` |
| `--max-items 40` | Giới hạn tổng item (mặc định 40), ưu tiên target; JSON luôn nguyên vẹn, có `truncated`, `omitted_count`. Đây là giới hạn item, không phải token |

Các lệnh query/impact chỉ đọc và kiểm tra freshness trước khi trả kết quả: stale trả exit 1, map thiếu/hỏng/tham số sai trả exit 2, target không tồn tại trả exit 3. Không tự rebuild. `--root <theme>` có thể đặt trước hoặc sau subcommand. Graph schema 2 giữ `confidence: static` cho compatibility và thêm `status: confirmed`; đây là bằng chứng cú pháp, không bảo đảm runtime. Page selector khớp slug tên file (`About.html`, `Done-About.html`, `template-about.php`, `page-about.php`); nếu tên không khớp, dùng `--file`.

Upgrade an toàn: chạy `python canhcam-agents-kit/scripts/install_kit.py --upgrade --dry-run`, kiểm tra danh sách, rồi chạy lại bỏ `--dry-run`. Không dùng `--force-reset` nếu cần giữ dữ liệu. Map schema cũ cần main build lại; khác version handoff cần review migration riêng, không tự đổi số để bỏ gate. Build map lỗi trả exit khác 0 và báo cài đặt chưa hoàn tất (core có thể đã được copy). Kit vẫn giữ version 2.3.0 trong thay đổi này; không tự phát hành 2.4.0.

Verifier ZTR-18 chỉ kiểm tra marker `<section>` literal ngoài PHP/comment/script. HTML được echo, DOM động, thứ tự/nesting, CSS và JS hooks cần runtime/browser; output ghi `[NOT RUN]` và không được dùng static PASS để đánh DONE cho kiểm tra runtime bắt buộc. Shards dùng giới hạn dòng mềm để giữ nguyên bảng; CODEMAP không bị cắt 150 dòng. Dùng query để giới hạn context.

Kiểm thử bằng standard library: `python -B -m unittest discover -s tests -v`; validator: `python -B scripts/validate_kit.py`. Fixtures nằm trong thư mục tạm, không sửa theme khách hàng. Xem [báo cáo triển khai](tasks/OPTIMIZE_CONTEXT_V2.4_REPORT.md).

---

## 2. Cơ chế phân nhóm file của `install_kit.py`

| Nhóm file | Nguồn | Đích ở gốc theme | Hành vi khi chạy `install_kit.py` |
|---|---|---|---|
| **Nhóm A: Core & Rules** | `AGENTS.md`, `KIT_VERSION`, `CANHCAM_THEME_BLUEPRINT.md`, `PROMPT_PLAYBOOK.md`, `PAGE_HANDOFF_TEMPLATE.md` | Cùng tên ở gốc theme | Luôn đồng bộ bản mới nhất từ kit |
| **Nhóm A: Native Agents** | `custom-agents/*.md`<br>`codex-agents/*.toml` | `.agents/agents/*.md`<br>`.codex/agents/*.toml` | Luôn đồng bộ bản mới nhất theo `--tool` |
| **Nhóm B: Project State** | `PROJECT_OVERRIDES_TEMPLATE.md`<br>`PROJECT_VARIANTS_TEMPLATE.md`<br>`HANDOVER_TRACKING_TEMPLATE.md` | `PROJECT_OVERRIDES.md`<br>`PROJECT_VARIANTS.md`<br>`HANDOVER_TRACKING.md`<br>+ thư mục `handoffs/` | **Chỉ tạo khi chưa tồn tại** (tự động điền `text_domain` và `options_menu_slug` nếu phát hiện trong code); giữ nguyên khi chạy lại hoặc `--upgrade` |
| **Nhóm C: Generated Code Map** | Sinh bởi `scripts/codemap.py` + `scripts/kitlib.py` | `CODEMAP.md`<br>`.ai-map/graph.json`<br>`.ai-map/meta.json`<br>`.ai-map/shards/*.md` | Tự động tái sinh từ mã nguồn theme khi cài đặt, `--upgrade` hoặc `--force-reset`; tự động đưa vào `.gitignore` |

`handoffs/_example-about.md` nằm trong kit để minh họa kết quả kiểm tra thật; **không copy** vào hàng đợi dự án. Không cài bốn agent Antigravity vào `~/.gemini/config/agents/` vì kit là quy trình riêng của từng theme.

---

## 3. Quy trình vận hành sau khi chạy `install_kit.py`

1. Mở **phiên mới tại gốc theme** để Antigravity / Codex nhận diện `.agents/agents/` hoặc `.codex/agents/` cùng `AGENTS.md`.
2. Kiểm tra nhanh `PROJECT_OVERRIDES.md` và `CODEMAP.md` (chỉ mục điều hướng nhanh cấu trúc theme).
3. Chạy **Prompt 0.1** trong `PROMPT_PLAYBOOK.md` để chốt bảng Hợp đồng dùng chung (Wave 0), sau đó chạy **Prompt 0.2** để khóa Foundation (Wave 1) và chạy song song các trang (Wave 2).
4. Trong quá trình làm việc, dùng `python canhcam-agents-kit/scripts/verify_theme.py` để kiểm tra trùng lặp `field_key` toàn cục (ZTR-17), quy chuẩn ACF JSON (ZTR-11/12/14) và đối chiếu DOM `<section>` giữa HTML và PHP (ZTR-18), kết hợp `python canhcam-agents-kit/scripts/codemap.py` (`build`/`check`).

## Changelog

- **2.3.0 (2026-11-07):** Bổ sung Bản đồ cấu trúc cho AI (`scripts/codemap.py`, `scripts/kitlib.py`) sinh `CODEMAP.md` và `.ai-map/` (Nhóm C Generated: `graph.json`, `meta.json` với SHA-256 content hash, và 3 shard `architecture.md`, `acf-schema.md`, `php-contracts.md`); tích hợp tự động vào `install_kit.py` và `.gitignore`.
- **2.2.0 (2026-11-07):** Thêm bộ cài đặt tự động 1 lệnh `scripts/install_kit.py` (`install.ps1` / `install.sh`); chuẩn hóa Multi-Page Pipeline 3 Wave (Inventory → Foundation → Parallel Pages); bổ sung quy tắc chống trùng `field_key` toàn cục (ZTR-17) và bảo toàn DOM/JS Parity (ZTR-18, Blueprint §8.5); thêm `scripts/verify_theme.py`; cập nhật đúng tên tool native của Antigravity (`read_file`, `write_file`, `edit_file`, `run_command`).
- **2.1.0 (2026-11-07):** Native install map cho Codex/Antigravity; role theo tool hợp lệ, stdout-only cho architect/reviewer; spawn contract, overlay dự án, bằng chứng review, version handoff và pipeline nhiều page.
- **2.0.0:** Blueprint WordPress và bốn vai trò chuyên môn ban đầu.

```text
theme-root/
├── AGENTS.md
├── KIT_VERSION
├── CANHCAM_THEME_BLUEPRINT.md
├── PROMPT_PLAYBOOK.md
├── PROJECT_OVERRIDES.md
├── PROJECT_VARIANTS.md
├── HANDOVER_TRACKING.md
├── PAGE_HANDOFF_TEMPLATE.md
├── CODEMAP.md             # Nhóm C (Generated, gitignored)
├── .ai-map/               # Nhóm C (Generated: graph.json, meta.json, shards/*.md)
├── UI/                    # HTML nguồn
├── handoffs/              # biên bản bàn giao từng trang
├── acf-json/
├── .codex/agents/         # 4 file *.toml cho Codex
└── .agents/agents/        # 4 file *.md cho Antigravity
```

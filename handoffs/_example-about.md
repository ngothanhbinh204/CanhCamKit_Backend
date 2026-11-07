# Ví dụ evidence handoff: About (không phải trạng thái dự án)

> Kit version: `2.2.0`. Snapshot kiểm tra trên theme `reviewgolf` ngày 2026-11-07. **Không copy file này thành handoff đang chạy.** Kết quả thực tế là `[ACTION REQUIRED]`; không có mẫu `[PASS]` vì code hiện tại vi phạm ZTR-04 và WordPress runtime chưa chạy được.

## Đầu vào và phạm vi

- HTML: `UI/Done-About.html` (đã có từ trước).
- Template: `templates/template-about.php`, `template-parts/about/*.php`.
- ACF: `acf-json/group_page_about.json` (namespace `field_about_*`).
- `PROJECT_OVERRIDES.md` và quyết định duyệt mapping: ví dụ này minh họa format bàn giao và cổng bằng chứng v2.2.0.

## Mapping — quan sát từ HTML và code hiện có

| Section (CSS class đầu tiên) | Tầng component | ACF Tab / không áp dụng | File hiện có | Nguồn dữ liệu |
|---|---|---|---|---|
| `section-NomalBanner` | Global | không áp dụng | `modules/common/banner.php` | CPT/banner contract (`select_banner`) |
| `section-about-intro` | Page | Giới thiệu tổng quan | `template-parts/about/section-about-intro.php` | ACF page group |
| `section-History` | Page | Lịch sử | `template-parts/about/section-history.php` | ACF page group |
| `section-about-team` | Page | Đội ngũ | `template-parts/about/section-about-team.php` | ACF page group |
| `section-certificate` | Page | Chứng chỉ | `template-parts/about/section-certificate.php` | ACF page group |
| `section-organization` | Page | Cơ cấu | `template-parts/about/section-organization.php` | ACF page group |

- DOM & JS hooks cần bảo toàn: Swiper (`section-about-intro`, `section-History`, `section-certificate`), Fancybox (`data-fancybox` tại `section-organization`).
- Nguồn: `python canhcam-agents-kit/scripts/verify_theme.py --html UI/Done-About.html --php templates/template-about.php modules/common/banner.php template-parts/about/*.php`.
- Duyệt mapping: `[NOT RUN]` — ví dụ không đại diện cho phê duyệt của người dùng.

## ACF — contract quan sát được

- File: `acf-json/group_page_about.json`, key `group_page_about`, location `templates/template-about.php`, style `default`.
- `python canhcam-agents-kit/scripts/verify_theme.py --acf` → exit `0` (JSON hợp lệ, không trùng `field_key` toàn cục, đạt ZTR-11/12/14/17).
- Duyệt contract: `[NOT RUN]` — không có handoff duyệt cũ để đối chiếu.

## Code — file kiểm tra

- `templates/template-about.php` và năm file `template-parts/about/section-*.php`.
- Chưa sửa code trong lượt lập ví dụ này.

## Review — kết quả thực tế

- Kết quả: `[ACTION REQUIRED]`.
- `php -l` trên template và năm section → cả sáu file: `No syntax errors detected`.
- `python canhcam-agents-kit/scripts/verify_theme.py --acf` → exit `0` (`[PASS]` ZTR-11/12/14/17).
- `python canhcam-agents-kit/scripts/verify_theme.py --html UI/Done-About.html --php templates/template-about.php modules/common/banner.php template-parts/about/section-about-intro.php template-parts/about/section-history.php template-parts/about/section-about-team.php template-parts/about/section-certificate.php template-parts/about/section-organization.php` → exit `0` (`[PASS]` ZTR-18 DOM section parity: 6/6 sections khớp).
- `rg 'query_posts\('` trên sáu PHP → exit `1` (không thấy).
- `rg '<img '` trên sáu PHP → exit `0`, tìm thấy ZTR-04 tại `section-about-team.php:33`, `section-history.php:132,136`, `section-certificate.php:45`, `section-organization.php:31`, `section-about-intro.php:63`.
- `rg 'the_post_thumbnail'` trên sáu PHP → exit `1` (không thấy).
- Cold Start / media hỏng / `?paged=999999`: `[NOT RUN]`; `wp core is-installed` trả `Error establishing a database connection` trong môi trường kiểm tra.
- Bước kế tiếp: sửa ZTR-04 trong phạm vi được main giao, khôi phục WordPress runtime để kiểm tra edge cases, rồi review lại. Main **không** đánh `DONE`.

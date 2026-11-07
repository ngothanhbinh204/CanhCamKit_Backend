# Project overrides

> Kit version: `2.3.0`. Copy thành `PROJECT_OVERRIDES.md` ở gốc theme và điền từ code/việc đã duyệt. Ô `[chưa chốt]` là điều kiện chặn bước ACF/code phụ thuộc; không tự lấy ví dụ Blueprint làm giá trị.

| Quyết định | Giá trị dự án | Nguồn xác nhận |
|---|---|---|
| `acf_page_group_pattern` | `group_page_{page_key}.json` cho page mới (`page_key` ASCII, gạch dưới); ghi ngoại lệ file cũ tại đây | Kit default / code hiện có |
| `acf_field_key_prefix` | `field_{page_key}_{section}_{field_name}` (bắt buộc duy nhất toàn cục trên toàn bộ `acf-json/`) | Blueprint §6.2 / ZTR-17 |
| `options_menu_slug` | `[chưa chốt]` | [file đăng ký hoặc người duyệt] |
| `text_domain` | `canhcamtheme` | [style.css hoặc người duyệt] |
| `banner_contract` | `[CPT banner / nguồn khác / không dùng]` | [file hoặc người duyệt] |
| `home_banner` | `[nguồn dữ liệu và component, nếu có]` | [file hoặc người duyệt] |
| `search_post_types` | `[chưa chốt nếu có Search page]` | [file hoặc người duyệt] |
| `search_overview_limit` | `[chưa chốt nếu có Search page]` | [file hoặc người duyệt] |
| `search_detail_per_page` | `[chưa chốt nếu có Search page]` | [file hoặc người duyệt] |
| `wpml` | `[có / không / chưa chốt]` | [plugin hoặc người duyệt] |

## Ngoại lệ đã chốt của project

- [Ghi file ACF hiện hữu không theo pattern mặc định, helper/banner khác chuẩn, hoặc “không có”.]

# 📐 BẢN THIẾT KẾ THEME CANHCAM (CANHCAM THEME BLUEPRINT)

> **Phạm vi áp dụng:** Bộ quy chuẩn cấu trúc, mô hình dữ liệu và nguyên tắc kỹ thuật dùng lại cho **MỌI DỰ ÁN** WordPress theme của CanhCam.  
> **Kit version:** 2.2.0 (xem `KIT_VERSION`; quy trình điều phối nằm trong `AGENTS.md`)
> **Cập nhật:** 2026-11-07  

---

## Mục lục theo vai trò

| Vai trò | Mục cần đọc |
|---|---|
| Architect | §2 (gồm bảng mapping §2.3 & phân tầng đa trang §2.4), §6.2; §3.1 khi có taxonomy phân cấp |
| ACF builder | §6–7 (nhất là quy tắc chống trùng `field_key` §6.2); quyết định dự án trong `PROJECT_OVERRIDES.md` |
| Coder | §2.1, §8–9 (gồm bảo toàn DOM/JS §8.5); mục khác khi page thực sự cần |
| Reviewer | §11 (18 ZTR); `PROJECT_OVERRIDES.md` và biến thể đã duyệt trong `PROJECT_VARIANTS.md` |

Blueprint chứa quy chuẩn kỹ thuật. State machine, Wave 0/1/2, ownership và spawn contract nằm duy nhất ở `AGENTS.md`.

---

## 1. TRIẾT LÝ KIẾN TRÚC CỐT LÕI (CORE ARCHITECTURAL PILLARS)

1. **Mô hình Component 4 Tầng (4-Tier Component Architecture):**  
   Mọi thành phần giao diện được phân bổ nghiêm ngặt theo 4 cấp độ: *Global System Modules* (dùng toàn site), *Shared Business Sections* (dùng từ 2 trang trở lên), *Atomic Data Cards* (1 Post Type = 1 card duy nhất cho Archive/Search/Slider), và *Page-Specific Sections* (chỉ thuộc về 1 trang).
2. **Defensive Programming & 3 Tầng Phòng Thủ (Zero-Pollution Bailout):**  
   Mọi component hiển thị dữ liệu động (ACF, Taxonomy, WP_Query, Repeater) bắt buộc phải có chuỗi fallback 3 tầng: *Validation -> Auto Fallback Query / Inherit -> Bailout (`return;`)*. Tuyệt đối không bao giờ render thẻ wrapper HTML rỗng hoặc sập giao diện khi admin chưa kịp nhập liệu.
3. **Single Root Term (Một Term Gốc Duy Nhất - HTTP 200 OK):**  
   Mỗi phân hệ nội dung phân cấp (Sản phẩm, Dịch vụ, Tin tức) chỉ có duy nhất **MỘT term bậc 1 lớn nhất** làm node gốc. Truy cập Term gốc luôn trả về **`HTTP 200 OK`**, hiển thị tổng hợp bài viết của tất cả các term con. Tuyệt đối không hardcode lệnh chuyển hướng 301 trong file view.
4. **Auxiliary Taxonomy Engine (Bộ Lọc Chéo Đa Chiều):**  
   Phân tách rõ ràng giữa *Primary Taxonomy* (tạo cấu trúc thư mục URL tĩnh) và *Auxiliary Taxonomies* (lọc chéo phân loại phụ như quy cách, xuất xứ, thương hiệu qua query params). Tự động bảo toàn tham số lọc trong phân trang chuẩn WordPress.
5. **Centralized Global Banner (khi dự án chọn CPT banner):**
   Page có banner/hero và hợp đồng dự án chọn CPT `banner` thì dùng component chung. Không tạo CPT hoặc field banner cho mọi page theo mặc định.
6. **Multi-Block Search (khi page là Search):**
   Trang kết quả tìm kiếm có nhiều Post Type được phân tách theo từng khối; không đưa search đa khối vào mapping của page không có chức năng tìm kiếm.
7. **Zero Inline Scripts & AJAX Security Nonce:**  
   Tuyệt đối cấm viết mã `<script>` inline rải rác trong file PHP view. Mọi logic tương tác JS phải đóng gói thành module độc lập, đăng ký qua `wp_enqueue_script()`, truyền tham số qua `wp_localize_script()` và bắt buộc xác thực bảo mật Nonce CSRF.
8. **Project Variants System & Triad Xử Lý (Cơ Chế Biến Thể Dự Án):**  
   Khi dự án có yêu cầu nghiệp vụ cá biệt làm thay đổi hành vi chuẩn (như redirect 301 term cấp 1), **bắt buộc điều phối qua Hook Filter**, không được sửa cứng vào file view. Các biến thể phải đăng ký trong `PROJECT_VARIANTS.md` và hoàn thiện đủ 3 khâu: *Routing tập trung + Loại trừ XML Sitemap + Breadcrumbs không liên kết*.
9. **DOM & JS Hook Parity (Bảo Toàn Cấu Trúc Giao Diện Gốc):**
   Frontend bundle (`core.min.js`, `main.min.js`, `main.min.css`) phụ thuộc chặt vào cấu trúc DOM, class CSS đầu tiên của `<section>` và các thuộc tính `data-*`. Khi chuyển từ HTML tĩnh sang PHP động, bắt buộc giữ nguyên cấu trúc selector và hook tương tác JS.

---

## 2. KIẾN TRÚC PHÂN RÃ COMPONENT 4 TẦNG (4-TIER ARCHITECTURE)

```
themes/canhcamtheme/
├── modules/common/               --> TẦNG 1: Global System Modules (Banner, Breadcrumb, Pagination, Popup, Toast)
├── template-parts/
│   ├── shared/                   --> TẦNG 2: Shared Business Sections (Dùng từ 2 trang trở lên: Certifications, Partners, CTA...)
│   ├── cards/                    --> TẦNG 3: Atomic Data Cards (1 Post Type = 1 Card duy nhất cho Archive, Slider, Search)
│   │   ├── card-product.php
│   │   ├── card-event.php
│   │   └── card-post.php
│   └── {page}/                   --> TẦNG 4: Page-Specific Sections (Chỉ thuộc về 1 trang duy nhất)
│       └── section-{first-class}.php
```

### 2.1. Quy Chuẩn Interface Contract cho Shared Components
Mọi component trong `template-parts/shared/` bắt buộc phải chuẩn hóa đầu vào bằng `wp_parse_args()` với chuỗi ưu tiên dữ liệu 3 cấp:
1. **Cấp 1:** Dữ liệu truyền trực tiếp qua `$args['items']` / `$args['title']`.
2. **Cấp 2:** Custom field của đối tượng hiện tại (`$args['source_id']` hoặc queried object).
3. **Cấp 3:** Dữ liệu cấu hình chung trong Theme Options (`$args['fallback_option']`).

```php
<?php
/**
 * Shared Component: Certification Slider
 * Path: template-parts/shared/section-certification.php
 */
$args = wp_parse_args($args ?? array(), array(
    'source_id'       => get_queried_object_id() ?: get_the_ID(),
    'title'           => '',
    'items'           => null,
    'bg_class'        => 'bg-Secondary-bg',
    'wrapper_class'   => '',
    'fallback_option' => 'opt_global_certifications',
));

$title = !empty($args['title']) ? $args['title'] : get_field('certification_title', $args['source_id']);
$items = !empty($args['items']) ? $args['items'] : get_field('certification_items', $args['source_id']);

// Fallback cấp 3: Lấy từ Theme Options nếu trang hiện tại không cấu hình riêng
if (empty($items) && !empty($args['fallback_option'])) {
    $items = get_field($args['fallback_option'], 'option');
    if (empty($title)) {
        $title = get_field($args['fallback_option'] . '_title', 'option') ?: __('Chứng nhận & Giải thưởng', 'canhcamtheme');
    }
}

// Defensive: Không render thẻ HTML rỗng nếu không có dữ liệu
if (empty($items) || !is_array($items)) {
    return;
}
?>
<section class="section-certification section-py <?php echo esc_attr(trim($args['bg_class'] . ' ' . $args['wrapper_class'])); ?>">
    ...
</section>
```

### 2.2. Quy Chuẩn Atomic Data Cards (Tầng 3)
- Mỗi Custom Post Type chỉ sở hữu **duy nhất 1 card template** đặt tại `template-parts/cards/card-{post-type}.php` (trừ trường hợp thiết kế có card hero đặc biệt được duyệt rõ trong hợp đồng dự án).
- Card được tái sử dụng đồng thời ở: Trang danh sách (Archive/Taxonomy), Slider trang chủ/chi tiết, Kết quả tìm kiếm (Search), và AJAX filter.
- Card hỗ trợ tham số modifier qua `$args['modifier']` (ví dụ: `'card-big'`, `'card-compact'`, `'featured-list'`, `'grid'`).

### 2.3. Bảng mapping chuẩn duy nhất

Architect trả đúng 5 cột dưới đây. Ghi “không áp dụng” khi section không cần ACF; không ép một ACF tab cho card hoặc component đọc dữ liệu từ query.

| Section (CSS class đầu tiên) | Tầng component | ACF Tab / không áp dụng | File dự kiến | Nguồn dữ liệu |
|---|---|---|---|---|
| `section-about` | Page Section | Giới thiệu | `template-parts/about/section-about.php` | ACF page group |

### 2.4. Quy tắc nhận diện thành phần Đa Trang (Cross-Page Classification)
- Trước khi lập bảng mapping cho 1 trang, đối chiếu mục **Hợp đồng dùng chung** trong `HANDOVER_TRACKING.md` (hoặc output của `verify_theme.py --inventory`).
- Nếu một `<section class="section-xyz">` xuất hiện ở $\ge 2$ file HTML trong `UI/`, Architect **phải** phân loại nó vào `Global` (`modules/common/`) hoặc `Shared` (`template-parts/shared/section-xyz.php`), không tạo bản sao cục bộ trong `template-parts/{page}/`.
- Mọi danh sách lặp lại của thực thể nội dung (Bài viết, Sản phẩm, Dự án, Sân golf, Đánh giá) phải quy chiếu về `Atomic Card` (`template-parts/cards/card-{cpt}.php`).

---

## 3. QUY CHUẨN DANH MỤC PHÂN CẤP & BỘ LỌC CHÉO (TAXONOMY & AUXILIARY ENGINE)

### 3.1. Cấu Trúc Term Gốc (Root Term) & Term Con (Child Terms)
- **Khi áp dụng:** Custom taxonomy phân cấp (`'hierarchical' => true`).
- **Quy tắc phân cấp:**
  - **Bậc 1 (Root Term):** `parent == 0`. Là danh mục bao trùm toàn bộ ngành hàng (ví dụ: "Sản phẩm", "Tin tức").
  - **Bậc 2 (Child Terms):** `parent == root_term_id`. Là danh mục chuyên môn (ví dụ: "Thịt gà", "Thịt heo").
  - Bài viết được gán trực tiếp vào Term Cấp 2.
- **Hành vi URL:**
  - Truy cập URL Term Cấp 1: Trả về **`HTTP 200 OK`**. Main Query tự động nạp toàn bộ bài viết của chính nó và các term con nhờ `'include_children' => true` mặc định.

### 3.2. Thanh Điều Hướng Tab (`ul.nav-primary`)
- **Tại Term Gốc (Root Term):**
  1. Tab **"Tất cả"**: Active khi đang ở Term gốc, trỏ về chính URL Term gốc.
  2. Danh sách các **Term con Cấp 2**: Trỏ về URL từng term con tương ứng.
- **Tại Term Con (Child Term):**
  - Hiển thị tab "Tất cả" (trỏ về Term cha) + Danh sách các Term anh em cùng cấp cha (Siblings).

### 3.3. Auxiliary Taxonomy Engine (Lọc Chéo Phân Loại Phụ)
Khi phân hệ có thêm tiêu chí lọc chéo (ví dụ: `quy_cach`, `xuat_xu`, `thuong_hieu`):
- Không lồng cấp thành Term cấp 3. Bắt buộc đăng ký thành một Custom Taxonomy độc lập gắn vào CPT.
- Bộ lọc truyền qua tham số URL: `?quy_cach=slug#list-section`.
- Helper chuẩn tạo link lọc chéo tự động đồng bộ tham số:
  ```php
  function canhcam_get_filter_term_url($taxonomy, $term_slug, $base_url = '') {
      $base_url = $base_url ?: get_term_link(get_queried_object());
      if (empty($term_slug)) {
          return esc_url(remove_query_arg(array($taxonomy, 'paged'), $base_url));
      }
      return esc_url(add_query_arg(array($taxonomy => $term_slug), remove_query_arg('paged', $base_url)));
  }
  ```
- **Xử lý Main Query:** Lọc tự động thông qua hook `pre_get_posts` tại `inc/function-post-types.php`. Luôn dùng `sanitize_title()` cho tham số URL.

---

## 4. QUY CHUẨN TRANG TÌM KIẾM (MULTI-BLOCK SEARCH)

- **File template:** `search.php`.
- **Cấu hình Post Types:** Khai báo qua mảng cấu hình có hook filter:
  ```php
  $searchable_post_types = apply_filters('canhcam_searchable_post_types', array(
      'product' => array(
          'title'         => __('Sản phẩm', 'canhcamtheme'),
          'card'          => 'template-parts/cards/card-product',
          'grid_class'    => 'grid lg:grid-cols-4 md:grid-cols-3 grid-cols-2 xl:gap-8 gap-base',
          'wrapper_class' => 'section-products',
      ),
      'event'   => array(...),
      'post'    => array(...),
  ));
  ```
- **Quy tắc hiển thị:**
  1. **Thanh Nav tổng quan:** Hiển thị tab "Tất cả" kèm tổng số kết quả `total_all` và các tab Post Type có kết quả đếm được.
  2. **Chế độ xem tổng quan (`empty($_GET['post_type'])`):** Mỗi khối dùng `search_overview_limit` đã chốt trong `PROJECT_OVERRIDES.md`; nếu có thêm kết quả thì hiển thị nút "Xem tất cả" trỏ về `?s={key}&post_type={pt_key}`. Không phân trang từng khối.
  3. **Chế độ xem chi tiết 1 Post Type (`!empty($_GET['post_type'])`):** Dùng `search_detail_per_page` từ overlay và phân trang số chuẩn `paginate_links()`.
- **Giới hạn tìm kiếm chỉ theo tiêu đề:**  
  Filter `posts_search` trong `inc/function-custom.php` giới hạn tìm kiếm chỉ theo `post_title`, bắt buộc có điều kiện `!is_admin()` để không ảnh hưởng trang quản trị.

---

## 5. QUY CHUẨN BANNER TẬP TRUNG (GLOBAL BANNER)

Chỉ áp dụng khi HTML có banner/hero **và** `PROJECT_OVERRIDES.md` xác nhận hợp đồng CPT `banner`. Page khác không tự thêm banner.

- **Đăng ký CPT:** `banner` với `'publicly_queryable' => false`, `'supports' => array('title')`.
- **Gán Banner:** Field Post Object `select_banner` chỉ gán vào Page templates/Taxonomies có banner theo mapping đã duyệt.
- **Component dùng chung:** `modules/common/banner.php`.
- **Quy tắc gọi:** Tại mọi template cần banner, gọi duy nhất:
  ```php
  get_template_part('modules/common/banner');
  ```
- **Fallback 2 chiều & Zero DOM rác:** Thiếu ảnh mobile tự lấy desktop; thiếu ảnh desktop tự lấy mobile; không chọn banner thì `return;` (tuyệt đối không render thẻ wrapper rỗng).

---

## 6. QUY CHUẨN MÔ HÌNH HÓA DỮ LIỆU & ACF LOCAL JSON (ACF DATA MODELING)

### 6.1. Quy Tắc Vàng Đối Với Relationship & Post Object
1. ❌ **CẤM:** Trong cấu hình JSON của ACF Relationship, thuộc tính `"taxonomy"` **BẮT BUỘC ĐỂ TRỐNG** (`"taxonomy": ""`).
   - *Lý do:* Khai báo tên taxonomy vào mảng sẽ khiến cơ chế split `:{term_id}` của ACF Core sinh ra `tax_query` sai lệch, khiến kết quả AJAX search bị trả về rỗng.
   - Chỉ bật bộ lọc giao diện: `"filters": ["search", "taxonomy"]`.
2. **Ma trận lựa chọn `post_object` vs `relationship`:**
   - Dùng `post_object`: Khi chọn **1 đối tượng duy nhất** (Banner `select_banner`, Page đích `opt_retail_stores_page`, Featured Post). Return format: `"id"`.
   - Dùng `relationship`: Khi chọn **nhiều đối tượng** có sắp xếp thứ tự và lọc kép theo danh mục (Sản phẩm nổi bật `tab_products`, Bài viết liên quan). Return format: `"object"` hoặc `"id"`.
3. **Phân định `gallery` vs `repeater`:**
   - Dùng `gallery` cho danh sách ảnh thuần túy (album ảnh sản phẩm, gallery nhà máy, slider logo). Dữ liệu lưu trong 1 dòng meta duy nhất.
   - ❌ **CẤM:** Tuyệt đối không tạo `repeater` chỉ chứa duy nhất 1 sub_field kiểu `image` (làm phình CSDL gấp $2N+1$ lần).
4. **Hạn chế `clone field` trong Local JSON:** Dùng Pattern Schema chuẩn thay vì clone field để tránh lỗi key mồ côi khi đồng bộ Git giữa các môi trường.

### 6.2. Quy Ước Đặt Tên Field, Tabs & Chống Trùng Lặp `field_key` Đa Trang
- **Tên file ACF page mới mặc định:** `acf-json/group_page_{page_key}.json`; key group `group_page_{page_key}`, với `page_key` là slug kỹ thuật ASCII dùng dấu gạch dưới (ví dụ `about`, `news_list`). Giữ tên file/key đã tồn tại trong dự án; mọi ngoại lệ ghi ở `PROJECT_OVERRIDES.md` trước khi tạo JSON. Không dùng song song `group_{page}_page.json` cho page mới.
- **Định danh `key` duy nhất toàn cục (Mandatory Key Namespacing):**
  - Trong WordPress ACF, thuộc tính `"key"` của mọi group, tab, field và sub_field phải **duy nhất trên toàn bộ thư mục `acf-json/`**.
  - Khi tạo JSON cho page/CPT, bắt buộc gắn tiền tố `{page_key}` hoặc `{cpt_key}` vào `"key"` của từng field:
    - Tab key: `field_{page_key}_tab_{section}`
    - Field key: `field_{page_key}_{section}_{field_name}`
    - Sub-field key (trong Repeater/Group): `field_{page_key}_{section}_{sub_field_name}`
  - ❌ **CẤM** đặt `"key"` chung chung không có tiền tố trang (như `"field_item_title"`, `"field_show_section"`, `"field_section_title"`) vì sẽ đụng độ trực tiếp với trang khác khi chạy nhiều `acf-builder` song song.
- **Tiền tố `name` của sub_fields trong Repeater:** Thuộc tính `"name"` bắt đầu bằng `item_*` (ví dụ: `item_title`, `item_desc`, `item_image`, `item_link`, `item_icon`), nhưng thuộc tính `"key"` vẫn phải mang đầy đủ namespace `field_{page_key}_{section}_item_*`.
- **Cờ bật/tắt Section:** Tab đại diện cho mỗi section luôn có field đầu tiên `show_{section}` (type: `true_false`, UI: `1`, default: `1`).
- **Đoạn văn mô tả `<p>`:** BẮT BUỘC dùng `"type": "wysiwyg"`, toolbar `"basic"`, `"media_upload": 0`. ❌ **CẤM** dùng `textarea` cho nội dung văn bản.
- **SVG Icon:** BẮT BUỘC dùng `"type": "image"`, `"mime_types": "svg"`. ❌ **CẤM** dùng `textarea` dán mã SVG thô (nguy cơ XSS và vỡ DOM).
- **Giao diện Metabox:** `"style": "default"`. ❌ **CẤM** `"seamless"`.

### 6.3. Bốn Mẫu Cấu Hình Chuẩn (Pattern Templates)
1. **Accordion Repeater:** Gập mở FAQ, thông số kỹ thuật (`item_title`, `item_is_active`, `item_content`, `item_image`).
2. **Rich Gallery Slider:** Slider hình ảnh có chú thích (`item_image`, `item_title`, `item_desc`, `item_link`).
3. **Media Hero / Video Popup:** Bật tắt linh hoạt giữa ảnh tĩnh và popup video (`media_type`, `image`, `video_url`).
4. **Grid Card Layout Selector:** Lựa chọn bố cục lưới 3 cột, 4 cột hoặc slider (`layout_type`, `items`).

---

## 7. HỆ THỐNG OPTIONS PAGES ĐA TẦNG (HIERARCHICAL THEME OPTIONS)

Đọc `options_menu_slug` trong `PROJECT_OVERRIDES.md` trước khi tạo options page/field. Nếu chưa có, hỏi main; slug trong ví dụ PHP bên dưới **không phải** cấu hình dự án. Chia subpages khi số lượng field và nghiệp vụ cần, thay vì tạo đủ subpages mẫu cho mọi theme.

```php
// Đăng ký tại inc/function-setup.php hoặc inc/function-field.php
add_action('acf/init', function () {
    if (!function_exists('acf_add_options_page')) return;
    $options_menu_slug = 'replace-with-project-slug'; // Ví dụ: thay bằng options_menu_slug đã chốt trong PROJECT_OVERRIDES.md.

    // Menu cha (Redirect về subpage đầu tiên)
    acf_add_options_page(array(
        'page_title' => __('Cài đặt Giao diện', 'canhcamtheme'),
        'menu_title' => __('Theme Options', 'canhcamtheme'),
        'menu_slug'  => $options_menu_slug, // lấy từ PROJECT_OVERRIDES.md
        'capability' => 'edit_theme_options',
        'redirect'   => true,
        'icon_url'   => 'dashicons-admin-customizer',
        'position'   => 59,
    ));

    // Subpage 1: Header & Logo (opt_header_*)
    acf_add_options_sub_page(array(
        'page_title'  => __('Cài đặt Header & Điều hướng', 'canhcamtheme'),
        'menu_title'  => __('Header & Logo', 'canhcamtheme'),
        'parent_slug' => $options_menu_slug,
        'menu_slug'   => 'opt-header-settings',
    ));

    // Subpage 2: Footer & Mạng xã hội (opt_footer_*)
    acf_add_options_sub_page(array(
        'page_title'  => __('Cài đặt Footer & Chân trang', 'canhcamtheme'),
        'menu_title'  => __('Footer & Mạng xã hội', 'canhcamtheme'),
        'parent_slug' => $options_menu_slug,
        'menu_slug'   => 'opt-footer-settings',
    ));

    // Subpage 3: Bán hàng & Phân hệ (opt_product_*)
    acf_add_options_sub_page(array(
        'page_title'  => __('Cài đặt Bán hàng & Phân hệ', 'canhcamtheme'),
        'menu_title'  => __('Bán hàng & Phân hệ', 'canhcamtheme'),
        'parent_slug' => $options_menu_slug,
        'menu_slug'   => 'opt-product-settings',
    ));

    // Subpage 4: Mã nhúng & Scripts (opt_script_*) - Bảo vệ quyền manage_options
    acf_add_options_sub_page(array(
        'page_title'  => __('Mã Nhúng & Tracking (Head/Body)', 'canhcamtheme'),
        'menu_title'  => __('Mã Nhúng (Scripts)', 'canhcamtheme'),
        'parent_slug' => $options_menu_slug,
        'menu_slug'   => 'opt-script-settings',
        'capability'  => 'manage_options',
    ));
});
```

### Helper Chuẩn Lấy Dữ Liệu Option:
Luôn dùng chuỗi `'option'` (số ít, chuẩn ACF Core), đi kèm helper an toàn:
```php
function canhcam_get_option($key, $default = null) {
    $value = get_field($key, 'option');
    return ($value !== null && $value !== '' && $value !== false) ? $value : $default;
}
```

---

## 8. QUY CHUẨN LẬP TRÌNH PHP, HIỆU NĂNG & HELPER CHUẨN

### 8.1. Nâng Cấp Helper Xử Lý Ảnh & Lazyload Lozad
BẮT BUỘC dùng helper chuẩn của theme, tích hợp sẵn tham số `$custom_attr` và fallback an toàn để **TRIỆT TIÊU 100% VIỆC VIẾT THẺ `<img>` THÔ**:

```php
// ACF Image Array, Attachment ID hoặc URL
echo get_image_attrachment($image_data, 'image', [
    'class'        => 'w-full h-full object-cover',
    'fallback_url' => THEME_URI . '/img/default-thumb.jpg',
    'alt'          => 'Tên mô tả ảnh',
]);

// Post Featured Image
echo get_image_post(get_the_ID(), 'image', [
    'class'        => 'card-thumb-img',
    'fallback_url' => THEME_URI . '/img/default-thumb.jpg',
]);

// Lấy trực tiếp mã nguồn SVG nội bộ theme (0 HTTP request, đổi màu CSS linh hoạt)
echo canhcam_get_theme_svg('img/icons/arrow-right.svg', 'w-5 h-5 text-Primary-1');
```

### 8.2. Kỹ Thuật Anti-N+1 Query (Single Batch Query + In-Memory Grouping)
❌ **CẤM:** Tuyệt đối không gọi `get_posts()` hoặc `WP_Query` bên trong vòng lặp term/category.  
✅ **ĐÚNG:** Chạy 1 query duy nhất lấy toàn bộ bài viết của tất cả các term qua `terms => wp_list_pluck($terms, 'term_id')`, sau đó dùng PHP gom nhóm bài viết theo term ID trong bộ nhớ.

### 8.3. Bốn Cờ Tối Ưu Bắt Buộc Cho `WP_Query` Không Phân Trang
```php
$args = array(
    'post_type'              => 'product',
    'posts_per_page'         => 8,
    'no_found_rows'          => true,  // Tắt đếm tổng dòng (Tối ưu SQL cực lớn)
    'ignore_sticky_posts'    => true,  // Bỏ qua sticky posts
    'update_post_meta_cache' => true,  // Nạp sẵn meta cache 1 lần
    'update_post_term_cache' => false, // Tắt nếu không dùng term của bài viết
);
```

### 8.4. Ma Trận Escaping & Quốc Tế Hóa (i18n)
- Plain text / Nhãn tĩnh: `echo esc_html($title);`, `esc_html__('Xem thêm', 'canhcamtheme')`.
- Thuộc tính HTML (class, id, data-*): `echo esc_attr($class);`.
- Đường dẫn URL: `echo esc_url($btn['url']);`.
- Đoạn văn WYSIWYG: `echo wp_kses_post($content);` và **BẮT BUỘC bọc trong thẻ `<div>`** (cấm thẻ `<p>`).
- Số nguyên: `absint()`, `intval()`.
- Text domain: `'canhcamtheme'`. Không bọc `__()` quanh kết quả trả về từ `get_field()`.

### 8.5. Quy Chuẩn Bảo Toàn DOM, CSS Selector & JS Data Attributes (DOM Parity)
1. **Bảo toàn Section Root & Thứ tự hiển thị:** Mọi `<section class="section-xyz ...">` trong file `UI/{Page}.html` phải được ánh xạ đầy đủ sang template/template-part tương ứng, giữ nguyên 100% các class CSS gốc trên thẻ `<section>`.
2. **Bảo toàn cấu trúc bao bọc ảnh khi dùng Helper (ZTR-04):**
   - Giữ nguyên thẻ bao ngoài của ảnh trong HTML gốc (`<div class="img-ratio ...">`, `<a data-fancybox="...">`, `<div class="swiper-slide">`).
   - Truyền toàn bộ class trên thẻ `<img>` của HTML gốc vào tham số `'class'` của `get_image_attrachment()` hoặc `get_image_post()`.
3. **Bảo toàn Typography khi đổi `<p>` sang `<div>` cho WYSIWYG (ZTR-15):**
   - Khi thay `<p class="body-1 text-Utility-gray-700">` bằng `<div>` để bọc `wp_kses_post($wysiwyg)`, bắt buộc chuyển toàn bộ class từ thẻ `<p>` gốc lên thẻ `<div>` để không làm gãy style văn bản.
4. **Bảo toàn JS Hooks (`data-*` & class điều khiển):**
   - Không tự ý đổi hoặc xóa các class/attribute phục vụ JS trong `main.min.js` / `core.min.js` (ví dụ: `.swiper`, `.swiper-wrapper`, `.swiper-slide`, `data-fancybox`, `data-tab`, `data-toggle`, `.tab-item`, `.tab-panel`).

---

## 9. QUY CHUẨN TƯƠNG TÁC FRONTEND & AJAX AN TOÀN

### 9.1. Nguyên Tắc "Zero Inline Scripts"
- Cấm viết mã `<script>` inline bên trong các file PHP template (`template-system.php`, `taxonomy-*.php`, `content-faq.php`).
- Mọi logic JavaScript phải viết trong file riêng tại thư mục `scripts/modules/` và nạp qua `wp_enqueue_script()`.
- Biến môi trường và Nonce được truyền qua `wp_localize_script()`.

### 9.2. Quy Chuẩn Handler AJAX An Toàn (Backend)
Mọi AJAX action bắt buộc phải tuân thủ:
```php
// inc/function-ajax.php
function canhcam_ajax_filter_stores() {
    // 1. Xác thực Nonce bảo mật bắt buộc
    check_ajax_referer('canhcam_ajax_nonce', 'nonce');

    // 2. Sanitize dữ liệu đầu vào nghiêm ngặt
    $region_id = isset($_POST['region_id']) ? absint($_POST['region_id']) : 0;
    $keyword   = isset($_POST['keyword']) ? sanitize_text_field(wp_unslash($_POST['keyword'])) : '';

    // 3. Thực thi truy vấn tối ưu
    ...

    // 4. Trả về JSON chuẩn
    wp_send_json_success(array(
        'html'  => $rendered_html,
        'total' => $query->found_posts,
    ));
}
add_action('wp_ajax_canhcam_filter_stores', 'canhcam_ajax_filter_stores');
add_action('wp_ajax_nopriv_canhcam_filter_stores', 'canhcam_ajax_filter_stores');
```

---

## 10. CƠ CHẾ BIẾN THỂ DỰ ÁN & BỘ BA BẮT BUỘC (PROJECT VARIANTS ENGINE)

Khi một dự án cần thay đổi hành vi chuẩn (ví dụ: chuyển hướng 301 term cấp 1 sang term con đầu tiên theo yêu cầu thiết kế), hệ thống bắt buộc phải thực thi qua cơ chế cờ hiệu:

1. **Helper Kiểm Tra Cờ Hiệu:**
   ```php
   function canhcam_root_term_redirect_enabled($taxonomy = '') {
       return (bool) apply_filters('canhcam_enable_root_term_redirect', false, $taxonomy);
   }
   ```
2. **Bộ Ba Bắt Buộc Khi Bật Biến Thể 301 (Variant Triad):**
   - **Khâu 1 (Routing Tập Trung):** Điều phối chuyển hướng tại hook `template_redirect` trong `inc/function-custom.php`. **Tuyệt đối cấm viết `wp_safe_redirect()` trong file template view**.
   - **Khâu 2 (Loại Trừ XML Sitemap):** Dùng hook `rank_math/sitemap/entry` để loại bỏ URL bị redirect khỏi sitemap, tránh lỗi Google Search Console.
   - **Khâu 3 (Breadcrumbs Không Link):** Chuyển node bị chuyển hướng trong breadcrumb thành text thuần không có thẻ `<a>`, tránh vòng lặp bot tìm kiếm.
3. **Đăng Ký Biến Thể:** Bắt buộc ghi nhận mã `VAR-xx` và lý do nghiệp vụ nguyên văn vào file `PROJECT_VARIANTS.md`.

---

## 11. BỘ QUY TẮC LỖI CẤM TUYỆT ĐỐI MỞ RỘNG (18 ZERO TOLERANCE RULES)

Bất kỳ vi phạm nào trong 18 quy tắc dưới đây sẽ bị `wp-reviewer` đánh **`[ACTION REQUIRED]` / `[FAIL]` NGAY LẬP TỨC**:

| Mã | Tên Lỗi Cấm | Quy Cách Bắt Buộc |
|---|---|---|
| **ZTR-01** | Unescaped Output / XSS | Mọi biến in ra phải escape đúng ngữ cảnh (`esc_html`, `esc_attr`, `esc_url`, `wp_kses_post`). Cấm echo trực tiếp `$_GET`/`$_POST`. |
| **ZTR-02** | SQL Injection | Cấm nối chuỗi vào `$wpdb->query()`. Bắt buộc dùng `WP_Query` hoặc `$wpdb->prepare()`. |
| **ZTR-03** | AJAX Thiếu Nonce | Mọi handler AJAX phải có `check_ajax_referer()` và sanitize toàn bộ input. |
| **ZTR-04** | Thẻ `<img>` Thô | Cấm viết thẻ `<img>` trực tiếp trong template, kể cả `data-src`; dùng `get_image_attrachment()` hoặc `get_image_post()` theo helper theme. |
| **ZTR-05** | Dùng `the_post_thumbnail()` | Phải thay bằng `get_image_post()` để đảm bảo class lazyload `lozad`. |
| **ZTR-06** | Dùng `query_posts()` | Tuyệt đối cấm. Bắt buộc dùng `new WP_Query()` hoặc `pre_get_posts`. |
| **ZTR-07** | Quên `wp_reset_postdata()` | Sau vòng lặp đã gọi `the_post()` hoặc `setup_postdata()`, reset postdata. Không bắt buộc reset sau `foreach` chỉ đọc dữ liệu. |
| **ZTR-08** | Truy Vấn N+1 Trong Loop | Cấm gọi `get_posts()`/`WP_Query` lồng trong loop term. Bắt buộc dùng Single Batch Query + In-Memory Grouping. |
| **ZTR-09** | Hardcode ID / URL | Cấm `$term_id = 4`. Dùng `canhcam_get_root_taxonomy_term()`. Cấm URL tĩnh, dùng `home_url('/')` hoặc ACF link. |
| **ZTR-10** | Hardcode Redirect Trong View | Cấm `wp_safe_redirect()` trong file view. Mọi redirect phải nằm ở hook `template_redirect`. |
| **ZTR-11** | ACF Relationship Gán `"taxonomy"` | File JSON relationship bắt buộc để `"taxonomy": ""`, chỉ bật filters UI. |
| **ZTR-12** | ACF Style `"seamless"` | Thuộc tính `"style"` trong JSON bắt buộc là `"default"`. |
| **ZTR-13** | Dùng `"textarea"` Cho Đoạn Văn | Các trường văn bản `<p>` bắt buộc dùng `"wysiwyg"` basic toolbar, cấm `textarea`. |
| **ZTR-14** | ACF Return Format Sai Chuẩn | Image bắt buộc `"return_format": "array"`. Cấm dùng `"url"`. |
| **ZTR-15** | WYSIWYG Bọc Trong Thẻ `<p>` | Nội dung WYSIWYG bắt buộc bọc trong thẻ `<div>` giữ nguyên class typography (tránh lỗi nested block element). |
| **ZTR-16** | Render Thẻ HTML Rỗng | Nếu không có dữ liệu, dùng `return;` bail out lập tức, không render thẻ bao bọc HTML rỗng. |
| **ZTR-17** | Trùng Lặp ACF `key` Toàn Cục | Mọi `group` key và `field` key trong `acf-json/*.json` phải duy nhất toàn site (mang tiền tố `field_{page_key}_{section}_*`). Cấm trùng `field_key` giữa các file JSON. |
| **ZTR-18** | Đứt Gãy DOM / JS Hook Gốc | Cấm bỏ sót `<section class="...">` hoặc làm mất class CSS đầu tiên / thuộc tính `data-*` kích hoạt JS (Swiper, Fancybox, Tabs) so với file HTML nguồn. |

---

## 12. Điều phối

State machine, Wave 0/1/2, quyền sở hữu file, spawn contract và bàn giao nằm duy nhất ở `AGENTS.md`. Blueprint chỉ giữ quy chuẩn kỹ thuật; không diễn giải lại pipeline ở đây.

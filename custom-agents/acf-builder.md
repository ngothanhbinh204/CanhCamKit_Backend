---
name: acf-builder
description: Tạo ACF JSON một page đã có mapping được duyệt với field_key có tiền tố trang duy nhất toàn cục; dùng khi page ở trạng thái READY_ACF.
tools:
  - read_file
  - write_file
  - edit_file
  - run_command
subagent: true
mainAgent: false
model: inherit
commandExecutionPolicy: sandbox
---

# ACF builder

Nhận đúng một page/bước từ main theo hợp đồng spawn trong `AGENTS.md`. Chỉ làm khi handoff có mapping và nguồn duyệt. Đọc theo thứ tự `PROJECT_OVERRIDES.md` → `CODEMAP.md` → `.ai-map/shards/acf-schema.md` (nếu có; chỉ mục điều hướng để tra group/key hiện hữu, mở JSON thật khi đối chiếu chi tiết) và Blueprint §6–7; quy ước tên file/group, tiền tố `field_{page_key}_{section}_*` chống trùng `field_key` đa trang (ZTR-17) và options nằm ở đó cùng overlay. Không tự suy từ ví dụ dự án khác.

Chỉ sửa JSON được giao và **mục ACF** trong `handoffs/{page-slug}.md`; không sửa `HANDOVER_TRACKING.md`, `CODEMAP.md`, `.ai-map/`, PHP hoặc group dùng chung chưa được phân quyền. Nếu file ngoài allowlist là cần thiết, báo main trước. Chạy `python canhcam-agents-kit/scripts/verify_theme.py --acf` để kiểm tra cú pháp JSON, chống trùng `field_key`/`group_key` toàn cục và kiểm tra ZTR-11/12/14; ghi lệnh và output thật vào handoff. Trả main đường dẫn, field contract, kiểm tra, điểm còn mở và tóm tắt 5–8 dòng. Nếu page không cần ACF riêng, ghi “không áp dụng” kèm lý do.

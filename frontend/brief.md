Backend + Frontend + Database — Chức năng đủ theo tiêu chí BTC (MVP bắt buộc)

Tôi chỉ đưa vào đây những gì map trực tiếp vào tiêu chí chấm điểm và ràng buộc bắt buộc của đề bài. Variant generation song song, generative b-roll... để sau khi xong phần lõi này.

Luồng lõi cần cover: Nhập brief → Sinh storyboard (reasoning) → Compliance check → Duyệt (HITL) → Render → QA → Xuất video.

1. FRONTEND — Giao diện

Backend là API boundary duy nhất — FE chỉ gọi Backend, không bao giờ gọi thẳng Agent/Data.

1.1 Màn hình Brief Intake Form

Nhập đủ 8 nhóm nguyên liệu + upload asset. Nên chia thành các section trong 1 trang (không wizard nhiều bước — giám khảo cần nhập/prefill nhanh).

Section trong form:

Product info (tên, category, giá, USP, features, ưu đãi, allowed claims)
Asset upload (hero/cận cảnh/lifestyle/variant/logo) — dropzone, preview ảnh
Audience (đối tượng, pain point, nhu cầu)
Objective (select: Conversion/Lead/Traffic/Awareness)
Key message (text)
Channel (select: TikTok/Reels/Meta — tự set ratio/duration mặc định)
Creative reference (optional: link video mẫu, style note)
Constraints (duration, ratio override, ngôn ngữ, CTA bắt buộc, banned claims — list)

API gọi:

POST /api/v1/briefs — tạo brief (JSON, chưa có asset)
POST /api/v1/briefs/{brief_id}/assets — upload từng file (multipart)
GET /api/v1/briefs/{brief_id} — load lại nếu edit
1.2 Màn hình Brief List / Dashboard

Danh sách brief đã tạo, trạng thái (draft/reasoning/awaiting_approval/rendering/done/failed) — cần thiết vì giám khảo có thể muốn thấy nhiều bộ input chạy song song.

API gọi:

GET /api/v1/briefs?status=&page=
1.3 Màn hình Storyboard Review (Action Card — Phase 1 HITL)

Đây là màn hình quan trọng nhất để "thuyết phục" — show reasoning minh bạch trước khi render.

Hiển thị:

Hook copy (2-3s đầu)
Danh sách shot: role (hook/product/benefit/cta), asset dùng (thumbnail thật), overlay text, thời lượng
Cảnh báo compliance nếu có câu bị chặn (kèm lý do — claim nào vi phạm)
Nút Approve & Render / Regenerate / Edit thủ công (sửa overlay text tay nếu muốn — cộng điểm UX)

API gọi:

POST /api/v1/briefs/{brief_id}/storyboard — trigger sinh storyboard (gọi lần đầu khi vào màn hình từ Brief Form)
GET /api/v1/storyboards/{storyboard_id}
POST /api/v1/storyboards/{storyboard_id}/regenerate
PATCH /api/v1/storyboards/{storyboard_id} — sửa tay overlay/hook nếu cho phép edit
POST /api/v1/storyboards/{storyboard_id}/approve — duyệt → trigger render
1.4 Màn hình Render Progress

Polling trạng thái render (vì render không tức thời).

API gọi:

GET /api/v1/renders/{render_id} (poll mỗi 2-3s, hoặc SSE/WebSocket nếu kịp)
1.5 Màn hình Result / Video Player

Xem video kết quả, QA report (đúng tỉ lệ/thời lượng/asset xuất hiện đủ), nút download, nút "Tạo thêm bản khác" (quay lại Storyboard Review để regenerate).

API gọi:

GET /api/v1/renders/{render_id}/result
GET /api/v1/videos/{video_id}/download
1.6 Màn hình Brief → Videos (phục vụ yêu cầu nộp "3 mẫu từ 3 input khác nhau")

Danh sách video đã sinh ra theo từng brief — để đóng gói nộp bài dễ dàng.

API gọi:

GET /api/v1/briefs/{brief_id}/videos
2. BACKEND — API

Backend expose API cho FE, và là nơi duy nhất gọi Agent pod + Data pod (sync HTTP timeout dài, đúng nguyên tắc bạn đã chốt).

2.1 Brief & Asset
Method	Path	Việc làm	Gọi Agent/Data
POST	/api/v1/briefs	Validate đủ 8 nhóm, lưu DB (status=draft)	—
POST	/api/v1/briefs/{id}/assets	Nhận file, lưu metadata	Gọi Data: POST /data/storage/upload (lưu object storage) + POST /data/assets/process (chuẩn hoá/cutout nền nếu cần)
GET	/api/v1/briefs/{id}	Trả brief + assets	—
GET	/api/v1/briefs	List có filter status	—
2.2 Storyboard (Reasoning + Compliance)
Method	Path	Việc làm	Gọi Agent/Data
POST	/api/v1/briefs/{id}/storyboard	Build context từ brief, gọi Agent reasoning, lưu StoryboardPlan (status=awaiting_approval hoặc blocked nếu vi phạm claim)	Gọi Agent: POST /agent/reasoning/storyboard (trả StoryboardPlan + ComplianceResult)
GET	/api/v1/storyboards/{id}	Trả storyboard + shots + compliance warnings	—
PATCH	/api/v1/storyboards/{id}	Sửa tay overlay/hook	—
POST	/api/v1/storyboards/{id}/regenerate	Gọi lại reasoning (có thể truyền feedback lý do reject)	Gọi Agent: POST /agent/reasoning/storyboard (regenerate mode)
POST	/api/v1/storyboards/{id}/approve	Đổi status → approved, trigger render job	Gọi Agent: POST /agent/render (async, trả render_id/task_id ngay)
2.3 Render & QA
Method	Path	Việc làm	Gọi Agent/Data
GET	/api/v1/renders/{id}	Poll trạng thái (queued/rendering/qa_checking/done/failed)	Gọi Agent: GET /agent/render/{task_id}/status (hoặc Agent tự callback webhook về Backend khi xong — ưu tiên webhook nếu kịp, đơn giản hơn thì polling)
GET	/api/v1/renders/{id}/result	Trả video info + QA report (ratio/duration/asset_visible_ratio)	— (đọc từ DB đã lưu khi Agent callback xong)
2.4 Video Output
Method	Path	Việc làm	Gọi Agent/Data
GET	/api/v1/briefs/{id}/videos	List video đã render xong theo brief	—
GET	/api/v1/videos/{id}/download	Stream file video	Gọi Data: GET /data/storage/{key} (proxy stream) hoặc trả presigned URL trực tiếp

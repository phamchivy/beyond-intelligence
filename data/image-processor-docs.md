# Image Processor — Data pod

> Tài liệu ngắn gọn giải thích component này làm gì. Code nằm ở [`image_processor/`](image_processor/).
> Chi tiết API cho Backend gọi: xem [image-processor-api.md](image-processor-api.md).
>
> **Phạm vi hiện tại đã thu hẹp có chủ đích:** chỉ còn `POST /data/assets/process`. Không có
> Postgres (không ai đọc lại metadata), không có API đọc file theo key, không có API lưu video —
> tất cả bị bỏ vì chưa có use case nào thật sự cần, giữ nguyên tắc không dựng trước cái chưa dùng.

## Nó là gì

Đây là phần **xử lý ảnh + lưu trữ file nhị phân** của Data pod, theo kiến trúc mô tả trong
`hackathon_docs/system-integration-flow.md`. Backend và Agent không tự quản lý file ảnh/video —
tất cả đi qua component này.

## Nó làm 3 việc

**1. Chuẩn hoá ảnh (bắt buộc)**
Ảnh khách hàng upload lên rất tuỳ tiện: kích thước bất kỳ, sai chiều xoay (do EXIF), định dạng
JPEG/PNG/WEBP lẫn lộn. Component này:
- Xoay ảnh đúng chiều (ảnh chụp bằng điện thoại hay bị nghiêng)
- Resize về chiều dài cạnh lớn nhất tối đa (mặc định 4096px), **không phóng to** ảnh nhỏ hơn
- Đổi về JPEG (ảnh thường) hoặc PNG (logo cần nền trong suốt)
- Xoá metadata/EXIF (rác + lộ vị trí GPS của khách hàng)

Việc này **không phải để cho đẹp** — ảnh chưa resize thì file lớn, tốn thời gian/băng thông khi
Backend hay Agent tải lại nhiều lần.

> **Lệch so với `system-integration-flow.md` §3.1:** tài liệu đó mô tả Data trả thẳng nội dung
> ảnh (base64) trong response để Backend không phải gọi lại. Bản hiện tại **luôn trả `object_presigned_url`**,
> bỏ hẳn nhánh base64 — đơn giản hoá response, nhưng nghĩa là Backend luôn cần 1 lần `GET` để lấy
> bytes thật. Nếu đọc tài liệu cũ thì phần này đã lỗi thời, ưu tiên theo code + doc này.

**2. Tách nền sản phẩm — cutout (tuỳ chọn)**
Với ảnh vai trò `hero`/`closeup`/`variant` (không áp dụng cho `lifestyle` — nền chính là nội dung,
và `logo` — đã là ảnh phẳng sẵn), component tách sản phẩm khỏi nền, tạo ra 1 ảnh PNG nền trong suốt
riêng. Dùng model segmentation (`rembg`/`u2netp`) chạy local, không gọi ảnh sinh (generative) —
vì sinh ảnh sẽ vẽ lại sản phẩm, không còn đúng sản phẩm thật của khách hàng.

Chất lượng phụ thuộc độ phức tạp của nền: nền phòng chụp sạch → tách rất tốt; nền đường phố/đám
đông → còn viền mờ/dính sót. Đây là giới hạn đã biết của model nhỏ đang dùng (`u2netp`), không phải
lỗi. Nếu cần tốt hơn, đổi `CUTOUT_BACKEND=replicate` (model lớn hơn, chạy qua API ngoài).

**3. Lưu trữ ảnh đã xử lý**
- Đọc ảnh gốc đã có sẵn trên object storage (S3) theo `object_key` do Backend cung cấp
  (Backend tự upload file gốc, Data **không** nhận file nhị phân qua request nữa)
- Ghi ảnh đã chuẩn hoá + ảnh cutout vào storage
- Trả URL tải trực tiếp (`object_presigned_url`/`cutout_presigned_url`) ngay trong response — không cần gọi thêm
  API nào khác để lấy bytes

## Vị trí trong luồng (theo `system-integration-flow.md`)

```
Bước 2   Backend upload ảnh gốc lên S3 → gọi Data xử lý → nhận lại URL ảnh đã chuẩn hoá + cutout
```

> Bước 5-6 (Agent đọc lại cutout lúc render) và bước 11 (lưu video render vĩnh viễn) **chưa có
> implementation** — đã bỏ cùng lúc với việc thu hẹp API. Component hiện tại chỉ phủ bước 2. Nếu
> sau này Agent/VideoRenderer cần đọc lại cutout hoặc lưu video, phải làm thêm endpoint mới.

## Không làm gì

- Không lưu metadata nghiệp vụ (task/brief/storyboard) — đó là việc của Backend
- Không gọi LLM, không reasoning — đó là việc của Agent
- Không sửa/xoá file gốc khách hàng upload
- Không đảm bảo cutout luôn thành công — thất bại thì vẫn trả về ảnh đã chuẩn hoá bình thường,
  không làm hỏng cả request

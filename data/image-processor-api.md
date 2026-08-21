# Image Processor API — dành cho Backend team

> Giải thích component làm gì: xem [image-processor-docs.md](image-processor-docs.md).
> Tài liệu này là contract kỹ thuật để Backend tích hợp.
>
> Data pod hiện chỉ có **1 endpoint nghiệp vụ**: `POST /data/assets/process`. Không có API đọc
> lại file theo key, không có API lưu video — nếu sau này cần thì làm thêm, hiện tại chưa có
> use case nào dùng nên không dựng trước.

## Base URL & auth

```
DATA_SERVICE_URL = http://data:8002        (trong docker-compose, service name "data")
```

Endpoint nghiệp vụ yêu cầu header:

```
X-Internal-Token: <giá trị INTERNAL_TOKEN dùng chung giữa Backend và Data>
```

Sai/thiếu token → `401`.

---

## ⚠️ Trước khi gọi: Backend tự upload ảnh gốc

Data pod **không nhận file nhị phân** qua API. Backend phải tự `PutObject` ảnh gốc lên S3
trước, theo đúng quy ước key sau, rồi mới gọi Data với `object_key`:

```
key = "{task_id}/{asset_id}.{ext}"
```

`task_id`, `asset_id` do Backend tự sinh (UUID). Bucket thật hiện tại là **`beyond-videos`** (region
`ap-southeast-1`), ảnh gốc upload vào key có prefix `raw-assets/` bên trong bucket đó, tức là:

```
PutObject vào bucket "beyond-videos", key = "raw-assets/{task_id}/{asset_id}.{ext}"
```

Khi gọi `/data/assets/process`, `object_key` gửi lên **không cần** prefix `raw-assets/` — chỉ cần
`{task_id}/{asset_id}.{ext}`, Data tự thêm prefix khi tra cứu. Credentials S3 (access key/secret)
phải khớp với cấu hình Data đang dùng (xem `data/image_processor/.env`) — đây là điểm cần đồng bộ
config giữa 2 team, không tự suy ra được, hỏi người phụ trách Data pod nếu chưa có.

---

## `POST /data/assets/process`

Chuẩn hoá + (tuỳ chọn) tách nền một batch ảnh của cùng 1 task. Trả về URL tải trực tiếp — không cần
gọi API nào khác để lấy ảnh.

**Request**

```json
{
  "task_id": "uuid",
  "assets": [
    {
      "asset_id": "uuid",
      "object_key": "{task_id}/{asset_id}.jpg",
      "asset_role": "hero",
      "mime_type": "image/jpeg"
    }
  ]
}
```

`asset_role` ∈ `hero | closeup | lifestyle | variant | logo`. `object_key` không cần prefix bucket,
chỉ cần đúng key đã upload ở bước trên.

**Response**

```json
{
  "assets": [
    {
      "asset_id": "uuid",
      "asset_role": "hero",
      "mime_type": "image/jpeg",
      "object_presigned_url": "<URL tạm, tải ảnh đã chuẩn hoá trực tiếp từ S3>",
      "object_ref": "processed-assets/{task_id}/{asset_id}_hero.jpg",
      "cutout_ref": "processed-assets/{task_id}/{asset_id}_hero_cutout.png (hoặc null)",
      "cutout_presigned_url": "<URL tạm, tải ảnh cutout -- null nếu không có cutout>",
      "metadata": {
        "width": 2048, "height": 1365, "bytes": 17057,
        "source_format": "JPEG", "had_alpha": false,
        "cutout": "ok | skipped | failed"
      }
    }
  ],
  "failed": [
    { "asset_id": "uuid", "reason": "raw_object_missing | unsupported_format: ... | invalid_key: ... | internal_error: ..." }
  ]
}
```

**Cách đọc response — quan trọng:**

- Ảnh đã xử lý **không được nhúng thẳng vào response** (không có field base64) — luôn `GET
  object_presigned_url` để lấy bytes thật. URL hết hạn sau `PRESIGN_TTL_SECONDS` (mặc định 1 giờ) —
  dùng ngay sau khi nhận response, không lưu URL này lâu dài.
- `cutout_presigned_url` cùng cơ chế, dùng khi cần ảnh đã tách nền (composite vào video). **Có thể
  null** — do role không thuộc diện tách nền (`lifestyle`, `logo`), hoặc model tách nền thất bại
  (`metadata.cutout == "failed"`). Cả 2 trường hợp asset chính vẫn xử lý thành công bình thường —
  cutout chỉ là phần thêm, không làm hỏng cả asset.
- `object_ref` / `cutout_ref` là **key nội bộ**, chỉ để lưu lại cho mục đích audit/tra cứu (ví dụ
  ghi vào bảng `asset_refs` phía Backend) — **không dùng được để tải file**, vì không có API đọc
  lại theo key. Muốn tải file thì phải dùng `object_presigned_url`/`cutout_presigned_url` nhận được
  ngay lúc gọi.

**HTTP status:**

| Status | Ý nghĩa |
|---|---|
| `200` | Tất cả asset xử lý thành công |
| `207` | Một phần thành công — check cả `assets[]` và `failed[]` |
| `422` | Toàn bộ batch thất bại |
| `401` | Thiếu/sai `X-Internal-Token` |

Một asset lỗi (ảnh hỏng, key sai, file không tồn tại) **không** làm hỏng cả batch — luôn kiểm tra
`failed[]` thay vì chỉ nhìn status code.

**Timeout phía Backend:** đặt HTTP client timeout ≥ 60s — batch nhiều ảnh + cutout có thể mất vài
giây mỗi ảnh, chạy tuần tự có giới hạn concurrency phía Data.

**Retry an toàn:** key đặt tên cố định theo `task_id`/`asset_id`, gọi lại y hệt request sẽ ghi đè
đúng chỗ cũ — an toàn để retry khi mất kết nối giữa chừng, nhưng sẽ chạy lại từ đầu (không có cách
kiểm tra "đã xử lý chưa" trước khi gọi lại).

---

## Ví dụ thật (đã test với `beyond-videos`)

`asset_role: hero`, ảnh JPEG studio sạch — kết quả có cutout thành công.

> URL bên dưới đã hết hạn (`Expires` là timestamp quá khứ) và `AWSAccessKeyId` đã bị xoá khỏi ví
> dụ — không dùng được để tải file, chỉ để tham khảo hình dạng response thật.

**Request** — `POST /data/assets/process`, header `X-Internal-Token: <token>`

```json
{
  "task_id": "f1231858-07cf-444a-8a15-d4a5650113dd",
  "assets": [
    {
      "asset_id": "2de75dbf-2837-4bc0-b966-c72ed766a485",
      "object_key": "f1231858-07cf-444a-8a15-d4a5650113dd/2de75dbf-2837-4bc0-b966-c72ed766a485.jpg",
      "asset_role": "hero",
      "mime_type": "image/jpeg"
    }
  ]
}
```

**Response** — `HTTP 200`

```json
{
  "assets": [
    {
      "asset_id": "2de75dbf-2837-4bc0-b966-c72ed766a485",
      "asset_role": "hero",
      "mime_type": "image/jpeg",
      "object_presigned_url": "https://beyond-videos.s3.amazonaws.com/processed-assets/f1231858-07cf-444a-8a15-d4a5650113dd/2de75dbf-2837-4bc0-b966-c72ed766a485_hero.jpg?AWSAccessKeyId=<redacted>&Signature=pjj%2By4cVtKPEC8%2FL7Yf94mzxDQk%3D&Expires=1787320195",
      "object_ref": "processed-assets/f1231858-07cf-444a-8a15-d4a5650113dd/2de75dbf-2837-4bc0-b966-c72ed766a485_hero.jpg",
      "cutout_ref": "processed-assets/f1231858-07cf-444a-8a15-d4a5650113dd/2de75dbf-2837-4bc0-b966-c72ed766a485_hero_cutout.png",
      "cutout_presigned_url": "https://beyond-videos.s3.amazonaws.com/processed-assets/f1231858-07cf-444a-8a15-d4a5650113dd/2de75dbf-2837-4bc0-b966-c72ed766a485_hero_cutout.png?AWSAccessKeyId=<redacted>&Signature=w6iN2laDSUxXxcOJGEaEZjIlV54%3D&Expires=1787320195",
      "metadata": {
        "width": 387,
        "height": 516,
        "bytes": 17674,
        "source_format": "JPEG",
        "had_alpha": false,
        "cutout": "ok"
      }
    }
  ],
  "failed": []
}
```

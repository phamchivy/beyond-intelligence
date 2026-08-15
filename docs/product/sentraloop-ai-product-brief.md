# SentraLoop AI — Product Brief & Team Plan

> Tài liệu tổng hợp định hướng sản phẩm cho Cross-border AI Innovation Summit Hanoi 2026.
> Tài liệu này tập trung vào ý tưởng sản phẩm cụ thể sẽ cắm vào platform, và cách chia việc cho đội 5 người.

**Đề bài mục tiêu tham khảo:** dạng đề Video Intelligence Engine (đề thật sẽ được ban tổ
chức công bố tại sự kiện — cấu trúc bên dưới được thiết kế để thích ứng khi đề bài chốt).

---

## 1. Vấn đề & định vị sản phẩm

### Vấn đề thực tế
Tài khoản Ads/kênh TikTok Shop bị khóa hoặc giảm reach vì video dính vi phạm chính sách
(bản quyền nhạc/logo, từ khóa cấm) là rủi ro thực tế và tốn kém đối với seller cross-border.
Đồng thời, seller thường không có căn cứ rõ ràng để biết vì sao một video chuyển đổi tốt
còn video khác thì không — quyết định content phần lớn dựa cảm tính, thiếu dữ liệu lịch sử
hỗ trợ.

### SentraLoop AI giải quyết đồng thời hai việc
1. **An toàn (Content Risk & Auto-Mitigation):** phát hiện vi phạm chính sách trong video,
   tự động khắc phục ở mức rủi ro thấp, đưa ra quyết định chờ phê duyệt ở mức rủi ro cao.
2. **Tăng trưởng (Historical Insight & Advisory):** đối chiếu video mới với dữ liệu lịch sử
   hiệu suất của kênh và sản phẩm đang bán, đưa ra đề xuất cụ thể có dẫn chứng để tăng khả
   năng chuyển đổi.

Cả hai luồng đều đi qua một cơ chế ra quyết định chung (Decision + Policy) và một bước
tương tác người dùng (Human-in-the-Loop) trước khi bất kỳ thay đổi nào được thực thi.

### Điểm khác biệt cần nhắm tới
So với các sản phẩm cùng nhóm đề bài (phát hiện rủi ro nội dung, video intelligence) từng
xuất hiện ở các mùa thi trước — phần lớn dừng ở mức phát hiện và báo cáo (reactive).
SentraLoop AI hướng tới việc đi xa hơn hai điểm:
- **Tự động khắc phục** thay vì chỉ báo lỗi, kèm cơ chế phê duyệt rõ ràng theo mức rủi ro.
- **Đề xuất tăng trưởng dựa trên dữ liệu lịch sử thật của kênh/sản phẩm**, không dừng ở
  kiểm duyệt an toàn đơn thuần.

---

## 2. Kiến trúc tổng thể (map vào 5 layer đã có của Beyond Intelligence)

Không đổi kiến trúc gốc trong `README.MD` — SentraLoop là một business domain cụ thể cắm
vào platform, dùng lại nguyên tầng `agent/` đã dựng.

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│  - Upload video, xem preview co highlight vung loi             │
│  - Man hinh phe duyet (Action/Decision Card)                   │
│  - Bang chung di kem quyet dinh (Evidence Timeline)             │
├─────────────────────────────────────────────────────────────┤
│ BACKEND                                                        │
│  - API nhan video, kich hoat Agent xu ly                        │
│  - Endpoint xu ly hanh dong phe duyet/tu choi                   │
│  - Quan ly trang thai luong xu ly (pending/approved/executed)   │
├─────────────────────────────────────────────────────────────┤
│ DATA                                                            │
│  - Ingest du lieu lich su kenh/san pham (neu co API ben ngoai)  │
│  - Fallback: suy pattern tu metadata video da co san              │
│  - Luu tru ket qua xu ly va phan hoi thuc te de cai thien sau     │
├─────────────────────────────────────────────────────────────┤
│ AGENT                                                            │
│  - Danh gia rui ro noi dung (Evaluator)                          │
│  - Truy xuat du lieu lich su lien quan (Retriever)                │
│  - Suy luan doi chieu pattern, sinh de xuat (LLM reasoning)        │
│  - Thuc thi hanh dong khac phuc/ap dung de xuat (Tool)             │
│  - Kiem soat muc do tu dong hoa theo rui ro (Policy)                │
├─────────────────────────────────────────────────────────────┤
│ BUSINESS (business/domains/sentraloop/)                          │
│  - Dinh nghia nguong rui ro cu the theo chinh sach nen tang        │
│  - KPI do luong hieu qua (giam ty le video bi flag, tang chi so    │
│    tuong tac sau khi ap dung de xuat)                               │
│  - Quy tac nghiep vu: loai rui ro nao tu dong xu ly, loai nao       │
│    bat buoc nguoi phe duyet                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Luồng nghiệp vụ ví dụ (end-to-end)

```
Video moi duoc dua vao he thong (kem thong tin: caption, danh muc san pham)
        │
        ▼
[Buoc 1] Danh gia rui ro noi dung
   → Phat hien vi tri va loai vi pham (bản quyền, chính sách nội dung...)
        │
        ▼
[Buoc 2] Truy xuat du lieu lich su
   → Video cung danh muc san pham, hieu suat lien quan (tu nguon du
     lieu ben ngoai neu co, hoac tu metadata da co san)
        │
        ▼
[Buoc 3] Doi chieu pattern, sinh de xuat
   → So sanh video moi voi cac video da chuyen doi tot truoc do, dua ra
     nhan dinh co dan chung cu the (khong chung chung)
        │
        ▼
[Buoc 4] Tong hop quyet dinh (hai nhanh, tach rieng theo muc rui ro)
   ├── Nhanh An toan: de xuat khac phuc vi pham
   └── Nhanh Tang truong: de xuat dieu chinh de tang chuyen doi
        │
        ▼
[Buoc 5] Trinh bay quyet dinh cho nguoi dung
   → Hien thi ro can cu/dan chung cho tung de xuat
   → Nguoi dung phe duyet tung nhanh doc lap nhau
        │
        ▼
[Buoc 6] Thuc thi hanh dong da duoc phe duyet
   → Ket qua duoc luu lai, dung lam du lieu doi chieu cho lan sau
```

---

## 4. Nguồn dữ liệu cần thiết

| Nguồn | Bắt buộc? | Dùng cho | Phương án dự phòng nếu không có |
|---|---|---|---|
| Video đầu vào (file thật) | Bắt buộc | Đánh giá rủi ro nội dung | — |
| Danh sách quy tắc/chính sách nội dung bị cấm | Bắt buộc | Đánh giá rủi ro nội dung | Tổng hợp từ nguồn công khai, cập nhật trong tầng Business |
| Dữ liệu lịch sử kênh (video cũ + hiệu suất) | Không chắc có sẵn | Đề xuất tăng trưởng | Suy pattern từ metadata video đầu vào (caption, danh mục) + bộ dữ liệu mẫu chuẩn bị trước |
| Thông tin sản phẩm đang bán | Nên có | Gắn ngữ cảnh cho đề xuất | Nhập thủ công tại bước tải video lên |
| Thư viện nội dung thay thế (nhạc/hình ảnh không vi phạm bản quyền) | Bắt buộc nếu triển khai tự động khắc phục | Thực thi hành động khắc phục | Chuẩn bị sẵn một bộ tài nguyên nhỏ, phân loại theo thuộc tính liên quan |

---

## 5. Phân việc theo 5 vai trò (gắn với kiến trúc, không đi vào chi tiết code)

Vì đề bài thật chưa được công bố, phần phân việc dưới đây mô tả phạm vi trách nhiệm theo
từng tầng kiến trúc, áp dụng chung cho tinh thần sản phẩm này — không chốt cứng tên
hàm/API cụ thể, để linh hoạt điều chỉnh khi biết đề bài thật.

### AI Engineer — tầng Agent
- Xây dựng và duy trì luồng orchestration tổng quát của Agent (điều phối các bước: đánh
  giá rủi ro → truy xuất dữ liệu → suy luận → ra quyết định → thực thi).
- Thiết kế và hiệu chỉnh cơ chế đánh giá rủi ro nội dung, đảm bảo có thể áp dụng cho nhiều
  loại vi phạm khác nhau mà không phải viết lại kiến trúc.
- Thiết kế cơ chế truy xuất dữ liệu lịch sử phục vụ suy luận, đảm bảo có thể thay đổi nguồn
  dữ liệu (có API thật hay không) mà không ảnh hưởng phần còn lại của hệ thống.
- Kiểm soát ngưỡng tự động hóa: xác định khi nào hệ thống được tự hành động, khi nào bắt
  buộc chờ người phê duyệt, dựa trên mức độ rủi ro của từng loại quyết định.

### Data Engineer — tầng Data
- Thiết kế và triển khai luồng thu thập, chuẩn hóa dữ liệu lịch sử kênh/sản phẩm từ nguồn
  bên ngoài khi có, đảm bảo dữ liệu đưa vào tầng Agent đúng định dạng đã thống nhất.
- Chuẩn bị bộ dữ liệu mẫu hợp lý để đội có thể phát triển và kiểm thử ngay cả khi chưa có
  nguồn dữ liệu thật.
- Thiết kế nơi lưu trữ kết quả xử lý và phản hồi thực tế, phục vụ việc đối chiếu, cải thiện
  độ chính xác của hệ thống theo thời gian.

### Backend Engineer — tầng Backend
- Xây dựng lớp API kết nối Frontend với tầng Agent, đảm bảo dữ liệu trao đổi hai chiều rõ
  ràng, có kiểm soát.
- Thiết kế và triển khai luồng xử lý hành động phê duyệt/từ chối của người dùng, đảm bảo
  mọi hành động thực thi đều được xác thực lại ở tầng backend trước khi thực hiện.
- Quản lý trạng thái của toàn bộ quy trình xử lý một video/nội dung, từ lúc tiếp nhận đến
  lúc hoàn tất.

### Frontend Engineer — tầng Frontend
- Xây dựng giao diện tiếp nhận nội dung đầu vào và hiển thị trực quan các vấn đề được phát
  hiện (vị trí, loại vấn đề, mức độ).
- Thiết kế giao diện phê duyệt quyết định, đảm bảo người dùng phân biệt rõ giữa các loại đề
  xuất có mức rủi ro khác nhau và có thể quyết định độc lập với từng loại.
- Xây dựng màn hình tổng quan thể hiện hiệu quả sử dụng hệ thống theo thời gian.

### Business Analyst — tầng Business
- Xác định và chuẩn hóa các quy tắc nghiệp vụ cụ thể: loại rủi ro nội dung nào cần ưu tiên
  phát hiện, ngưỡng nào hợp lý về mặt vận hành thực tế (không chỉ về mặt kỹ thuật).
- Định nghĩa chỉ số đo lường hiệu quả sản phẩm và cách trình bày giá trị sản phẩm mang lại.
- Làm cầu nối thu thập yêu cầu/ràng buộc thực tế từ phía đơn vị cung cấp đề bài, đảm bảo
  các tầng kỹ thuật khác xây dựng đúng hướng khi đề bài chính thức được công bố.

---

## 6. Rủi ro chính & phương án xử lý

| Rủi ro | Mức độ | Phương án |
|---|---|---|
| Không có nguồn dữ liệu lịch sử kênh từ bên ngoài | Cao | Chuẩn bị dữ liệu mẫu trước, thiết kế tầng truy xuất dữ liệu có khả năng chuyển đổi nguồn linh hoạt |
| Xử lý nội dung thật (khắc phục vi phạm) tốn thời gian phát triển trong thời gian hạn chế | Trung bình | Ưu tiên dùng công cụ/thư viện có sẵn, giới hạn phạm vi khắc phục ở mức khả thi trong thời gian cho phép |
| Đề xuất tăng trưởng bị đánh giá là thiếu căn cứ | Cao nếu không xử lý | Bắt buộc mọi đề xuất phải trích dẫn cụ thể từ dữ liệu đã truy xuất được |
| Đề xuất thực thi thay đổi ngân sách/chiến dịch quảng cáo thật | Cao (khó khả thi) | Giới hạn phạm vi ở mức đề xuất và mô phỏng, không thực thi thay đổi tài chính thật |

---

## 7. Bám sát tiêu chí chấm giải

| Tiêu chí | Trọng số | SentraLoop AI đáp ứng bằng |
|---|---|---|
| Solution Quality | 30đ | Giải quyết vấn đề thực tế có tác động rõ ràng, có số liệu trước/sau minh chứng |
| Usability | 20đ | Cơ chế phê duyệt trực quan, tách rõ các loại quyết định theo mức rủi ro |
| Technical | 20đ | Kiến trúc ra quyết định có cấu trúc, pipeline nhiều bước có dẫn chứng dữ liệu cụ thể |
| Innovation & Differentiation | 15đ | Kết hợp khắc phục rủi ro tự động và đề xuất tăng trưởng dựa trên dữ liệu lịch sử trong cùng một hệ thống |
| Demo | 15đ | Luồng ngắn, trực quan: tiếp nhận nội dung → phát hiện vấn đề → phê duyệt → thấy kết quả xử lý |
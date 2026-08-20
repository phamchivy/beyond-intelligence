# 🎨 Báo cáo Thiết kế UI/UX: AI Short Video Ads Generator

---

## 1. Triết lý thiết kế (Design Philosophy) & Theme

Sản phẩm giải quyết một bài toán phức tạp (8 nhóm input, nhiều ràng buộc kỹ thuật) nên triết lý cốt lõi của UI/UX là: **"Đơn giản hóa sự phức tạp thông qua Hé lộ dần (Progressive Disclosure) và Tự động hóa (Smart Pre-fill)"**.

*   **Design System:** Sử dụng **Nuxt UI** (dựa trên Tailwind CSS và Headless UI) để đảm bảo tính nhất quán, hiện đại và tối ưu hiệu suất.
*   **Theme:** 
    *   **Màu chủ đạo (Primary):** `indigo` hoặc `violet` (tạo cảm giác công nghệ, AI, sáng tạo).
    *   **Màu nền (Background):** Hỗ trợ Dark/Light mode chuẩn của Nuxt UI (khuyến khích dùng Dark mode `bg-gray-900` để làm nổi bật video kết quả và asset hình ảnh).
    *   **Kiểu dáng:** Flat design, bo góc mềm mại (`rounded-lg`), sử dụng border tinh tế thay vì đổ bóng (shadow) quá đậm để giao diện phẳng và nhanh.
*   **Layout chính:** Dạng **Split-pane (Chia đôi màn hình)** trên Desktop để người dùng không phải cuộn trang hoặc chuyển context giữa việc nhập liệu và xem kết quả.

---

## 2. Cấu trúc các trang (Sitemap)

Hệ thống được thiết kế dạng Single Page Application (SPA) hoặc chia thành các module rất gọn:

1.  **`/` (Home / Dashboard):** Nơi hiển thị thống kê tổng quan (số video đã tạo), nút "Tạo chiến dịch mới" (Call-to-Action chính) và danh sách các video đã tạo gần đây (Gallery).
2.  **`/workspace` (Trang Tạo Video - Cốt lõi):** Giao diện Split-pane chia làm 2 cột chính (Input và Output/Preview).
3.  **`/history` (Thư viện):** Quản lý các video đã render thành công, xem lại thông số đầu vào của từng video (tái sử dụng cấu hình).

---

## 3. Chi tiết Thiết kế Trang Workspace (Tính năng cốt lõi)

Trang `/workspace` là linh hồn của ứng dụng. Giao diện được chia thành hai cột: **Left Panel (Cột nhập liệu)** chiếm 40% màn hình, và **Right Panel (Cột AI & Preview)** chiếm 60% màn hình.

### 3.1. Left Panel: Khu vực Nhập liệu (Input)
Sử dụng `UTabs` của Nuxt UI để chia 8 nhóm input thành 3 tab logic, tránh gây "ngợp" cho người dùng:

*   **⚡ Smart Input (Nổi bật trên cùng):**
    *   **UI:** Một `UTextarea` lớn kèm nút "🪄 AI Auto-fill".
    *   **UX:** Người dùng dán 1 đoạn text lộn xộn (ví dụ: brief từ khách hàng). AI tự động phân tích và điền vào các trường bên dưới.
*   **Tab 1: 📦 Nguyên liệu (Product & Assets)**
    *   *Thông tin cơ bản:* `UInput` cho Tên, Giá. `UTextarea` cho USP và Tính năng.
    *   *Quản lý Asset:* Khu vực Drag & Drop bọc trong `UCard`. Hỗ trợ hiển thị thumbnail ngay lập tức khi upload (Ảnh hero, logo, video mẫu).
*   **Tab 2: 🎯 Chiến lược (Strategy)**
    *   *Kênh & Mục tiêu:* Dùng `USelectMenu` để chọn (Meta, TikTok, Reels) và (Conversion, Traffic).
    *   *Khách hàng & Thông điệp:* `UFormGroup` với các gợi ý mờ (placeholder) hướng dẫn cách viết pain point hiệu quả.
*   **Tab 3: ⚙️ Ràng buộc (Constraints)**
    *   Đặt trong `UAccordion` (mặc định đóng). Chứa các setting nâng cao: tỷ lệ khung hình, thời lượng tối đa, các từ cấm nói (Negative prompt), và Text CTA bắt buộc.

### 3.2. Right Panel: Khu vực Xử lý & Kết quả (Output)
Khu vực này thay đổi trạng thái dựa trên hành động của người dùng:

*   **Trạng thái 1: Empty State (Chưa có dữ liệu)**
    *   Hiển thị một placeholder nhẹ nhàng với icon minh họa: "Nhập thông tin bên trái hoặc sử dụng AI Auto-fill để bắt đầu."
*   **Trạng thái 2: Generation State (Đang xử lý - Cực kỳ quan trọng để ghi điểm)**
    *   **UI:** Thay vì một spinner vô hồn, sử dụng `UProgress` kết hợp với một danh sách các bước (Stepper).
    *   **UX:** Hiển thị "Luồng tư duy" của Agent. Ví dụ text nhảy liên tục: 
        *   `[✓] Đang phân tích USP sản phẩm...`
        *   `[✓] Đang viết kịch bản Hook 3s...`
        *   `[⏳] Đang xử lý hình ảnh và khớp âm thanh...`
    *   Điều này giúp người dùng cảm thấy AI thực sự đang làm việc (show-off công nghệ dưới nền).
*   **Trạng thái 3: Result State (Hoàn thành)**
    *   **Mobile Mockup:** Video được đặt bên trong một frame điện thoại (tỷ lệ 9:16). Có các overlay giả lập UI của TikTok/Reels (nút tim, comment, caption) để chứng minh text/CTA của video không bị che khuất.
    *   **Action Bar:** Các `UButton` xếp ngang bên dưới: 
        *   `Tải xuống Video` (Primary)
        *   `Tạo lại (Regenerate)` (Secondary)
        *   `Xem Kịch bản AI đã dùng` (Ghost button - Mở ra 1 slide-over hoặc modal để giám khảo chấm cấu trúc Hook -> Product -> Benefit -> CTA).

---

## 4. User Flow (Trải nghiệm xuyên suốt)

1. **Khởi tạo:** User vào `/workspace`, thấy màn hình chia đôi sạch sẽ.
2. **Nhập liệu nhanh:** User dán brief vào *Smart Input*. Nhấn "AI Auto-fill". Form bên dưới tự động nhảy dữ liệu vào các ô.
3. **Bổ sung Asset:** User kéo thả ảnh sản phẩm, logo vào vùng Drag & Drop.
4. **Trigger AI:** Nhấn nút `Tạo Video Quảng Cáo` (Sticky ở góc dưới bên trái).
5. **Chờ đợi có chủ đích:** Nhìn sang cột phải xem AI đang chạy các bước nào (Extract, Scripting, Rendering).
6. **Nghiệm thu:** Video hiện ra trong khung Mobile. User bấm Play để xem. 
7. **Kiểm tra tính thực tiễn:** Bật/tắt layer giao diện TikTok đè lên video để check xem có bị lấp chữ không.
8. **Hoàn tất:** Bấm Tải xuống.

---

## 5. Ràng buộc & Tương tác kỹ thuật (Technical UI/UX)

*   **Real-time Validation:** Sử dụng Zod kết hợp với tính năng validation của Nuxt UI Form. Nếu người dùng quên up ảnh hoặc chọn sai mục tiêu, input sẽ báo đỏ ngay lập tức mà không cần đợi bấm Submit.
*   **Non-blocking UI:** Trong lúc video đang render (có thể mất vài phút), người dùng vẫn có thể click qua lại các Tab ở cột trái để xem xét (read-only) hoặc mở tab trình duyệt khác mà không bị lỗi (cần có cơ chế polling hoặc WebSocket để update trạng thái).
*   **Responsive:** Mặc dù công cụ làm việc chuyên sâu thường dùng trên Desktop, trang web vẫn cần responsive. Trên mobile, Layout Split-pane sẽ chuyển thành Stack (Cột trái nằm trên, cột phải nằm dưới).

---

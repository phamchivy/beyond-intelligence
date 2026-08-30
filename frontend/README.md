# Beyond Videos — Frontend Service

> **AI Short Video Ads Generator (9:16 Video Engine)**  
> Nền tảng tạo video quảng cáo ngắn tự động cho TikTok, Instagram Reels và Meta Feed từ Brief sản phẩm & Assets đa phương tiện, tích hợp quy trình duyệt kịch bản **Human-In-The-Loop (HITL)**.

---

## 🚀 Công Nghệ Cốt Lõi (Tech Stack)

* **Framework:** [Nuxt 4](https://nuxt.com/) (`v4.5.2`) + Vue 3.5 + Vite + Nitro Server.
* **Giao Diện & Styling:** [@nuxt/ui](https://ui.nuxt.com/) (`v4.10.0`) + [Tailwind CSS v4](https://tailwindcss.com/) + `@iconify-json/lucide`.
* **Ngôn ngữ:** TypeScript (Strict Type Checking với `vue-tsc`).
* **Trực Quan Hóa & Video:** HTML5 9:16 Smartphone Mockup with TikTok Safe Zone Overlay, ECharts (`echarts`, `vue-echarts`).
* **Kiến Trúc Tích Hợp:** Hỗ trợ song song **Demo Mock Mode** (qua Nitro Server) và **Live Pods Mode** (kết nối trực tiếp Backend .NET 8 FastEndpoints tại `http://localhost:8000/api/v1`).

---

## 📁 Cấu Trúc Dự Án (Project Structure)

```text
frontend/
├── app/
│   ├── app.vue                           # App root wrap <UApp> & <NuxtLayout>
│   ├── assets/css/main.css               # Cấu hình Tailwind CSS v4 & theme tokens
│   ├── composables/
│   │   ├── useApi.ts                     # HTTP client ($fetch), Error parser & Base URL handler
│   │   └── usePipelineApi.ts             # API Service gọi pipeline theo đúng Backend Contract
│   ├── layouts/
│   │   └── default.vue                   # Header bar, Navigation, Theme toggle (☀️/🌙), Demo Switcher
│   ├── pages/
│   │   ├── index.vue                     # Dashboard tổng quan, KPI cards thời gian thực, Recent briefs
│   │   ├── workspace.vue                 # Flagship Split-Pane Workspace (AI Stepper & 9:16 Mockup)
│   │   ├── history.vue                   # Thư viện video đã render kèm modal xem video 9:16
│   │   ├── briefs/
│   │   │   ├── index.vue                 # Danh sách quản lý các brief
│   │   │   ├── new.vue                   # Form tạo brief chi tiết
│   │   │   └── [id]/storyboard.vue       # Cổng duyệt kịch bản Human-in-the-loop (HITL)
│   │   └── renders/
│   │       └── [id].vue                  # Giám sát tiến độ render video & tải MP4
│   └── types/
│       └── brief.ts                      # TypeScript Model & API Contract Schemas
├── server/
│   └── api/v1/                           # Nitro Mock API routes phục vụ Demo Mode
│       ├── pipeline/
│       │   ├── submit-brief.post.ts      # Mock sinh Storyboard 4 phân cảnh
│       │   └── review-storyboard.post.ts # Mock xử lý duyệt / sửa / hủy
│       ├── renders/
│       │   └── [id].get.ts               # Mock polling tiến độ render
│       ├── dashboard/
│       │   └── overview.get.ts           # Mock số liệu KPI
│       └── workspace/
│           ├── brief.get.ts
│           └── generate.post.ts
└── nuxt.config.ts                        # Cấu hình Nuxt 4, modules, icon & colorMode
```

---

## 🌟 Tính Năng Nổi Bật (Key Features)

### 1. Flagship Split-Pane Workspace (`/workspace`)
* **Cột Trái (Input & Chiến Lược - 42%):**
  * **⚡ 1-Click Presets:** Nạp nhanh mẫu chiến dịch (*Serum Vitamin C, Laptop Gaming AI, Giày Chạy Bộ Urban*).
  * **🪄 Smart AI Auto-Fill:** Tự động phân tích và trích xuất thông tin từ đoạn văn bản thô.
  * **3 Tabs Quản Lý:**
    1. `📦 Nguyên liệu`: Tên, USP, Giá, Tính năng, Ưu đãi & **Bộ kéo thả Upload 4 nhóm Asset** (*Hero, Closeup, Lifestyle, Logo*) có thumbnail preview tức thì.
    2. `🎯 Chiến lược`: Kênh phát hành (TikTok, Reels, Meta), Mục tiêu quảng cáo, Chân dung khách hàng, Thông điệp cốt lõi.
    3. `⚙️ Ràng buộc`: Thời lượng video (15s/30s), Ngôn ngữ, CTA bắt buộc, Negative Claims cấm kỵ.
* **Cột Phải (AI Output & HITL Review - 58%):**
  * **Reasoning Stepper:** Trực quan hóa tiến trình tư duy đa tác tử thời gian thực (`[✓] Phân tích USP` $\rightarrow$ `[✓] Tạo Storyboard` $\rightarrow$ `[⏳] Khớp Video & Audio`).
  * **HITL Storyboard Review:** Xem thẻ từng phân cảnh (Hook $\rightarrow$ Problem $\rightarrow$ Solution $\rightarrow$ CTA), âm nhạc nền, giọng đọc và gửi phản hồi yêu cầu AI sửa đổi (hỗ trợ tối đa 3 vòng lặp revision).
  * **Smartphone 9:16 Mockup Frame:** Trình phát video chuẩn kích thước dọc, nút **Bật/Tắt Overlay TikTok Safe Zone** (đảm bảo text/CTA không bị che khuất), nút tải file MP4 và popup xem kịch bản AI chi tiết.

### 2. Dashboard KPIs & Lịch Sử (`/` & `/history`)
* Hiển thị 4 chỉ số KPI cốt lõi: Doanh thu mục tiêu, Tỷ suất lợi nhuận, Chiến dịch đang chạy, Mức độ rủi ro QA.
* Thư viện video trực quan với popup phát video và nút nhân bản chiến dịch.

### 3. Cơ Chế Xử Lý Lỗi Minh Bạch & Thông Báo Toast
* Toàn bộ lỗi HTTP từ Backend (`400`, `401`, `403`, `404`, `500`) được bắt và hiển thị chuẩn xác qua **Nuxt UI `useToast()`** và trạng thái UI `failed`, không sử dụng mock ngầm che giấu lỗi trong chế độ Live.

---

## 🔄 API Response Contracts Đã Đồng Bộ

Frontend đồng bộ 100% với Backend FastEndpoints .NET 8:

| Endpoint | Method | Mô Tả | Payload / Response |
| :--- | :---: | :--- | :--- |
| `/api/v1/pipeline/submit-brief` | `POST` | Gửi Brief dạng Multipart Form-Data | Nhận về `{ taskId, storyboardId, revisionNumber, plan: { scenes, soundtrack, voiceover_tone }, taskStatus }` |
| `/api/v1/pipeline/review-storyboard` | `POST` | HITL Review Storyboard | Gửi `{ taskId, storyboardId, decision, feedback }`. Nhận về trạng thái `render_processing` hoặc `storyboard_review` (revision mới) |
| `/api/v1/renders/{id}` | `GET` | Polling tiến độ Render Video | Nhận về `{ status: "processing" \| "completed" \| "failed", video_url }` |
| `/api/v1/dashboard/overview` | `GET` | Lấy số liệu KPI tổng quan | Nhận về `{ totalRevenue, profitMargin, activeCampaigns, riskLevel }` |
| `/api/v1/briefs` | `POST` | Lưu bản nháp Brief | Nhận về `{ id, status: "draft", message }` |

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy (Getting Started)

### 1. Cài đặt Dependencies
```bash
npm install
# hoặc
pnpm install
```

### 2. Khởi chạy Development Server
```bash
npm run dev
```
Truy cập ứng dụng tại: **`http://localhost:3000`**

### 3. Kiểm tra Typecheck (TypeScript & Nuxt UI Templates)
```bash
npm run typecheck
```

### 4. Đóng gói Production Build
```bash
npm run build
```

### 5. Kiểm tra kết quả
```bash
npm run preview
```

---

## ⚙️ Cấu Hình Môi Trường (Environment Variables)

Các biến môi trường có thể cấu hình trong file `.env` hoặc `docker-compose.yml`:

```env
NUXT_PUBLIC_APP_NAME="Beyond Videos"
NUXT_PUBLIC_APP_DESCRIPTION="AI Short Video Ads Generator"
NUXT_PUBLIC_API_BASE="http://localhost:8000/api/v1"
NUXT_PUBLIC_DEMO_MODE="false"
```

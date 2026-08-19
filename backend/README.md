# Beyond Intelligence - Backend Engine (P6: Action & Workflow Engine)

Thư mục này chứa mã nguồn **Backend Service** thuộc dự án **Beyond Intelligence**. Backend đóng vai trò là **Action & Workflow Engine (Platform 6)**, điều phối luồng quyết định (Decision Flow), quản lý trạng thái phê duyệt (Human-in-the-Loop Approval), tiếp nhận dữ liệu đa phương tiện từ người dùng, và cung cấp REST API cho giao diện **Intelligence Workspace** (NuxtJS Frontend).

---

## Công Nghệ Sử Dụng

- **Framework:** .NET 8 Web API
- **API Architecture:** [FastEndpoints](https://fast-endpoints.com/) (REPR Pattern - Request-Endpoint-Response)
- **Containerization:** Docker & Dockerfile đa tầng (Multi-stage build)
- **API Documentation:** Swagger UI (OpenAPI)
- **Unit & Integration Testing:** xUnit, FluentAssertions, Moq, FastEndpoints.Testing
- **Communication:** RESTful JSON APIs / Multipart Form-Data / CORS Enabled cho NuxtJS

---

## Cấu Trúc Dự Án

```text
backend/
├── Endpoints/                          # Danh sách các REST API Endpoints (FastEndpoints)
│   ├── UploadVideoEndpoint.cs          # API nhận file video, lưu trữ & kích hoạt luồng AI
│   ├── GetDashboardOverviewEndpoint.cs # API lấy số liệu KPIs tổng quan (View 1)
│   ├── RunSimulationEndpoint.cs        # API chạy giả lập kịch bản What-If (View 2)
│   ├── GetDecisionEndpoint.cs          # API lấy Quyết định & Evidence từ AI (View 3 & 5)
│   └── ExecuteWorkflowEndpoint.cs      # API xử lý Phê duyệt & Trigger Action (View 4)
├── Models/                             # Data Transfer Objects (DTOs) & Request/Response Models
│   └── UploadVideoDtos.cs              # Cấu trúc Request/Response cho Endpoint upload video
├── Properties/                         # Cấu hình khởi chạy môi trường phát triển cục bộ
│   └── launchSettings.json             # Thiết lập ports, profiles (IIS/Kestrel) cho Visual Studio/VS Code
  ├── tests/                              # Module kiểm thử tự động (Unit & Integration Tests)
│   └── AIHackathonApi.Tests/
│       ├── Endpoints/
│       │   ├── DashboardOverviewTests.cs   # Test kiểm thử logic Dashboard
│       │   └── UploadVideoEndpointTests.cs # Test kiểm thử upload video, validate & mock storage
│       └── AIHackathonApi.Tests.csproj     # Cấu hình xUnit, Moq, FluentAssertions
├── .dockerignore                       # Loại trừ các file/thư mục không cần thiết khi build Docker
├── .env.example                        # File mẫu biến môi trường cấu hình kết nối DB, AI Service
├── .gitignore                          # Cấu hình bỏ qua mã nguồn tạm của git (.vs, obj, bin...)
├── AIHackathonApi.csproj               # File cấu hình dự án Backend .NET 8, nạp thư viện NuGet
├── appsettings.json                    # Cấu hình môi trường Production & Storage
├── appsettings.Development.json        # Cấu hình ghi đè khi chạy dưới môi trường Development
├── Dockerfile                          # Kịch bản đóng gói ứng dụng Backend thành Docker Image độc lập
├── Program.cs                          # Cấu hình Middleware, CORS, FastEndpoints, Swagger, DI Container
└── README.md                           # Tài liệu hướng dẫn kỹ thuật Backend
```

---

## Khởi Chạy Dự Án

### 1. Khởi chạy toàn bộ hệ thống qua Docker Compose
```powershell
docker compose -f infrastructure/docker-compose.yml up -d 
```
### 2. Chạy độc lập riêng container Backend
```powershell
docker pull duytrong298/be-beyond-intelligence:demo-v1.0
docker run -d -p 8000:8000 --name beyond_backend duytrong298/be-beyond-intelligence:demo-v1.0
```
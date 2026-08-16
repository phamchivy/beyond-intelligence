# Beyond Intelligence - Backend Engine (P6: Action & Workflow Engine)

Thư mục này chứa mã nguồn **Backend Service** thuộc dự án **Beyond Intelligence**. Backend đóng vai trò là **Action & Workflow Engine (Platform 6)**, điều phối luồng quyết định (Decision Flow), quản lý trạng thái phê duyệt (Human-in-the-Loop Approval), tiếp nhận dữ liệu đa phương tiện từ người dùng, và cung cấp REST API cho giao diện **Intelligence Workspace** (NuxtJS Frontend).

---

## Công Nghệ Sử Dụng

- **Framework:** .NET 8 Web API
- **API Architecture:** [FastEndpoints](https://fast-endpoints.com/) (REPR Pattern - Request-Endpoint-Response)
- **API Documentation:** Swagger UI (OpenAPI)
- **Unit & Integration Testing:** xUnit, FluentAssertions, Moq, FastEndpoints.Testing
- **Communication:** RESTful JSON APIs / Multipart Form-Data / CORS Enabled cho NuxtJS

---

## Cấu Trúc Dự Án

```text
backend/
├── Endpoints/                            # Danh sách các REST API Endpoints (FastEndpoints)
│   ├── UploadVideoEndpoint.cs            # API nhận file video, lưu trữ & kích hoạt luồng AI
│   ├── GetDashboardOverviewEndpoint.cs   # API lấy số liệu KPIs tổng quan (View 1)
│   ├── RunSimulationEndpoint.cs          # API chạy giả lập kịch bản What-If (View 2)
│   ├── GetDecisionEndpoint.cs            # API lấy Quyết định & Evidence từ AI (View 3 & 5)
│   └── ExecuteWorkflowEndpoint.cs        # API xử lý Phê duyệt & Trigger Action (View 4)
├── Models/                               # Data Transfer Objects (DTOs) & Request/Response Models
│   └── UploadVideoDtos.cs                # Cấu trúc Request/Response cho Endpoint upload video
├── wwwroot/                              # Thư mục lưu trữ tài nguyên tĩnh được Web Server phục vụ
│   └── uploads/                          # Thư mục chứa media upload từ người dùng
│       ├── images/                       # Lưu trữ hình ảnh sản phẩm, thumbnail
│       └── videos/                       # Lưu trữ file video đầu vào (.mp4, .mov)
├── tests/                                # Module kiểm thử tự động (Unit & Integration Tests)
│   └── AIHackathonApi.Tests/
│       ├── Endpoints/
│       │   ├── DashboardOverviewTests.cs # Test kiểm thử logic Dashboard
│       │   └── UploadVideoEndpointTests.cs # Test kiểm thử upload video, validate & mock storage
│       └── AIHackathonApi.Tests.csproj   # Cấu hình xUnit, Moq, FluentAssertions
├── Program.cs                            # Cấu hình Middleware, Static Files, CORS, FastEndpoints, Swagger
├── AIHackathonApi.csproj                 # File cấu hình dự án Backend .NET 8
└── appsettings.json                      # Cấu hình môi trường & Storage
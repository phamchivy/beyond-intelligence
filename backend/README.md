# Beyond Intelligence - Backend Engine (P6: Action & Workflow Engine)

Thư mục này chứa mã nguồn **Backend Service** thuộc dự án **Beyond Intelligence**. Backend đóng vai trò là **Action & Workflow Engine (Platform 6)**, điều phối luồng quyết định (Decision Flow), quản lý trạng thái phê duyệt (Human-in-the-Loop Approval), và cung cấp REST API cho giao diện **Intelligence Workspace** (NuxtJS Frontend).

---

## Công Nghệ Sử Dụng

- **Framework:** .NET 8 Web API
- **API Architecture:** [FastEndpoints](https://fast-endpoints.com/) (REPR Pattern - Request-Endpoint-Response)
- **API Documentation:** Swagger UI (OpenAPI)
- **Communication:** RESTful JSON APIs / CORS Enabled cho NuxtJS

---

## Cấu Trúc Dự Án

```text
backend/
├── Endpoints/                     # Danh sách các REST API Endpoints (FastEndpoints)
│   ├── GetDashboardOverviewEndpoint.cs   # API lấy số liệu KPIs tổng quan (View 1)
│   ├── RunSimulationEndpoint.cs          # API chạy giả lập kịch bản What-If (View 2)
│   ├── GetDecisionEndpoint.cs            # API lấy Quyết định & Evidence từ AI (View 3 & 5)
│   └── ExecuteWorkflowEndpoint.cs        # API xử lý Phê duyệt & Trigger Action (View 4)
├── Program.cs                     # Cấu hình Middleware, CORS, FastEndpoints, Swagger
├── AIHackathonApi.csproj          # File cấu hình dự án .NET 8
└── appsettings.json               # Cấu hình môi trường

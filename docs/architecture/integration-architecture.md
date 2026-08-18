# Beyond Intelligence — Integration Architecture (4 Pods: FE / BE / AI / DATA)

> Tài liệu này mô tả cách 4 service (pod) độc lập đóng gói, triển khai, và giao tiếp với nhau. Mục tiêu: mỗi thành viên (FE/BE/AI/DATA engineer) chỉ cần đọc file này là biết mình cần expose gì, gọi ai, và chờ gì.

Kiến trúc tích hợp thử nghiệm (flow có thể giao tiếp nhiều hơn giữa Agent + Data + Database)

```
                    ┌─────────────┐
                    │     FE      │
                    └──────┬──────┘
                           │ REST / SSE
                           ▼
                    ┌─────────────┐
                    │     BE      │
                    │ API / Auth  │
                    │ Orchestrate │
                    └───┬─────┬───┘
                        │     │
              API/gRPC  │     │ API/gRPC
                        ▼     ▼
                 ┌─────────┐ ┌─────────┐
                 │   AI    │ │  DATA   │
                 │ Agent   │ │ Pipeline│
                 │ Models  │ │ Storage │
                 └────┬────┘ └────┬────┘
                      │            │
                      └──────┬─────┘
                             ▼
                       DB / Object Store
```

---

## 1. Nguyên tắc tổng quát

- **FE không gọi AI/DATA trực tiếp.** Mọi request từ FE đều đi qua BE.
- **BE là Application/API boundary**, không chứa AI reasoning logic, không chứa data processing logic.
- **AI (agent/) là Intelligence layer.** Chỉ nhận task từ BE, gọi DATA qua Tool/API khi cần, trả về Decision/Result.
- **DATA không biết Agent.** DATA chỉ expose data qua API sạch (query, ingestion), không quan tâm ai gọi.
- **Domain layer của từng service không phụ thuộc framework hay service khác.** Giao tiếp giữa các pod luôn qua HTTP API (REST/JSON cho hackathon), không share code Python giữa container.

```
FE ──REST/SSE──> BE ──REST──> AI ──REST──> DATA ──> DB / Object Storage
```

Đây **không phải pipeline cứng**. AI có thể gọi DATA nhiều lần trong 1 flow; BE luôn là entrypoint nhưng logic thật nằm ở AI/DATA.

---

## 2. Đóng gói (Packaging)

Mỗi pod là **1 Docker image độc lập**, có thể build/run/test riêng lẻ mà không cần 3 pod còn lại (dùng mock/stub khi cần).

| Pod | Base image gợi ý | Port nội bộ | Thư mục nguồn |
|---|---|---|---|
| frontend | node:20-alpine | 3000 | `frontend/` |
| backend | python:3.12-slim | 8000 | `backend/` |
| ai (agent) | python:3.12-slim | 8001 | `agent/` |
| data | python:3.12-slim | 8002 | `data/` |

**Quy tắc đóng gói:**
- Mỗi service có `Dockerfile` riêng trong thư mục gốc của nó, không có Dockerfile dùng chung.
- Mỗi service có `.env.example` liệt kê toàn bộ biến môi trường cần thiết — không hardcode config (đúng nguyên tắc đã chốt trong `config/settings.py`).
- Mỗi service **bắt buộc có endpoint `GET /health`** trả `200 OK` kèm trạng thái phụ thuộc (DB connected? Gemini key valid? DATA reachable?). Đây là điều kiện để service khác được phép gọi vào.
- Không service nào import trực tiếp code Python của service khác. Nếu cần schema dùng chung, dùng convention (xem mục 4), không dùng shared package trong giai đoạn hackathon.

---

## 3. Triển khai (Deployment) — Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      backend: {condition: service_healthy}

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - AI_SERVICE_URL=http://ai:8001
      - DATA_SERVICE_URL=http://data:8002
    depends_on:
      ai: {condition: service_healthy}
      data: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  ai:
    build: ./agent
    ports: ["8001:8001"]
    environment:
      - DATA_SERVICE_URL=http://data:8002
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  data:
    build: ./data
    ports: ["8002:8002"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  default:
    name: beyond-intelligence-net
```

**Lưu ý triển khai:**
- Dùng **service name làm hostname nội bộ** (`http://ai:8001`), không dùng `localhost` giữa các container.
- `depends_on` + `condition: service_healthy` đảm bảo BE không gọi AI trước khi Gemini client init xong.
- Biến môi trường nhạy cảm (`GEMINI_API_KEY`) chỉ nằm trong `.env` ở máy host, không commit vào repo, không truyền qua FE.

---

## 4. Giao tiếp giữa các pod (API Contract)

### 4.1 Nguyên tắc schema

- Mỗi service tự định nghĩa Pydantic model cho request/response của **chính nó**. Không import model chéo giữa container.
- Domain entity (ví dụ `Decision`, `Task` trong `agent/domain/entities`) **không được** trả thẳng ra HTTP response. Mỗi service cần một lớp DTO (`interface/api/schemas.py`) để convert domain entity → response model. Đây là nơi thêm layer **Interface** theo đúng 4 tầng đã chốt (Interface → Application → Domain → Infrastructure).
- Field name/type giữa các pod đồng bộ bằng **convention + FastAPI Swagger** (`/docs` tự sinh ở mỗi service), không bằng code sharing.

### 4.2 Endpoint tối thiểu mỗi pod cần expose

**BE (backend, :8000)**
```
GET  /health
POST /api/v1/tasks                    # tạo task mới (FE gọi)
GET  /api/v1/tasks/{id}                # xem trạng thái task
POST /api/v1/tasks/{id}/approve        # human approval (FE gọi)
```

**AI (agent, :8001)**
```
GET  /health
POST /api/v1/agent/analyze             # phân tích + tạo Decision (BE gọi)
POST /api/v1/agent/execute             # thực thi action sau approval (BE gọi)
```

**DATA (data, :8002)**
```
GET  /health
POST /api/v1/data/query                # AI/BE gọi để lấy dữ liệu đã xử lý
GET  /api/v1/policy-rules              # ví dụ cho AdGuard AI
GET  /api/v1/channel-history/{id}
```

### 4.3 Sync vs Async

Vì Agent call (Gemini + Tool + Evaluator + DecisionPolicy) có thể mất 5–20 giây, và AdGuard AI có bước Human-in-the-Loop, flow chia làm **2 pha** thay vì 1 request-response:

```
Pha 1 (analyze):  FE → BE → AI → DATA → AI (Decision) → BE lưu → FE hiện Action Card
Pha 2 (execute):  FE (Approve) → BE → AI (Tool.execute) → BE lưu → FE hiện kết quả
```

Quy mô hackathon: **không dựng message queue (Kafka/Celery)**. Dùng HTTP request đồng bộ với timeout dài hơn bình thường:
- BE → AI: timeout 30–60s.
- FE hiện loading state trong lúc chờ; nếu muốn UX mượt hơn, BE có thể proxy SSE để báo tiến trình ("đang phân tích..." → "đang detect violation..." → "done").

---

## 5. Luồng xử lý cụ thể — AdGuard AI (ví dụ tham chiếu)

```
1. FE upload video          → BE POST /api/v1/tasks (status = pending)
2. BE                       → AI POST /api/v1/agent/analyze { task_id, video_url }
3. AI: ContextBuilder        → Tool → DATA GET /api/v1/policy-rules, /api/v1/channel-history
4. AI: Evaluator → DecisionPolicy → tạo Decision (violation_type, confidence, suggested_fix)
5. AI                        → BE trả về Decision
6. BE lưu Decision            → FE render Action Card
7. User bấm Approve          → FE → BE POST /api/v1/tasks/{id}/approve
8. BE                        → AI POST /api/v1/agent/execute { task_id, action }
9. AI: ToolPolicy → Tool.execute() (Smart Blur / music swap / caption rewrite)
10. AI                       → BE trả Result → BE lưu → FE hiện kết quả
```

Pipeline `Evaluator → DecisionPolicy → ToolPolicy → Tool.execute()` đã có sẵn trong `agent/`; phần cần thêm chỉ là lớp `interface/api/` mỏng (FastAPI) để expose `/analyze` và `/execute` — không sửa domain/application logic.

---

## 6. Error handling giữa các pod

- Mỗi pod trả lỗi theo format thống nhất:
```json
{
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "Gemini request timed out after 30s",
    "task_id": "..."
  }
}
```
- BE là nơi quyết định retry/fallback/abort khi AI hoặc DATA lỗi — không để FE tự retry, không để AI tự retry vô hạn (tránh nhân retry: Agent retry × LLM retry × HTTP retry).
- AI dùng domain errors riêng (`LLMTimeoutError`, `ToolExecutionError`, `InvalidAgentStateError`) nội bộ, nhưng khi trả ra HTTP response cho BE thì convert sang error format thống nhất ở trên.

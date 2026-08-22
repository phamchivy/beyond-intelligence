# Beyond Intelligence — Giải pháp, Kiến trúc & Hướng dẫn chạy

> Tài liệu này mô tả **giải pháp thực tế đã build** trong repo: sản phẩm giải quyết bài toán gì, hệ thống gồm những thành phần nào, chúng nói chuyện với nhau ra sao, và cách chạy toàn bộ hệ thống (hoặc từng phần) trên máy local.

Sơ đồ kiến trúc: [`docs/architecture/overall-architecture.svg`](docs/architecture/overall-architecture.svg)

---

## Mục lục

1. [Giải pháp](#1-giải-pháp)
2. [Kiến trúc tổng quan](#2-kiến-trúc-tổng-quan)
3. [Chi tiết từng pod](#3-chi-tiết-từng-pod)
4. [Luồng xử lý end-to-end](#4-luồng-xử-lý-end-to-end)
5. [RAG: trending video từ Kalodata](#5-rag-trending-video-từ-kalodata)
6. [Hướng dẫn chạy](#6-hướng-dẫn-chạy)
7. [Biến môi trường](#7-biến-môi-trường)
8. [Kiểm thử](#8-kiểm-thử)
9. [Giới hạn hiện tại & lưu ý](#9-giới-hạn-hiện-tại--lưu-ý)

---

## 1. Giải pháp

### Bài toán

Doanh nghiệp bán hàng cross-border (TikTok Shop, e-commerce) cần liên tục sản xuất **video quảng cáo ngắn**. Quy trình truyền thống tốn nhiều ngày: viết brief, lên kịch bản, dựng, duyệt, chỉnh sửa. Chi phí cao, tốc độ chậm, và kịch bản thường không bám theo xu hướng đang thực sự chạy tốt trên nền tảng.

### Sản phẩm

**AI Short Video Ads Generator** — người dùng nhập brief sản phẩm, hệ thống tự sinh storyboard bám theo video đang trending thật, cho người dùng duyệt/chỉnh, rồi render ra video hoàn chỉnh.

Điểm khác biệt so với việc gọi thẳng một LLM:

| Thành phần | Giá trị mang lại |
|---|---|
| **RAG trên dữ liệu trending thật** | Storyboard được grounding bằng storyboard của video TikTok đang có doanh thu cao (nguồn Kalodata), không phải LLM tự bịa |
| **Human-in-the-Loop 3 trạng thái** | `approved` / `needs_revision` / `rejected` — người dùng chỉnh kịch bản trước khi tốn chi phí render |
| **Decision có cấu trúc** | AI trả về object có confidence, evidence, risk — không phải text tự do, nên backend áp policy được |
| **Tách 4 pod độc lập** | Mỗi pod build/deploy/test riêng, giao tiếp thuần HTTP |

### Triết lý hệ thống

```
Sense → Understand → Reason → Simulate → Decide → Act → Learn
  │         │           │                    │       │
 data/    data/       agent/              agent/  backend/
```

`data/` trả lời *"chúng ta có dữ liệu gì?"*. `agent/` trả lời *"nên làm gì?"*. `backend/` quyết định *"khi nào được phép làm"*. Không pod nào lấn sân pod khác.

---

## 2. Kiến trúc tổng quan

### 2.1 Bốn pod

```
                    ┌──────────────┐
                    │   FRONTEND   │  Nuxt 4 + Nuxt UI
                    │  Workspace   │
                    └──────┬───────┘
                           │ REST (JSON / multipart)
                           ▼
                    ┌──────────────┐        ┌──────────────┐
                    │   BACKEND    │───────▶│  Postgres    │  task / brief /
                    │  .NET 8 API  │        │  (app DB)    │  storyboard / ref
                    │ Orchestrate  │        └──────────────┘
                    └───┬──────┬───┘
                        │      │
              REST      │      │  REST
                        ▼      ▼
        ┌───────────────────┐  ┌────────────────────┐
        │   AI (agent/)     │  │      DATA          │
        │ Python, Clean Arch│─▶│ FastAPI :8002      │
        │ Reason / Decide   │  │ Postgres + pgvector│
        └─────────┬─────────┘  └─────────┬──────────┘
                  │                      │
                  ▼                      ▼
            Gemini API            Kalodata API (cron hằng ngày)
```

### 2.2 Nguyên tắc bất biến

| Nguyên tắc | Ý nghĩa |
|---|---|
| **Frontend không gọi AI/DATA trực tiếp** | Mọi request đi qua Backend. Backend là API boundary duy nhất |
| **Backend không chứa AI reasoning** | Backend điều phối, lưu state, áp policy — không prompt LLM |
| **Database per service** | Backend có Postgres riêng; Data có Postgres + object storage riêng. Backend **không bao giờ** query DB của Data, luôn qua HTTP API |
| **Agent không sở hữu DB lâu dài** | Agent chỉ giữ Memory trong phạm vi 1 task (context, lịch sử revision), trả kết quả về Backend |
| **Data không biết Agent tồn tại** | Data expose API sạch, không quan tâm ai gọi |
| **Không share code Python giữa container** | Mỗi pod tự định nghĩa Pydantic/DTO model của mình. Đồng bộ bằng convention + Swagger, không bằng shared package |
| **Mỗi pod có `GET /health`** | Điều kiện để pod khác được phép gọi vào (`depends_on: service_healthy`) |

### 2.3 Ai được gọi ai

| Từ | Đến | Cách |
|---|---|---|
| Frontend | Backend | REST — kênh duy nhất |
| Backend | Data | REST |
| Backend | Agent | REST |
| Agent | Data | REST (RAG retrieval) |
| Agent | Gemini / VideoRenderer | Qua Port trong `domain/ports/` |
| Backend | DB/storage của Data | **KHÔNG BAO GIỜ** trực tiếp |
| Frontend | Agent / Data | **KHÔNG BAO GIỜ** trực tiếp |

### 2.4 Đồng bộ vs bất đồng bộ

Agent call (Gemini + retrieval + evaluator + policy) mất 5–20 giây, và có bước duyệt của người dùng ở giữa. Nên luồng chia làm **2 pha**, không phải 1 request-response:

```
Pha 1 (analyze):  FE → BE → AI → DATA → AI (Storyboard) → BE lưu → FE hiện Action Card
                                   ⏸ người dùng duyệt
Pha 2 (execute):  FE (Approve) → BE → AI (render) → BE lưu → FE hiện video
```

Quy mô hackathon: **không dựng message queue**. Dùng HTTP đồng bộ với timeout dài (BE → AI: 30–60s), FE hiện loading state. Riêng bước render video là bất đồng bộ — trả `render_job_id` ngay, FE poll.

---

## 3. Chi tiết từng pod

### 3.1 Frontend — `frontend/`

**Stack:** Nuxt 4 · Vue 3 · Nuxt UI 4 · Tailwind 4 · ECharts · TypeScript · pnpm

```text
frontend/
├── app/
│   ├── pages/
│   │   ├── index.vue                  # landing
│   │   ├── workspace.vue              # Intelligence Workspace
│   │   ├── history.vue
│   │   ├── briefs/index.vue           # danh sách brief
│   │   ├── briefs/new.vue             # form nhập brief (8 nhóm)
│   │   ├── briefs/[id].vue
│   │   ├── briefs/[id]/storyboard.vue # màn HITL duyệt storyboard
│   │   ├── briefs/[id]/videos.vue
│   │   ├── renders/[id].vue           # theo dõi tiến trình render
│   │   └── renders/[id]/result.vue    # player + download
│   ├── composables/
│   │   ├── useApi.ts                  # chọn base URL: demo mock hay backend thật
│   │   ├── usePipelineApi.ts          # brief → storyboard → review → render
│   │   └── useEngineApi.ts
│   └── types/brief.ts
└── server/api/v1/                     # Nitro mock server (chỉ dùng ở DEMO MODE)
```

**Demo mode** — điểm quan trọng khi chạy:

- `NUXT_PUBLIC_DEMO_MODE=true` → `useApi` trỏ base URL về `/api/v1` (Nitro server nội bộ), toàn bộ dữ liệu lấy từ `server/utils/mockData.ts`. Chạy được **độc lập, không cần backend**.
- `NUXT_PUBLIC_DEMO_MODE=false` → trỏ về `NUXT_PUBLIC_API_BASE` (backend thật).

`usePipelineApi.ts` có hàm `mapAgentPlanToUiPlan` chuyển shape storyboard của Agent (`hook` / `scenes[]` / `call_to_action`, dùng `time_start_seconds`) sang shape phẳng mà UI render (`scenes[]` với `duration_ms`, `visual_description`, `audio_script`).

### 3.2 Backend — `backend/`

**Stack:** .NET 8 Web API · FastEndpoints (REPR pattern) · Swagger · xUnit + FluentAssertions + Moq

```text
backend/
├── Endpoints/
│   ├── HealthCheckEndpoint.cs           GET  /health
│   ├── UploadVideoEndpoint.cs           POST /api/v1/videos/upload
│   ├── GetDashboardOverviewEndpoint.cs  GET  /api/v1/dashboard/overview
│   ├── RunSimulationEndpoint.cs         POST /api/v1/simulation/run
│   ├── GetDecisionEndpoint.cs           GET  /api/v1/decision/latest
│   └── ExecuteWorkflowEndpoint.cs       POST /api/v1/workflow/execute
├── Models/UploadVideoDtos.cs
├── Program.cs                           CORS, FastEndpoints, Swagger, Kestrel 150MB
└── tests/AIHackathonApi.Tests/
```

Cấu hình đáng chú ý trong `Program.cs`:
- Upload limit nâng lên **150 MB** (cả Kestrel lẫn `FormOptions`) để nhận video.
- CORS `AllowAnyOrigin` — chấp nhận được ở phạm vi hackathon, cần siết trước khi lên production.
- Swagger UI bật sẵn tại `/swagger`.

### 3.3 AI Agent — `agent/`

**Stack:** Python 3.12 · Clean Architecture 4 tầng · `google-genai` (Gemini) · Pydantic Settings · pytest

```text
agent/
├── domain/                  # thuần logic, không phụ thuộc framework
│   ├── entities/            task.py · context.py · decision.py · agent_state.py
│   ├── policies/            decision_policy.py · tool_policy.py · retry_policy.py
│   ├── ports/               llm.py · tool.py · retriever.py · memory.py · evaluator.py
│   └── value_objects/       confidence.py · token_usage.py
├── application/
│   ├── context/context_builder.py       # gom brief + asset + RAG docs
│   ├── reasoning/reasoning_service.py   # gọi LLM
│   ├── services/decision_service.py     # sinh Decision có cấu trúc
│   ├── execution/executor.py            # thực thi tool sau khi được duyệt
│   ├── workflows/workflow.py
│   └── agent/agent.py, agent_factory.py
├── infrastructure/
│   ├── llm/gemini_provider.py, mock_llm.py
│   ├── retrieval/http_json_retriever.py, in_memory_retriever.py
│   └── memory/in_memory_memory.py
├── bootstrap/container.py   # Composition Root DUY NHẤT
├── config/settings.py
└── observability/logging.py
```

**Quy tắc kiến trúc quan trọng:** `bootstrap/container.py` là nơi **duy nhất** được phép import cả `GeminiProvider` lẫn `MockLLM` cùng lúc, và là nơi duy nhất đọc `settings` trực tiếp. Mọi nơi khác chỉ biết Protocol (`domain/ports/llm.py`) và nhận dependency qua constructor. Thêm provider mới (OpenAI, Anthropic) chỉ sửa file này.

**Workflow 5 bước** (đúng như sơ đồ SVG):

1. **Context Builder** — gom brief + asset + gọi `HttpJsonRetriever` lấy trending video từ Data
2. **Evaluator** — LLM (Gemini) phân tích, sinh storyboard nháp
3. **Decision Policy** — áp ngưỡng confidence, sinh `Decision` có cấu trúc
   → ⏸ trả về Backend → Frontend, chờ người dùng duyệt
4. **Tool Policy** — kiểm tra action có được phép thực thi không (`TOOL_AUTO_DENY_UNKNOWN_TOOLS=true`)
5. **Tool.execute()** — render video, QA check, trả `Result` về Backend

`DecisionPolicy` điều khiển bằng env, không hardcode:
- `DECISION_AUTO_EXECUTE_THRESHOLD=0.85` — trên ngưỡng này được tự chạy
- `DECISION_REJECT_THRESHOLD=0.3` — dưới ngưỡng này từ chối luôn
- `DECISION_ALLOW_HIGH_RISK_AUTO_EXECUTE=false` — action rủi ro cao luôn phải có người duyệt

Vòng lặp `needs_revision` chỉ gửi `{ task_id, feedback }` — **không gửi lại brief/asset**, vì Agent đã lưu Context vào `Memory` theo `task_id` từ lần sinh đầu tiên. Giới hạn bằng `MAX_STORYBOARD_REVISIONS=3`, vượt ngưỡng thì đánh dấu cần review thủ công.

### 3.4 Data — `data/`

**Stack:** Python 3.12 · FastAPI · Postgres 16 + pgvector · fastembed · Dagster (asset graph) · DuckDB + Delta Lake (tầng transform) · Polars

```text
data/
├── api.py                  # FastAPI edge :8002
├── defs/                   # Dagster assets — ingest, transform, publish, checks, schedules
├── lib/                    # settings · db · embedding · rerank · storyboard · gemini · sql · delta
├── sql/
│   ├── 001_init.sql        # schema khởi tạo (chạy tự động khi container Postgres lên lần đầu)
│   └── transforms/         # SQL sinh Silver / Gold
├── contracts/              # Pandera schema, mỗi dataset một file
├── scripts/                # seed data + pipeline Kalodata
├── docker-compose.yml      # postgres(pgvector) + api + kalodata-cron
├── Dockerfile              # image cho API
└── Dockerfile.pipeline     # image cho cron pipeline (deps tối thiểu)
```

**HTTP API (`:8002`)** — 4 endpoint thực sự đang chạy:

```
GET  /health
GET  /api/v1/data/query          ?q=...&top_k=...
POST /api/v1/data/query          { q, top_k }
GET  /api/v1/videos/trending     ?q=...&top_k=...
POST /api/v1/videos/trending     { q, top_k, key_message, audience_profile, product_features }
```

`POST /api/v1/videos/trending` là endpoint Agent gọi khi làm RAG. `q` nên là `productInfoJson.productName` (fallback sang `productCategory`) — giữ tên tham số là `q` vì `HttpJsonRetriever` bên Agent hardcode tên này. Ba trường `key_message` / `audience_profile` / `product_features` chỉ làm giàu vế **semantic**, không đụng vào vế lexical.

**Retrieval hybrid:** `pg_trgm` (lexical) + vector similarity (semantic) chạy song song, fuse bằng RRF trong **một câu SQL duy nhất**, rồi rerank bằng cross-encoder. Cấu hình qua env: `RETRIEVAL_RRF_K`, `RETRIEVAL_LEG_K`, `RETRIEVAL_TRIGRAM_THRESHOLD`, `RETRIEVAL_TRENDING_HALF_LIFE_DAYS` (video cũ bị giảm điểm theo hàm mũ, chu kỳ bán rã 14 ngày).

**Định dạng lỗi thống nhất** — mọi pod dùng chung envelope này:

```json
{ "error": { "code": "LLM_TIMEOUT", "message": "...", "request_id": "..." } }
```

### 3.5 Business — `business/`

Chứa định nghĩa nghiệp vụ (domain, use case, KPI, ràng buộc), **không chứa implementation**. Tách ra để cùng một nền tảng kỹ thuật phục vụ được bài toán khác mà không phải sửa core.

---

## 4. Luồng xử lý end-to-end

```
1.  FRONTEND      Người dùng nhập Brief (8 nhóm) + upload asset (ảnh/video)
                       ↓
2.  BACKEND       Validate Brief → lưu Postgres của Backend → gọi DATA gửi asset thô
                       ↓
3.  DATA          Xử lý asset (chuẩn hoá, validate) → lưu file vào object storage,
                  ghi object_key vào Postgres riêng → TRẢ VỀ nội dung đã xử lý
                  (bytes/base64) + object_ref trong CÙNG một lần gọi
                       ↓
4.  BACKEND       Lưu object_ref (audit) → giữ nội dung thật trong request hiện tại
                  → gọi AGENT lần 1: POST /agent/reasoning/storyboard
                    kèm BRIEF ĐẦY ĐỦ + NỘI DUNG ASSET THẬT (không phải ref)
                       ↓
5.  AGENT (1)     Lưu Context vào Memory theo task_id
                  → ContextBuilder gọi DATA /api/v1/videos/trending lấy storyboard trending
                  → Gemini sinh StoryboardPlan + compliance check
                  → trả StoryboardPlan về BACKEND
                       ↓
6.  BACKEND       Lưu StoryboardPlan (revision 1) → trả FRONTEND render Action Card
                       ↓
7.  ⏸ HITL       Người dùng quyết định — 3 nhánh:
                  ├─ approved        → sang bước 9
                  ├─ needs_revision  → BE → AGENT POST /storyboard/revise
                  │                    body CHỈ { task_id, feedback }
                  │                    Agent đọc lại Context từ Memory → sinh revision N+1
                  │                    → quay lại bước 7 (giới hạn MAX_STORYBOARD_REVISIONS)
                  └─ rejected        → task kết thúc
                       ↓ (chỉ khi approved)
9.  AGENT (2)     POST /agent/render → trả render_job_id NGAY (bất đồng bộ)
                       ↓
10. AGENT         VideoRenderer (Seedance) submit → poll status
                  QAChecker so frame output với asset gốc (Gemini Vision)
                  → trả RenderResult { video_url tạm, qa_report }
                  Agent KHÔNG tự lưu, KHÔNG tự tải video về
                       ↓
11. BACKEND       Gửi video_url tạm sang DATA để tải và lưu vĩnh viễn
                  → nhận ref/URL vĩnh viễn → ghi vào DB của mình
                       ↓
12. FRONTEND      Poll GET /api/v1/renders/{id} → hiện player + download
```

**Hai quyết định thiết kế đã chốt:**

1. **Data trả nội dung đã xử lý, không chỉ ref.** Trước đây Data chỉ trả `object_ref`, buộc Backend gọi lại xin `presigned_url` mỗi lần cần chuyển asset cho Agent — URL có thể hết hạn trong lúc chờ người dùng duyệt. Giờ Data trả luôn bytes trong cùng lần gọi; `object_ref` vẫn được lưu hai phía để audit.

2. **HITL có 3 trạng thái, không nhị phân.** `needs_revision` cho phép chỉnh kịch bản mà không phải làm lại từ đầu, và không tốn chi phí render cho bản chưa ưng.

---

## 5. RAG: trending video từ Kalodata

Đây là phần tạo ra khác biệt thật của giải pháp — storyboard được grounding bằng dữ liệu video đang chạy tốt, không phải LLM tự nghĩ.

### Pipeline hằng ngày

Container `kalodata-cron` chạy `scripts/kalodata_daily_pipeline.py` lúc **03:00 UTC**:

```
discover  →  fetch  →  analyze  →  index
```

1. **discover** (`kalodata_top_videos.discover_keywords`) — tự tìm category/sản phẩm doanh thu cao nhất hôm nay qua Kalodata API. Không cần nhập keyword thủ công.
2. **fetch** (`kalodata_download_videos`) — tải video mới cho từng keyword, ghi vào Bronze.
3. **analyze** (`kalodata_analyze_videos`) — Gemini phân tích từng video Bronze mới, trích ra storyboard có cấu trúc, ghi vào Silver.
4. **index** (`index_storyboards`) — chunk + embed Silver bằng fastembed, upsert vào pgvector.

**Toàn bộ pipeline idempotent** — chạy hai lần trong ngày vẫn an toàn: Bronze/Silver dedup theo `video_id`, index upsert theo `chunk_id`. Chạy lại một video đã xử lý tốn **0 lời gọi model**.

Chạy tay:

```bash
cd data
python -m scripts.kalodata_daily_pipeline
```

### Đường đi từ dữ liệu tới prompt

```
Kalodata API ──▶ Bronze ──Gemini──▶ Silver (storyboard) ──fastembed──▶ pgvector
                                                                          │
                        Agent ContextBuilder ◀── /api/v1/videos/trending ─┘
                                    │
                                    ▼
                        Gemini prompt (có ví dụ thật) ──▶ StoryboardPlan
```

Bên Agent, bật RAG bằng cách set `RETRIEVAL_BASE_URL`. **Nếu để trống, retrieval tự degrade thành no-op** — Agent vẫn chạy được, chỉ mất phần grounding. Rất tiện khi test local không có Data pod.

```bash
RETRIEVAL_BASE_URL=http://data:8002/api/v1/videos/trending
RETRIEVAL_TOP_K=5
```

---

## 6. Hướng dẫn chạy

### Yêu cầu

| Công cụ | Phiên bản | Cần cho |
|---|---|---|
| Docker + Docker Compose | v2+ | Cách 1 (khuyến nghị) |
| Node.js | 20+ | Frontend dev |
| pnpm | 11+ | Frontend dev |
| .NET SDK | 8.0 | Backend dev |
| Python | 3.12 | Agent / Data dev |

**API key cần có** (xin trước khi chạy bản đầy đủ):
- `LLM_GEMINI_API_KEY` — https://aistudio.google.com/apikey
- `KALODATA_API_KEY` — chỉ cần nếu muốn chạy pipeline trending

---

### Cách 1 — Chạy nhanh toàn hệ thống bằng image dựng sẵn (khuyến nghị cho demo)

```bash
cd beyond-intelligence

# 1. Tạo .env cho agent (bắt buộc — compose mount file này vào container ai)
cp agent/.env.example agent/.env
# mở agent/.env, điền LLM_GEMINI_API_KEY=<key thật>

# 2. Kéo image và chạy
docker compose -f infrastructure/docker-compose.yml up -d

# 3. Kiểm tra
docker compose -f infrastructure/docker-compose.yml ps
```

Sau khi các container `healthy`:

| Service | URL | Ghi chú |
|---|---|---|
| Frontend | http://localhost:3000 | UI chính |
| Backend | http://localhost:8000 | API |
| Backend Swagger | http://localhost:8000/swagger | Thử API trực tiếp |
| Agent | http://localhost:8001/health | |
| Postgres | `localhost:5432` | user `postgres` / pass `mysecretpassword` / db `my_app_db` |

Dừng:

```bash
docker compose -f infrastructure/docker-compose.yml down        # giữ dữ liệu
docker compose -f infrastructure/docker-compose.yml down -v     # xoá luôn volume Postgres
```

> **Lưu ý:** `infrastructure/docker-compose.yml` **không khai báo service `data`**, dù backend có sẵn biến `DATA_SERVICE_URL=http://data:8002`. Muốn chạy đủ cả Data pod thì làm theo mục [6.3](#63-chạy-data-pod).

---

### Cách 2 — Chạy từng pod ở chế độ dev

#### 6.1 Chỉ Frontend (demo mode — không cần backend)

Nhanh nhất để xem toàn bộ UI/UX. Nitro server nội bộ trả dữ liệu mock, đi được trọn luồng brief → storyboard → render → result.

```bash
cd frontend
cp .env.example .env          # NUXT_PUBLIC_DEMO_MODE="true" đã bật sẵn
pnpm install
pnpm dev                      # http://localhost:3000
```

Muốn nối vào backend thật, sửa `.env`:

```bash
NUXT_PUBLIC_DEMO_MODE="false"
NUXT_PUBLIC_API_BASE="http://localhost:8000/api/v1"
```

Lệnh khác: `pnpm build` · `pnpm preview` · `pnpm lint` · `pnpm typecheck`

#### 6.2 Backend

```bash
cd backend
cp .env.example .env
dotnet restore
dotnet run                    # http://localhost:8000 · Swagger tại /swagger
```

Chạy riêng bằng Docker:

```bash
docker pull duytrong298/be-beyond-intelligence:demo-v1.1
docker run -d -p 8000:8000 --name beyond_backend duytrong298/be-beyond-intelligence:demo-v1.1
```

#### 6.3 Chạy Data pod

Data có compose riêng (Postgres + pgvector, API, cron pipeline):

```bash
cd data
cp .env.example .env
# điền GEMINI_API_KEY và KALODATA_API_KEY nếu muốn chạy pipeline trending

docker compose up -d           # postgres :5432 · api :8002 · kalodata-cron

curl http://localhost:8002/health
curl "http://localhost:8002/api/v1/videos/trending?q=skincare&top_k=5"
```

`sql/001_init.sql` được nạp tự động khi container Postgres khởi tạo lần đầu.

Chạy API ở chế độ dev không qua Docker:

```bash
cd data
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # đầy đủ (gồm Dagster, dlt, docling)
# hoặc nhẹ hơn:
pip install -r requirements-api.txt      # chỉ để chạy api.py
pip install -r requirements-pipeline.txt # chỉ để chạy pipeline Kalodata

uvicorn api:app --port 8002 --reload
```

Seed dữ liệu mẫu (không cần API key ngoài) và chạy asset graph:

```bash
python scripts/seed_files.py
python -m scripts.seed_erp_db
uvicorn scripts.mock_channel_api:app --port 8099 &   # mock nguồn REST
python scripts/verify_integrations.py                # kiểm tra kết nối
dagster dev                                          # UI Dagster, materialize asset graph
```

**Nối Data vào network chung:** hai compose file nằm ở hai project khác nhau nên mặc định **không thấy nhau**. Cho container `data` join vào network của hệ thống chính:

```bash
docker network connect beyond-intelligence-net data-api-1
```

(kiểm tra tên container thật bằng `docker compose -p data ps`)

#### 6.4 Agent

```bash
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# điền LLM_GEMINI_API_KEY
```

Chạy không tốn quota LLM — dùng mock provider:

```bash
LLM_PROVIDER=mock python -m pytest
```

> **Lưu ý:** repo `agent/` hiện **chưa có tầng HTTP** (không có FastAPI/uvicorn trong `requirements.txt`, không có thư mục `interface/`). Container `ai` trong compose dùng image dựng sẵn `phamchivy/agent-beyond-intelligence:demo-v1` đã có sẵn tầng này. Xem [mục 9](#9-giới-hạn-hiện-tại--lưu-ý).

---

## 7. Biến môi trường

### `agent/.env`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` \| `openai` \| `anthropic` \| `mock` |
| `LLM_MODEL` | `gemini-2.0-flash` | |
| `LLM_GEMINI_API_KEY` | — | **Bắt buộc** khi provider là gemini |
| `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` / `LLM_TIMEOUT_SECONDS` | `0.2` / `2048` / `30` | |
| `DECISION_AUTO_EXECUTE_THRESHOLD` | `0.85` | Trên ngưỡng → tự thực thi |
| `DECISION_REJECT_THRESHOLD` | `0.3` | Dưới ngưỡng → từ chối |
| `DECISION_ALLOW_HIGH_RISK_AUTO_EXECUTE` | `false` | Action rủi ro cao luôn cần người duyệt |
| `RETRY_MAX_ATTEMPTS` / `RETRY_BASE_DELAY_SECONDS` / `RETRY_BACKOFF_MULTIPLIER` | `3` / `1.0` / `2.0` | |
| `TOOL_AUTO_DENY_UNKNOWN_TOOLS` | `true` | Tool lạ bị chặn mặc định |
| `RETRIEVAL_BASE_URL` | *(trống)* | Trống = tắt RAG, agent vẫn chạy |
| `RETRIEVAL_TOP_K` | `5` | |
| `MAX_ITERATIONS` | `10` | Trần vòng lặp reasoning |
| `MAX_STORYBOARD_REVISIONS` | `3` | Trần vòng lặp HITL |
| `OBSERVABILITY_LOG_PROMPTS` | `false` | Chỉ bật khi debug local |

### `data/.env`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | `postgresql://bi:bi@localhost:5432/bi` | Trong compose bị override thành host `postgres` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-3.6-flash` | Phân tích video |
| `KALODATA_API_KEY` | — | Bắt buộc cho pipeline trending |
| `KALODATA_REGION` / `_LANGUAGE` / `_CURRENCY` | `US` / `en-US` / `USD` | |
| `STORAGE_URL` | `s3://bi-data-dev` | Để trống `STORAGE_ENDPOINT_URL` nếu dùng AWS S3 thật |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_MAX_TOP_K` | `5` / `50` | |
| `RETRIEVAL_RRF_K` / `RETRIEVAL_LEG_K` | `60` / `50` | Tham số fuse hybrid search |
| `RETRIEVAL_TRENDING_HALF_LIFE_DAYS` | `14.0` | Giảm điểm video cũ |
| `QUALITY_MAX_REJECTED_RATIO` / `QUALITY_BLOCKING` | `0.05` / `true` | Quá 5% row hỏng → chặn pipeline |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8002` | |

### `backend/.env`

| Biến | Ví dụ |
|---|---|
| `ASPNETCORE_URLS` | `http://+:8000` |
| `ConnectionStrings__DefaultConnection` | `Host=db;Port=5432;Database=my_app_db;Username=postgres;Password=...` |
| `AI_SERVICE_URL` | `http://ai:8001` |
| `DATA_SERVICE_URL` | `http://data:8002` |

### `frontend/.env`

| Biến | Ví dụ |
|---|---|
| `NUXT_PUBLIC_DEMO_MODE` | `true` = dùng mock nội bộ, `false` = gọi backend thật |
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` |
| `NUXT_PUBLIC_APP_NAME` / `_DESCRIPTION` | `"Beyond Intelligence"` / `"AI Short Video Ads Generator"` |

> Trong container, luôn dùng **service name** làm hostname (`http://ai:8001`), không dùng `localhost`. Riêng `NUXT_PUBLIC_API_BASE` là ngoại lệ — biến này chạy trên **browser của người dùng**, nên phải là địa chỉ browser truy cập được.

---

## 8. Kiểm thử

```bash
# Agent — unit test không cần API key
cd agent && LLM_PROVIDER=mock python -m pytest

# Agent — có cả integration test (cần Gemini key thật)
cd agent && python -m pytest -m integration

# Data — unit test (integration bị loại mặc định)
cd data && python -m pytest

# Data — integration (cần Postgres + object storage + mạng)
cd data && python -m pytest -m integration

# Backend
cd backend && dotnet test

# Frontend
cd frontend && pnpm lint && pnpm typecheck
```

Cả hai pytest suite đều đánh dấu `integration` cho test cần mạng/API key thật, nên chạy `pytest` trần luôn an toàn và offline.

---

## 9. Giới hạn hiện tại & lưu ý

Ghi lại trung thực để người tiếp nhận không mất thời gian dò:

| Vấn đề | Chi tiết | Cách xử lý |
|---|---|---|
| **Agent thiếu tầng HTTP trong repo** | `agent/requirements.txt` không có FastAPI/uvicorn, không có `interface/`. Domain + application logic đã đủ; chỉ thiếu lớp mỏng expose `/analyze`, `/execute` | Container `ai` dùng image dựng sẵn đã có tầng này. Muốn build lại từ source thì thêm `interface/api/` — **không sửa domain/application** |
| **`infrastructure/docker-compose.yml` thiếu service `data`** | Backend có `DATA_SERVICE_URL` nhưng compose chính không dựng Data pod | Chạy `data/docker-compose.yml` riêng rồi `docker network connect` (mục 6.3) |
| **API surface Backend chưa khớp Frontend** | FE gọi `/briefs`, `/storyboards`, `/renders`; BE hiện expose `/videos/upload`, `/decision/latest`, `/workflow/execute`, `/simulation/run` | FE đang chạy DEMO MODE với Nitro mock. Cần map lại contract trước khi tắt demo mode |
| **`data/README.md` mô tả rộng hơn phần đã build** | Media pipeline (ffmpeg + Gemini), `POST /api/v1/assets`, `GET /api/v1/assets/{id}` **chưa build** | Phần đang chạy thật: retrieval hybrid + `/data/query` + `/videos/trending` + pipeline Kalodata |
| **CORS mở toàn bộ** | `AllowAnyOrigin()` trong `Program.cs` | Chấp nhận ở hackathon; siết theo domain trước production |
| **Secret trong compose** | Password Postgres hardcode trong `infrastructure/docker-compose.yml` | Chuyển sang `.env` / secret manager trước production |
| **Không có message queue** | BE → AI đồng bộ, timeout 30–60s | Có chủ đích, đúng quy mô hackathon. Ngưỡng để thêm queue: khi render vượt timeout HTTP hoặc cần chạy song song nhiều task |

### Xử lý sự cố thường gặp

**Container `ai` không lên `healthy`** — thiếu `agent/.env` hoặc `LLM_GEMINI_API_KEY` rỗng. Compose mount file này qua `env_file`, không có là container chết lúc init Gemini client.

```bash
docker compose -f infrastructure/docker-compose.yml logs ai
```

**Frontend gọi API lỗi CORS/404** — kiểm tra `NUXT_PUBLIC_DEMO_MODE`. Nếu là `false` mà backend chưa chạy, mọi request sẽ fail. Bật lại `true` để dùng mock.

**Data query trả rỗng** — index chưa có dữ liệu. Chạy `python -m scripts.kalodata_daily_pipeline` (cần `KALODATA_API_KEY`) hoặc seed bằng `scripts/seed_files.py` + `dagster dev`.

**Port bị chiếm** — mặc định dùng 3000 / 8000 / 8001 / 8002 / 5432. Đổi phần host trong `ports:` của compose (`"3001:3000"`).

---

## Tài liệu liên quan

| Tài liệu | Nội dung |
|---|---|
| [`docs/architecture/overall-architecture.svg`](docs/architecture/overall-architecture.svg) | Sơ đồ kiến trúc tổng quan |
| [`docs/architecture/integration-architecture.md`](docs/architecture/integration-architecture.md) | Hợp đồng API giữa 4 pod, packaging, error handling |
| [`docs/architecture/agent-architecture-standard.md`](docs/architecture/agent-architecture-standard.md) | Chuẩn kiến trúc tầng `agent/` |
| [`data/data-architecture.md`](data/data-architecture.md) | Chuẩn kiến trúc tầng dữ liệu — layering, pipeline, contract, quality |
| [`data/tech-stack-evaluation.md`](data/tech-stack-evaluation.md) | Đánh giá từng framework, cái nào chọn/loại và vì sao |
| [`data/implementation-plan.md`](data/implementation-plan.md) | Thứ tự build, file manifest, test manifest |
| [`data/rag-trending-video.md`](data/rag-trending-video.md) | Thiết kế pipeline RAG trending video |
| [`backend/README.md`](backend/README.md) | Tài liệu kỹ thuật Backend |
| [`../hackathon_docs/system-integration-flow.md`](../hackathon_docs/system-integration-flow.md) | Luồng tích hợp 12 bước, quyết định thiết kế |

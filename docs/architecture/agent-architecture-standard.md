# Agent Architecture Standard — Beyond Intelligence

> Chuẩn kiến trúc & quy tắc code cho lớp `agent/`, thiết kế để tái sử dụng cho mọi dự án AI Agent trong tương lai — chỉ thay đổi nội dung nghiệp vụ, không thay đổi khung.

**Phiên bản:** 1.0
**Ngày:** 10/08/2026
**Áp dụng cho:** thư mục `agent/`
**Nền tảng lý thuyết:** Clean Architecture (Robert C. Martin) + Hexagonal Architecture / Ports & Adapters (Alistair Cockburn) + Dependency Inversion Principle (SOLID), điều chỉnh riêng cho hệ thống AI/LLM.

---

## 1. Tư duy kiến trúc nền tảng

Agent **không phải là một class**, mà là một hệ thống nhiều lớp, phụ thuộc theo một chiều duy nhất:

```
Interface
    ↓
Application (Use Cases)
    ↓
Domain (Core)

Infrastructure (Adapters) ──── implements ────► Domain Ports
```

**Nguyên tắc bất biến:** Domain không được biết implementation cụ thể bên dưới.

```python
# Agent chỉ biết:
response = llm.generate(request)

# Agent KHÔNG được biết:
openai.chat.completions.create(...)
```

### Luật cấm tuyệt đối

Domain (`domain/`) **không được import**:
- `langgraph`, `llama_index`, bất kỳ agent framework nào
- `openai`, `anthropic`, bất kỳ LLM SDK nào
- `qdrant_client`, `redis`, bất kỳ driver DB/vector store nào

> **Use frameworks at the edges, not at the core.**
> Framework nằm ở `infrastructure/` (adapter) hoặc `application/workflows/` (orchestration), không bao giờ ở `domain/`.

---

## 2. Bốn tầng kiến trúc

```
┌─────────────────────────────────────────────┐
│                INTERFACE                     │
│         API / CLI / Event / UI               │
├─────────────────────────────────────────────┤
│              APPLICATION                     │
│   Agent / Workflow / Use Case / Orchestration │
├─────────────────────────────────────────────┤
│                 DOMAIN                       │
│  State / Task / Decision / Policy / Context  │
├─────────────────────────────────────────────┤
│              INFRASTRUCTURE                  │
│  LLM / DB / VectorDB / Tools / APIs / Kafka  │
└─────────────────────────────────────────────┘
```

| Tầng | Vai trò | Được phép biết |
|---|---|---|
| Domain | Định nghĩa "luật chơi": entity, port, policy | Không gì bên ngoài Python chuẩn + Pydantic/dataclass |
| Application | Điều phối use case, gọi domain qua port | Domain |
| Infrastructure | Cài đặt cụ thể (adapter) cho từng port | SDK, driver, framework ngoài |
| Interface | Expose ra ngoài (API/CLI) | Application |

---

## 3. Khung thư mục `agent/` — dùng lại cho mọi dự án

```text
agent/
│
├── domain/
│   ├── entities/
│   │   ├── task.py
│   │   ├── agent_state.py
│   │   ├── decision.py
│   │   └── context.py
│   │
│   ├── value_objects/
│   │   ├── confidence.py
│   │   └── token_usage.py
│   │
│   ├── ports/                     # trước đây gọi là interfaces/
│   │   ├── llm.py
│   │   ├── memory.py
│   │   ├── retriever.py
│   │   ├── tool.py
│   │   └── evaluator.py
│   │
│   └── policies/
│       ├── decision_policy.py
│       ├── retry_policy.py
│       └── tool_policy.py
│
├── application/                   # = Use Case layer
│   ├── agent/
│   │   ├── agent.py
│   │   └── agent_factory.py
│   │
│   ├── planning/
│   │   ├── planner.py
│   │   └── strategy.py
│   │
│   ├── reasoning/
│   │   └── reasoning_service.py
│   │
│   ├── execution/
│   │   ├── executor.py
│   │   └── parallel_executor.py   # fan-out/fan-in cho tool calls
│   │
│   ├── workflows/
│   │   ├── workflow.py
│   │   └── nodes/
│   │
│   └── services/
│       └── decision_service.py
│
├── infrastructure/                 # = Adapters
│   ├── llm/
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── vllm_provider.py
│   │   └── mock_llm.py
│   │
│   ├── memory/
│   │   ├── postgres_memory.py
│   │   └── redis_memory.py
│   │
│   ├── retrieval/
│   │   ├── pgvector_retriever.py
│   │   └── qdrant_retriever.py
│   │
│   └── tools/
│       ├── web_search_tool.py
│       ├── database_tool.py
│       └── api_tool.py
│
├── prompts/                        # prompt versioning
│   ├── registry.py
│   └── templates/
│       └── v1/
│
├── bootstrap/                      # Composition Root
│   └── container.py
│
├── config/
│   ├── settings.py
│   └── providers.py
│
├── observability/
│   ├── logging.py
│   ├── tracing.py
│   └── metrics.py
│
├── evaluation/
│   ├── evaluators/
│   ├── datasets/
│   ├── metrics/
│   └── runners/
│
└── tests/
    ├── unit/
    │   ├── domain/
    │   ├── planning/
    │   ├── reasoning/
    │   └── policies/
    │
    ├── integration/
    │   ├── llm/
    │   ├── retrieval/
    │   ├── memory/
    │   └── tools/
    │
    └── e2e/
        └── agent/
```

---

## 4. Quy tắc Function vs Class vs Interface

### Function — khi logic không cần giữ state

```python
def normalize_query(query: str) -> str:
    return query.strip().lower()

def calculate_confidence(scores: list[float]) -> float:
    return sum(scores) / len(scores)
```

Không biến mọi thứ thành class chỉ vì "cho giống OOP".

### Class — dùng khi object có

1. **State**
   ```python
   class AgentState:
       messages: list
       current_task: Task
       observations: list
   ```
2. **Lifecycle** (`run()`, `reset()`)
3. **Dependency** (constructor nhận llm, retriever, memory...)
4. **Nhiều implementation cho cùng một abstraction** (`OpenAILLM`, `VLLM`, `OllamaLLM`)

### Interface (Protocol) — chỉ dùng cho boundary quan trọng

Dùng khi bạn dự đoán implementation sẽ thay đổi hoặc cần mock để test.

```python
from typing import Protocol

class LLM(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
```

**Các boundary hợp lệ để dùng Interface:** LLM, Retriever, Embedding, VectorStore, Memory, Tool, Evaluator, Policy.

**Không lạm dụng interface** cho mọi service (`UserServiceInterface` + `UserService` + `UserServiceImpl` + `UserServiceFactory`...). Nếu chỉ có một hàm thuần túy → cứ để là function.

---

## 5. Data Model tách khỏi Business Logic

Dùng Pydantic/dataclass cho toàn bộ data object, không trộn logic vào entity.

```python
@dataclass(frozen=True)
class AgentState:
    task: Task
    messages: list[Message]
    observations: list[Observation]

    def with_observation(self, obs: Observation) -> "AgentState":
        return replace(self, observations=[*self.observations, obs])
```

```python
class DecisionResponse(BaseModel):
    action: str
    confidence: float
    reasoning: str
    evidence: list[str]
```

> **`AgentState` bắt buộc immutable (`frozen=True`).** Mọi thay đổi trả về instance mới thay vì mutate tại chỗ. Đây là điều kiện để "replay" lại toàn bộ trajectory của agent phục vụ debug và evaluation — nếu state bị mutate trực tiếp, khả năng time-travel debug sẽ mất.

**Nguyên tắc:** Data structure ≠ Business logic.

---

## 6. Agent phải cực kỳ mỏng (Thin Agent, No God Object)

**Không viết:**

```python
class Agent:
    def run(self):
        # retrieve
        # call llm
        # parse
        # memory
        # tools
        # database
        # business logic
        # retry
        # logging
        ...
```

**Thay vào đó, tách trách nhiệm:**

```
Agent
 ├── ContextBuilder
 ├── Planner
 ├── Reasoner
 ├── ToolExecutor
 ├── Memory
 ├── Policy
 └── Evaluator
```

Agent chỉ làm nhiệm vụ **orchestration**:

```python
class Agent:
    async def run(self, task: Task) -> Decision:
        state = self.context.build(task)
        plan = await self.planner.plan(state)

        for step in plan:
            result = await self.executor.execute(step)
            state = state.with_observation(result)

        return await self.decision.make(state)
```

---

## 7. Các Port bắt buộc và Adapter tương ứng

### Tool

```python
class Tool(Protocol):
    @property
    def name(self) -> str: ...

    async def execute(self, arguments: dict) -> ToolResult: ...
```

```
Tool
├── SearchTool
├── DatabaseTool
├── CalculatorTool
└── APIActionTool
```

Trước khi `ToolExecutor` chạy, phải đi qua **`ToolPolicy`** — lớp kiểm soát quyền hạn: tool nào được phép chạy trong ngữ cảnh nào, tool có side-effect cao (ghi DB, gọi API bên ngoài, thanh toán...) cần thêm bước xác nhận/giới hạn, và chặn agent gọi tool ngoài kế hoạch (phòng prompt-injection cố lái agent gọi tool không được yêu cầu).

```
Planner → ToolPolicy → ToolExecutor → Tool
```

### Memory

```python
class Memory(Protocol):
    async def get(self, key: str) -> MemoryItem | None: ...
    async def save(self, item: MemoryItem) -> None: ...
```

```
Memory
├── InMemory
├── RedisMemory
├── PostgreSQLMemory
└── VectorMemory
```

Agent gọi `memory.get(...)`, không bao giờ gọi trực tiếp `redis.get(...)`.

### Retriever

```python
class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int) -> list[Document]: ...
```

```
Retriever
├── PGVectorRetriever
├── QdrantRetriever
├── ElasticsearchRetriever
└── HybridRetriever
```

Có thể đổi vector DB mà không cần sửa Agent.

---

## 8. Retry Policy — tách khỏi cả LLM lẫn Agent

**Không** để cả hai bên cùng retry:

```
Agent retry × LLM retry × HTTP retry → có thể tạo ra 27 requests từ 1 lỗi
```

Retry phải là một policy tường minh, nằm giữa Application và LLM:

```
Application
    ↓
Retry Policy
    ↓
LLM
```

---

## 9. Prompt Versioning

Mọi quyết định (`Decision`) do agent sinh ra phải truy vết được **prompt version** đã tạo ra nó — đây là điều kiện bắt buộc để hệ thống explainable/traceable.

```text
prompts/
├── registry.py       # map: prompt_name + version → template
└── templates/
    └── v1/
        ├── planner_system.md
        └── decision_prompt.md
```

`Decision` / trace log phải lưu kèm `prompt_version` đã dùng để sinh ra nó, tương tự như lưu `model` và `model_version`.

---

## 10. Dependency Injection & Composition Root

**Không** hard-code implementation trong Agent:

```python
# SAI — khóa cứng vào infrastructure
class Agent:
    def __init__(self):
        self.llm = OpenAI(...)
        self.memory = Redis(...)
```

**Đúng** — inject từ bên ngoài:

```python
agent = Agent(
    planner=planner,
    llm=llm,
    memory=memory,
    retriever=retriever,
    tools=tools,
)
```

### Composition Root (`bootstrap/container.py`)

Nơi **duy nhất** trong toàn bộ `agent/` được phép biết implementation cụ thể (OpenAI, Qdrant, Redis...).

```python
def build_agent(settings: Settings) -> Agent:
    llm = create_llm(settings)
    memory = create_memory(settings)
    retriever = create_retriever(settings)

    planner = Planner(llm)
    executor = ToolExecutor(tool_policy=ToolPolicy(...))

    return Agent(
        planner=planner,
        memory=memory,
        retriever=retriever,
        executor=executor,
    )
```

```
                container.py
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
     OpenAI        Qdrant        Redis
       │             │             │
       └─────────────┼─────────────┘
                      ▼
                    Agent
```

---

## 11. Song song hoá Tool Calls (Fan-out / Fan-in)

Không phải mọi plan đều tuần tự. Nhiều bước (ví dụ gọi nhiều tool độc lập cùng lúc) nên chạy song song. Định nghĩa sẵn interface cho `ParallelExecutor` ngay cả khi giai đoạn đầu chưa cần dùng, để tránh phải đổi contract của `Executor` về sau:

```python
class Executor(Protocol):
    async def execute(self, step: Step) -> StepResult: ...

class ParallelExecutor(Executor):
    async def execute_many(self, steps: list[Step]) -> list[StepResult]: ...
```

---

## 12. Config: một nguồn duy nhất

**Không** rải config khắp code:

```python
# SAI
MODEL = "claude-sonnet-5"
TEMPERATURE = 0.2
DB_URL = "..."
```

**Đúng** — tập trung tại `config/settings.py`:

```python
class Settings(BaseSettings):
    app_name: str
    environment: str

    llm_provider: str
    llm_model: str
    llm_temperature: float

    database_url: str
    log_level: str

settings = Settings()
```

### Ba loại config, xử lý khác nhau

| Loại | Ví dụ | Nơi lưu |
|---|---|---|
| **Secret** | `OPENAI_API_KEY`, `DATABASE_PASSWORD` | Secret manager / env |
| **Deployment config** | `LOG_LEVEL`, `DATABASE_URL`, `LLM_ENDPOINT` | Environment variables |
| **Application behavior** | `max_iterations`, `temperature`, `retrieval_top_k`, `timeout` | Typed configuration (Pydantic Settings) |

Không hard-code bất kỳ loại nào ở trên.

---

## 13. Logging — tuyệt đối không `print()`

```python
# SAI
print("Agent done")

# ĐÚNG
logger.info(
    "agent_step_completed",
    extra={"agent_id": agent_id, "step": step, "latency_ms": latency},
)
```

Trong production, ứng dụng chỉ cần phát log ra stdout/stderr; việc thu thập và routing log là trách nhiệm của môi trường vận hành (Twelve-Factor App).

### Trường bắt buộc log với AI Agent

```
request_id, trace_id, agent_id, task_id, step_id
model, model_version, prompt_version
prompt_tokens, completion_tokens, latency
tool_name, tool_latency, tool_success
retrieval_top_k, retrieval_score
decision, confidence
```

**Không log:** API key, password, raw sensitive data, hoặc toàn bộ prompt/user data một cách vô kiểm soát. AI system rất dễ biến logging thành nguồn rò rỉ dữ liệu.

---

## 14. Tracing

Một request đi qua agent tạo ra cả một cây span:

```
Trace
 └── Span: Agent
      ├── Span: Retrieval
      ├── Span: LLM
      ├── Span: Tool
      └── Span: Decision
```

Kiến trúc phải hỗ trợ tracing ngay từ đầu (interface đơn giản trong `observability/tracing.py`), để sau này gắn OpenTelemetry/Langfuse/Phoenix mà **không cần sửa business logic**.

---

## 15. Testing — 3 tầng, và AI cần thêm 1 tầng nữa

```text
tests/
├── unit/          # không gọi OpenAI, DB, internet — nhanh
├── integration/   # Agent ↔ real LLM / DB / VectorDB
└── e2e/           # input → Agent → Tools → Decision → output
```

### Tầng đánh giá riêng cho AI (khác software test truyền thống)

Software test thông thường: `expected == actual`
AI system: `quality >= threshold`

Ví dụ metric: agent accuracy, tool selection accuracy, Retrieval Recall@K, faithfulness, task completion rate, cost, latency.

→ `evaluation/` là **một component chính của hệ thống**, không phải notebook phụ chạy tay.

---

## 16. Nguyên tắc phát triển — đừng over-engineer ngay từ đầu

**Ngày đầu chỉ cần dựng:**

```
Agent Core
├── State
├── LLM port
├── Tool port
├── Planner
├── Executor
└── Decision
```

**Thêm dần theo nhu cầu thực tế, không làm trước:**

```
Agent Core
   │
   ├── LLM ── Tools ── Memory
   │            │
   │            ▼
   │        Retrieval
   │            │
   │            ▼
   │        Simulation
   │            │
   │            ▼
   │        World Model
```

Ghi nhớ: kiến trúc này là một **engineering hypothesis**, không phải "best architecture" bất biến. Mỗi lần thay LLM provider, agent framework, memory hay retrieval engine, nên ghi lại lý do kiến trúc cũ không còn phù hợp — đây là tư liệu quý để phát triển tư duy AI systems engineering về sau.

---

## 17. Checklist nhanh khi review code trong `agent/`

- [ ] `domain/` không import bất kỳ SDK/framework ngoài nào
- [ ] Class chỉ được tạo khi có state / lifecycle / dependency / nhiều implementation
- [ ] Mọi boundary quan trọng (LLM, Tool, Memory, Retriever, Evaluator) đều có Port (Protocol)
- [ ] `AgentState` là immutable (`frozen=True`)
- [ ] Agent không tự chứa business logic — chỉ orchestration
- [ ] Tool luôn đi qua `ToolPolicy` trước khi execute
- [ ] Retry nằm ở một Policy riêng, không lặp ở nhiều tầng
- [ ] Mọi Decision lưu kèm `prompt_version`, `model_version`
- [ ] Không `print()` — chỉ dùng `logger` có structured fields
- [ ] Không hard-code config — tất cả qua `Settings`
- [ ] Implementation cụ thể chỉ được "biết" ở `bootstrap/container.py`
- [ ] Có test unit (mock hoàn toàn) + integration + e2e + evaluation riêng
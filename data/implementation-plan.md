# Data Layer — Implementation Blueprint

**Version:** 2.0
**Date:** 18/08/2026
**Implements:** [data-architecture.md](data-architecture.md) v1.1
**Status of `data/`:** zero code. Everything in this document is to be created.

---

## 0. How to use this document

[data-architecture.md](data-architecture.md) is **why**. This document is **what**. It does not re-argue a single decision; where you want a reason, follow the `(§n)` citation.

Three rules for whoever implements this, human or agent:

1. **Never invent a name that is not in this document.** Every identifier that two files must agree on — port methods, entity fields, SQL columns, JSON keys, env vars, path templates, error codes — is fixed here. If you need a name that is not here, that is a gap in this document: add it here first, then use it.
2. **Never create a file listed under DO NOT CREATE YET (§8.9).** An empty file with a docstring is worse than a missing one: it looks implemented, it imports fine, and nothing fails.
3. **Never skip a stage gate (§15).** Each stage ends in one command. Run it. If it fails, the fault is in that stage's files and nowhere else — which is the entire reason the stages exist.

Everything runs with `data/` as the working directory.

---

## 1. Scope

### Built here

The media slice end to end, then the structured path over the boundaries it proved:

```
register an asset → extract (frames, audio, transcript, captions) → index → query over HTTP
                                    then
                     CSV → Bronze → normalize → Silver → model → Gold → api.v1_*
```

Six pipelines (§7), four medallion layers (§3), the ports of §6, the four HTTP endpoints of §11.4, and the eval harness skeleton.

### DO NOT BUILD — each with its unblocking trigger

| Deferred | Build it when |
|---|---|
| Iceberg / any table format | a second concurrent writer, or a real need for row-level `MERGE` (§17) |
| Local transcription (`faster-whisper`) | the network dependency becomes unacceptable, or Vietnamese quality is the binding constraint (§17) |
| Multimodal / CLIP embeddings | an **eval shows** caption retrieval losing — not a suspicion (§12.4) |
| Perceptual hashing (`imagehash`) | near-duplicate catalog detection becomes a requirement (§17) |
| A queue behind `POST /assets` | extraction starts exceeding the caller's timeout (§17) |
| CDC / streaming | a consumer's value depends on sub-minute freshness (§17) |
| Quarantine reprocessing UI | someone actually needs to reprocess (§10) |
| The four detectors (§13) | there is an on-call rotation to page |
| `contracts/jsonschema/` export | the .NET backend actually connects to the database |
| OpenLineage | lineage is needed across teams and tools (§17) |

---

## 2. Non-negotiable rules

Eight rules. Each has the command that catches a violation, because a rule nothing checks is a wish.

| # | Rule | Caught by |
|---|---|---|
| 1 | `domain/` imports no framework, driver or SDK (§2) | `tests/unit/test_architecture_rules.py::TestDomainPurity` |
| 2 | Every `application/pipelines/` function is callable with no `dagster` and no `fastapi` import (§2) | `TestPipelinesAreFrameworkFree` |
| 3 | Only `orchestration/resources.py` may import from `infrastructure.` (§18) | `TestCompositionRoot` |
| 4 | No `print()` anywhere outside tests (§13) | `TestNoPrint` |
| 5 | Bronze is append-only; media blobs are never mutated (§3) | code review + `TestBronzeImmutability` |
| 6 | No bare `except Exception` that swallows and continues (§8 rule 6) | `TestNoBroadExcept` (AST scan) |
| 7 | No transcript, caption or record payload in a log (§13) | `test_extract_pipeline.py::TestLogging.test_transcript_text_never_appears_in_log_output` |
| 8 | Every derivation is keyed on `content_hash + extractor_version` (§7.6) | `TestCacheHit.test_second_run_makes_zero_model_calls` |

### Import prohibitions, per layer

| Layer | Must NOT import |
|---|---|
| `domain/` | `dlt` `dagster` `dbt` `duckdb` `psycopg` `sqlalchemy` `s3fs` `fsspec` `docling` `fastembed` `pymupdf` `polars` `pandas` `fastapi` `httpx` `pandera` `google.genai` |
| `application/` | `dagster` `fastapi` `psycopg` `dlt` `fsspec` `google.genai` — and anything under `infrastructure.` |
| `interface/` | anything under `infrastructure.` (adapters arrive on `app.state`) |
| `orchestration/resources.py` | *nothing* — the only file allowed to name concrete classes |
| everything | `print()` |

**The Arrow exception (§2):** `domain/entities/record_batch.py` may import `pyarrow`, and only that file.

---

## 3. Repository conventions

Mirrors `agent/` so an engineer who has read one layer can navigate the other.

| Convention | Rule |
|---|---|
| Packages | **No `__init__.py` anywhere.** Implicit namespace packages, resolved by `pythonpath = .` |
| Working directory | always `data/`. Imports are absolute from there: `from domain.entities.chunk import Chunk` |
| Module header | every module starts `from __future__ import annotations` |
| Docstrings | unaccented Vietnamese, matching `agent/`. Explain *why*, never *what* |
| Settings | read only via `from config.settings import settings`. **Never call `Settings()` outside `config/settings.py`** |
| Errors | `RetryableError` / `NonRetryableError` from `domain/policies/retry_policy.py`. Adapters translate vendor errors; nothing else raises them |
| Retryable HTTP statuses | `{408, 429, 500, 502, 503, 504}` — the same set as `agent/infrastructure/llm/gemini_provider.py` |
| Logging | `logger = get_logger(__name__)` at module level; `log_event(logger, "info", "event_name", **fields)` |
| Timestamps | `datetime.now(UTC)` only. **Never `datetime.utcnow()`** — it is naive, deprecated, and a naive value into `timestamptz` is a wrong-by-hours bug that surfaces on a demo |
| Immutability | domain entities are `@dataclass(frozen=True, slots=True)` |
| Tests | bare `Test*` classes, `async def` methods, **no decorators, no conftest, no mock library**. Inject fakes through constructors |

### `pytest.ini`

```ini
[pytest]
pythonpath = .
asyncio_mode = auto
markers =
    integration: can ket noi that -- Postgres, MinIO, ffmpeg, API key
    e2e: can docker compose chay day du
```

---

## 4. Environment

### `data/requirements.txt`

Versions from [tech-stack-evaluation.md](tech-stack-evaluation.md) §14. **The media and serving packages there are unverified — check each against PyPI before pinning.**

```
# core
pydantic>=2.13
pydantic-settings>=2.15
pyarrow>=25.0

# ingestion + compute
dlt[duckdb,postgres,filesystem,s3,parquet]>=1.30
polars>=1.43
duckdb>=1.5
pandera[polars]>=0.32

# storage
s3fs>=2026.7
psycopg[binary]>=3.3
pgvector>=0.5

# media + models
imageio-ffmpeg>=0.5
google-genai>=1.0
fastembed>=0.8

# serving
fastapi>=0.115
uvicorn[standard]>=0.32

# orchestration + modelling
dagster>=1.13
dagster-webserver>=1.13
dbt-core>=1.12
dbt-duckdb>=1.11

# eval
scikit-learn>=1.9

# dev
pytest>=9.0
pytest-asyncio>=0.24
httpx>=0.27
ruff>=0.16
```

No `structlog` — see §16.22.

### `data/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model. A 200 MB download on first use at the venue
# is a self-inflicted outage.
RUN python -c "from fastembed import TextEmbedding; \
    TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .
EXPOSE 8002
CMD ["uvicorn", "interface.api.app:app", "--host", "0.0.0.0", "--port", "8002"]
```

No `apt-get`. `imageio-ffmpeg` ships its own binary (tech-stack §15).

### `infrastructure/docker-compose.yml` — currently 0 bytes

Add three services. **Nothing integrates until this file exists.**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: bi
      POSTGRES_PASSWORD: bi
      POSTGRES_DB: bi
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ../data/sql/001_init.sql:/docker-entrypoint-initdb.d/001_init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bi"]
      interval: 5s
      retries: 10

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      retries: 10

  data:
    build: ../data
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: postgresql://bi:bi@postgres:5432/bi
      OBJECT_STORE_ENDPOINT_URL: http://minio:9000
      OBJECT_STORE_ACCESS_KEY: minioadmin
      OBJECT_STORE_SECRET_KEY: minioadmin
      OBJECT_STORE_ASSET_ROOT: /data/uploads
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    volumes:
      # The .NET backend writes uploads here. Pass paths, never bytes (§4).
      - ../backend/wwwroot/uploads:/data/uploads:ro
    depends_on:
      postgres: { condition: service_healthy }
      minio:    { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 10s
      retries: 5

volumes:
  pgdata:
  miniodata:
```

### `data/.env.example`

Every variable from §5, secrets blank, one comment block per group. Follow `agent/.env.example`'s layout — but **put comments on their own line**, never trailing a value: `pydantic-settings` does not reliably strip a trailing `# comment` from an unquoted value.

---

## 5. Settings

`data/config/settings.py`. Structure mirrors `agent/config/settings.py` exactly: one `_BaseAppSettings(BaseSettings)` declares `env_file` **once** as an absolute path; children declare only `env_prefix`; nesting uses `Field(default_factory=...)`; a module-bottom singleton.

```python
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class _BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )
```

**Enums** (all `str, Enum`): `Environment{DEVELOPMENT,STAGING,PRODUCTION}` · `LogLevel{DEBUG,INFO,WARNING,ERROR}` · `TranscriberProvider{GEMINI,MOCK}` · `CaptionerProvider{GEMINI,BYTEPLUS,MOCK}` · `EmbedderProvider{FASTEMBED,API,MOCK}` · `ParserProvider{DOCLING,PYMUPDF}` · `RetrievalMode{HYBRID,DENSE,LEXICAL}`.

| Class | `env_prefix` | Field | Type | Default |
|---|---|---|---|---|
| `ObjectStoreSettings` | `OBJECT_STORE_` | `url` | `str` | `"s3://bi-data-dev"` |
| | | `endpoint_url` | `str \| None` | `"http://localhost:9000"` |
| | | `access_key` | `SecretStr \| None` | `None` |
| | | `secret_key` | `SecretStr \| None` | `None` |
| | | `region` | `str` | `"us-east-1"` |
| | | `asset_root` | `str` | `"/data/uploads"` |
| | | `local_cache_dir` | `str` | `"/tmp/bi-data"` |
| | | `compression` | `str` | `"zstd"` |
| `DatabaseSettings` | `DATABASE_` | `url` | `str` | `"postgresql://bi:bi@localhost:5432/bi"` |
| | | `pool_size` | `int` ge=1 le=50 | `5` |
| | | `statement_timeout_ms` | `int` gt=0 | `30000` |
| | | `apply_schema_on_startup` | `bool` | `True` |
| `MediaSettings` | `MEDIA_` | `frame_count` | `int` ge=1 le=32 | `8` |
| | | `frame_interval_seconds` | `float` gt=0 | `2.0` |
| | | `frame_max_dimension` | `int` ge=128 le=2048 | `512` |
| | | `frame_jpeg_quality` | `int` ge=1 le=31 | `3` |
| | | `audio_sample_rate` | `int` | `16000` |
| | | `audio_channels` | `int` | `1` |
| | | `max_audio_seconds` | `int` gt=0 | `600` |
| | | `max_asset_size_bytes` | `int` | `524_288_000` |
| | | `max_inline_request_bytes` | `int` | `15_000_000` |
| | | `ffmpeg_timeout_seconds` | `float` | `120.0` |
| | | `transcribe_language` | `str \| None` | `None` |
| | | `caption_instruction_file` | `str` | `"prompts/caption_instruction.txt"` |
| | | `caption_instruction` | `str` | loaded from the file by a `model_validator`; an env value wins |
| | | `extractor_version_override` | `str \| None` | `None` |
| | | `extractor_version` | `str` **property** | derived — see below |
| `GeminiSettings` | `GEMINI_` | `api_key` | `SecretStr \| None` | `None` |
| | | `timeout_seconds` | `float` gt=0 | `120.0` |
| `TranscriberSettings` | `TRANSCRIBER_` | `provider` | `TranscriberProvider` | `GEMINI` |
| | | `model` | `str` | `"gemini-3.6-flash"` |
| `CaptionerSettings` | `CAPTIONER_` | `provider` | `CaptionerProvider` | `GEMINI` |
| | | `model` | `str` | `"gemini-3.6-flash"` |
| | | `temperature` | `float` ge=0 le=2 | `0.0` |
| | | `max_output_tokens` | `int` gt=0 | `4096` |
| | | `thinking_level` | `str` | `"low"` |
| | | `byteplus_base_url` | `str \| None` | `None` |
| | | `byteplus_api_key` | `SecretStr \| None` | `None` |
| `EmbedderSettings` | `EMBEDDER_` | `provider` | `EmbedderProvider` | `FASTEMBED` |
| | | `model` | `str` | `"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"` |
| | | `dimensions` | `int` | `384` — **must equal the DDL's `vector(384)`** |
| | | `batch_size` | `int` ge=1 | `32` |
| | | `cache_dir` | `str` | `"/opt/fastembed"` |
| `ChunkSettings` | `CHUNK_` | `max_tokens` | `int` gt=0 | `512` |
| | | `overlap_tokens` | `int` ge=0 | `64` |
| | | `min_chars` | `int` ge=1 | `20` |
| `RetrievalSettings` | `RETRIEVAL_` | `mode` | `RetrievalMode` | `HYBRID` |
| | | `rrf_k` | `int` ge=1 | `60` (§12.1) |
| | | `leg_top_k` | `int` ge=1 le=200 | `20` |
| | | `trgm_similarity_threshold` | `float` ge=0 le=1 | `0.2` |
| `QualitySettings` | `QUALITY_` | `max_rejected_ratio` | `float` ge=0 le=1 | `0.05` |
| | | `block_on_schema_violation` | `bool` | `True` |
| | | `min_rows_expected` | `int` ge=0 | `1` |
| | | `freshness_hours` | `int` gt=0 | `24` |
| `ApiSettings` | `API_` | `host` | `str` | `"0.0.0.0"` |
| | | `port` | `int` | `8002` |
| | | `default_top_k` | `int` ge=1 | `5` |
| | | `max_top_k` | `int` ge=1 le=200 | `50` |
| | | `cors_origins` | `list[str]` | `["*"]` |
| `ObservabilitySettings` | `OBSERVABILITY_` | `log_level` | `LogLevel` | `INFO` |
| | | `log_payloads` | `bool` | `False` |
| | | `tracing_enabled` | `bool` | `False` |
| `Settings` | *(none)* | `app_name` | `str` | `"beyond-intelligence-data"` |
| | | `environment` | `Environment` | `DEVELOPMENT` |
| | | the eleven above | nested | `Field(default_factory=...)` each |

**Methods.** `GeminiSettings.require_api_key() -> SecretStr` raises `ValueError` naming `GEMINI_API_KEY` when unset, mirroring `LLMSettings.require_api_key`. `Settings.is_production() -> bool`.

### `MediaSettings.extractor_version` is derived, not typed

```python
@property
def extractor_version(self) -> str:
    if self.extractor_version_override:
        return self.extractor_version_override
    material = "|".join([
        self.caption_instruction,
        str(self.frame_count),
        str(self.frame_interval_seconds),
        str(self.frame_max_dimension),
        self._transcriber_model,   # injected by Settings at composition
        self._captioner_model,
    ])
    return "ext-" + hashlib.sha256(material.encode()).hexdigest()[:12]
```

§7.6 requires the version to cover the prompt, the sampling parameters and the model ids. A hand-typed string is bumped by a person who is tired, and forgetting produces silently mixed artifacts — the exact failure §7.6 exists to prevent. Deriving it costs six lines. The override exists for deliberately reusing a cache across a cosmetic prompt edit.

---

## 6. Postgres schema

`data/sql/001_init.sql`. Every statement idempotent. Applied two ways: mounted into the Postgres container's `/docker-entrypoint-initdb.d/`, and by `apply_schema()` from the FastAPI lifespan when `DATABASE_APPLY_SCHEMA_ON_STARTUP=true`.

`index` is quoted everywhere — it is keyword-shaped and quoting costs nothing.

```sql
-- ========================================================= extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- unaccent() is STABLE, not IMMUTABLE, so it cannot appear in a generated
-- column or an index expression. This wrapper is the standard workaround
-- and it is load-bearing for both lexical legs (§12.2).
CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT public.unaccent('public.unaccent', $1) $$;

-- ========================================================= schemas
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS "index";
CREATE SCHEMA IF NOT EXISTS asset;
CREATE SCHEMA IF NOT EXISTS api;
CREATE SCHEMA IF NOT EXISTS ops;

-- ========================================================= ops (§8, §10, §13)
CREATE TABLE IF NOT EXISTS ops.ingestion_watermark (
    dataset       text PRIMARY KEY,
    cursor_column text NOT NULL,
    cursor_value  text NOT NULL,
    cursor_type   text NOT NULL CHECK (cursor_type IN ('timestamp','integer','string')),
    run_id        text NOT NULL,
    committed_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.run_log (
    run_id           text NOT NULL,
    asset_key        text NOT NULL,            -- 'silver/asset_artifact' (§15)
    pipeline         text NOT NULL CHECK (pipeline IN
                     ('ingest','normalize','extract','model','index','evaluate')),
    partition_key    text,
    dataset          text,
    source_system    text,
    status           text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    rows_in          bigint NOT NULL DEFAULT 0,
    rows_out         bigint NOT NULL DEFAULT 0,
    rows_rejected    bigint NOT NULL DEFAULT 0,
    bytes_written    bigint NOT NULL DEFAULT 0,
    duration_ms      integer,
    engine           text,
    contract_version text,
    watermark_from   text,
    watermark_to     text,
    error_code       text,
    error_message    text,
    started_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz,
    PRIMARY KEY (run_id, asset_key)
);
CREATE INDEX IF NOT EXISTS run_log_asset_started_idx
    ON ops.run_log (asset_key, started_at DESC);

CREATE TABLE IF NOT EXISTS ops.quality_violations (
    violation_id     bigserial PRIMARY KEY,
    run_id           text NOT NULL,
    dataset          text NOT NULL,
    partition_key    text,
    contract_version text NOT NULL,
    check_name       text NOT NULL,
    column_name      text,
    violation_code   text NOT NULL,     -- see the vocabulary in §16.18
    severity         text NOT NULL DEFAULT 'error'
                     CHECK (severity IN ('warning','error')),
    decision         text NOT NULL CHECK (decision IN
                     ('PUBLISH','PUBLISH_WITH_WARNING','QUARANTINE_AND_PUBLISH','BLOCK')),
    failure_count    bigint NOT NULL DEFAULT 1,
    quarantine_path  text,
    detail           text,              -- NEVER a row payload (§13)
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS quality_violations_dataset_idx
    ON ops.quality_violations (dataset, created_at DESC);

-- §9: "never silently drop an unknown column"
CREATE TABLE IF NOT EXISTS ops.schema_drift (
    drift_id    bigserial PRIMARY KEY,
    run_id      text NOT NULL,
    dataset     text NOT NULL,
    change_type text NOT NULL CHECK (change_type IN
                ('column_added','column_removed','type_changed')),
    column_name text NOT NULL,
    from_type   text,
    to_type     text,
    detected_at timestamptz NOT NULL DEFAULT now()
);

-- ========================================================= asset (§7.6, §11)
CREATE TABLE IF NOT EXISTS asset.asset (
    asset_id       text PRIMARY KEY,             -- VID-20260821-a1b2c3  (§7)
    kind           text NOT NULL CHECK (kind IN ('video','image','audio','document')),
    source_uri     text NOT NULL,
    content_hash   char(64) NOT NULL UNIQUE,     -- lowercase hex sha256
    media_type     text NOT NULL,
    size_bytes     bigint NOT NULL CHECK (size_bytes > 0),
    classification text NOT NULL DEFAULT 'confidential'
                   CHECK (classification IN ('public','internal','confidential','pii')),
    external_refs  text[] NOT NULL DEFAULT '{}', -- backend analysisId values (§16.1)
    ingested_date  date NOT NULL,
    ingested_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS asset_ingested_date_idx ON asset.asset (ingested_date DESC);

-- THE cache. §7.6 step 2. The load-bearing table of this whole design.
CREATE TABLE IF NOT EXISTS asset.extract_cache (
    content_hash         char(64) NOT NULL,
    extractor_version    text NOT NULL,
    asset_id             text NOT NULL REFERENCES asset.asset(asset_id) ON DELETE CASCADE,
    silver_path          text NOT NULL,
    frames_prefix        text NOT NULL,
    frame_count          integer NOT NULL CHECK (frame_count >= 0),
    duration_seconds     numeric(10,3) NOT NULL DEFAULT 0,
    has_transcript       boolean NOT NULL DEFAULT false,
    transcriber_model_id text,
    captioner_model_id   text,
    signals              jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_hash, extractor_version)
);
CREATE INDEX IF NOT EXISTS extract_cache_asset_idx ON asset.extract_cache (asset_id);

CREATE TABLE IF NOT EXISTS asset.transcript (
    asset_id          text NOT NULL,
    extractor_version text NOT NULL,
    language          text,
    text              text NOT NULL,
    char_count        integer NOT NULL,
    model_id          text NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, extractor_version),
    FOREIGN KEY (asset_id) REFERENCES asset.asset(asset_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asset.frame_annotation (
    asset_id          text NOT NULL,
    extractor_version text NOT NULL,
    ordinal           integer NOT NULL CHECK (ordinal >= 0),
    t_seconds         numeric(10,3) NOT NULL,
    frame_uri         text NOT NULL,
    caption           text NOT NULL,
    ocr_text          text NOT NULL DEFAULT '',
    signals           jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, extractor_version, ordinal),
    FOREIGN KEY (asset_id) REFERENCES asset.asset(asset_id) ON DELETE CASCADE
);

-- ========================================================= index (§7.4, §12)
CREATE TABLE IF NOT EXISTS "index".chunk (
    chunk_id       text PRIMARY KEY,      -- VID-20260821-a1b2c3:frame_caption:03
    document_id    text NOT NULL,
    source_type    text NOT NULL CHECK (source_type IN
                   ('transcript','frame_caption','document','record')),
    chunk_index    integer NOT NULL CHECK (chunk_index >= 0),
    content        text NOT NULL CHECK (length(content) > 0),
    content_hash   char(64) NOT NULL,
    token_count    integer,
    classification text NOT NULL DEFAULT 'internal'
                   CHECK (classification IN ('public','internal','confidential','pii')),
    source_uri     text,
    metadata       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now(),
    content_tsv    tsvector GENERATED ALWAYS AS
                   (to_tsvector('simple', public.immutable_unaccent(content))) STORED,
    UNIQUE (document_id, chunk_index, source_type)
);
CREATE INDEX IF NOT EXISTS chunk_document_idx ON "index".chunk (document_id);
CREATE INDEX IF NOT EXISTS chunk_tsv_idx      ON "index".chunk USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS chunk_trgm_idx     ON "index".chunk
    USING gin (public.immutable_unaccent(content) gin_trgm_ops);

-- 384 is pinned to EmbedderSettings.model. Changing the model is a new index
-- generation and a rebuild (§7.4), never an ALTER.
CREATE TABLE IF NOT EXISTS "index".embedding (
    chunk_id          text NOT NULL REFERENCES "index".chunk(chunk_id) ON DELETE CASCADE,
    embedder_model_id text NOT NULL,
    dimensions        integer NOT NULL CHECK (dimensions = 384),
    embedding         vector(384) NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, embedder_model_id)
);
CREATE INDEX IF NOT EXISTS embedding_hnsw_idx ON "index".embedding
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS embedding_model_idx ON "index".embedding (embedder_model_id);

-- ========================================================= gold (§7.3, §15)
CREATE TABLE IF NOT EXISTS gold.dim_asset (
    asset_id              text PRIMARY KEY,
    kind                  text NOT NULL,
    duration_seconds      numeric(10,3) NOT NULL DEFAULT 0,
    frame_count           integer NOT NULL DEFAULT 0,
    has_transcript        boolean NOT NULL DEFAULT false,
    transcript_char_count integer NOT NULL DEFAULT 0,
    language              text,
    classification        text NOT NULL DEFAULT 'confidential',
    extractor_version     text NOT NULL,
    ingested_date         date NOT NULL,
    updated_at            timestamptz NOT NULL DEFAULT now()
);

-- Grain: one row per (asset, signal, frame). EAV because the signal set is
-- prompt-driven and changes with the problem statement; a wide table would
-- need a migration per problem. Grain stated per §7.3.
-- frame_ordinal = -1 means an asset-level rollup. NOT NULL with a sentinel
-- default because a PRIMARY KEY cannot contain an expression.
CREATE TABLE IF NOT EXISTS gold.fct_asset_signal (
    asset_id          text NOT NULL REFERENCES gold.dim_asset(asset_id) ON DELETE CASCADE,
    signal_name       text NOT NULL,
    frame_ordinal     integer NOT NULL DEFAULT -1,
    signal_value_num  numeric,
    signal_value_text text,
    signal_value_bool boolean,
    extractor_version text NOT NULL,
    computed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, signal_name, frame_ordinal)
);

-- ========================================================= api (§11.2) — THE CONTRACT
CREATE OR REPLACE VIEW api.v1_asset_overview AS
SELECT asset_id, kind, duration_seconds, frame_count, has_transcript,
       transcript_char_count, language, ingested_date, updated_at
FROM gold.dim_asset;

CREATE OR REPLACE VIEW api.v1_asset_signal AS
SELECT asset_id, signal_name, frame_ordinal,
       signal_value_num, signal_value_text, signal_value_bool, computed_at
FROM gold.fct_asset_signal;

-- ========================================================= roles (§14)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='backend_reader') THEN
     CREATE ROLE backend_reader NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='data_writer') THEN
     CREATE ROLE data_writer NOLOGIN;
  END IF;
END $$;

GRANT USAGE ON SCHEMA api TO backend_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO backend_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT SELECT ON TABLES TO backend_reader;

GRANT USAGE, CREATE ON SCHEMA gold, "index", asset, ops TO data_writer;
GRANT ALL ON ALL TABLES IN SCHEMA gold, "index", asset, ops TO data_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold, "index", asset, ops
    GRANT ALL ON TABLES TO data_writer;
```

`backend_reader` having `SELECT` on `api` **only** is what makes §11.2's boundary real rather than advisory. Stage 12's gate tests the denial, not just the grant.

---

## 7. Object storage layout and asset ids

### Path templates (§15)

```
bronze records   {bucket}/bronze/{source_system}/{dataset}/ingested_date={d}/part-{run_id}-{n}.parquet
bronze assets    {bucket}/bronze/assets/{kind}/ingested_date={d}/{asset_id}.{ext}
silver records   {bucket}/silver/{entity}/event_date={d}/part-{run_id}-{n}.parquet
silver artifacts {bucket}/silver/asset_artifact/event_date={d}/part-{asset_id}.parquet
silver frames    {bucket}/silver/frames/{asset_id}/{ordinal:02d}.jpg
quarantine       {bucket}/quarantine/{entity}/event_date={d}/part-{run_id}-{n}.parquet
```

Worked example:

```
s3://bi-data-dev/bronze/assets/video/ingested_date=2026-08-21/VID-20260821-a1b2c3.mp4
s3://bi-data-dev/silver/asset_artifact/event_date=2026-08-21/part-VID-20260821-a1b2c3.parquet
s3://bi-data-dev/silver/frames/VID-20260821-a1b2c3/03.jpg
```

`layer ∈ {bronze, silver, quarantine}`. **Never create a `gold/` prefix** — Gold lives in Postgres, and an empty prefix that looks like a layer is a trap for the next reader.

### Asset id derivation

Shape `{PREFIX}-{YYYYMMDD}-{discriminator}` where `PREFIX ∈ {VID, IMG, AUD, DOC}` and the discriminator is 6 hex characters.

```
caller supplied an id      ->  reuse its entropy
  "ANL-20260821103000-a1b2c3" + kind=video  ->  "VID-20260821-a1b2c3"
no caller id               ->  sha256(bytes)[:6]
  ->  "VID-20260821-9f3c01"
```

Deterministic in both cases: a retry produces the same id, and no per-day counter is needed. The caller's original id is appended to `asset.asset.external_refs` so the backend can be answered in its own vocabulary. See §16.1.

### Chunk ids

```
{asset_id}:transcript:{NN}        VID-20260821-a1b2c3:transcript:00
{asset_id}:frame_caption:{NN}     VID-20260821-a1b2c3:frame_caption:03
```

`NN` is zero-padded to two digits. This string appears in the API response, the eval dataset and the logs, so it must be stable across a re-index.

---

## 8. File manifest

Grouped by build stage (§15). Every entry lists what it must NOT import; the global table in §2 applies on top.

### 8.1 Stage 0 — skeleton

| File | Purpose | Public API |
|---|---|---|
| `pytest.ini` | §3 | — |
| `requirements.txt` · `.env.example` · `Dockerfile` | §4 | — |
| `config/settings.py` | §5; module-bottom `settings = Settings()` | the classes of §5 |
| `observability/logging.py` | **Port `agent/observability/logging.py` verbatim** — stdlib `logging` + a `_JsonFormatter`, JSON one line to stdout | `get_logger(name: str) -> Logger` · `log_event(logger, level: str, event: str, **fields) -> None` · `log_duration(logger, event: str, **fields)` context manager |
| `observability/tracing.py` | interface only, no-op body (§13) | `start_span(name: str, **attrs)` context manager |
| `prompts/caption_instruction.txt` | the default captioner prompt | — |

### 8.2 Stage 1 — domain (pure, no I/O)

**Must NOT import:** everything in §2's `domain/` row.

| File | Public API |
|---|---|
| `domain/value_objects/content_hash.py` | `ContentHash(value: str)` — `__post_init__` rejects anything but 64 lowercase hex chars · `@classmethod of_bytes(cls, data: bytes) -> ContentHash` · `__str__` |
| `domain/value_objects/asset_id.py` | `MediaKind(str, Enum){VIDEO,IMAGE,AUDIO,DOCUMENT}` · `prefix_for(kind: MediaKind) -> str` · `build_asset_id(kind, ingested_date: date, discriminator: str) -> str` · `derive_discriminator(external_id: str \| None, content_hash: ContentHash) -> str` |
| `domain/value_objects/partition_key.py` | `PartitionKey(column: str, value: str)` · `@classmethod daily(cls, column: str, d: date)` · `as_path_segment() -> str` → `"event_date=2026-08-21"` |
| `domain/value_objects/time_window.py` | `TimeWindow(start: datetime, end: datetime)` · `@classmethod day(cls, d: date)` |
| `domain/value_objects/watermark.py` | `Watermark(column: str, value: str, kind: Literal["timestamp","integer","string"])` |
| `domain/value_objects/vector.py` | `Vector(values: tuple[float, ...], model_id: str)` · `@property dimensions -> int` |
| `domain/value_objects/classification.py` | `Classification(str, Enum){PUBLIC,INTERNAL,CONFIDENTIAL,PII}` |
| `domain/entities/media_asset.py` | `MediaAsset(asset_id, kind, source_uri, content_hash, media_type, size_bytes, classification=CONFIDENTIAL, external_refs=(), ingested_date)` · `FrameRef(ordinal: int, t_seconds: float, path: str)` · `Transcript(text, language, model_id)` + `@property char_count` · `FrameAnnotation(ordinal, t_seconds, caption, ocr_text="", frame_uri="", signals=())` · `AssetArtifacts(asset, duration_seconds, transcript, frames: tuple[FrameAnnotation,...], signals: tuple[Signal,...], extractor_version, cached=False)` · `Signal(name: str, value: str, frame_ordinal: int = -1)` |
| `domain/entities/chunk.py` | `Chunk(chunk_id, document_id, source_type, chunk_index, content, content_hash, metadata)` · `EmbeddedChunk(chunk: Chunk, vector: Vector)` · `RetrievedChunk(content, source, score, metadata)` — four fields, deliberately identical to the agent's `RetrievedDocument` (§12.3, §16.12) |
| `domain/entities/record_batch.py` | `RecordBatchEnvelope(batch: pa.RecordBatch, dataset, source_system, run_id, ingested_at)` — **the only file that may import `pyarrow`** |
| `domain/entities/document.py` | `DocumentBlob(path, media_type, size_bytes, content_hash)` · `ParsedDocument(document_id, title, sections: tuple[str,...], metadata)` |
| `domain/entities/data_contract.py` | `FieldSpec(type, nullable, unique, classification)` · `DataContract(name, version, owner, classification, fields: Mapping[str, FieldSpec], grain, freshness_hours, completeness)` |
| `domain/entities/quality_report.py` | `Violation(check_name, column_name, violation_code, failure_count, severity)` · `ValidationResult(dataset, contract_version, rows_total, rows_valid, violations)` + `@property rejected_ratio -> float` + `@property has_schema_violation -> bool` |
| `domain/entities/run_stats.py` | `RunStats(rows_in, rows_out, rows_rejected, bytes_written, duration_ms, engine, ...)` · `as_metadata() -> dict[str, object]` — **named `as_metadata`, not `as_dagster_metadata`**; domain must not know Dagster |
| `domain/ports/*.py` | the ports of §6 plus the three additions below. All `@runtime_checkable` `Protocol`s |
| `domain/policies/quality_policy.py` | `QualityDecision(str, Enum){PUBLISH,PUBLISH_WITH_WARNING,QUARANTINE_AND_PUBLISH,BLOCK}` · `ThresholdQualityPolicy(max_rejected_ratio, block_on_schema_violation)` + `decide(result: ValidationResult) -> QualityDecision` |
| `domain/policies/retry_policy.py` | **Byte-copy of `agent/domain/policies/retry_policy.py`** — `RetryableError`, `NonRetryableError`, `RetryPolicy(max_attempts, base_delay_seconds, max_delay_seconds, backoff_multiplier)` with `should_retry` / `next_delay_seconds`. Duplicated by design: pods must not share Python code |
| `domain/policies/fusion.py` | `reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], k: int = 60) -> dict[str, float]` — pure arithmetic, unit-testable without a database (§16.11) |
| `domain/policies/partition_policy.py` · `retention_policy.py` · `classification_policy.py` | `partition_for(ts) -> PartitionKey` · `retention_days(layer, classification) -> int` · `classify(field_name, declared) -> Classification` |

**Ports — the three added beyond §6**, each because the architecture is otherwise not composable (§16.2–§16.4):

```python
class ObjectStore(Protocol):          # §6's four methods PLUS:
    def read_bytes(self, path: str) -> bytes: ...
    def write_bytes(self, path: str, data: bytes) -> int: ...
    def exists(self, path: str) -> bool: ...
    def sha256(self, path: str) -> str: ...          # streamed, never loads the file
    def materialize_local(self, path: str) -> str: ...  # a real local path for subprocess

class AssetRepository(Protocol):
    def get_asset(self, asset_id: str) -> MediaAsset | None: ...
    def find_by_content_hash(self, h: ContentHash) -> MediaAsset | None: ...
    def register(self, asset: MediaAsset) -> MediaAsset: ...
    def get_artifacts(self, h: ContentHash, extractor_version: str) -> AssetArtifacts | None: ...
    def get_artifacts_by_id(self, asset_id: str) -> AssetArtifacts | None: ...
    def save_artifacts(self, artifacts: AssetArtifacts) -> None: ...
    def count_assets(self) -> int: ...

class ChunkStore(Protocol):
    def upsert(self, chunks: Sequence[EmbeddedChunk]) -> int: ...
    def delete_by_document(self, document_id: str) -> int: ...
    def count_by_document(self, document_id: str) -> int: ...
```

`Transcriber` and `FrameCaptioner` are as specified in §6 of the architecture. `Retriever.retrieve(query: str, top_k: int = 5, filters: Mapping[str, object] | None = None)` — both defaults present, so the adapter stays structurally compatible with the agent's protocol (§16.13).

### 8.3 Stage 2 — physical stores

| File | Public API | Must NOT import |
|---|---|---|
| `sql/001_init.sql` | §6 | — |
| `infrastructure/storage/postgres_schema.py` | `apply_schema(dsn: str, sql_path: str = "sql/001_init.sql") -> None` | `fastapi`, `dagster` |
| `infrastructure/storage/fsspec_object_store.py` | `FsspecObjectStore(base_url, *, endpoint_url, key, secret, local_cache_dir, compression="zstd")` implementing `ObjectStore`. `sha256` streams in 1 MiB blocks. `materialize_local` returns the path unchanged for local/`file://`, downloads into `local_cache_dir` for `s3://` | `psycopg`, `dagster`, `fastapi` |
| `infrastructure/storage/object_store_sink.py` | `ObjectStoreSink(store, layer, entity)` + `write(batch, partition) -> RunStats` — delete-prefix **then** write (§8 rule 2) | ditto |
| `infrastructure/storage/postgres_asset_repository.py` | `PostgresAssetRepository(dsn)` implementing `AssetRepository`. `save_artifacts` writes `extract_cache` + `transcript` + `frame_annotation` in **one transaction** | `fastapi`, `dagster` |
| `infrastructure/storage/postgres_chunk_store.py` | `PostgresChunkStore(dsn)` implementing `ChunkStore`. `upsert` is `INSERT … ON CONFLICT (chunk_id) DO UPDATE`, then the same on `(chunk_id, embedder_model_id)` for `"index".embedding` | ditto |
| `infrastructure/catalog/postgres_catalog.py` | `PostgresCatalog(dsn)` implementing `Catalog`, plus `log_run(...) -> None` and `record_violation(...) -> None` | ditto |

### 8.4 Stage 3 — `extract`, offline

| File | Public API |
|---|---|
| `infrastructure/asr/mock_transcriber.py` | `MockTranscriber` — `model_id = "mock-asr-v1"`, `call_count: int`, `async transcribe(audio_path, language=None) -> Transcript` deterministic on `sha256(audio_path)` |
| `infrastructure/vision/mock_captioner.py` | `MockCaptioner` — `model_id = "mock-vlm-v1"`, `call_count: int`, `async caption(frames, instruction) -> list[FrameAnnotation]`, one per frame, caption `f"mock caption for frame {ordinal}"` |
| `infrastructure/embedding/mock_embedder.py` | `MockEmbedder` — `model_id = "mock-embed-v1"`, `dimensions = 384`, `embed(texts) -> list[Vector]` derived from `sha256(text)`, L2-normalised |
| `contracts/pandera/asset_artifact.py` | `AssetArtifactSchema(pandera.polars.DataFrameModel)` — §13 · `CONTRACT_VERSION = "1.0.0"` |
| `infrastructure/validation/pandera_validator.py` | `PanderaValidator` + `validate(batch, contract) -> ValidationResult`. `lazy=True`. **Never raises on bad data** (§6) |
| `application/pipelines/ingest.py` | `register_asset(uri, kind, *, store, repository, asset_root, external_ref=None, run_id) -> MediaAsset` |
| `application/pipelines/extract.py` | `async extract_asset(asset, *, store, repository, transcriber, captioner, validator, catalog, quality_policy, config: MediaSettings, frame_extractor=extract_frames, audio_extractor=extract_audio, run_id) -> AssetArtifacts` · `async extract_partition(assets, **deps) -> RunStats` |
| `application/services/asset_service.py` | `async ingest_extract_index(uri, kind, *, deps, run_id) -> tuple[AssetArtifacts, int]` — the one function the route calls · `get_artifacts(asset_id, *, repository) -> AssetArtifacts \| None` |

`frame_extractor` and `audio_extractor` are **injected plain callables with module defaults**, not a port. This is how `extract` stays unit-testable with no ffmpeg binary while honouring §6's "no port for ffmpeg". Their types:

```python
FrameExtractorFn = Callable[..., list[FrameRef]]
AudioExtractorFn = Callable[..., tuple[str, float]]
```

### 8.5 Stage 4 — ffmpeg

| File | Public API | Must NOT import |
|---|---|---|
| `infrastructure/media/ffmpeg.py` | `extract_frames(video_path, out_dir, *, max_frames, interval_seconds, longest_side, jpeg_quality, timeout_seconds) -> list[FrameRef]` · `extract_audio(video_path, out_dir, *, sample_rate, channels, timeout_seconds) -> tuple[str, float]` · `probe_duration_from_wav(path) -> float` · `class MediaDecodeError(NonRetryableError)` | anything but `subprocess`, `wave`, `pathlib`, `imageio_ffmpeg`, and the domain entities |

The two commands, fixed:

```
frames:  {ffmpeg} -y -i {src} -vf fps=1/{interval},scale={longest_side}:-1:force_original_aspect_ratio=decrease
                  -frames:v {max_frames} -q:v {jpeg_quality} {out_dir}/%02d.jpg
audio:   {ffmpeg} -y -i {src} -vn -ac {channels} -ar {sample_rate} {out_dir}/audio.wav
```

`{ffmpeg}` is `imageio_ffmpeg.get_ffmpeg_exe()`. Duration comes from the WAV header via the stdlib `wave` module — `imageio-ffmpeg` ships no `ffprobe` (tech-stack §15). A non-zero exit or a timeout raises `MediaDecodeError` carrying the last 500 characters of stderr.

### 8.6 Stage 5 — hosted model adapters

| File | Public API |
|---|---|
| `infrastructure/asr/gemini_transcriber.py` | `GeminiTranscriber(config: TranscriberSettings, gemini: GeminiSettings, client: genai.Client \| None = None)` · `@property model_id` · `async transcribe(audio_path, language=None) -> Transcript` · `@staticmethod _translate_error(exc) -> Exception` |
| `infrastructure/vision/gemini_captioner.py` | `GeminiCaptioner(config: CaptionerSettings, gemini: GeminiSettings, client=None)` · `@property model_id` · `async caption(frames, instruction) -> list[FrameAnnotation]` · `_build_contents(frames, instruction)` · `_split_if_oversized(frames) -> list[list[FrameRef]]` · `@staticmethod _translate_error(exc)` |

Both take an optional injected `client` for the same reason `HttpJsonRetriever` takes an optional `httpx.AsyncClient` — it is how the unit tier stays offline with no mock library. Error translation copies `agent/infrastructure/llm/gemini_provider.py::_translate_error` exactly, including the status set. Request shapes are in §10.

### 8.7 Stage 6 — index and retrieval

| File | Public API |
|---|---|
| `infrastructure/embedding/fastembed_embedder.py` | `FastEmbedEmbedder(model_name, cache_dir, batch_size)` · `model_id`, `dimensions`, `embed(texts) -> list[Vector]` |
| `infrastructure/retrieval/pgvector_retriever.py` | `PgVectorRetriever(dsn, embedder, leg_top_k)` · `async retrieve(...)`. Score is `1 - (embedding <=> :q)` |
| `infrastructure/retrieval/lexical_retriever.py` | `LexicalRetriever(dsn, leg_top_k, similarity_threshold)` · `async retrieve(...)`. Ranks by `GREATEST` of `similarity(immutable_unaccent(content), immutable_unaccent(:q))` and a `content_tsv @@ plainto_tsquery('simple', …)` rank |
| `infrastructure/retrieval/hybrid_retriever.py` | `HybridRetriever(dense, lexical, k)` · `async retrieve(...)` — both legs via `asyncio.gather`, then `reciprocal_rank_fusion`, then normalise the fused score to `[0,1]` by the maximum (§16.20) |
| `application/pipelines/index.py` | `build_chunks_from_artifacts(a, *, config: ChunkSettings) -> list[Chunk]` · `index_chunks(chunks, *, embedder, chunk_store, batch_size) -> RunStats` · `index_asset_artifacts(a, *, embedder, chunk_store, config) -> RunStats` |
| `application/services/retrieval_service.py` | `async search(retriever, q, top_k, *, max_top_k) -> list[RetrievedChunk]` — clamps `top_k`. Deliberately thin; RRF is **not** here (§16.11) |

**Chunk text templates, fixed as module constants** (they appear in the API response, the eval dataset and the logs):

```python
FRAME_CHUNK_TEMPLATE     = "Frame at {t:.0f}s: {caption}"
FRAME_CHUNK_OCR_SUFFIX   = ", on-screen text '{ocr_text}'"   # appended when ocr_text != ""
```

### 8.8 Stage 7 / 9 — interface and orchestration

| File | Public API |
|---|---|
| `interface/api/schemas.py` | §11 |
| `interface/api/mappers.py` | `chunk_to_item(c: RetrievedChunk) -> QueryItem` · `artifacts_to_register_response(a, chunks: int) -> RegisterAssetResponse` · `artifacts_to_detail(a) -> AssetDetailResponse` |
| `interface/api/routes.py` | `router = APIRouter()` · private `async _run_query(state, q, top_k) -> QueryResponse` · five decorated handlers (§11) |
| `interface/api/app.py` | `create_app(config: Settings \| None = None) -> FastAPI` · an `asynccontextmanager` lifespan that calls `build_resources`, applies the schema, and stores the result on `app.state.resources` · module-bottom `app = create_app()` |
| `orchestration/resources.py` | `build_resources(config: Settings) -> Resources` plus private `_build_transcriber`, `_build_captioner`, `_build_embedder`, `_build_retriever`, `_build_store`, `_build_repository`, `_build_chunk_store`, `_build_catalog`, `_build_validator`, `_build_quality_policy`. Enum-equality chain, `raise ValueError` on an unknown provider — the same shape as `agent/bootstrap/container.py::_build_llm`. **The only file in `data/` that may import from `infrastructure.`** |
| `orchestration/definitions.py` | `defs = Definitions(assets=[...], resources={...}, schedules=[...], asset_checks=[...])` |
| `orchestration/assets/silver.py` | `@asset(key=["silver","asset_artifact"]) def silver_asset_artifact(context) -> MaterializeResult` — body is `asyncio.run(extract_partition(...))` and a `MaterializeResult(metadata=stats.as_metadata())`. Nothing else |
| `orchestration/assets/{bronze,gold,index,evaluation}.py` | same pattern, one call each |
| `orchestration/{partitions,schedules,asset_checks}.py` | `daily = DailyPartitionsDefinition(start_date="2026-08-01")` · `@asset_check(blocking=True)` for the schema-violation gate |

### 8.9 DO NOT CREATE YET

Each with its unblocking trigger. **An empty file is worse than a missing one.**

| Path | Create when |
|---|---|
| `infrastructure/sources/{file,excel,api,database,mock}_source.py` | stage 11 — the structured path |
| `application/pipelines/normalize.py` | stage 11 |
| `application/pipelines/model.py` · `application/services/publish_service.py` | stage 12 |
| `application/pipelines/evaluate.py` · `evaluation/{metrics,runners,reports}/` | stage 13 |
| `infrastructure/parsing/{docling,pymupdf}_parser.py` · `infrastructure/chunking/docling_chunker.py` | a document source actually arrives |
| `infrastructure/vision/byteplus_captioner.py` | the BytePlus experiment is attempted — and then with `httpx` against the OpenAI chat-completions shape, **not** by adding the `openai` package (§16.31) |
| `infrastructure/embedding/api_embedder.py` | fastembed quality becomes the constraint |
| `infrastructure/storage/{duckdb_engine,postgres_sink}.py` | stage 12 |
| `transformations/**` (dbt) | stage 12, and only after one raw SQL model exists to justify it |
| `contracts/jsonschema/**` · `application/services/contract_service.py` | the .NET backend connects to the database |

---

## 9. The `extract` pipeline

The one place in the layer where media is a special case. Everything else is ordinary text work.

### `extract_asset()` — exact step order

| # | Step | Writes | Ref |
|---|---|---|---|
| 1 | `local = store.materialize_local(asset.source_uri)`; `h = ContentHash(store.sha256(asset.source_uri))` — streamed, a 150 MB video is never in memory | — | §16.2 |
| 2 | `repository.register(asset)` if new; classification set to `confidential` **here** | `asset.asset` | §14 |
| 3 | **`cached = repository.get_artifacts(h, config.extractor_version)`** → on a hit, `log_event(..., cache_hit=True)` and `return replace(cached, cached=True)` | — | §7.6 step 2 |
| 4 | `frames = frame_extractor(local, tmp, max_frames=config.frame_count, interval_seconds=…, longest_side=…)`. For `kind=IMAGE`: a single `FrameRef(0, 0.0, local)` | tmp | §7.6 step 3 |
| 5 | if `kind != IMAGE`: `audio_path, duration = audio_extractor(local, tmp, …)`; else `(None, 0.0)` | tmp | §7.6 step 4 |
| 6 | `transcript = await transcriber.transcribe(audio_path, language=config.transcribe_language)` when `audio_path` is not `None` | — | §7.6 step 5 |
| 7 | `annotations = await captioner.caption(frames, instruction=config.caption_instruction)` — **one call** | — | §7.6 step 6 |
| 8 | upload each JPEG to `silver/frames/{asset_id}/{ordinal:02d}.jpg`; set `FrameAnnotation.frame_uri` | object store | §15 |
| 9 | build one Polars frame of `asset_artifact` rows; `result = validator.validate(...)`; `decision = quality_policy.decide(result)` | — | §10 |
| 10 | `BLOCK` → raise `AssetExtractionError("CONTRACT_BLOCKED")`. `QUARANTINE_AND_PUBLISH` → write failing rows to `quarantine/asset_artifact/event_date=…/part-{asset_id}.parquet`, `catalog.record_violation(...)`, publish the rest | quarantine | §10 |
| 11 | write `silver/asset_artifact/event_date={ingested_date}/part-{asset_id}.parquet` — **overwrite that one object; never `delete_prefix` on the date** | Silver | §16.5 |
| 12 | `repository.save_artifacts(artifacts)` — one transaction over `extract_cache` + `transcript` + `frame_annotation`. **Commits after the Silver write** | Postgres | §8 rule 4 |
| 13 | `catalog.log_run(...)` and `log_event(logger, "info", "asset_extracted", asset_id=, content_hash=, extractor_version=, cache_hit=False, transcriber_model_id=, captioner_model_id=, frame_count=, transcript_char_count=, duration_ms=)` | `ops.run_log` | §13 |

**Step 13 logs the transcript's character count, never its text** (§13). Same for captions.

### Error handling

| Failure | Raised | Quarantine row | HTTP |
|---|---|---|---|
| ffmpeg non-zero exit or timeout | `MediaDecodeError` (`NonRetryableError`) | `DECODE_FAILED`, stderr tail ≤500 chars | 422 `ASSET_DECODE_FAILED` |
| model 429 / 5xx | `RetryableError`; retried by `RetryPolicy` in `asset_service` | on exhaustion, `MODEL_UNAVAILABLE` | 503 `UPSTREAM_MODEL_ERROR` |
| model 400 / 403 | `NonRetryableError` | `MODEL_REJECTED` | 502 `UPSTREAM_MODEL_ERROR` |
| captioner returns unparseable JSON | `NonRetryableError("CAPTION_SCHEMA_INVALID")` | `CAPTION_SCHEMA_INVALID` | 502 `UPSTREAM_MODEL_ERROR` |
| audio present but transcript empty | **no raise** — `Violation("EMPTY_TRANSCRIPT", severity="warning")`, decision `PUBLISH_WITH_WARNING` | violation row only | 200, `has_transcript: false` |
| contract `BLOCK` | `AssetExtractionError` | full row | 422 `CONTRACT_BLOCKED` |

`extract_partition` catches **only** `AssetExtractionError` per asset and continues (§7.6 failure mode). No bare `except Exception` anywhere (§8 rule 6). A non-decodable asset still produces a one-row quarantine artifact — it has no rows otherwise, and the layer's rule is quarantine, not drop (§10).

---

## 10. The Gemini requests

Non-derivable SDK shape, and the project's highest-risk block. Verbatim.

### Captioner

```python
def _build_contents(self, frames, instruction):
    parts = [genai_types.Part.from_text(text=instruction)]
    for f in frames:
        parts.append(genai_types.Part.from_text(
            text=f"[frame {f.ordinal:02d} t={f.t_seconds:.1f}s]"))
        parts.append(genai_types.Part.from_bytes(
            data=Path(f.path).read_bytes(), mime_type="image/jpeg"))
    return [genai_types.Content(role="user", parts=parts)]

CAPTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "frames": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "ordinal":  {"type": "integer"},
                "caption":  {"type": "string"},
                "ocr_text": {"type": "string"},
                "signals":  {"type": "array", "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"},
                                   "value": {"type": "string"}},
                    "required": ["name", "value"]}}},
            "required": ["ordinal", "caption", "ocr_text"]}},
        "asset_signals": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
            "required": ["name", "value"]}}},
    "required": ["frames"]}

response = await self._client.aio.models.generate_content(
    model=self._config.model,
    contents=self._build_contents(frames, instruction),
    config=genai_types.GenerateContentConfig(
        temperature=self._config.temperature,
        max_output_tokens=self._config.max_output_tokens,
        response_mime_type="application/json",
        response_json_schema=CAPTION_RESPONSE_SCHEMA,
        thinking_config=genai_types.ThinkingConfig(
            thinking_level=self._config.thinking_level),
    ),
)
```

**Signals are name/value pairs, not a free-form object.** Structured-output schemas do not express open objects well, and the pair shape is exactly what `gold.fct_asset_signal` stores. One shape end to end.

**Oversize guard.** Sum the JPEG bytes before the call. Above `config.max_inline_request_bytes` (15 MB), split into two calls of `ceil(n/2)` frames and concatenate the annotations. `TestFallback.test_oversized_payload_splits_into_two_calls` proves it against a fake client, so the fallback is not discovered on stage.

### Transcriber

```python
contents = [genai_types.Content(role="user", parts=[
    genai_types.Part.from_text(text=TRANSCRIBE_INSTRUCTION),
    genai_types.Part.from_bytes(data=Path(audio_path).read_bytes(),
                                mime_type="audio/wav"),
])]
config = genai_types.GenerateContentConfig(
    temperature=0.0,
    response_mime_type="application/json",
    response_json_schema={
        "type": "object",
        "properties": {"language": {"type": "string"}, "text": {"type": "string"}},
        "required": ["text"]},
)
```

16 kHz mono WAV is ~32 kB/s, so a 15-second clip is ~480 kB — safely inline. Above `config.max_audio_seconds` (600), transcribe the first 600 seconds and record `Violation("TRANSCRIPT_TRUNCATED", severity="warning")`. Honest and bounded.

### Default caption instruction

`prompts/caption_instruction.txt`. This file is the **only** place problem-specific intelligence lives — retargeting the platform to a different problem statement is an edit here, not a code change. Changing it changes `extractor_version` automatically (§5).

Default signals requested: `has_face`, `text_overlay_ratio`, `primary_language`, `product_visible`. **Not `cut_count`** — see §16.14.

---

## 11. The HTTP interface

### DTOs — `interface/api/schemas.py`

```python
QueryRequest(q: str, top_k: int = 5)
QueryItem(id: str, text: str, score: float, metadata: dict[str, Any])
QueryResponse(items: list[QueryItem])

RegisterAssetRequest(uri: str, kind: str, asset_id: str | None = None)
ArtifactCounts(frames: int, duration_s: float, has_transcript: bool, chunks: int)
RegisterAssetResponse(asset_id: str, status: str, cached: bool, artifacts: ArtifactCounts)

FrameOut(t: float, caption: str, ocr_text: str)
AssetDetailResponse(asset_id: str, kind: str, duration_s: float,
                    transcript: str | None, frames: list[FrameOut],
                    signals: dict[str, Any])

HealthResponse(status: str, db: bool, assets: int)
ErrorBody(code: str, message: str, request_id: str)
ErrorResponse(error: ErrorBody)
```

`QueryItem`'s four field names are **fixed by the agent's existing mapper** and must not change: it reads `payload["items"][*]` taking `id` → `source`, `text` → `content`, `score` → `score`.

### Endpoints

| Method | Path | Calls | Success | Errors |
|---|---|---|---|---|
| `GET` | `/health` | `repository.count_assets()` | **always 200** | never — see §16.17 |
| `GET` | `/api/v1/data/query?q=&top_k=` | `_run_query` | 200 `QueryResponse` | 400 `INVALID_QUERY` |
| `POST` | `/api/v1/data/query` | `_run_query` | 200 `QueryResponse` | 400 `INVALID_QUERY` |
| `POST` | `/api/v1/assets` | `asset_service.ingest_extract_index` | 200 `RegisterAssetResponse` | 400 `INVALID_URI` · 413 `ASSET_TOO_LARGE` · 422 `ASSET_DECODE_FAILED` / `CONTRACT_BLOCKED` · 502/503 `UPSTREAM_MODEL_ERROR` |
| `GET` | `/api/v1/assets/{asset_id}` | `asset_service.get_artifacts` | 200 `AssetDetailResponse` | 404 `ASSET_NOT_FOUND` / `ASSET_NOT_EXTRACTED` |

### The dual-verb handler

```python
async def _run_query(state, q: str, top_k: int) -> QueryResponse: ...

@router.get("/api/v1/data/query", response_model=QueryResponse)
async def query_get(request: Request, q: str, top_k: int = 5): ...

@router.post("/api/v1/data/query", response_model=QueryResponse)
async def query_post(request: Request, body: QueryRequest): ...
```

One implementation, two three-line wrappers. §11.4 requires one handler; the acceptance gate is `diff` between the two responses being empty, which this satisfies without fighting the framework (§16.19).

### Error envelope

Mandated by [integration-architecture.md](../docs/architecture/integration-architecture.md) §6, so a global exception handler replaces FastAPI's `{"detail": …}`:

```json
{"error": {"code": "ASSET_DECODE_FAILED", "message": "...", "request_id": "..."}}
```

Fixed code vocabulary: `ASSET_NOT_FOUND` · `ASSET_NOT_EXTRACTED` · `ASSET_DECODE_FAILED` · `ASSET_UNSUPPORTED_KIND` · `ASSET_TOO_LARGE` · `CONTRACT_BLOCKED` · `UPSTREAM_MODEL_ERROR` · `INVALID_QUERY` · `INVALID_URI`.

### The `uri` is a trust boundary

```python
local = (Path(settings.object_store.asset_root) / uri.removeprefix("/uploads/")).resolve()
if not local.is_relative_to(Path(settings.object_store.asset_root).resolve()):
    raise ApiError("INVALID_URI", status=400)
```

Path traversal at a trust boundary is not something to simplify away (§16.16).

---

## 12. Contracts

`contracts/pandera/asset_artifact.py`, `CONTRACT_VERSION = "1.0.0"`. Uses `pandera.polars`, always `lazy=True` (§16.25).

| Column | Type | Nullable | Checks |
|---|---|---|---|
| `asset_id` | `str` | no | matches `^(VID\|IMG\|AUD\|DOC)-\d{8}-[0-9a-f]{6}$` |
| `extractor_version` | `str` | no | starts with `ext-` |
| `artifact_type` | `str` | no | in `{transcript, frame_annotation}` |
| `ordinal` | `int` | no | `>= 0` |
| `t_seconds` | `float` | no | `>= 0` |
| `text` | `str` | no | length `> 0` |
| `ocr_text` | `str` | no | — |
| `frame_uri` | `str` | yes | — |
| `language` | `str` | yes | — |
| `model_id` | `str` | no | — |
| `event_date` | `date` | no | — |
| `classification` | `str` | no | in the four values |

Grain: one row per `(asset_id, extractor_version, artifact_type, ordinal)`. Semantics: `text` is the transcript for `artifact_type=transcript`, and the caption for `frame_annotation`.

---

## 13. Test manifest

`tests/unit` must run with **no container, no API key and no network**. If it cannot, the seams are wrong.

### Unit

| File | Named methods |
|---|---|
| `tests/unit/test_architecture_rules.py` | `TestDomainPurity.test_domain_imports_no_framework_driver_or_sdk` · `TestPipelinesAreFrameworkFree.test_application_imports_no_dagster_or_fastapi` · `TestCompositionRoot.test_only_resources_py_imports_infrastructure` · `TestNoPrint.test_no_print_calls_outside_tests` · `TestNoBroadExcept.test_no_bare_except_exception` — all by AST scan over the tree |
| `tests/unit/domain/test_content_hash.py` | `TestOfBytes.test_known_vector` (empty → `e3b0c442…`) · `TestValidation.test_rejects_wrong_length` · `test_rejects_non_hex` |
| `tests/unit/domain/test_asset_id.py` | `TestFromBackendId.test_derives_vid_id_from_analysis_id` · `test_is_deterministic` · `TestFromContentHash.test_id_matches_naming_convention` |
| `tests/unit/domain/test_quality_policy.py` | `TestDecide.test_no_violations_publishes` · `test_under_threshold_quarantines_and_publishes` · `test_over_threshold_blocks` · `test_schema_violation_blocks_regardless_of_ratio` |
| `tests/unit/domain/test_fusion.py` | `TestReciprocalRankFusion.test_item_ranked_first_in_both_legs_wins` · `test_larger_k_flattens_ranking` · `test_empty_legs_return_empty` |
| **`tests/unit/application/test_extract_pipeline.py`** | `TestCacheMiss.test_calls_transcriber_once_and_captioner_once` · `test_writes_silver_and_cache_row` · `test_frames_uploaded_under_asset_prefix` · **`TestCacheHit.test_second_run_makes_zero_model_calls`** · `test_cache_hit_skips_frame_extraction` · `test_cache_hit_returns_cached_true` · `TestExtractorVersion.test_version_bump_forces_recompute` · `TestImage.test_image_yields_one_frame_and_no_transcript` · `TestFailure.test_decode_error_quarantines_and_raises` · `test_partition_run_continues_after_one_bad_asset` · `TestQuality.test_empty_transcript_with_audio_records_warning` · `TestLogging.test_transcript_text_never_appears_in_log_output` |
| `tests/unit/application/test_index_pipeline.py` | `TestChunkIds.test_frame_chunk_id_matches_naming_convention` · `test_transcript_chunk_id` · `TestChunkText.test_frame_chunk_uses_the_fixed_template` · `TestIdempotency.test_reindexing_produces_identical_chunk_ids` · `TestEmbedding.test_dimension_mismatch_raises` |
| `tests/unit/infrastructure/test_gemini_captioner.py` | `TestRequestShape.test_one_call_with_eight_image_parts` · `test_requests_json_response_schema` · `test_frame_marker_text_precedes_each_image` · `TestFallback.test_oversized_payload_splits_into_two_calls` · `TestErrors.test_429_raises_retryable` · `test_400_raises_non_retryable` · `TestParsing.test_maps_response_to_frame_annotations` · `test_unparseable_json_raises_non_retryable` |
| `tests/unit/infrastructure/test_gemini_transcriber.py` | `TestRequestShape.test_sends_wav_part_with_correct_mime_type` · `TestTruncation.test_long_audio_is_truncated_and_flagged` · `TestErrors.test_503_raises_retryable` |
| `tests/unit/infrastructure/test_mock_adapters.py` | `TestMockEmbedder.test_same_text_gives_same_vector` · `test_dimensions_match_declared` · `TestMockCaptioner.test_one_annotation_per_frame` |
| `tests/unit/interface/test_routes.py` | `TestQuery.test_get_and_post_return_identical_bodies` · `test_top_k_clamped_to_max` · `test_missing_q_returns_error_envelope` · `TestAssets.test_register_returns_asset_id_and_cached_flag` · `test_unknown_asset_returns_404_error_envelope` · `test_path_traversal_uri_rejected` · `TestHealth.test_returns_200_and_degraded_when_db_unreachable` |
| **`tests/unit/interface/test_agent_contract.py`** | `TestAgentContract.test_payload_maps_to_retrieved_document_fields` — build a real `QueryResponse` through `mappers.chunk_to_item`, run the agent's four-line mapper (replicated inline; pods do not share code) over `response.model_dump()`, assert all four fields populate. The offline half of stage 8 |
| `tests/unit/config/test_settings.py` | `TestExtractorVersion.test_changes_when_prompt_changes` · `test_changes_when_frame_count_changes` · `test_stable_when_log_level_changes` · `test_override_wins` |
| `tests/unit/orchestration/test_resources.py` | `TestProviderSelection.test_mock_providers_build_offline` · `test_unknown_provider_raises_valueerror` · `TestBothEdges.test_api_and_dagster_use_the_same_builder` |

### Integration — `@pytest.mark.integration`

| File | Proves |
|---|---|
| `test_postgres_schema.py` | `apply_schema` is idempotent (run twice); the three extensions exist; `immutable_unaccent` is usable in an index expression |
| `test_object_store.py` | write/read/list/`delete_prefix`/`sha256`/`materialize_local` against MinIO; `sha256` of a 10 MB file matches `hashlib` |
| `test_asset_repository.py` | cache round trip; `save_artifacts` is atomic; `find_by_content_hash` dedupes a re-upload |
| `test_chunk_store.py` | upsert twice → one row; a dimension mismatch is rejected by the CHECK |
| `test_pgvector_retriever.py` | cosine ordering correct; `EXPLAIN` shows the HNSW index used |
| `test_lexical_retriever.py` | **`test_matches_across_missing_diacritics`** — `"giam gia"` retrieves `"giảm giá"`. This is §12.2's entire claim |
| `test_hybrid_retriever.py` | the fused result contains an item only the lexical leg found and one only the dense leg found |
| `test_ffmpeg.py` | a committed 5-second MP4 → exactly `frame_count` JPEGs, longest side ≤512, and a WAV reporting 16000 Hz / 1 channel |
| `test_gemini_live.py` | the real 8-image request; skipped without `GEMINI_API_KEY` |

### E2E — `@pytest.mark.e2e`

`tests/e2e/test_media_slice.py`: `TestSlice.test_register_extract_index_query_roundtrip` · `test_second_register_reports_cached_true_with_lower_duration` · `test_query_returns_frame_caption_item_shape`. Must finish in under a few minutes (§16 of the architecture).

---

## 14. Fixtures

| Path | What |
|---|---|
| `tests/fixtures/sample_5s.mp4` | 5 seconds, H.264 + AAC, under 1 MB. Committed |
| `tests/fixtures/sample.jpg` | one image for the `kind=image` path |
| `tests/fixtures/orders.csv` | 10 rows, **one deliberately malformed**, for stage 11 |
| `evaluation/datasets/retrieval.jsonl` | ~15 hand-written `{query, expected_chunk_ids}` cases |

---

## 15. Build stages and acceptance gates

Ordered by dependency. **Each gate is one command. If it fails, the fault is in that stage's files and nowhere else.**

| Stage | Depends on | Builds | Gate |
|---|---|---|---|
| **0 Skeleton** | — | §8.1 | `python -c "from config.settings import settings; print(settings.media.extractor_version)"` prints `ext-…`; `pytest tests/unit/config` green |
| **1 Domain** | 0 | §8.2 | `pytest tests/unit/domain tests/unit/test_architecture_rules.py::TestDomainPurity` green. **Runs before any adapter exists** — that is the point |
| **2 Physical stores** | 1 | §8.3 + compose | `docker compose up -d postgres minio`, then `python -m infrastructure.storage.postgres_schema` **twice** with no error; `pytest -m integration tests/integration/test_{postgres_schema,object_store,asset_repository}.py` |
| **3 `extract`, offline** | 1, 2 | §8.4 | **`pytest tests/unit/application` green — no ffmpeg binary, no API key, no network.** Includes `TestCacheHit.test_second_run_makes_zero_model_calls` |
| **4 ffmpeg** | 3 | §8.5 + the MP4 fixture | `pytest -m integration tests/integration/test_ffmpeg.py` → 8 JPEGs and one 16 kHz mono WAV |
| **5 Hosted models** | 3 | §8.6 | `pytest tests/unit/infrastructure` green, **then** `pytest -m integration tests/integration/test_gemini_live.py` with a real key. **Nothing downstream starts until this passes** — it is the single biggest unknown in the project |
| **6 Index + retrieval** | 2, 3 | §8.7 | `pytest -m integration tests/integration/test_*retriever*.py`, specifically `test_matches_across_missing_diacritics` |
| **7 API** | 3, 6 | §8.8 interface | `uvicorn interface.api.app:app --port 8002`, then `curl -s "localhost:8002/api/v1/data/query?q=x&top_k=3" > a.json` and `curl -s -X POST localhost:8002/api/v1/data/query -H 'content-type: application/json' -d '{"q":"x","top_k":3}' > b.json`; **`diff a.json b.json` is empty**. `pytest tests/unit/interface` green |
| **8 Cross-layer proof** | 7 | nothing new | From `agent/`: construct the real `HttpJsonRetriever(base_url="http://localhost:8002/api/v1/data/query", map_response=…)` and `await retrieve("…")` → `list[RetrievedDocument]`. Then `git status --porcelain agent/domain` is **empty** and `pytest agent/tests` is still green |
| **9 Composition root + Dagster** | 3–7 | §8.8 orchestration | `dagster dev` lists the assets; `pytest tests/unit/orchestration tests/unit/test_architecture_rules.py::TestCompositionRoot` green |
| **10 E2E** | 8, 9 | nothing new | `docker compose up -d && pytest -m e2e` → `test_second_register_reports_cached_true_with_lower_duration` passes |
| **11 Structured path** | 9 | `file_source`, `normalize.py`, its Pandera contract | the CSV fixture → Bronze Parquet exists, Silver Parquet exists, one row in `quarantine/`, one row in `ops.quality_violations` |
| **12 Gold + views** | 11 | one model, `publish_service`, `api.v1_*` | as `backend_reader`: `select count(*) from api.v1_asset_overview` returns > 0 **and** `select * from gold.dim_asset` returns **permission denied**. The denial is what makes §11.2's boundary real |
| **13 Evaluate** | 6 | `evaluate.py`, the JSONL, a report template | `python -m application.pipelines.evaluate` writes a Markdown report naming the dataset version, the pipeline version, `n`, and two arms |

---

## 16. Decisions register

Every ambiguity in the architecture that an implementer would otherwise have to guess at. **Follow the Decided line; do not re-litigate.**

**16.1 Asset id vs the backend's `analysisId`.** §15 specifies `VID-20260821-0007` with a zero-padded sequence; the backend emits `ANL-{yyyyMMddHHmmss}-{6 hex}`. A sequence needs a per-kind-per-day counter — extra state, non-deterministic under retry. **Decided:** keep §15's shape, replace the sequence with 6 hex characters, and reuse the caller's entropy when there is one. Store the original in `external_refs`. **Because** it is deterministic on retry, needs no counter, keeps the sort-by-listing property §15 wanted, and `UNIQUE(content_hash)` catches genuine duplicates that a random id would not.

**16.2 `ObjectStore` cannot read bytes, and ffmpeg cannot open `s3://`.** §6's port has only `read_parquet/write_parquet/list/delete_prefix`; §7.6 step 1 says "read the blob" and step 8 writes JPEGs — neither is expressible, and no fsspec URL can be handed to a subprocess. **Decided:** extend the port with `read_bytes`, `write_bytes`, `exists`, `sha256` (streamed) and `materialize_local`. **Because** without `materialize_local` the ffmpeg decision and the object-storage decision do not compose, and the implementer would otherwise open a private `open()` inside a pipeline.

**16.3 No port backs the extract cache.** §5 lists `asset_service.py` as "a read-through cache over extract" but nothing implements the lookup; `Catalog` is about watermarks and the run log. **Decided:** add `AssetRepository`. **Because** the alternative is `application/` importing `psycopg`, which §2 forbids outright.

**16.4 No port expresses the chunk upsert.** `Sink.write(batch, partition)` cannot express "upsert on `(document_id, chunk_index, embedder_model_id)`" (§7.4). **Decided:** add `ChunkStore`. Keep `postgres_sink` for the Gold publish path only.

**16.5 `delete_prefix` contradicts per-asset grain.** §8 rule 2 says delete-prefix-then-write per partition; §7.6 says the unit of work is one asset. Following §8 inside `extract` **would delete every other asset in the same `event_date` partition.** **Decided:** `extract` writes a deterministic per-asset object and overwrites it in place, never `delete_prefix` on a date. `normalize` keeps delete-then-write, where the partition genuinely is the unit. **Because** the cache already provides `extract`'s idempotency, and this is a silent data-loss bug rather than a style question.

**16.6 `extract` is async but Dagster is not.** **Decided:** `async def extract_asset(...)`; the Dagster asset body is `asyncio.run(extract_partition(...))`; tests rely on `asyncio_mode = auto`. Do not add a sync wrapper inside `application/`.

**16.7 `extractor_version` is hand-maintained.** **Decided:** derive it (§5), with an override. **Because** forgetting to bump it produces exactly the silent artifact mixing §7.6 exists to prevent, and the moment it must be bumped is the moment a person is most rushed.

**16.8 Where the DDL lives.** §5's tree has no `sql/`. **Decided:** `data/sql/001_init.sql`, applied from the FastAPI lifespan behind `DATABASE_APPLY_SCHEMA_ON_STARTUP` and mounted into the container's initdb directory. Every statement `IF NOT EXISTS` / `OR REPLACE`. No migration tool for one file.

**16.9 `unaccent()` is not IMMUTABLE.** It cannot appear in a generated column or an index expression, which is exactly what §12.2's lexical leg needs. **Decided:** the `public.immutable_unaccent(text)` wrapper, used in both the `content_tsv` column and the trigram index. **Because** writing `to_tsvector('simple', unaccent(content))` fails with `generation expression is not immutable`, and the natural "fix" is to drop `unaccent` — silently deleting the diacritic tolerance that is the entire Vietnamese mitigation.

**16.10 Embedding dimension is fixed in DDL but the port exposes `dimensions`.** **Decided:** pin `vector(384)` with `CHECK (dimensions = 384)`; a model change is a new index generation and a rebuild (§7.4). `embedder_model_id` is in the primary key but **not** the HNSW index — HNSW cannot be composite; filter in the `WHERE` and accept post-filtering while one model is live.

**16.11 Two files claim to fuse the legs.** §5 gives the job to both `retrieval_service.py` and `hybrid_retriever.py`. **Decided:** RRF is pure arithmetic → `domain/policies/fusion.py`. `HybridRetriever` runs both legs and calls it. `retrieval_service.search()` survives as a thin `top_k` clamp, because §2 requires routes to call an application function.

**16.12 `RetrievedChunk` is used in §6 but never defined.** **Decided:** define it in `domain/entities/chunk.py` with four fields identical to the agent's `RetrievedDocument` — that is what §12.3's structural compatibility means. Compatibility is enforced at the **JSON boundary**, not by a Python import; pods do not share code.

**16.13 `Retriever.retrieve` signatures differ across layers.** **Decided:** `retrieve(query: str, top_k: int = 5, filters: Mapping[str, object] | None = None)`. Both defaults present keeps the data adapter structurally compatible with the agent's `@runtime_checkable` protocol if it is ever checked.

**16.14 `cut_count` cannot come from 8 frames.** It appears in §11.4's example response but requires the whole video. **Decided:** signals are name/value pairs the prompt asks for, per frame and rolled up per asset, stored EAV in `gold.fct_asset_signal`. Default set: `has_face`, `text_overlay_ratio`, `primary_language`, `product_visible`. **Drop `cut_count`.** If it is genuinely wanted it is an ffmpeg scene filter and a separate step, not a VLM answer. **Because** asking a model for a number it cannot know returns a confident fabrication into a Gold table.

**16.15 Does `POST /assets` also register and index?** §11.4's response mentions neither, but §18's first cut shows `ingest → extract → index → query`, and a query cannot find an asset that was never indexed. **Decided:** the route calls one function, `asset_service.ingest_extract_index`, chaining all three synchronously and returning the chunk count. **Because** embedding nine short texts is milliseconds, and the alternative is a demo where the asset you just uploaded is not searchable.

**16.16 The `uri` is backend-relative and is a trust boundary.** **Decided:** resolve under `asset_root` and reject with 400 `INVALID_URI` when the resolved path escapes it (§11).

**16.17 `/health` status code when the database is down.** Compose healthchecks use `curl -f`, so a 503 stops the other three pods from ever starting. **Decided:** always 200 while the process is alive; `status` is `"ok"` or `"degraded"`, `db` is a boolean, `assets` is `0` when degraded. Matches integration-architecture §2's "200 OK plus dependency status".

**16.18 Error envelope.** integration-architecture §6 mandates `{"error":{code,message,task_id}}`; FastAPI's default is `{"detail": …}`. **Decided:** a global handler producing the mandated shape with `request_id` in place of `task_id` — the data pod has no tasks. Vocabulary fixed in §11.

**16.19 The dual-verb handler.** **Decided:** one private `_run_query` plus two decorated wrappers. **Because** §11.4's requirement is one implementation, and the gate is `diff` being empty — which this satisfies without fighting the framework.

**16.20 RRF scores look broken.** Fused scores cluster near `1/61 ≈ 0.016`, and the agent maps `score` straight into `RetrievedDocument.score`, where anything reading it as a confidence sees near-zero. **Decided:** normalise to `[0,1]` by the maximum in the returned set. **This is presentation only — RRF ranks, it does not score.**

**16.21 What text becomes a chunk.** §15 gives the id forms but not the text. **Decided:** two kinds only. Transcript → one chunk per `CHUNK_MAX_TOKENS` split, id `{asset_id}:transcript:{NN}`. Each frame → one chunk, id `{asset_id}:frame_caption:{NN}`, text from the fixed templates in §8.7 — matching §11.4's example byte for byte.

**16.22 structlog vs the agent's logger.** [tech-stack-evaluation.md](tech-stack-evaluation.md) §11 chose structlog. **Decided: mirror `agent/observability/logging.py` and drop structlog.** Same three functions, same JSON shape, zero new dependencies. **Because** structlog was chosen to make structured fields the default, and `log_event(logger, level, event, **fields)` already forces exactly that at every call site — the stated benefit is already obtained. Identical log shapes across the two Python pods is worth more than structlog's ergonomics. Recorded as a deliberate reversal so nobody re-opens it.

**16.23 Docstring language.** `agent/` is unaccented Vietnamese; the design docs are English. **Decided:** match `agent/` — unaccented Vietnamese in code, English in documents. The specific choice matters far less than the fact that it is made.

**16.24 `run_id` provenance.** Never specified, yet it is a mandatory log field (§13) and a Bronze filename component (§8). **Decided:** `uuid4().hex[:12]`, generated by the **caller** (the route, or Dagster's `context.run_id`) and passed into pipelines as a parameter. Never generated inside a pipeline — two writes in one run must share it.

**16.25 Pandera backend.** **Decided:** `import pandera.polars as pa`; contracts are `pandera.polars.DataFrameModel`; always `lazy=True` (§7.2 step 6). Stated explicitly because the pandas API is the default and it behaves differently.

**16.26 Timezones.** **Decided:** every column `timestamptz`; every Python timestamp `datetime.now(UTC)`.

**16.27 Re-upload of identical bytes.** The backend mints a new `analysisId` per upload, so the same video twice gives two files and one content hash — and `UNIQUE(content_hash)` would reject the second registration. **Decided:** on a hash collision, return the **existing** `asset_id`, append the new id to `external_refs`, and report `cached: true`. Makes deduplication visible instead of an error.

**16.28 Dagster partitioning for a per-asset pipeline.** §15's asset keys are per-entity; §7.6's unit is per-asset. **Decided:** first build uses a **non-partitioned** `["silver","asset_artifact"]` asset that processes assets with no cache row for the current `extractor_version`. `DynamicPartitionsDefinition` keyed on `asset_id` is the named upgrade. **Because** dynamic partitions add a registration step with no first-slice benefit.

**16.29 `GET /assets/{id}` for a registered-but-unextracted asset.** **Decided:** 404 with `ASSET_NOT_EXTRACTED`, distinct from `ASSET_NOT_FOUND`. The synchronous POST means it should not happen; the distinct code is how you find out when it does.

**16.30 `gold` appears in §15's object-path enum but lives in Postgres.** **Decided:** `layer ∈ {bronze, silver, quarantine}` for object paths. Never create a `gold/` prefix in MinIO.

**16.31 BytePlus would add an unused dependency.** **Decided:** DO NOT CREATE YET. If attempted, implement with `httpx` against the OpenAI chat-completions shape — `httpx` is already present. Do not add the `openai` package for an experiment that may be abandoned.

**16.32 fastembed model cache path.** Getting this wrong silently re-downloads 200 MB at the venue. **Decided:** `ENV FASTEMBED_CACHE_PATH=/opt/fastembed` at build **and** runtime, warmed by a `RUN` line (§4), mirrored in `EmbedderSettings.cache_dir`, with an e2e assertion that the directory is non-empty.

---

## 17. Operational appendix

Carried from the previous version of this document. These are things that must be true, not schedule.

### Network insurance

Transcription and captioning are hosted calls, so a venue network failure takes both out. Three defences, all to be tested rather than assumed:

1. **The content-hash cache is the primary defence** — an asset processed once never needs the network again.
2. **Pre-warm every demo asset**: run each through `POST /api/v1/assets` and confirm `cached: true` on a second call.
3. **Bake the embedding model into the image** (§4).

**What this does not cover:** a genuinely new asset uploaded live. Either the demo uses pre-warmed assets, or that risk is accepted knowingly.

### The cross-team dependency that blocks stage 8

Nothing in `agent/` currently calls a `Retriever`. `agent/application/agent/agent.py` constructs an empty `Context` that is never populated; `agent/bootstrap/container.py` builds the agent with `tools={}` and no retriever; `HttpJsonRetriever` exists, is tested, and is wired to nothing.

Two pieces are needed from whoever owns that layer:

| Need | Agent port | Data endpoint |
|---|---|---|
| "what do we know about this topic" | `Retriever` — construct `HttpJsonRetriever` in `container.py`, populate `Context` before the reasoning loop | `GET /api/v1/data/query` |
| "give me the artifacts for this asset" | `Tool` — one tool in the empty registry | `GET /api/v1/assets/{id}` |

**Do not route the second through `Retriever`.** An asset id forced through text similarity is a lookup pretending to be a search, and it will occasionally return a different asset, silently.

The data side's obligation is to make this nearly free: emit exactly the JSON the existing adapter already parses, so the agent side needs a four-line mapper and no change under `agent/domain/`.

### Risks

| Risk | Handling |
|---|---|
| The 8-image request hits a provider limit | Stage 5's gate, before anything depends on it. Falls back to two calls of four frames (§10) |
| Venue network failure | Covered for pre-warmed assets, not for live novel uploads |
| `imageio-ffmpeg` fails on a real codec | Falls back to `apt-get install ffmpeg` — a Dockerfile line, no code change, because decoding is behind plain functions returning paths |
| The drawn problem needs no media | The structured path (stage 11) and the same API serve it; the media slice becomes unused rather than wrong |
| fastembed's ONNX download at runtime | §16.32, asserted in e2e |

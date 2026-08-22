# Data Layer — Implementation Plan

**Version:** 3.0
**Date:** 19/08/2026
**Implements:** [data-architecture.md](data-architecture.md) v3.0
**Tool rationale:** [tech-stack-evaluation.md](tech-stack-evaluation.md)

---

## 0. How to use this document

[data-architecture.md](data-architecture.md) says what the layer is. This says
what to build, in what order, and how you know each step worked.

Three rules for reading it:

1. **Build in stage order (§7).** Each stage depends only on the ones before it,
   so a failing gate localises the fault to that stage's files.
2. **Every gate is one command.** If it does not pass, do not start the next stage.
3. **§8's decisions are settled.** They exist so an ambiguity is not re-argued at
   hour 14. Follow them; do not re-litigate.

**Changed in 3.0:** dbt is removed and Delta Lake is the table format. The
`dbt-core` / `dbt-duckdb` / `dagster-dbt` dependencies are gone, the
`transformations/` project is replaced by `sql/transforms/`, decision §8.9 is
**withdrawn** (Delta's `MERGE` supersedes the workaround it described), and
stage 0.5 now verifies the Delta integration points instead of the dbt ones.

---

## 1. Scope

### Built here

Six source types, each end to end:

```
CSV ────┐
XLSX ───┤ dlt
API ────┼──▶ Landing ──▶ Bronze Delta ──▶ DuckDB SQL ──▶ Silver Delta ──▶ Gold Delta
DB  ────┘                                                                     │
                                                          publish ──▶ Postgres gold
                                                                     → api.v1_* → .NET
PDF ────▶ Landing blob ──▶ Docling + Polars ──▶ Silver Delta ──▶ Gold + Index
MEDIA ──▶ Landing blob ──▶ ffmpeg + Gemini ───▶ Silver Delta ──▶ Gold + Index
                                                                     │
                                                    Index → pgvector → :8002 → agent/
```

Plus: the four HTTP endpoints, the eval harness, and structured logging.

### Not built — each with the trigger that unblocks it

| Deferred | Build it when |
| --- | --- |
| `VACUUM` / `OPTIMIZE` schedules | storage cost is visible, or small files slow reads |
| Delta concurrent-write locking | genuine concurrent writers to one table |
| dbt or SQLMesh, again | more than ~a dozen SQL models, or real macro reuse |
| Column-level lineage | someone needs to know which column fed which |
| Local transcription (`faster-whisper`) | the network dependency becomes unacceptable, or Vietnamese quality binds |
| Multimodal / CLIP embeddings | an **eval shows** caption retrieval losing — not a suspicion |
| Perceptual hashing (`imagehash`) | near-duplicate detection becomes a requirement |
| A queue behind `POST /assets` | extraction starts exceeding the caller's timeout |
| CDC / streaming | a consumer's value depends on sub-minute freshness |
| A quarantine reprocessing UI | someone actually needs to reprocess |
| Alert detectors | there is an on-call rotation to page |
| OpenLineage | lineage is needed across teams and tools |

---

## 2. The rules that are checked

| # | Rule | Caught by |
| --- | --- | --- |
| 1 | Every asset body calls a function, never contains one | code review — and by `api.py` being able to call the same function |
| 2 | DuckDB never writes Delta; it returns Arrow and `deltalake` writes | code review — one write path, `lib/delta.py` |
| 3 | No `print()` outside tests | `ruff` (`T20` rule set) |
| 4 | Landing and Bronze are append-only | `test_append_only.py` |
| 5 | Every derivation is keyed so a re-run is free | `test_media_cache.py::test_second_run_makes_zero_model_calls` |
| 6 | No transcript, caption or payload in a log | `test_media_pipeline.py::test_transcript_text_never_appears_in_log_output` |
| 7 | Bad rows are quarantined, never dropped | `test_contracts.py::test_rejected_rows_land_in_quarantine` |
| 8 | GET and POST `/data/query` return identical bodies | `test_api.py` + the stage-8 `diff` gate |
| 9 | `/health` is 200 even with the database down | `test_api.py::test_degraded_when_db_unreachable` |

A rule nothing checks is a wish.

---

## 3. Environment

### `data/requirements.txt`

Versions from [tech-stack-evaluation.md](tech-stack-evaluation.md) §14. **The
media and serving packages there are unverified — check each against PyPI before
pinning.**

```
# core
pydantic>=2.13
pydantic-settings>=2.15
pyarrow>=25.0

# table format -- 3.0's centre of gravity
deltalake>=1.0                  # delta-rs: Rust + Python, no JVM

# ingestion + compute
dlt[duckdb,postgres,filesystem,s3,parquet,deltalake]>=1.30
polars>=1.43
duckdb>=1.5
pandera[polars]>=0.32
fastexcel>=0.20                 # Excel via calamine -- see §6.2 of the architecture

# storage
s3fs>=2026.7
psycopg[binary]>=3.3
pgvector>=0.5

# documents + media + models
docling>=2.119
imageio-ffmpeg>=0.5
google-genai>=1.0
fastembed>=0.8

# serving
fastapi>=0.115
uvicorn[standard]>=0.32

# orchestration
dagster>=1.13
dagster-webserver>=1.13
dagster-dlt>=0.29
dagster-duckdb>=0.29

# eval
scikit-learn>=1.9

# dev
pytest>=9.0
pytest-asyncio>=0.24
httpx>=0.27
ruff>=0.16
```

**Removed in 3.0:** `dbt-core`, `dbt-duckdb`, `dagster-dbt`.
**Added:** `deltalake`, and the `deltalake` extra on dlt.
Verify the dlt extra's exact name at 1.30 — it is the first thing stage 0.5 checks.

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
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
```

No `apt-get` — `imageio-ffmpeg` ships its own static binary, and delta-rs ships
as a wheel.

### `docker-compose.yml`

Two services. Postgres needs `pgvector`, `pg_trgm` and `unaccent`; MinIO holds
every Delta table.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment: {POSTGRES_USER: bi, POSTGRES_PASSWORD: bi, POSTGRES_DB: bi}
    ports: ["5432:5432"]
    volumes:
      - ./sql/001_init.sql:/docker-entrypoint-initdb.d/001_init.sql:ro
      - pgdata:/var/lib/postgresql/data
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U bi"], interval: 5s, retries: 10}

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment: {MINIO_ROOT_USER: minio, MINIO_ROOT_PASSWORD: minio123}
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]

volumes: {pgdata: {}, miniodata: {}}
```

The `wwwroot/uploads` directory from the .NET backend is mounted into whatever
runs `api.py` — see §8.3.

### `data/.env.example`

```
ENVIRONMENT=development
STORAGE_URL=s3://bi-data-dev              # landing/ bronze/ silver/ gold/ quarantine/
STORAGE_ENDPOINT_URL=http://localhost:9000
STORAGE_ACCESS_KEY=minio
STORAGE_SECRET_KEY=minio123
ASSET_ROOT=/data/uploads
DATABASE_URL=postgresql://bi:bi@localhost:5432/bi
GEMINI_API_KEY=
USE_MOCK_MODELS=true                       # the offline switch -- architecture §2
MEDIA_FRAME_COUNT=8
CHUNK_MAX_TOKENS=512
RETRIEVAL_RRF_K=60
QUALITY_MAX_REJECTED_RATIO=0.05
```

**delta-rs needs the S3 credentials as `storage_options` on every call**, not as
ambient environment variables the way fsspec tolerates. `lib/delta.py` builds
that dict once from `Settings` and every read and write passes it — getting this
wrong produces a confusing "table not found" against a bucket that plainly exists.

---

## 4. Settings

One `Settings` object in `lib/settings.py`, built on `pydantic-settings`, with one
nested class per concern. **Never call `Settings()` anywhere else** — import the
singleton.

```python
class Settings(BaseSettings):
    environment: Environment = Environment.DEVELOPMENT
    storage:   StorageSettings   = Field(default_factory=StorageSettings)
    database:  DatabaseSettings  = Field(default_factory=DatabaseSettings)
    sources:   SourceSettings    = Field(default_factory=SourceSettings)
    media:     MediaSettings     = Field(default_factory=MediaSettings)
    gemini:    GeminiSettings    = Field(default_factory=GeminiSettings)
    chunk:     ChunkSettings     = Field(default_factory=ChunkSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    quality:   QualitySettings   = Field(default_factory=QualitySettings)
    api:       ApiSettings       = Field(default_factory=ApiSettings)
    use_mock_models: bool = True

settings = Settings()
```

`StorageSettings` also exposes the layer URLs — `landing_url`, `bronze_url`,
`silver_url`, `gold_url`, `quarantine_url` — and the `storage_options` dict
delta-rs needs, so no pipeline builds a path by string concatenation.

### `extractor_version` is derived, not typed

It must change whenever anything that changes the output changes. Deriving it from
the prompt text, the frame count, the sampling parameters and the model ids removes
the failure mode where someone forgets to bump it — which is exactly the silent
artifact-mixing the cache exists to prevent, and it happens when a person is most
rushed.

```python
@property
def extractor_version(self) -> str:
    material = f"{self.caption_instruction}|{self.frame_count}|{self.fps}|" \
               f"{self.longest_side}|{self.captioner_model}|{self.transcriber_model}"
    return self._override or f"ext-{hashlib.sha256(material.encode()).hexdigest()[:8]}"
```

An explicit override exists for the case where you need to force a rebuild.

---

## 5. Postgres schema — `sql/001_init.sql`

Postgres now holds three things: the retrieval index, the operational tables, and
the published Gold. **Silver and Gold themselves live in Delta** — what lands here
is a copy for serving.

Every statement is `IF NOT EXISTS` / `OR REPLACE`, so the file is safe to apply
twice: once from the container's initdb mount, once from the API on startup.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS "index";
CREATE SCHEMA IF NOT EXISTS asset;
CREATE SCHEMA IF NOT EXISTS api;
CREATE SCHEMA IF NOT EXISTS ops;

-- unaccent() is not IMMUTABLE, so it cannot be used in a generated column or an
-- index expression. This wrapper is what makes the Vietnamese mitigation legal.
CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT public.unaccent('public.unaccent', $1) $$;

-- ============================================================ media + documents
CREATE TABLE IF NOT EXISTS asset.asset (
    asset_id      text PRIMARY KEY,
    kind          text NOT NULL,
    source_uri    text NOT NULL,
    content_hash  text NOT NULL UNIQUE,     -- catches genuine duplicate uploads
    media_type    text,
    size_bytes    bigint,
    ingested_date date NOT NULL,
    external_refs text[] NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- The load-bearing cache. Keyed on the bytes AND the extractor, never one alone.
CREATE TABLE IF NOT EXISTS asset.extract_cache (
    content_hash      text NOT NULL,
    extractor_version text NOT NULL,
    asset_id          text NOT NULL REFERENCES asset.asset(asset_id),
    artifacts         jsonb NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_hash, extractor_version)
);

-- ============================================================ retrieval index
CREATE TABLE IF NOT EXISTS "index".chunk (
    chunk_id     text PRIMARY KEY,
    document_id  text NOT NULL,
    source_type  text NOT NULL,             -- transcript | frame_caption | document
    chunk_index  int  NOT NULL,
    content      text NOT NULL,
    metadata     jsonb NOT NULL DEFAULT '{}',
    content_tsv  tsvector GENERATED ALWAYS AS (
                     to_tsvector('simple', public.immutable_unaccent(content))
                 ) STORED,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chunk_tsv_idx  ON "index".chunk USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS chunk_trgm_idx ON "index".chunk
    USING gin (public.immutable_unaccent(content) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS "index".embedding (
    chunk_id          text NOT NULL REFERENCES "index".chunk(chunk_id) ON DELETE CASCADE,
    embedder_model_id text NOT NULL,
    dimensions        int  NOT NULL CHECK (dimensions = 384),
    embedding         vector(384) NOT NULL,
    PRIMARY KEY (chunk_id, embedder_model_id)
);
CREATE INDEX IF NOT EXISTS embedding_hnsw_idx ON "index".embedding
    USING hnsw (embedding vector_cosine_ops);

-- ============================================================ ops
CREATE TABLE IF NOT EXISTS ops.run_log (
    run_id        text NOT NULL,
    asset_key     text NOT NULL,
    pipeline      text NOT NULL,
    partition_key text,
    dataset       text,
    status        text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    rows_in       bigint NOT NULL DEFAULT 0,
    rows_out      bigint NOT NULL DEFAULT 0,
    rows_rejected bigint NOT NULL DEFAULT 0,
    bytes_written bigint NOT NULL DEFAULT 0,
    duration_ms   integer,
    delta_version bigint,                   -- the Delta commit this run produced
    error_code    text,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    PRIMARY KEY (run_id, asset_key)
);

CREATE TABLE IF NOT EXISTS ops.quality_violations (
    violation_id     bigserial PRIMARY KEY,
    run_id           text NOT NULL,
    dataset          text NOT NULL,
    partition_key    text,
    contract_version text NOT NULL,
    check_name       text NOT NULL,
    column_name      text,
    violation_code   text NOT NULL,
    severity         text NOT NULL DEFAULT 'error' CHECK (severity IN ('warning','error')),
    failure_count    bigint NOT NULL DEFAULT 1,
    quarantine_table text,                  -- the Delta table the rows went to
    detail           text,                  -- NEVER a row payload
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- architecture §8: "never silently drop an unknown column"
CREATE TABLE IF NOT EXISTS ops.schema_drift (
    drift_id    bigserial PRIMARY KEY,
    run_id      text NOT NULL,
    dataset     text NOT NULL,
    change_type text NOT NULL CHECK (change_type IN ('column_added','column_removed','type_changed')),
    column_name text NOT NULL,
    from_type   text,
    to_type     text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ============================================================ roles
DO $$ BEGIN
    CREATE ROLE backend_reader LOGIN PASSWORD 'backend_reader';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA api TO backend_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT SELECT ON TABLES TO backend_reader;
-- Deliberately NOT granted on gold. That denial is what makes architecture §9's
-- serving boundary real rather than a convention.
```

`gold` tables and the `api.v1_*` views over them are created by the publish step
(§6.7), not here — their columns follow the Gold Delta tables.

`ops.run_log.delta_version` is new in 3.0: recording which Delta commit a run
produced is what makes "show me the table as this run left it" a one-line query
rather than an archaeology exercise.

---

## 6. File manifest, by stage

### 6.1 Stage 0 — skeleton

```
lib/settings.py · lib/logging.py · requirements.txt · Dockerfile
docker-compose.yml · .env.example · pytest.ini · pyproject.toml (ruff config)
tests/unit/test_settings.py
```

### 6.2 Stage 1 — storage and database

```
sql/001_init.sql
lib/delta.py       read_delta, write_delta, merge_delta, table_uri, storage_options,
                   sha256 (streamed), materialize_local -- ffmpeg cannot open s3://
lib/sql.py         run_sql_to_delta() + read_sql() -- architecture §2
lib/db.py          psycopg helpers: upsert_chunks, get_cache, save_cache, log_run,
                   record_violation, and the architecture §10 retrieval query
lib/contracts.py   split_on_contract() -- architecture §8
tests/integration/test_delta.py · test_db.py
```

`sha256` must stream. A 150 MB video is never held in memory.

### 6.3 Stage 2 — CSV to Gold, the shared spine

```
defs/__init__.py · defs/resources.py · defs/ingest.py (CSV only) · defs/transform.py
contracts/orders.py
sql/transforms/silver/stg_erp__orders.sql
sql/transforms/gold/fct_order.sql
tests/fixtures/orders.csv          10 rows, ONE deliberately malformed
tests/unit/test_transform_sql.py   runs the .sql against a tmp_path Delta fixture
```

### 6.4 Stage 3 — the other three tabular sources

```
defs/ingest.py     + Excel transformer, rest_api_source, sql_database
contracts/catalog.py · channel_history.py
sql/transforms/silver/stg_shop__catalog.sql · stg_api__channel_history.sql ·
                      stg_erp__customers.sql
sql/transforms/gold/dim_customer.sql
tests/fixtures/catalog.xlsx · tests/integration/test_ingest_sources.py
```

### 6.5 Stage 4 — documents

```
defs/documents.py       Docling parse -> HybridChunker -> Silver Delta -> embed -> index
contracts/document_chunk.py
tests/fixtures/policy.pdf
tests/unit/test_chunking.py · tests/integration/test_docling.py
```

### 6.6 Stage 5 — media

```
lib/ffmpeg.py           two fixed commands, returning paths
lib/gemini.py           transcribe() + caption(), with the USE_MOCK_MODELS switch
contracts/asset_artifact.py
defs/media.py           extract_asset() + the asset that calls it; MERGE on asset_id
prompts/caption.txt
tests/fixtures/sample_5s.mp4 · sample.jpg
tests/unit/test_media_pipeline.py · test_media_cache.py · test_media_merge.py
tests/integration/test_ffmpeg.py · test_gemini_live.py
```

### 6.7 Stage 6 — retrieval, API, publish

```
api.py                  the four endpoints, the error envelope, the URI trust boundary
defs/publish.py         Gold Delta -> Postgres gold + api.v1_* views, one transaction
defs/checks.py · defs/schedules.py
tests/unit/test_api.py · tests/integration/test_retrieval.py · test_publish.py
```

### 6.8 Stage 7 — eval

```
defs/evaluate.py
evaluation/datasets/retrieval.jsonl      ~100-200 hand-labeled cases
evaluation/reports/ (generated)
```

### 6.9 Do not create

`transformations/` or any dbt project · `dbt_project.yml` · `profiles.yml` ·
`lib/ports.py` · any `Protocol` with one implementation · `domain/` ·
`infrastructure/` · `application/` · a composition root · a mock adapter class
(use `USE_MOCK_MODELS`) · `tests/unit/test_architecture_rules.py`.

**An empty file is worse than a missing one.**

---

## 7. Stage gates

Ordered by dependency. **Each gate is one command. If it fails, the fault is in
that stage's files and nowhere else.**

| Stage | Builds | Gate |
| --- | --- | --- |
| **0 Skeleton** | §6.1 | `python -c "from lib.settings import settings; print(settings.media.extractor_version)"` prints `ext-…`; `pytest tests/unit/test_settings.py` green |
| **0.5 Verify integrations** | nothing | **Do this first — see §10.** Four checks, one script: dlt writes Delta; `delta_scan` reads it; `DeltaTable.merge` updates by key; `dagster-dlt` imports. Each has a named fallback in architecture §17 |
| **1 Stores** | §6.2 | `docker compose up -d`, then apply `001_init.sql` **twice** with no error; `pytest -m integration tests/integration/test_delta.py test_db.py` — including a write, a read-back, a `MERGE`, and `history()` showing two versions |
| **2 CSV → Gold** | §6.3 | `dagster asset materialize --select '*' -m defs` then: `landing/orders` has the raw file, `delta_scan('bronze/orders')` returns 10 rows, `silver/orders` returns 9, **`quarantine/orders` returns 1**, one row in `ops.quality_violations`, and `gold/fct_order` is non-empty |
| **3 Three more sources** | §6.4 | the same six assertions for `catalog_xlsx`, `channel_api`, `erp_db`. **A `.sql` file and a contract should be the only things you had to write** |
| **4 Documents** | §6.5 | `pytest -m integration tests/integration/test_docling.py` → the PDF yields >0 chunks and a table survives as text |
| **5 Media offline** | §6.6 | **`pytest tests/unit/test_media_pipeline.py test_media_cache.py test_media_merge.py` green with no ffmpeg binary, no API key and no network.** Includes `test_second_run_makes_zero_model_calls` and `test_merge_updates_one_asset_without_touching_others` |
| **5b Media live** | — | `pytest -m integration tests/integration/test_ffmpeg.py` → 8 JPEGs and one 16 kHz mono WAV; then `test_gemini_live.py` with a real key. **Nothing downstream starts until this passes** — it is the single biggest unknown |
| **6 Retrieval** | §6.7 | `pytest -m integration tests/integration/test_retrieval.py`, specifically `test_matches_across_missing_diacritics` — `"giam gia"` must retrieve `"giảm giá"` |
| **7 API** | §6.7 | `uvicorn api:app --port 8002`, then `curl -s "localhost:8002/api/v1/data/query?q=x&top_k=3" > a.json` and the equivalent POST `> b.json`; **`diff a.json b.json` is empty** |
| **7b Publish** | §6.7 | as `backend_reader`: `select count(*) from api.v1_asset_overview` returns > 0 **and** `select * from gold.dim_asset` returns **permission denied**. The denial is what makes the boundary real |
| **8 Cross-layer** | nothing new | from `agent/`: build `HttpJsonRetriever(base_url="http://localhost:8002/api/v1/data/query", …)`, `await retrieve("…")` → `list[RetrievedDocument]`. Then `git status --porcelain agent/domain` is **empty** |
| **9 Eval** | §6.8 | `dagster asset materialize --select eval_retrieval -m defs` writes a Markdown report naming the dataset version, the pipeline version, `n`, and two arms |

---

## 8. Decisions register

Ambiguities an implementer would otherwise have to guess at. **Follow the Decided
line; do not re-litigate.**

**8.1 Asset id shape.** The backend emits `ANL-{yyyyMMddHHmmss}-{6 hex}`; the
naming convention wants `VID-20260821-0007`. A sequence needs per-kind-per-day
state and is non-deterministic under retry. **Decided:** keep the shape, replace
the sequence with 6 hex characters, and reuse the caller's entropy when there is
one. Store the original in `external_refs`. **Because** it is deterministic on
retry, needs no counter, and `UNIQUE(content_hash)` catches genuine duplicates
that a random id would not.

**8.2 Re-upload of identical bytes.** The backend mints a new id per upload, so
the same video twice gives two filenames and one content hash — and
`UNIQUE(content_hash)` would reject the second registration. **Decided:** return
the **existing** `asset_id`, append the new reference to `external_refs`, and
report `cached: true`. Makes deduplication visible instead of an error.

**8.3 The `uri` is a trust boundary.** **Decided:** resolve under `ASSET_ROOT` and
reject with `400 INVALID_URI` when the resolved path escapes it. The backend sends
`/uploads/videos/x.mp4`; anything containing `..` is an attack, not a typo.

**8.4 `POST /api/v1/assets` also indexes.** A query cannot find an asset that was
never indexed. **Decided:** the route runs register → extract → index
synchronously and returns the chunk count. **Because** embedding nine short texts
is milliseconds, and the alternative is a demo where the video you just uploaded
is not searchable.

**8.5 The dual-verb query handler.** **Decided:** one private `_run_query` plus two
route decorators. The gate is `diff` being empty, which this satisfies without
fighting the framework.

**8.6 `/health` status code when the database is down.** **Decided:** always 200
while the process is alive; `status` is `"ok"` or `"degraded"`, `db` is a boolean,
`assets` is `0` when degraded. A 503 would fail the compose healthcheck and stop
the other pods from starting.

**8.7 Error envelope.** **Decided:** a global handler producing
`{"error":{code,message,request_id}}` — the shape the other pods use, with
`request_id` in place of their `task_id`, since this pod has no tasks.

**8.8 `extract` is async, Dagster is not.** **Decided:** `async def
extract_asset(...)`; the asset body is `asyncio.run(...)`; tests use
`asyncio_mode = auto`. Do not add a sync wrapper.

**8.9 — WITHDRAWN in 3.0.** This decision said media must write one deterministic
per-asset object and never `delete_prefix` on a date, because deleting the date
partition would destroy every other asset in it. **Delta's `MERGE` supersedes it
entirely**: one asset updating its own rows inside a shared table is exactly what
`MERGE` is for (architecture §6.6). The decision is left in place, numbered and
struck, rather than renumbered — the reasoning is still the clearest statement of
*why* Delta earns its place here, and a gap in the register invites someone to
re-derive the workaround.

**8.10 `embedder_model_id` is in the primary key, not the HNSW index.** HNSW
cannot be composite. **Decided:** pin `vector(384)` with `CHECK (dimensions =
384)`, filter on the model id in the `WHERE`, and accept post-filtering while
exactly one embedding generation is live.

**8.11 What text becomes a chunk.** **Decided:** three kinds. Transcript → one
chunk per `CHUNK_MAX_TOKENS` window, id `{asset_id}:transcript:{NN}`. Each frame →
one chunk, id `{asset_id}:frame_caption:{NN}`, text `"Frame at {t}s: {caption}"`
plus `", on-screen text '{ocr}'"` when present. Document → one chunk per Docling
chunk, id `{document_id}:document:{NN}`. **The templates are fixed strings** — they
appear in the API response, the eval dataset and the logs, so they must not drift.

**8.12 RRF scores look broken.** Fused values cluster near `1/61 ≈ 0.016`, and the
agent maps `score` straight into its own entity where anything reading it as a
confidence sees near-zero. **Decided:** normalise to `[0,1]` by the maximum in the
returned set. **This is presentation only — RRF ranks, it does not score.**

**8.13 `run_id` provenance.** **Decided:** `uuid4().hex[:12]`, generated by the
**caller** (the route, or Dagster's `context.run.run_id`) and passed in as a
parameter. Never generated inside a pipeline — two writes in one run must share it.

**8.14 Pandera backend.** **Decided:** `import pandera.polars as pa`; contracts are
`pandera.polars.DataFrameModel`; always `lazy=True`. Stated explicitly because the
pandas API is the default and behaves differently.

**8.15 Timezones.** **Decided:** every column `timestamptz`; every Python timestamp
`datetime.now(UTC)`.

**8.16 Logging.** **Decided:** stdlib `logging` plus a JSON formatter mirroring
`agent/observability/logging.py`. No structlog. `log_event(logger, level, event,
**fields)` already forces structured fields at every call site.

**8.17 Docstring language.** **Decided:** English throughout `data/`, Google style
(`Args:`/`Returns:`/`Raises:`). `agent/` keeps unaccented Vietnamese; the
divergence is deliberate and recorded.

**8.18 SQL files are parameterised by Python, not by a templating language.**
Removing dbt removes Jinja. **Decided:** `.sql` files use `{bronze}` / `{silver}`
placeholders filled by `read_sql(path, **paths)` from `Settings`, and nothing
else. **Because** the moment a SQL file grows conditionals it stops being
reviewable as SQL, and that is the point at which architecture §16's trigger to
reconsider dbt has been hit.

**8.19 `schema_mode="merge"` is opt-in per write, never a default.** **Decided:**
Delta writes are strict by default; `schema_mode="merge"` is passed only for a
deliberate additive change. **Because** a write failing on a schema mismatch is
the contract working, and reaching for `merge` to make a red pipeline green is how
a table gets corrupted quietly.

**8.20 No `VACUUM` in the build.** **Decided:** do not schedule `VACUUM` or
`OPTIMIZE`. **Because** old versions cost storage and buy time travel, and a
retention window shorter than the slowest reader breaks live queries. Add it when
storage is a real problem — or when a compliance delete must actually remove bytes
(the right-to-erasure row in architecture §13).

---

## 9. Test manifest

`tests/unit` must run with **no container, no API key and no network**. If it
cannot, `USE_MOCK_MODELS` is not being honoured somewhere.

**Delta makes the SQL layer unit-testable**, which is new in 3.0: a Delta table is
a directory, so a test writes a small one to `tmp_path`, points a `.sql` file at
it, and asserts on the Arrow result — no container, no dbt process.

### Unit

| File | Named methods |
| --- | --- |
| `test_settings.py` | `test_extractor_version_changes_when_prompt_changes` · `test_stable_when_log_level_changes` · `test_override_wins` |
| `test_asset_id.py` | `test_derives_vid_id_from_backend_id` · `test_is_deterministic` · `test_falls_back_to_content_hash` |
| **`test_transform_sql.py`** | `test_stg_orders_dedupes_on_business_key` · `test_stg_orders_casts_amount` · `test_no_select_star_in_any_sql_file` — all against a `tmp_path` Delta fixture |
| `test_contracts.py` | `test_valid_rows_pass_through` · **`test_rejected_rows_land_in_quarantine`** · `test_lazy_reports_every_violation` |
| `test_chunking.py` | `test_frame_chunk_uses_the_fixed_template` · `test_transcript_chunk_id_format` · `test_reindexing_produces_identical_chunk_ids` |
| `test_fusion.py` | `test_item_ranked_first_in_both_legs_wins` · `test_larger_k_flattens_ranking` · `test_scores_normalised_to_unit_interval` |
| **`test_media_pipeline.py`** | `test_calls_transcribe_once_and_caption_once` · `test_image_yields_one_frame_and_no_transcript` · `test_decode_error_quarantines_and_continues` · **`test_transcript_text_never_appears_in_log_output`** |
| **`test_media_cache.py`** | **`test_second_run_makes_zero_model_calls`** · `test_cache_hit_skips_frame_extraction` · `test_version_bump_forces_recompute` |
| **`test_media_merge.py`** | **`test_merge_updates_one_asset_without_touching_others`** · `test_rerunning_same_asset_is_idempotent` |
| `test_api.py` | `test_get_and_post_return_identical_bodies` · `test_top_k_clamped_to_max` · `test_path_traversal_uri_rejected` · `test_degraded_when_db_unreachable` · `test_unknown_asset_returns_404_envelope` |

### Integration — `@pytest.mark.integration`

| File | Proves |
| --- | --- |
| `test_delta.py` | write / read / `MERGE` / `history()` against MinIO; `storage_options` are correct; `sha256` of a 10 MB file matches `hashlib` |
| `test_db.py` | `001_init.sql` is idempotent; the three extensions exist; `immutable_unaccent` is usable in an index expression |
| `test_ingest_sources.py` | each of the four dlt sources produces Landing and a readable Bronze Delta table |
| `test_docling.py` | the fixture PDF yields >0 chunks and a table survives as text |
| `test_ffmpeg.py` | the 5-second MP4 → exactly `frame_count` JPEGs, longest side ≤512, and a WAV reporting 16000 Hz / 1 channel |
| `test_retrieval.py` | **`test_matches_across_missing_diacritics`** · `test_hnsw_index_is_used` (via `EXPLAIN`) · `test_hybrid_returns_an_item_only_one_leg_found` |
| `test_publish.py` | Gold Delta → Postgres in one transaction; `backend_reader` can read `api.v1_*` and **cannot** read `gold.*` |
| `test_gemini_live.py` | the real batched 8-image request; skipped without `GEMINI_API_KEY` |
| `test_append_only.py` | a second run appends a new Delta version and never rewrites an earlier one; `history()` shows both |

### Fixtures

| Path | What |
| --- | --- |
| `tests/fixtures/orders.csv` | 10 rows, **one deliberately malformed** — the quarantine proof |
| `tests/fixtures/catalog.xlsx` | one sheet, a few rows |
| `tests/fixtures/policy.pdf` | a short document **with a table** |
| `tests/fixtures/sample_5s.mp4` | 5 seconds, H.264 + AAC, under 1 MB |
| `tests/fixtures/sample.jpg` | one image, for the `kind=image` path |
| `evaluation/datasets/retrieval.jsonl` | hand-written `{query, expected_chunk_ids}` cases |

---

## 10. Stage 0.5 — the four checks, in full

Run this before writing anything that depends on them. Each failure has a named
fallback in architecture §17, so a red result costs a design change, not a day.

```python
# 1. Does dlt write Delta?  -- if not: dlt writes Parquet to Landing,
#    and a Polars step produces Bronze Delta. §3's split makes this natural.
import dlt
from dlt.sources.filesystem import filesystem, read_csv
p = dlt.pipeline("probe", destination=dlt.destinations.filesystem("/tmp/probe"))
p.run(filesystem("/tmp/csv", "*.csv") | read_csv(), table_format="delta")

# 2. Does DuckDB read Delta?  -- if not: read with Polars, register the Arrow
#    table into DuckDB. One extra line per transform.
import duckdb
con = duckdb.connect(); con.execute("INSTALL delta; LOAD delta;")
con.sql("SELECT * FROM delta_scan('/tmp/probe/probe_dataset/probe_table')").show()

# 3. Does MERGE work?  -- if not: fall back to a per-asset object,
#    and re-open whether Delta is earning its place at all.
from deltalake import DeltaTable, write_deltalake
import pyarrow as pa
write_deltalake("/tmp/m", pa.table({"id":[1,2],"v":["a","b"]}), mode="overwrite")
(DeltaTable("/tmp/m").merge(pa.table({"id":[2],"v":["B"]}),
    predicate="t.id = s.id", source_alias="s", target_alias="t")
    .when_matched_update_all().when_not_matched_insert_all().execute())
assert DeltaTable("/tmp/m").to_pyarrow_table().num_rows == 2

# 4. Does dagster-dlt import?  -- if not: call the dlt pipeline inside a
#    plain @asset. It is a normal Python call.
from dagster_dlt import dlt_assets, DagsterDltResource
```

**Check 3 is the one that decides the architecture.** `MERGE` is the reason Delta
is here (§8.9); if it does not work as expected, the honest response is to
reconsider the table format, not to work around it.

---

## 11. Risks

| Risk | Handling |
| --- | --- |
| dlt cannot write Delta at 1.30 | **Stage 0.5 check 1.** Fallback is built into the layering: dlt writes Parquet to Landing, Polars converts to Bronze Delta |
| `delta_scan` cannot reach MinIO | **Stage 0.5 check 2.** Read with Polars and register the Arrow table into DuckDB |
| `DeltaTable.merge` behaves differently | **Stage 0.5 check 3.** This is the decisive one — reconsider Delta rather than working around it |
| delta-rs `storage_options` misconfigured | Presents as "table not found" against a bucket that plainly exists. `lib/delta.py` builds the dict once; never assemble it at a call site |
| Small-file accumulation on the media table | One `MERGE` per asset means many small files. Not a stage-gate concern, but watch read times; `OPTIMIZE` is the answer and §1 records the trigger |
| A wheel has no Python 3.12 build | Verify the unverified media/serving pins early — this is the kind of thing that costs an evening |
| Venue network dies | The `content_hash + extractor_version` cache is the primary defence. **Pre-warm every demo asset** and confirm `cached: true` on a second call. The embedding model is baked into the image |
| A genuinely new asset uploaded live | Not covered by the cache. Either the demo uses pre-warmed assets, or that risk is accepted knowingly |
| Vietnamese retrieval quality | Real limitation, documented in architecture §10. State the caveat rather than discovering it on stage |
| Six pipelines is breadth, and breadth hides depth | Stage 2 goes all the way to Gold before stage 3 starts. One complete path first, then three configurations of it |
| No dbt means no column-level lineage | Known and accepted (architecture §11). Dagster gives table-to-table; Delta `history()` gives when. Revisit if someone actually asks which column fed which |

# Data Architecture Standard — Beyond Intelligence

> Architecture and coding standard for the `data/` layer (**Platform 1 — Data Intelligence**), designed to be reused across AI projects: the business content changes, the frame does not.

**Version:** 1.1
**Date:** 18/08/2026
**Applies to:** the `data/` directory
**Companion documents:** [tech-stack-evaluation.md](tech-stack-evaluation.md) — why each tool was chosen · [implementation-plan.md](implementation-plan.md) — the build order and schedule for this architecture · [agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) — the same standard for the `agent/` layer
**Theoretical basis:** Clean Architecture + Ports & Adapters (as established for `agent/`) applied to the five-stage data lifecycle (generation → storage → ingestion → transformation → serving), with medallion layering.

**Changes in 1.1.** Media assets — video, image, audio — become a first-class source type (§7.6, §6, §12.4). Request-time invocation joins Dagster as a second orchestration edge (§1, §2). The serving claim in §11 is scoped: Postgres remains the contract surface for the .NET backend, and a thin FastAPI process on `:8002` serves the agent layer (§11.4). No section from 1.0 was removed.

---

## 1. Purpose and scope

The `data/` layer owns the **Sense** step of the platform's philosophy (`Sense → Understand → Reason → Simulate → Decide → Act → Learn`). It takes messy, untyped outside data — CSVs, API responses, database rows, documents, uploaded videos and images — and turns it into two trusted products:

1. **Structured data** the backend and the simulation layer can query.
2. **Retrievable knowledge** document chunks and media annotations go into the retrieval index for the agent layer to search.

### In scope

| Responsibility                                            | Where it is specified |
| --------------------------------------------------------- | --------------------- |
| Ingest CSV, Excel, JSON, API, Database, Documents         | §7.1                  |
| Ingest media assets — video, image, audio                 | §7.1, §7.6            |
| Validation and data quality                               | §10                   |
| Cleaning, typing, deduplication, normalization            | §7.2                  |
| Data integration and modelling                            | §7.3                  |
| Feature / analytics tables                                | §7.3                  |
| Media derivation — frames, audio, transcript, annotations | §7.6                  |
| Chunking, embedding, indexing for retrieval               | §7.4, §12             |
| Retrieval implementation behind the agent's port          | §12                   |
| Data contracts toward the backend                         | §9, §11               |
| The HTTP data service the agent layer calls               | §11.4                 |
| Pipeline observability and lineage                        | §13                   |
| The evaluation harness (DE half of Platform 7)            | §7.5                  |

### Two invocation modes

Version 1.0 assumed every pipeline was started by a Dagster schedule. That is still the default, but it is not the only edge. A consumer who has just uploaded a video needs an answer in seconds, not at the next scheduled tick.

| Mode | Started by | Latency | Used for |
| --- | --- | --- | --- |
| **Scheduled** | Dagster schedule or sensor | minutes to hours | reference corpora — historical performance, catalogs, policy documents, brand guidelines |
| **Request-time** | an HTTP call to `interface/api/` (§11.4) | seconds | the asset a user just uploaded and is waiting on |

**This needs no new architecture, and that is the point.** §2 already requires every function in `application/pipelines/` to be callable from a plain `pytest` test with no Dagster import. A rule written for testability turns out to have bought a second orchestration edge for free: FastAPI becomes another thin caller of the same pipeline functions, exactly as a Dagster asset is. If a pipeline cannot be called this way, §2 was already being violated.

### Explicitly out of scope

- **Reasoning over the data.** Context construction, planning and decision generation belong to `agent/`. This layer returns documents, rows and media annotations; it never interprets them.
- **Streaming.** Everything here is batch, micro-batch or request-time. Request-time is not streaming: it is a synchronous run over one asset with a bounded end, with no continuous ingestion, no windowing and no broker. §17 states the trigger for genuine streaming.
- **Media generation.** This layer describes media; it does not create it. Producing a mockup image or rendering a video is a `Tool` in `agent/`, invoked after a decision. The line is the same one §1 already draws for text.
- **Being a warehouse migration.** No attempt to consolidate all company data. One pipeline per dataset that a consumer actually asked for.
- **Pitch and business-case material.** `business/` holds the hackathon's problem framing, market sizing and go-to-market case — pitch content, not runtime configuration. It is not a dependency of this layer.

---

## 2. Architectural stance

This layer uses Clean Architecture (also called Ports & Adapters). The goal is simple:

> **Business rules must not depend on tools such as dlt, DuckDB, Postgres, MinIO or Dagster. Tools plug into the business rules through small interfaces called ports.**

This separation lets us test pipelines without external services and replace a tool without rewriting business logic.

### The four layers

```text
orchestration/  interface/api/    start a use case (Dagster, CLI, HTTP)
       │              │
       └──────┬───────┘
              ▼
application/         coordinates the steps (ingest, normalize, model, index, extract, evaluate)
       │
       ▼
domain/              defines data concepts, rules and ports
       ▲
       │ implements the ports
infrastructure/      talks to tools and external systems
```

`orchestration/` and `interface/api/` are peers: two thin edges onto the same application layer. Neither may contain transformation logic, and neither may be imported by the other.

A run follows the diagram from top to bottom:

1. **Orchestration starts it.**
2. **Application coordinates it.**
3. **Domain defines what is valid.**
4. **Infrastructure performs external I/O.**

| Layer | Main question | Contains | May depend on |
| --- | --- | --- | --- |
| `orchestration/` | Who starts the work, and when? | Dagster assets, schedules, partitions and CLI commands | Application |
| `interface/api/` | Who asks for work right now? | FastAPI routes, request/response DTOs, mappers | Application |
| `application/` | What steps does the use case perform? | The six pipelines in §7 and their supporting services | Domain; processing engines such as Polars and DuckDB |
| `domain/` | What do the data concepts mean, and what is valid? | Entities, policies and port definitions (§6) | Standard library, Pydantic and Arrow boundary types |
| `infrastructure/` | How do we talk to a specific external system? | dlt sources, database adapters, object storage and model adapters | Domain ports; any required SDK, driver or framework |

#### `orchestration/`: start the work on a schedule

This layer decides when and with which parameters a pipeline runs, for example: “normalize partition `2026-08-12` and retry twice.” It must not contain transformation logic.

A Dagster asset should normally do only two things: call an application pipeline and return its result as metadata.

#### `interface/api/`: start the work on request

The same rule, one layer over. A route handler resolves its arguments, calls one application function, and converts the result into a response DTO. It must not open a database connection, call a vendor SDK, or contain a transformation step.

**Route handlers return DTOs, never domain entities.** This is the rule [integration-architecture.md](../docs/architecture/integration-architecture.md) §4.1 states for every pod: a domain entity that leaks into a JSON response becomes a cross-service contract by accident, and then cannot be refactored. `interface/api/schemas.py` holds the response models; `interface/api/mappers.py` holds the conversion.

#### `application/`: coordinate the work

Each pipeline is one use case written as a clear sequence, for example:

1. Read a batch.
2. Validate it.
3. Separate valid and invalid rows.
4. Write both results.

Application code uses domain ports such as `Source` and `Sink`. It may use processing engines such as Polars or DuckDB, but it must not open a specific database connection or call a vendor SDK directly.

#### `domain/`: define meaning and rules

The domain is the stable core. It contains:

- **Entities and policies**, such as `DataContract`, `PartitionKey` and `QualityPolicy`.
- **Ports**, such as `Source` and `Sink`, which describe required capabilities without naming a tool.

Domain code is plain data and pure logic: it does not open files, run queries or use the network.

A practical test: if a rule cannot be unit-tested without a database, filesystem or orchestration framework, it probably does not belong in `domain/`.

#### `infrastructure/`: connect real tools

Infrastructure implements the domain ports with concrete tools. For example:

- `api_source.py` calls dlt.
- `pgvector_retriever.py` runs vector SQL.
- `fsspec_object_store.py` connects to MinIO or S3.

Infrastructure depends on the domain's port definitions. The domain never depends on infrastructure.

### Dependency inversion

The domain defines what it needs; infrastructure supplies it. Never the reverse.

```python
# Application knows only the ports.
def ingest(source: Source, sink: Sink, window: TimeWindow) -> RunStats:
    for batch in source.read(window, since=catalog.watermark(source.name)):
        sink.write(batch, partition=PartitionKey.from_window(window))

# Application must never contain tool-specific I/O such as:
dlt.pipeline(destination="duckdb").run(...)
duckdb.connect().execute("COPY ...")
psycopg.connect(...).cursor().execute(...)
```

`Source` is a `Protocol` (§6). The dlt import and calls belong in `infrastructure/sources/api_source.py`. This gives us:

1. **Fast tests.** Pass fake `Source` and `Sink` implementations; no Postgres, MinIO or network is needed (§16).
2. **Replaceable tools.** To replace dlt or pgvector, add another adapter that implements the same port. Application callers do not change.

Concrete adapters are connected to pipelines in one place: `orchestration/resources.py`, the composition root (§18). Everywhere else, application code sees only the port.

This indirection is justified because `data/` is a reusable platform expected to add sources and replace tools. It would be unnecessary for a one-off script that imports a single CSV.

### Hard boundaries

`data/domain/` must not import:

- ingestion or orchestration frameworks: `dlt`, `dagster`, `dbt`
- database or filesystem clients: `duckdb`, `psycopg`, `sqlalchemy`, `s3fs`, `fsspec`
- parsing or model libraries: `docling`, `fastembed`, `pymupdf`
- dataframe engines: `polars`, `pandas`

> **Use frameworks at the edges, not at the core.**

**Arrow exception:** domain ports may use `pyarrow`-backed types, such as `RecordBatch`, as a neutral boundary format (§6). They must not use `pl.DataFrame` or `pandas.DataFrame`; logic that needs those types belongs in `application/`.

### Keep orchestration thin

Dagster starts and monitors work; it does not perform the transformation.

```python
# Wrong: transformation logic is trapped inside Dagster.
@asset
def silver_orders(context):
    raw = pl.read_parquet(...)
    clean = raw.filter(...)
    context.log.info(...)
    return clean.write_parquet(...)

# Right: Dagster calls a plain application function.
@asset(partitions_def=daily)
def silver_orders(context, store: ObjectStore) -> MaterializeResult:
    stats = normalize_orders(store, partition=context.partition_key)
    return MaterializeResult(metadata=stats.as_dagster_metadata())
```

**Compliance check:** every function in `application/pipelines/` must be callable from a plain `pytest` test with no Dagster import and no FastAPI import. If it cannot, pipeline logic has leaked into an edge.

This check is what makes the two invocation modes of §1 possible at all. A pipeline that satisfies it can be called by a Dagster asset, an HTTP route, a CLI command or a test, and none of those callers knows about the others.

---

## 3. Medallion layering

Four layers. The first three are the standard medallion pattern; the fourth exists because this platform serves an agent, not only a dashboard.

```
                        EXTERNAL SOURCES
    CSV · Excel · JSON · REST API · Database · Documents · Media
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ BRONZE — raw, append-only, schema-on-read                   │
│ Mirrors the source exactly. Never edited, never deleted     │
│ before retention. Every future bug is fixable by            │
│ reprocessing from here instead of re-fetching.              │
│                                                             │
│  records/  Parquet, one prefix per dataset                  │
│  assets/   media and document blobs, byte-for-byte          │
└──────────────┬───────────────────────────┬──────────────────┘
               │ records                   │ asset blobs
               ▼                           ▼
     ┌──────────────────┐        ┌──────────────────────┐
     │ normalize (§7.2) │        │   extract (§7.6)     │
     │ Polars + Pandera │        │ ffmpeg → ASR → VLM   │
     └────────┬─────────┘        └──────────┬───────────┘
              │                             │
              ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│ SILVER — typed, deduplicated, schema-on-write               │
│ One table per entity. Contract enforced at write time.      │
│ PII tagged. Failures quarantined, not dropped.              │
│ Media derivations land here as ordinary typed rows.         │
└───────────────┬─────────────────────────┬───────────────────┘
                ▼                         ▼
┌───────────────────────────┐  ┌────────────────────────────┐
│ GOLD — modelled for       │  │ INDEX — chunks + vectors   │
│ consumption, stable       │  │ for retrieval. Rebuildable │
│ schema, SLA-backed        │  │ from Silver at any time.   │
└───────────┬───────────────┘  └────────────┬───────────────┘
            ▼                               ▼
    api.v1_* views (§11)        Retriever port (§12) · data API (§11.4)
            │                               │
      .NET backend                    agent/ layer
```

| Layer      | Physical store              | Format                   | Engine that writes it                        | Schema posture | Mutability          |
| ---------- | --------------------------- | ------------------------ | -------------------------------------------- | -------------- | ------------------- |
| Bronze     | Object storage (MinIO / S3) | Parquet + zstd           | dlt                                          | on read        | append-only         |
| Bronze     | Object storage `assets/`    | original bytes, unaltered | `ingest` / the upload path                  | none           | append-only         |
| Silver     | Object storage              | Parquet + zstd           | Polars                                       | on write       | partition overwrite |
| Silver     | Object storage `frames/`    | JPEG                     | `extract`                                    | none           | overwrite by asset  |
| Gold       | Postgres `gold` schema      | Postgres tables          | DuckDB + dbt, published by `publish_service` | on write       | MERGE by key        |
| Index      | Postgres `index` schema     | tables + `pgvector` HNSW | embed pipeline                               | on write       | upsert by chunk id  |
| Quarantine | Object storage              | Parquet + zstd           | Polars                                       | on read        | append-only         |

**Media is not a new layer.** A video is a blob in Bronze under exactly the rule §7.1 already states for documents: copied byte-for-byte, parsed later. Its derivations — transcript, frame captions, extracted signals — are ordinary typed rows in Silver, subject to the same contract, quarantine and partition rules as any other entity. Frame JPEGs sit beside them in object storage because a JPEG in a Parquet column helps nobody; the Silver row carries the path.

The reason this works without a special case is that `extract` produces **text and numbers**. Once a video has become a transcript and eight captions, every downstream layer is doing the work it already knew how to do.

**Bronze is not optional.** It is tempting to skip it when a pipeline reads one CSV. Don't. Bronze is what makes "we had a bug in the normalizer for three days" a fifteen-minute reprocess instead of a conversation about whether the source still has the data.

**Index is derived, never authoritative.** Deleting the whole `index` schema and rebuilding it from Silver must always be a safe operation. Nothing may be stored only in the index.

**Silver media derivations are expensive, so they are cached, not recomputed.** Rebuilding Silver from Bronze normally costs CPU. Rebuilding a transcript and eight captions costs a model call per asset, in money and in latency, and it depends on a network that may be unavailable exactly when it is needed. §7.6 therefore keys every derivation on the content hash of the blob plus the extractor version, so a re-run over unchanged input is free. This is §8's idempotency principle applied to a call rather than a partition, and it is the same mechanism that lets a pre-warmed set of assets survive a dead network.

---

## 4. Technology stack and physical topology

### The stack, end to end

§3 showed what each layer *means*; this shows how data actually moves through it, which pipeline moves it, and which tool does the work.

```mermaid
flowchart TB
    subgraph SRC["External sources — §7.1"]
        S1["CSV / JSON / Parquet"]
        S2["Excel"]
        S3["REST API"]
        S4["Database"]
        S5["Documents — PDF, DOCX, PPTX"]
        S6["Media — video, image, audio"]
    end

    ING(["<b>ingest</b><br/>dlt"])
    NORM(["<b>normalize</b><br/>Polars + Pandera"])
    EXT(["<b>extract</b><br/>ffmpeg → Transcriber<br/>→ FrameCaptioner"])
    MOD(["<b>model</b><br/>DuckDB + dbt"])
    IXP(["<b>index</b><br/>Docling + fastembed"])
    EVAL(["<b>evaluate</b><br/>scikit-learn<br/>labeled JSONL in git"])

    subgraph LAKE["Object storage — MinIO local, S3 / R2 / GCS cloud"]
        BRONZE[("Bronze records<br/>Parquet + zstd<br/>append-only")]
        BLOB[("Bronze assets<br/>original bytes<br/>append-only")]
        SILVER[("Silver<br/>Parquet + zstd<br/>contract enforced")]
        QUAR[("Quarantine<br/>rejected rows<br/>+ violation")]
    end

    subgraph PG["Postgres 16 + pgvector"]
        GOLD[("gold<br/>dim_* / fct_*")]
        IDX[("index<br/>chunks + HNSW vectors")]
        API[["api.v1_* views<br/>the contract surface"]]
        OPS[("ops<br/>watermarks, run log,<br/>quality violations")]
    end

    DAPI[["interface/api — :8002<br/>FastAPI, DTOs only"]]

    subgraph CONS["Consumers"]
        NET[".NET 8 backend"]
        AGENT["agent/ layer"]
    end

    S1 & S2 & S3 & S4 & S5 --> ING --> BRONZE
    S6 --> ING --> BLOB
    BRONZE --> NORM --> SILVER
    BLOB --> EXT --> SILVER
    NORM -.->|"rejected rows"| QUAR
    EXT -.->|"unparseable asset"| QUAR
    SILVER --> MOD --> GOLD
    SILVER --> IXP --> IDX
    BLOB -.->|"document blobs"| IXP
    ING -.->|"watermarks, run stats"| OPS

    GOLD --> API
    API -->|"SQL, read-only role"| NET
    IDX --> DAPI
    GOLD --> DAPI
    DAPI -->|"HTTP JSON — §11.4<br/>Retriever + Tool ports"| AGENT
    AGENT -.->|"POST /api/v1/assets<br/>request-time"| DAPI
    DAPI -.->|"calls the same<br/>pipeline functions"| EXT

    EVAL -.->|"measures"| IDX
    EVAL -.->|"measures"| GOLD
```

The six rounded nodes are the pipelines of §7, each labelled with the tool that implements it; cylinders are stores and the yellow boxes are the systems they live in. Solid arrows are the main data path, dashed ones are side paths — quarantine, document blobs, operational metadata, measurement, and the request-time edge.

Two things in this diagram are worth stating in words. **`interface/api` is not a data store and holds no state**: it reads Postgres and calls pipeline functions, nothing more. And **the dashed line from the API back to `extract`** is the request-time mode of §1 — the same function Dagster calls on a schedule, called by a route handler instead.

Dagster does not appear as a box because it is not in the data path: it schedules and monitors the pipelines, which is §13's subject.

### Stack decisions

| Concern | Tool | Specified in |
| --- | --- | --- |
| Ingestion adapters | dlt | §7.1 |
| Normalize engine | Polars | §7.2 |
| Frame contracts | Pandera | §9, §10 |
| Record contracts, JSON Schema export | Pydantic v2 | §9, §11 |
| SQL modelling | DuckDB + dbt-core | §7.3 |
| Object storage | MinIO local, S3 / R2 / GCS cloud, via `fsspec` | §4 |
| File format | Parquet + zstd | §3 |
| Serving store | Postgres 16 | §11 |
| Serving API | FastAPI + uvicorn, port `8002` | §11.4 |
| Document parsing | Docling, with `pymupdf4llm` as a fast path | §7.4 |
| Media decoding — frames, audio | `imageio-ffmpeg` driven by `subprocess` | §7.6 |
| Transcription | Gemini audio, behind the `Transcriber` port | §6, §7.6 |
| Frame captioning and on-screen text | Gemini vision, behind the `FrameCaptioner` port | §6, §7.6 |
| Embeddings | fastembed | §7.4 |
| Vector and lexical search | `pgvector` + `pg_trgm` + `unaccent` | §12 |
| Orchestration and quality gating | Dagster — assets, asset checks | §10, §13 |
| Evaluation metrics | scikit-learn | §7.5 |
| Logging | structlog | §13 |
| Packaging, lint, tests, config | uv, Ruff, pytest, pydantic-settings | §16, §18 |

**No local model weights.** Transcription and captioning are hosted calls, not bundled models. This keeps the container small and the build fast, at the cost of a hard network dependency on the path that matters most. That cost is paid down by the content-hash cache of §7.6 rather than by shipping a local model, and §17 records the trigger for reversing the decision. `tech-stack-evaluation.md` §16 argues it in full.

**No table format yet.** There is deliberately no Iceberg or Delta Lake here — plain Parquet partitions are enough while there is one writer per dataset and nothing needs `MERGE` or time travel. §17 records the trigger for adopting one.

Candidates considered, trade-offs and rejected alternatives are in [tech-stack-evaluation.md](tech-stack-evaluation.md); this table records only the outcome.

### Local — `infrastructure/docker-compose.yml`

```
┌──────────────────────────────────────────────────────────────┐
│  Developer laptop                                            │
│                                                              │
│  ┌────────────────┐        ┌──────────────────────────────┐  │
│  │  Dagster       │        │  MinIO                       │  │
│  │  (dagster dev) │───────▶│  bronze/ silver/ quarantine/ │  │
│  │  control plane │        │  S3 API on :9000             │  │
│  └───────┬────────┘        └──────────────┬───────────────┘  │
│          │                                │                  │
│          │  in-process compute            │ httpfs / s3fs    │
│          ▼                                ▼                  │
│  ┌────────────────┐        ┌──────────────────────────────┐  │
│  │ DuckDB         │        │  Postgres 16                 │  │
│  │ + Polars       │───────▶│  + pgvector + pg_trgm        │  │
│  │ (a file, not   │ publish│  gold · index · api · ops    │  │
│  │  a service)    │        │  :5432                       │  │
│  └────────────────┘        └──────────────┬───────────────┘  │
│                                           │                  │
│  ┌────────────────────────────────────────┴───────────────┐  │
│  │  data API — uvicorn :8002                              │  │
│  │  interface/api/  ·  reads Postgres, calls pipelines    │  │
│  └───────┬──────────────────────────────────┬─────────────┘  │
└──────────┼──────────────────────────────────┼────────────────┘
           │ HTTP JSON (§11.4)                │ SQL, read-only role
           ▼                                  ▼
      agent/ layer                     .NET 8 backend
```

Two containers (MinIO, Postgres) plus two processes (`dagster dev`, `uvicorn`). DuckDB and Polars are libraries — nothing to run, nothing to keep alive.

**The upload directory is a shared volume, not an HTTP transfer.** The .NET backend already writes uploaded media to `backend/wwwroot/uploads/`. That directory is mounted into the data container, and `POST /api/v1/assets` (§11.4) receives a *path*, never the bytes. Moving a 150 MB video through a second HTTP hop when both processes can see the same disk buys nothing and adds a timeout to the demo path.

### Cloud — the same code

Only the resource configuration changes. No pipeline code is aware of which column it is in.

| Local                    | Cloud                            | What changes                    |
| ------------------------ | -------------------------------- | ------------------------------- |
| MinIO on `:9000`         | S3 / R2 / GCS                    | `OBJECT_STORE_URL`, credentials |
| Postgres container       | Neon / Supabase / RDS            | `DATABASE_URL`                  |
| DuckDB in-process        | DuckDB in-process                | nothing                         |
| `dagster dev`            | Dagster OSS on a container / K8s | deployment manifest only        |
| `uvicorn` on `:8002`     | the same container, behind a proxy | nothing in code                |
| Mounted upload directory | a shared volume or an object-store prefix | `ASSET_ROOT`           |

**This is the whole reason `fsspec`-style URLs and a single `Settings` object are non-negotiable.** The moment a path is hard-coded to `/home/…` or `localhost`, the cloud path stops being free.

---

## 5. Directory structure

Mirrors `agent/` deliberately: an engineer who has read one layer can navigate the other.

```text
data/
│
├── domain/
│   ├── entities/
│   │   ├── dataset.py              # identity, owner, classification, retention
│   │   ├── record_batch.py         # Arrow-backed batch + provenance
│   │   ├── document.py             # ParsedDocument, DocumentBlob
│   │   ├── media_asset.py          # MediaAsset, FrameRef, Transcript,
│   │   │                           #   FrameAnnotation, AssetArtifacts
│   │   ├── chunk.py                # Chunk, EmbeddedChunk
│   │   ├── data_contract.py        # name, version, fields, semantics, SLA
│   │   ├── quality_report.py       # ValidationResult, Violation
│   │   └── run_stats.py            # rows in/out/rejected, bytes, duration
│   │
│   ├── value_objects/
│   │   ├── partition_key.py
│   │   ├── time_window.py
│   │   ├── watermark.py
│   │   ├── vector.py               # dimensions + model identity
│   │   ├── content_hash.py         # sha256 of a blob — the cache key (§7.6)
│   │   └── classification.py       # public | internal | confidential | pii
│   │
│   ├── ports/
│   │   ├── source.py
│   │   ├── sink.py
│   │   ├── object_store.py
│   │   ├── validator.py
│   │   ├── transformer.py
│   │   ├── document_parser.py
│   │   ├── transcriber.py          # audio  → Transcript
│   │   ├── frame_captioner.py      # frames → FrameAnnotation
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── retriever.py
│   │   └── catalog.py              # watermarks, run log
│   │
│   └── policies/
│       ├── quality_policy.py       # block | warn | quarantine
│       ├── partition_policy.py
│       ├── retention_policy.py
│       └── classification_policy.py
│
├── application/
│   ├── pipelines/
│   │   ├── ingest.py               # Source        → Bronze
│   │   ├── normalize.py            # Bronze        → Silver
│   │   ├── extract.py              # Bronze assets → Silver  (§7.6)
│   │   ├── model.py                # Silver        → Gold
│   │   ├── index.py                # Silver/docs   → Index
│   │   └── evaluate.py             # cases         → metrics + report
│   │
│   └── services/
│       ├── quality_service.py      # runs validation, applies QualityPolicy
│       ├── contract_service.py     # load, compare, export JSON Schema
│       ├── retrieval_service.py    # fuses lexical + dense legs
│       ├── asset_service.py        # read-through cache over extract (§7.6)
│       └── publish_service.py      # Gold → Postgres, MERGE by key
│
├── infrastructure/
│   ├── sources/
│   │   ├── file_source.py          # dlt filesystem: csv, jsonl, parquet
│   │   ├── excel_source.py         # custom — see §7.1
│   │   ├── api_source.py           # dlt rest_api
│   │   ├── database_source.py      # dlt sql_database
│   │   └── mock_source.py          # for unit tests
│   │
│   ├── storage/
│   │   ├── fsspec_object_store.py  # MinIO / S3 / local, one adapter
│   │   ├── object_store_sink.py    # Sink over ObjectStore (bronze, silver)
│   │   ├── duckdb_engine.py
│   │   └── postgres_sink.py        # Sink into Postgres (gold, index)
│   │
│   ├── parsing/
│   │   ├── docling_parser.py
│   │   └── pymupdf_parser.py       # fast path for text-only PDF
│   │
│   ├── media/
│   │   └── ffmpeg.py               # plain functions, no port — see §6
│   │
│   ├── asr/
│   │   ├── gemini_transcriber.py
│   │   └── mock_transcriber.py     # deterministic, for tests
│   │
│   ├── vision/
│   │   ├── gemini_captioner.py
│   │   ├── byteplus_captioner.py   # OpenAI-compatible base_url swap
│   │   └── mock_captioner.py       # deterministic, for tests
│   │
│   ├── chunking/
│   │   └── docling_chunker.py
│   │
│   ├── embedding/
│   │   ├── fastembed_embedder.py
│   │   ├── api_embedder.py
│   │   └── mock_embedder.py        # deterministic, for tests
│   │
│   ├── retrieval/
│   │   ├── pgvector_retriever.py   # dense leg
│   │   ├── lexical_retriever.py    # pg_trgm + FTS leg
│   │   └── hybrid_retriever.py     # RRF fusion
│   │
│   ├── validation/
│   │   └── pandera_validator.py
│   │
│   └── catalog/
│       └── postgres_catalog.py     # ops.ingestion_watermark, ops.run_log
│
├── orchestration/                  # Dagster — the scheduled edge
│   ├── definitions.py              # the single Definitions object
│   ├── resources.py                # composition root (§18)
│   ├── partitions.py
│   ├── schedules.py
│   ├── asset_checks.py
│   └── assets/
│       ├── bronze.py
│       ├── silver.py
│       ├── gold.py
│       ├── index.py
│       └── evaluation.py
│
├── interface/                      # FastAPI — the request-time edge
│   └── api/
│       ├── app.py                  # the ASGI app, lifespan, health
│       ├── routes.py               # the four endpoints of §11.4
│       ├── schemas.py              # response DTOs — never domain entities
│       └── mappers.py              # domain entity → DTO
│
├── transformations/                # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/                # stg_<source>__<entity>
│       ├── intermediate/           # int_<entity>__<verb>
│       └── marts/                  # dim_<entity>, fct_<event>
│
├── contracts/
│   ├── pydantic/                   # record-level models
│   ├── pandera/                    # frame-level schemas
│   └── jsonschema/                 # GENERATED — consumed by .NET (§11)
│
├── evaluation/
│   ├── datasets/                   # labeled cases, JSONL, in git
│   ├── metrics/
│   ├── runners/
│   └── reports/                    # GENERATED
│
├── config/
│   └── settings.py                 # the single Settings object
│
├── observability/
│   ├── logging.py
│   └── tracing.py
│
└── tests/
    ├── unit/                       # no network, no DB, mock adapters
    ├── integration/                # real DuckDB, real Postgres
    ├── e2e/                        # one partition through every pipeline
    └── fixtures/
```

---

## 6. The ports

### What is a port?

A **port** is a small interface that describes what the application needs without choosing a specific tool. For example, the application needs “something that can read records,” but it should not care whether those records come from a CSV file, an API or a database.

In this project, ports are written as Python `Protocol` classes.

### What is a `Protocol` class?

`Protocol` comes from Python's `typing` module. It lists the attributes and methods an object must provide. A concrete class satisfies the protocol by having the same shape; it does not need to inherit from the protocol.

```python
from typing import Iterator, Protocol


class Source(Protocol):
    @property
    def name(self) -> str: ...

    def read(self, window: TimeWindow, since: Watermark | None) -> Iterator[RecordBatch]: ...


# This class satisfies Source because it provides name and read().
# It does not need to write "class CsvSource(Source)".
class CsvSource:
    @property
    def name(self) -> str:
        return "orders_csv"

    def read(self, window: TimeWindow, since: Watermark | None) -> Iterator[RecordBatch]:
        yield from read_csv_batches("orders.csv")


def ingest(source: Source, window: TimeWindow) -> None:
    for batch in source.read(window=window, since=None):
        process(batch)


ingest(CsvSource(), window)  # Accepted because CsvSource matches Source.
```

This is called **structural typing**: compatibility is based on what an object can do, not what it inherits from.

The roles are:

- **Port:** the required behavior, such as `Source`.
- **Adapter:** a concrete implementation, such as `CsvSource`, `ApiSource` or `MockSource`.
- **Application pipeline:** accepts the port and works with any matching adapter.

Use a port only at a boundary where implementations are expected to change or where a fake implementation is useful in tests. Do not create a `Protocol` for every class (see the agent standard §4).

### Port definitions

```python
from typing import Protocol, Iterator, Sequence, Mapping


class Source(Protocol):
    """Reads records from outside the platform. One adapter per source type."""

    @property
    def name(self) -> str: ...

    def read(self, window: TimeWindow, since: Watermark | None) -> Iterator[RecordBatch]: ...


class Sink(Protocol):
    """Writes a batch to a layer. Must be idempotent for a given partition."""

    def write(self, batch: RecordBatch, partition: PartitionKey) -> RunStats: ...


class ObjectStore(Protocol):
    """The only way the layer touches object storage. Local, MinIO and S3
    are all the same adapter with a different URL."""

    def read_parquet(self, path: str) -> RecordBatch: ...
    def write_parquet(self, path: str, batch: RecordBatch) -> int: ...
    def list(self, prefix: str) -> list[str]: ...
    def delete_prefix(self, prefix: str) -> int: ...   # partition overwrite (§8)


class Validator(Protocol):
    """Checks a batch against a contract. NEVER raises on bad data --
    it returns a report and lets QualityPolicy decide (§10)."""

    def validate(self, batch: RecordBatch, contract: DataContract) -> ValidationResult: ...


class Transformer(Protocol):
    """A named, pure step in the normalize pipeline."""

    @property
    def name(self) -> str: ...

    def apply(self, batch: RecordBatch) -> RecordBatch: ...


class DocumentParser(Protocol):
    def parse(self, blob: DocumentBlob) -> ParsedDocument: ...
    def supports(self, media_type: str) -> bool: ...


class Transcriber(Protocol):
    """Speech in an audio file becomes text. One hosted or local
    implementation at a time; a mock keeps the unit tier offline."""

    @property
    def model_id(self) -> str: ...

    async def transcribe(self, audio_path: str, language: str | None = None) -> Transcript: ...


class FrameCaptioner(Protocol):
    """Describes sampled frames: a caption, any on-screen text, and
    whatever structured signals the caller's prompt asks for.

    Takes the whole list of frames, not one at a time -- a single
    batched call per asset is both cheaper and the reason §7.6 fits
    inside a request-time budget."""

    @property
    def model_id(self) -> str: ...

    async def caption(
        self, frames: Sequence[FrameRef], instruction: str
    ) -> list[FrameAnnotation]: ...


class Chunker(Protocol):
    def chunk(self, document: ParsedDocument) -> list[Chunk]: ...


class Embedder(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[Vector]: ...


class Retriever(Protocol):
    """MUST stay structurally compatible with agent/domain/ports/retriever.py --
    see §12.3. This is the one port shared across two layers."""

    async def retrieve(
        self, query: str, top_k: int, filters: Mapping[str, object] | None = None
    ) -> list[RetrievedChunk]: ...


class Catalog(Protocol):
    """Operational metadata. Watermarks live here, never on local disk."""

    def watermark(self, dataset: str) -> Watermark | None: ...
    def commit(self, dataset: str, watermark: Watermark, stats: RunStats) -> None: ...
```

### Adapter table

| Port              | Adapters                                                                      | Notes                                                          |
| ----------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `Source`          | `file_source`, `excel_source`, `api_source`, `database_source`, `mock_source` | §7.1 maps these to the required source types                   |
| `Sink`            | `object_store_sink`, `postgres_sink`                                          | both idempotent per partition                                  |
| `ObjectStore`     | `fsspec_object_store`                                                         | one adapter covers local, MinIO, S3, R2, GCS                   |
| `Validator`       | `pandera_validator`                                                           |                                                                |
| `DocumentParser`  | `docling_parser`, `pymupdf_parser`                                            | dispatch on `supports()`                                       |
| `Transcriber`     | `gemini_transcriber`, `mock_transcriber`                                      | `faster-whisper` is the named local successor (§17)            |
| `FrameCaptioner`  | `gemini_captioner`, `byteplus_captioner`, `mock_captioner`                    | BytePlus is a `base_url` swap if it stays OpenAI-compatible    |
| `Chunker`         | `docling_chunker`                                                             |                                                                |
| `Embedder`        | `fastembed_embedder`, `api_embedder`, `mock_embedder`                         | `mock_embedder` is deterministic so retrieval tests are stable |
| `Retriever`       | `pgvector_retriever`, `lexical_retriever`, `hybrid_retriever`                 | `hybrid_retriever` composes the other two                      |
| `Catalog`         | `postgres_catalog`                                                            |                                                                |

`mock_source`, `mock_embedder`, `mock_transcriber` and `mock_captioner` are not an afterthought — they are what make the unit tier of §16 possible. With the media work behind ports, `extract` is fully testable with no ffmpeg binary, no API key and no network.

### What deliberately has no port: ffmpeg

Frame sampling and audio extraction live in `infrastructure/media/ffmpeg.py` as plain functions — `extract_frames(path) -> list[FrameRef]` and `extract_audio(path) -> str` — with no `Protocol` over them.

This follows the rule stated above rather than breaking it. A port earns its place where implementations are expected to change or where a fake is useful in a test. Neither applies: there will be one ffmpeg implementation, and a test that needs frames is better served by a directory of pre-extracted JPEGs than by a fake decoder. Adding a `MediaExtractor` protocol here would be an interface with one implementation forever, which is the exact anti-pattern the agent standard §4 names.

The line between the two decisions is worth stating, because it is the useful part: **decoding is deterministic and local, so it needs no seam; understanding is a model call, so it needs one.**

---

## 7. The six pipelines

Mapping to the required `Source → Ingestion → Validation → Normalization → Storage → Feature/Analytics` flow:

| Required stage      | Pipeline                                                                    |
| ------------------- | --------------------------------------------------------------------------- |
| Source, Ingestion   | `ingest` (§7.1)                                                             |
| Validation          | the Bronze→Silver boundary in `normalize`, plus asset checks (§10)          |
| Normalization       | `normalize` (§7.2) for records, `extract` (§7.6) for media                  |
| Storage             | the layers of §3, written by each pipeline's sink                           |
| Feature / Analytics | `model` (§7.3), and `index` (§7.4) for retrieval                            |

`extract` sits in the same position as `normalize` — both take one Bronze partition and produce contract-conforming Silver rows. They differ only in what the input bytes happen to be.

### 7.1 `ingest` — Source → Bronze

|                  |                                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------- |
| **Input**        | one external source, one time window                                                      |
| **Output**       | Parquet files under `bronze/<source>/<dataset>/ingested_date=…/`                          |
| **Engine**       | dlt                                                                                       |
| **Partition**    | `ingested_date` (daily) — the date we _received_ it, not the date it happened             |
| **Idempotency**  | append-only + `run_id` in the filename; duplicates are removed in `normalize`, never here |
| **Failure mode** | fail the partition loudly; never partially commit a window                                |

**Why `ingested_date` and not `event_date`:** Bronze mirrors an arrival, and arrivals are the only thing the ingestion step actually knows. Repartitioning by event time is a Silver concern, where late data can be handled deliberately.

**The six required source types:**

| Source type  | Adapter           | Mechanism                                                                                                                                                                                             |
| ------------ | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CSV          | `file_source`     | dlt `readers()` → `read_csv`, or `read_csv_duckdb` for files too large for memory                                                                                                                     |
| **Excel**    | `excel_source`    | **Custom.** dlt ships no Excel reader — `filesystem()` pipes file items into a small transformer using `polars.read_excel` (calamine engine via `fastexcel`). Verified: not covered by dlt built-ins. |
| JSON / JSONL | `file_source`     | dlt `readers()` → `read_jsonl`; nested objects are normalized into child tables automatically                                                                                                         |
| REST API     | `api_source`      | dlt `rest_api_source` — declarative pagination, auth and incremental cursor                                                                                                                           |
| Database     | `database_source` | dlt `sql_database` / `sql_table`; use the `pyarrow` backend for stable destination types                                                                                                              |
| Documents    | see §7.4          | Docling; binary blobs land in Bronze unaltered, parsing happens in `index`                                                                                                                            |
| **Media**    | `asset_source`    | Video, image and audio blobs land in Bronze unaltered under `assets/`; derivation happens in `extract` (§7.6). Files arriving through the upload path are registered by reference, not re-copied.     |

**Documents and media land as blobs.** A PDF or an MP4 is copied byte-for-byte into Bronze and processed later. Processing is code, code has bugs, and the point of Bronze is that a parser bug costs a reprocess rather than a re-download. For media the argument is stronger still: the re-fetch may be impossible, because the user uploaded the file once and moved on.

**Uploaded media is registered, not copied.** The .NET backend writes the file into the shared upload directory (§4); `ingest` records the asset — its id, path, content hash, media type and arrival time — and treats that directory as a Bronze prefix. Copying a 150 MB file to prove a point about layering would double the disk and add a failure mode. What matters is that the bytes are never mutated afterwards, and that holds either way.

**Incremental loading.** Where the source supports a cursor, `ingest` reads the last watermark from `Catalog`, requests only newer rows, and commits the new watermark _only after_ the write succeeds. Full reloads are acceptable while a dataset is small; §17 gives the trigger to stop doing that.

### 7.2 `normalize` — Bronze → Silver

|                  |                                                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------------------- |
| **Input**        | one Bronze partition (or a range, for backfill)                                                               |
| **Output**       | `silver/<entity>/event_date=…/`                                                                               |
| **Engine**       | Polars (lazy), Pandera for the contract                                                                       |
| **Partition**    | `event_date`, derived from a business timestamp                                                               |
| **Idempotency**  | delete-prefix-then-write for the target partition, in that order, one partition at a time                     |
| **Failure mode** | rows failing the contract go to `quarantine/`; the partition still publishes unless `QualityPolicy` blocks it |

Steps, in order:

1. Read the Bronze partition — **explicit column projection, never `SELECT *`**.
2. Cast to the contract's types. A cast failure is a violation, not an exception.
3. Deduplicate on the business key, keeping the latest by source timestamp.
4. Apply named `Transformer`s (trim, normalize case, parse dates, unify units).
5. Tag classification per `ClassificationPolicy` — PII is marked here, at landing, not later.
6. Validate with Pandera (`lazy=True`, so one pass reports every violation).
7. Split: valid rows → Silver, invalid rows → quarantine with the violation attached.
8. Write, then record stats through `Catalog`.

**Why explicit projection is a rule and not a preference:** `SELECT *` couples Silver to the source's column order and makes a new upstream column change Silver's schema silently. Naming columns turns an upstream addition into a visible, reviewable decision.

### 7.3 `model` — Silver → Gold

|                  |                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------- |
| **Input**        | Silver Parquet on object storage                                                         |
| **Output**       | `gold` schema tables in Postgres, then `api.v1_*` views (§11)                            |
| **Engine**       | DuckDB reading Silver via `httpfs`; models defined in dbt (`dbt-duckdb`)                 |
| **Partition**    | usually none — Gold marts are rebuilt whole while they are small                         |
| **Idempotency**  | rebuild in DuckDB, then `MERGE` into Postgres on the business key inside one transaction |
| **Failure mode** | fail before publishing; Postgres keeps the previous good version                         |

The publish step is deliberately separate from the transform step. DuckDB does the joins and aggregation over Parquet at object-storage speed; `publish_service` then moves a finished, small result into Postgres where the backend can serve it with an index. One SQL dialect for modelling, one narrow write path to production.

> **Alternative, for later:** point dbt at Postgres directly (`dbt-postgres`) and drop the publish step. Correct once Gold outgrows "rebuild the whole mart" and you need incremental models in the serving database. Not now — the publish step is what keeps a half-built mart from ever being visible to the backend.

**Modelling choice.** Default to a star schema (`dim_*` / `fct_*`) once there are multiple consumers, and to one wide table when there is exactly one consumer and no reuse. State the grain of every fact table in its dbt model description — the grain is the modelling decision that is expensive to change later.

### 7.4 `index` — Silver + documents → Index

|                  |                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------- |
| **Input**        | document blobs from Bronze; text columns from Silver                                  |
| **Output**       | `index.chunk` + `index.embedding` in Postgres                                         |
| **Engine**       | Docling → `Chunker` → `Embedder` → pgvector                                           |
| **Partition**    | by source document                                                                    |
| **Idempotency**  | chunk id is a content hash; upsert on `(document_id, chunk_index, embedder_model_id)` |
| **Failure mode** | an unparseable document goes to the DLQ with its error; the run continues             |

Steps: resolve parser via `supports()` → parse → chunk → embed in batches → upsert.

**`embedder_model_id` is part of the key, not metadata.** Embeddings from two different models are not comparable, and mixing them silently degrades retrieval in a way that is very hard to notice and very easy to prevent. Changing the embedding model means a new index generation and a rebuild — cheap, because Index is derived (§3).

**A document that fails to parse is a data quality event**, not a crash. It lands in the DLQ, increments a counter, and shows up in the quality report — the same treatment as a malformed row.

### 7.5 `evaluate` — labeled cases → metrics + report

|                  |                                                                   |
| ---------------- | ----------------------------------------------------------------- |
| **Input**        | `evaluation/datasets/*.jsonl`, versioned in git                   |
| **Output**       | a metrics table + a Markdown report in `evaluation/reports/`      |
| **Engine**       | scikit-learn for the metrics, a template for the report           |
| **Idempotency**  | pure function of (dataset version, pipeline version, config)      |
| **Failure mode** | a metric below its configured threshold fails the check — visibly |

The harness runs at least two arms — a **baseline** and the **pipeline under test** — over the same cases, and reports precision, recall, F1 and the confusion matrix for each, with `n` stated.

Three properties make this worth building as a pipeline instead of a notebook:

1. **Reproducible.** The report names the dataset version, the pipeline version and the config that produced it.
2. **Re-run on change.** It is an asset with upstream dependencies, so it re-runs when they change rather than when someone remembers.
3. **Comparable.** Two arms over identical cases is the only honest way to claim an improvement.

**Labeled cases live in git, as JSONL.** Not in a database, not in a spreadsheet. Labels are source code: they get reviewed, they get diffed, and a change to them must be as visible as a change to the code they measure.

### 7.6 `extract` — Bronze media → Silver derivations

|                  |                                                                                                    |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| **Input**        | one media blob in Bronze (video, image or audio)                                                   |
| **Output**       | `silver/asset_artifact/event_date=…/`, plus frame JPEGs under `silver/frames/<asset_id>/`          |
| **Engine**       | `imageio-ffmpeg` for decoding, then the `Transcriber` and `FrameCaptioner` ports                   |
| **Partition**    | by asset — one asset is the unit of work                                                           |
| **Idempotency**  | keyed on `sha256(blob) + extractor_version`; a repeat run over unchanged input performs no model call |
| **Failure mode** | an undecodable or unanswerable asset goes to quarantine with its error; the run continues           |

Steps, in order:

1. Read the blob and compute its content hash.
2. **Look up `(content_hash, extractor_version)`. On a hit, return the stored artifacts and stop.**
3. Sample frames — `fps=1/2`, longest side 512, capped at 8. An image is its own single frame.
4. Extract audio as mono 16 kHz WAV. Skip for a still image.
5. Transcribe the audio through the `Transcriber` port.
6. Caption all frames in **one** batched call through the `FrameCaptioner` port, asking for a caption, any on-screen text, and the structured signals the current business domain needs.
7. Validate against the `asset_artifact` contract and write Silver, quarantining what fails.
8. Record the derivation against its cache key, then record stats through `Catalog`.

**Step 2 is the load-bearing one.** It is what makes `extract` cheap to re-run, safe to call from a request handler, and survivable when the model provider is unreachable — an asset processed once stays processed. It also makes the frame cap meaningful: eight frames is one request, so an asset costs a bounded, known amount exactly once.

**`extract` returns text and numbers, and that is the whole design.** A transcript is text. A caption is text. On-screen text is text. Cut count and face presence are numbers. Everything downstream — contracts, quarantine, chunking, embedding, retrieval, SQL — is the machinery this platform already had, and none of it learns that a video existed. The alternative, carrying pixels down the stack, would have required a second embedding space, a second index and a second retrieval path; §12.4 records what that choice costs and where it breaks.

**The extractor version is part of the key, not metadata.** It covers the prompt, the frame sampling parameters and the model ids. Changing any of them produces different artifacts, and artifacts from two different extractor versions must never be silently mixed — the same argument §7.4 makes for `embedder_model_id`. Bumping it invalidates the cache deliberately and costs a rebuild, which is affordable because Silver is derived from Bronze and Bronze still has the bytes.

**Frame count is configuration, not a constant.** Eight is the default in `Settings`, chosen because it is one request and enough to see a 15-second video's structure. A two-minute walkthrough will want more. A hard-coded `8` in the pipeline breaks the first time someone uploads something longer, and breaks quietly.

---

## 8. Idempotency and recovery

**Running any pipeline twice produces the same result as running it once.** Everything below exists to make that true, because it is what makes retries, backfills and recovery ordinary instead of frightening.

| Layer  | Mechanism                                        | Why this one                                          |
| ------ | ------------------------------------------------ | ----------------------------------------------------- |
| Bronze | append-only, `run_id` in the filename            | never mutate raw data; duplicates die in Silver       |
| Silver | `delete_prefix(partition)` then write            | one partition is the unit of atomicity                |
| Silver derivations | lookup on `content_hash + extractor_version` | a model call is expensive and may be unavailable |
| Gold   | `MERGE` on business key, one transaction         | consumers must never see a half-built mart            |
| Index  | upsert on content-hash chunk id                  | re-embedding the same text is a no-op                 |

The third row generalises the others. Everywhere else in this table, idempotency protects correctness — running twice must not duplicate rows. For a derivation it also protects cost and availability, because the second run would otherwise re-spend money and re-depend on a network. Same principle, one more reason.

### Rules

1. **One partition per run.** A run that writes two partitions cannot be retried safely.
2. **Delete then write, never write then delete.** A crash between the two leaves a partition empty, which a freshness check catches. The reverse order leaves duplicates, which nothing catches.
3. **Watermarks live in `ops.ingestion_watermark`.** Never on local disk — the disk is not the durable part of the system.
4. **Commit the watermark after the write succeeds.** In that order, a crash re-reads data; in the other order, a crash loses it. Re-reading is recoverable, losing is not.
5. **Never overwrite a partition a consumer is reading.** Delete-then-write inside a single partition prefix is acceptable because consumers read whole partitions; a live table overwrite is not.
6. **Never catch a broad exception and continue.** A bare `except Exception: pass` in a pipeline is silent data loss discovered hours later. Bad _records_ are routed to quarantine deliberately; bad _runs_ fail.

### Backfill

A backfill is a partition range re-run through the ordinary code path. There is no backfill script, and that is the point — a separate backfill path is a second implementation that will drift from the first.

```
# conceptually
for partition in range(start, end):
    normalize(partition)   # same function the schedule calls
```

**If replaying the last 30 days is not routine, the design is not finished.**

---

## 9. Data contracts and schema evolution

### One source of truth, two shapes

| Shape    | Tool                                  | Used for                                                   |
| -------- | ------------------------------------- | ---------------------------------------------------------- |
| Record   | Pydantic v2 (`contracts/pydantic/`)   | API payloads, config, anything crossing a service boundary |
| Frame    | Pandera (`contracts/pandera/`)        | Silver and Gold table schemas                              |
| Exported | JSON Schema (`contracts/jsonschema/`) | **generated**, consumed by the .NET backend (§11)          |

`contracts/jsonschema/` is generated output committed to git. Committing it means a contract change shows up as a reviewable diff, and the .NET side can regenerate DTOs from a file rather than from a conversation.

### A contract states more than a schema

```yaml
name: orders
version: 2.1.0
owner: data-engineering
classification: internal
fields:
  order_id: { type: string, nullable: false, unique: true }
  customer_id: { type: string, nullable: false, classification: pii }
  amount: { type: decimal, nullable: false, min: 0 }
  ordered_at: { type: timestamp, nullable: false, timezone: utc }
semantics:
  grain: one row per order
  amount: gross, in minor units, before discount
sla:
  freshness: 24h
  completeness: 0.99
```

Schema alone does not stop a consumer misreading `amount`. Semantics and SLA are the part that does.

### Evolution rules

| Change                         | Compatibility | Allowed                                                    |
| ------------------------------ | ------------- | ---------------------------------------------------------- |
| Add a nullable column          | backward      | yes, patch version                                         |
| Add a required column          | breaking      | new minor, with a default during a grace period            |
| Widen a type (`int32`→`int64`) | backward      | yes                                                        |
| Narrow a type                  | breaking      | new major                                                  |
| Rename a column                | breaking      | add the new one, dual-write, remove after the grace period |
| Remove a column                | breaking      | new major, only after consumers confirm                    |

**Additive by default. Semver. A breaking change is a new version with a grace period, never an edit in place.**

### Two prohibitions worth stating separately

- **Never silently drop an unknown column.** A producer adding a field must produce a visible event — a logged drift record and a warning check — not silence. Silence here is invisible data loss.
- **Never couple Gold to Bronze column names.** Silver exists to absorb source renames. If a Bronze rename reaches Gold, the layer boundary was skipped.

Bronze is schema-on-read: dlt infers and evolves the schema and records what changed. Silver and Gold are schema-on-write: the contract is enforced at write time and violations are quarantined.

---

## 10. Data quality

### Audit → Write → Audit → Publish

Validate before writing, validate what was written, and only then make it visible.

```
Bronze ──▶ [structural checks] ──▶ Silver staging ──▶ [full suite] ──▶ Silver published
                    │                                       │
                    ▼                                       ▼
              drift record                              quarantine
```

### Where each check runs

| Layer  | Checks                                                                                         | Cost             |
| ------ | ---------------------------------------------------------------------------------------------- | ---------------- |
| Bronze | is it readable, non-empty, roughly the expected volume, did the schema drift                   | cheap, every run |
| Bronze assets | does the file decode, is it under the size limit, is the media type one we handle        | cheap, every run |
| Silver | the full contract — types, nullability, uniqueness, ranges, referential integrity              | the main suite   |
| Silver derivations | frame count matches what was requested, transcript is not empty for a video with an audio track, every annotation has a caption | per asset |
| Gold   | dbt tests — `unique`, `not_null`, `relationships`, `accepted_values`, plus business assertions | on rebuild       |
| Index  | chunk count per document non-zero, embedding dimensions match `Embedder.dimensions`            | on rebuild       |

**An empty transcript is a finding, not a fact.** A silent video legitimately has none; a video with an audio track that transcribes to nothing means the audio extraction failed or the model refused. Distinguishing the two costs one check and prevents a whole class of confidently wrong analysis downstream.

**Running checks only on Gold is the classic mistake**: by the time Gold fails, everything upstream is already contaminated and you cannot tell how far back.

### QualityPolicy — a domain decision

Validation produces a report. What to _do_ about the report is a policy, and it belongs in the domain where it can be tested without a database.

```python
class QualityPolicy(Protocol):
    def decide(self, result: ValidationResult) -> QualityDecision: ...
    # QualityDecision: PUBLISH | PUBLISH_WITH_WARNING | QUARANTINE_AND_PUBLISH | BLOCK
```

Default posture:

| Situation                                          | Decision                             |
| -------------------------------------------------- | ------------------------------------ |
| No violations                                      | `PUBLISH`                            |
| Row-level violations under the threshold           | `QUARANTINE_AND_PUBLISH`             |
| Row-level violations over the threshold            | `BLOCK` — something changed upstream |
| A schema-level violation (missing required column) | `BLOCK`                              |
| A freshness miss with valid data                   | `PUBLISH_WITH_WARNING`               |

**Thresholds live in `Settings`, never in code.** A hard-coded `if bad_rows > 100` breaks the first week real volume grows past it, and it breaks by blocking a healthy pipeline.

### Quarantine, not drop

Failed rows go to `quarantine/<entity>/event_date=…/` with the violation, the contract version and the run id attached, and are counted in `ops.quality_violations`. Reprocessing a fixed quarantine batch is an ordinary `normalize` run over a different prefix.

Dropping rows is indistinguishable from never having received them. Quarantine keeps the difference visible.

### Wiring to the orchestrator

Quality gates are expressed as Dagster **asset checks** — `@asset_check(blocking=True)` when a failure must stop downstream materialization, non-blocking (the default) when it should only warn. The decision lives with the asset and shows up in the UI next to it, so nobody has to go looking for whether the data is trustworthy.

---

## 11. The serving contracts

This layer has two consumers with incompatible needs, and therefore two surfaces.

| Consumer | Reads | Surface | Specified in |
| --- | --- | --- | --- |
| .NET 8 backend | rows | `api.v1_*` views over SQL | §11.1–§11.3 |
| `agent/` layer | documents and asset artifacts | HTTP JSON on `:8002` | §11.4 |

**Version 1.0 said "no Python service sits between them," and that sentence stays true where it was aimed.** It was written when the backend was the only consumer, and it still governs that path: nothing sits between .NET and Postgres. It was never a claim that the data layer may not expose an API — and the agent layer cannot use the SQL surface, because [agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) forbids `domain/` from importing a database driver, and [integration-architecture.md](../docs/architecture/integration-architecture.md) forbids pods from sharing code. HTTP is the only remaining option, and it is the one that document already specifies.

Scoped precisely: **Postgres is the contract surface for the .NET backend. The FastAPI process serves the agent, and sits between the agent and Postgres — never between the backend and Postgres.**

### 11.1 The backend's contract

The backend is .NET 8 + FastEndpoints and cannot import Python. The data layer writes; the backend reads SQL.

### 11.2 Versioned views are the actual interface

```
gold.dim_customer          ← internal, refactor freely
gold.fct_order             ← internal, refactor freely
        │
        ▼
api.v1_customer_overview   ← THE CONTRACT. .NET reads only this.
api.v1_order_daily         ← additive changes only
```

| Rule                                                   | Reason                                                               |
| ------------------------------------------------------ | -------------------------------------------------------------------- |
| The backend reads only the `api` schema                | table refactors stop being cross-team events                         |
| `api` views are additive within a major version        | a new column never breaks a consumer                                 |
| A breaking change ships as `api.v2_*` alongside `v1_*` | the backend migrates on its own schedule                             |
| `v1_*` is dropped only after the backend confirms      | coordination happens once, at removal                                |
| The backend's DB role has `SELECT` on `api` only       | least privilege, and it makes the boundary real rather than advisory |

The last row is what makes this hold. A convention the backend _could_ bypass eventually gets bypassed at 2am; a permission it _cannot_ bypass stays a boundary.

### 11.3 Keeping DTOs in sync

`contract_service` exports every `api.v1_*` shape to `contracts/jsonschema/`. The .NET side generates or hand-writes DTOs against those files. A contract change is then a reviewable diff in a shared file rather than a runtime surprise.

### Postgres schemas

| Schema  | Contents                                       | Backend access |
| ------- | ---------------------------------------------- | -------------- |
| `gold`  | published marts                                | none           |
| `index` | chunks, embeddings                             | none           |
| `asset` | asset registry, derivations, the extract cache | none           |
| `api`   | versioned views                                | `SELECT`       |
| `ops`   | watermarks, run log, quality violations        | none           |

Silver deliberately does not appear: it stays in object storage. Postgres holds only what is served or operational, which keeps the serving database small and fast.

### 11.4 The data service — the agent's contract

A thin FastAPI application on port `8002`, matching the pod topology in [integration-architecture.md](../docs/architecture/integration-architecture.md) §3. It holds no state, owns no data, and does two things: read Postgres, and call pipeline functions.

**Four handlers. The response shape is dictated, not chosen.** `agent/infrastructure/retrieval/http_json_retriever.py` already exists as a generic REST-JSON adapter for the agent's `Retriever` port, with an injectable response mapper. Emitting what it already parses means the agent side needs a four-line mapping function and no new adapter, no new port, and no change under `agent/domain/`.

```
GET  /health
     → {"status":"ok","db":true,"assets":12}

GET  /api/v1/data/query?q=<text>&top_k=5
POST /api/v1/data/query          {"q":"<text>","top_k":5}
     → {"items":[
          {"id":     "asset:VID-20260821-0007:frame:07",
           "text":   "Frame at 7s: hand holding the product, on-screen text 'GIAM 50%'",
           "score":  0.83,
           "metadata":{"asset_id":"VID-20260821-0007",
                       "kind":"frame_caption",
                       "t_seconds":7,
                       "source_uri":"s3://…/frames/VID-20260821-0007/07.jpg"}}
        ]}

POST /api/v1/assets              {"uri":"/uploads/videos/x.mp4","kind":"video"}
     → {"asset_id":"VID-20260821-0007","status":"ready","cached":false,
        "artifacts":{"frames":8,"duration_s":15.2,"has_transcript":true}}

GET  /api/v1/assets/{asset_id}
     → {"asset_id":"…","kind":"video","duration_s":15.2,
        "transcript":"…",
        "frames":[{"t":0,"caption":"…","ocr_text":"…"}],
        "signals":{"cut_count":9,"has_face":true,"text_overlay_ratio":0.4}}
```

**The query endpoint answers both GET and POST, on one handler.** The existing agent adapter issues a `GET` with `q` and `top_k` as query parameters; [integration-architecture.md](../docs/architecture/integration-architecture.md) §4.2 specifies `POST /api/v1/data/query`. Both are correct, the disagreement is not worth a negotiation, and satisfying both costs one extra route decorator over the same function.

**`POST /api/v1/assets` is synchronous.** It runs `extract` and returns when the artifacts exist — typically a few seconds, and free on a cache hit. No queue, no job id, no polling endpoint, no status machine. This fits inside the 30–60 second budget [integration-architecture.md](../docs/architecture/integration-architecture.md) §4.3 already allocates for a backend-to-AI call, and every one of those omitted mechanisms is a component that can fail during a demo.

**It receives a path, never bytes.** See §4: the upload directory is a shared volume.

**Two endpoints, two agent ports.** `/data/query` backs the agent's `Retriever` — "what do we know about this topic." `/assets/{id}` backs a `Tool` — "give me the artifacts for this asset." These are different questions and should not be merged: an asset id forced through a text-similarity query is a lookup pretending to be a search, and it will occasionally return the wrong asset.

**Endpoints deliberately not built.** [integration-architecture.md](../docs/architecture/integration-architecture.md) §4.2 sketches `GET /api/v1/policy-rules` and `GET /api/v1/channel-history/{id}`. Both are `/data/query` with a different `q`. One general endpoint that the retrieval layer already serves beats three specific ones that each need their own handler, their own DTO and their own test.

---

## 12. Retrieval

The data layer owns retrieval **mechanics**. The agent layer owns what to do with the results.

### 12.1 Hybrid by default

Dense-only retrieval misses exact identifiers, rare tokens and misspellings — precisely the cases where a user typed something specific and expects it back. Lexical-only retrieval misses paraphrase. Two legs, fused:

```
                   query
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌────────────────┐      ┌──────────────────┐
│ LEXICAL leg    │      │ DENSE leg        │
│ pg_trgm        │      │ pgvector HNSW    │
│ + Postgres FTS │      │ cosine distance  │
│ + unaccent     │      │                  │
└───────┬────────┘      └────────┬─────────┘
        │      top_k each         │
        └────────────┬────────────┘
                     ▼
        Reciprocal Rank Fusion (RRF)
             score = Σ 1/(k + rank)
                     ▼
              top_k results
```

RRF fuses on **rank**, not score, which is why it needs no calibration between two legs whose scores are not on the same scale. `k` (conventionally 60) lives in `Settings`.

### 12.2 An honest limitation

**Postgres full-text search ships no Vietnamese dictionary.** There is no `vietnamese` text search configuration, so stemming and stop-words are unavailable for Vietnamese text.

The mitigation adopted here: `unaccent` + the `simple` configuration for tokenization, with `pg_trgm` trigram similarity carrying most of the lexical weight. Trigram matching is diacritic- and typo-tolerant, which covers a good deal of what a real analyzer would do — and it does so without another service.

This is a real limitation, not a solved problem. §17 names the upgrade. Anyone reporting retrieval quality on Vietnamese text should state this caveat.

### 12.3 The shared port

`agent/domain/ports/retriever.py` already defines what the agent needs. **The data layer's `hybrid_retriever` is an adapter for the agent's port** — the one place these two layers meet in code.

Consequences, both directions:

- The data layer returns objects structurally compatible with `agent/domain/entities/context.py::RetrievedDocument` — `content`, `source`, `score`, `metadata`.
- Changing that shape is a cross-layer breaking change and follows §9's rules.
- The agent never imports `psycopg` or `pgvector`, and never learns that retrieval is hybrid. Swapping the index for a different store is invisible to it.

`metadata` is `dict[str, Any]`, which is the pressure valve: a new field on a media chunk — timestamp, frame path, risk label — travels to the agent without a contract change on either side.

### 12.4 Media enters the same index, as text

A frame becomes a caption; a caption is text. Video, image and audio therefore share one index, one embedding model and one retrieval path with every document in the system. The `Embedder` port is unchanged, the vector space is single, and a query can return a PDF paragraph and a video frame ranked against each other.

The alternative was a multimodal embedding model — CLIP or similar — putting pixels and text in a shared space directly. Rejected for now, deliberately:

| | Captions as text | Multimodal embeddings |
| --- | --- | --- |
| Vector spaces | one | two, or one much larger model |
| Retrieval path | the existing hybrid query | a second path to build and tune |
| What is matched | what the model *says* is in the frame | what the frame *looks* like |
| Extra cost | none — the caption is already needed for the agent | a second model, a second index, a second eval |

**Where this breaks, stated plainly.** Caption similarity is topical similarity. Two creatives that are visually different but describable the same way — two white t-shirts with different graphics, two ads for the same product with different pacing — will collide. For search and analysis this is usually acceptable and sometimes preferable. For **near-duplicate detection over a large catalog it is not**, and anyone reporting deduplication quality on this index should say so.

The escape hatch is not CLIP. A perceptual hash (`imagehash.phash`) stored as a `bigint` beside the chunk gives exact near-duplicate detection through a Hamming-distance comparison in SQL, at the cost of one dependency and one column. §17 records the trigger for adding it, and the separate, larger trigger for genuine multimodal embeddings — which is an eval showing caption retrieval losing, not an intuition that it might.

Two structural properties keep this reversible: the Index is derived and rebuildable from Silver (§3), and `Embedder` is a port (§6). Reversing the decision costs one adapter and one rebuild, not a migration.

---

## 13. Observability

### Structured logs, stdout only

No `print()`. One structured event per meaningful step, emitted to stdout; collection and routing are the environment's job (Twelve-Factor).

```python
logger.info(
    "asset_materialized",
    run_id=run_id,
    asset_key="silver/orders",
    partition="2026-08-12",
    rows_in=124_301,
    rows_out=124_288,
    rows_rejected=13,
    bytes_written=8_412_663,
    duration_ms=4_182,
    contract_version="2.1.0",
    engine="polars",
)
```

### Mandatory fields

```
run_id, asset_key, partition, source_system, dataset
contract_version, schema_version
rows_in, rows_out, rows_rejected, bytes_written
duration_ms, engine
watermark_from, watermark_to
```

For a `extract` run, four more (§7.6):

```
asset_id, content_hash, extractor_version, cache_hit
transcriber_model_id, captioner_model_id, frame_count
```

`cache_hit` is the one to watch. A cache hit rate that collapses means the extractor version is churning or the same asset is arriving under different bytes, and both are cost problems that are otherwise invisible until the bill arrives.

### Never log

API keys, connection strings, full record payloads, or any column classified `pii`. Log the **count** of bad rows and a violation code; the rows themselves belong in quarantine, which is access-controlled. Logs are the easiest place to turn a data layer into a leak.

**Transcripts and captions count as payload.** A transcript is a verbatim record of what someone said and routinely contains names, addresses and phone numbers; a caption may describe an identifiable person. Log the character count and the model id, never the text — the same rule as any other record payload, and worth stating because a transcript does not look like a database row and the rule gets forgotten.

### The four detectors

| Detector             | Fires when                                                      | Severity                      |
| -------------------- | --------------------------------------------------------------- | ----------------------------- |
| Flow interruption    | a dataset has had no new partition for longer than its SLA      | page                          |
| Volume skew          | row count deviates more than three sigma from its trailing mean | warn, page on repeat          |
| Freshness / SLA miss | the contract's freshness budget is exceeded                     | page if a consumer has an SLA |
| Quality-rate drift   | the rejected-row ratio rises materially against its baseline    | warn                          |

**Never page on a warning**, and **never ship an alert without a runbook link**. Both produce the same outcome: alerts that get ignored, including the real ones.

### Lineage

Dagster's asset graph is the lineage graph — it is derived from the code, so it cannot drift from it. dbt contributes column-level detail within the SQL layer via its manifest.

**A hand-drawn lineage diagram is out of date by the second deploy.** The diagrams in this document are for explaining the architecture; they are not the lineage record and must not be used as one.

### Tracing

`observability/tracing.py` holds a thin interface only, so OpenTelemetry can be attached later without touching pipeline code — the same posture as the agent standard §14.

---

## 14. Security and governance

| Concern                    | Rule                                                                                                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Classification             | every field carries one of `public` / `internal` / `confidential` / `pii`, set in the contract                                                       |
| PII tagging                | applied in `normalize` at landing (§7.2 step 5), never retrofitted                                                                                   |
| Secrets                    | environment variables locally, a secret manager in cloud; never in git, never in logs                                                                |
| DB roles                   | `data_writer` (pipelines: write `gold`/`index`/`ops`), `backend_reader` (`SELECT` on `api` only), `analyst_reader` (read `gold`, PII columns masked) |
| Object storage             | per-bucket credentials; the pipeline role cannot delete Bronze                                                                                       |
| Production data on laptops | prohibited — the single most common avoidable PII leak. Use `mock_source` and generated fixtures                                                     |
| Test data                  | synthetic, or a masked sample; never a production dump, and never in CI logs                                                                         |
| Retention                  | Bronze per policy, Silver aligned to Bronze, quarantine 90 days, Index rebuildable so retention is irrelevant                                        |
| Right to erasure           | a keyed delete against Silver plus a Gold rebuild plus an Index rebuild; Bronze handled per its retention policy                                     |
| Uploaded media             | classify at registration, never after. A user video is `confidential` by default: it may contain identifiable people, and it was uploaded for one purpose |
| Media leaving the machine  | frames and audio are sent to a hosted model (§4). Say so in the privacy notice, and keep the local-model successor in §17 open as the answer when a customer objects |

**Every dataset has exactly one owner**, recorded in its contract. A dataset owned by everyone is maintained by no one and becomes the on-call's problem eventually.

---

## 15. Naming conventions

Boring and predictable beats clever. These are not negotiable per-pipeline.

### Object paths

```
s3://bi-data-<env>/<layer>/<source_system>/<dataset>/<partition_col>=<value>/part-<run_id>-<n>.parquet

layer         ∈ {bronze, silver, gold, quarantine}
env           ∈ {dev, staging, prod}
partition_col = ingested_date (bronze) | event_date (silver)
```

```
s3://bi-data-prod/bronze/erp/orders/ingested_date=2026-08-12/part-a1b2c3-0.parquet
s3://bi-data-prod/silver/orders/event_date=2026-08-11/part-a1b2c3-0.parquet
```

### Media assets and their derivations

```
s3://bi-data-<env>/bronze/assets/<kind>/ingested_date=<value>/<asset_id>.<ext>
s3://bi-data-<env>/silver/frames/<asset_id>/<index>.jpg

kind          ∈ {video, image, audio}
asset_id      = <PREFIX>-<YYYYMMDD>-<discriminator>     VID · IMG · AUD · DOC
discriminator = 6 hex characters
index         = the frame's zero-padded ordinal, not its timestamp
```

```
s3://bi-data-prod/bronze/assets/video/ingested_date=2026-08-21/VID-20260821-a1b2c3.mp4
s3://bi-data-prod/silver/frames/VID-20260821-a1b2c3/03.jpg
```

The asset id carries its arrival date so a directory listing sorts usefully, and the frames of one asset live together so deleting an asset's derivations is a prefix delete. Frames are numbered by ordinal rather than timestamp because the sampling rate is configuration (§7.6) and a filename that encodes it becomes wrong when it changes.

**The discriminator is derived, never a counter.** A sequence number requires a per-kind-per-day counter — extra state, and non-deterministic under retry, so the same file re-processed gets a second id and a second copy. Two derivations, in order of preference:

| Situation | Discriminator |
| --- | --- |
| The caller supplied an id | its own trailing entropy — the backend's `ANL-20260821103000-a1b2c3` becomes `VID-20260821-a1b2c3` |
| No caller id | `sha256(bytes)[:6]` |

Both are deterministic, so a retry produces the same id and the same object path. The caller's original identifier is kept in `asset.asset.external_refs` so the backend can be answered in its own vocabulary, and `UNIQUE(content_hash)` catches genuine duplicate uploads that a random id would silently admit.

**One identifier crosses the whole system.** The alternative — data minting its own id and storing the caller's as a foreign reference — means two ids for the same file in every log line, trace and support conversation. Reusing the caller's entropy costs nothing and removes that translation.

### Chunk and cache ids

```
chunk id       <asset_id>:<kind>:<ordinal>     VID-20260821-0007:frame_caption:03
                                               VID-20260821-0007:transcript:00
extract cache  (content_hash, extractor_version)
```

The chunk id appears in the `id` field of the API response (§11.4), so it must be stable across a re-index and readable in a log line.

### Postgres

| Object       | Pattern                                                            | Example              |
| ------------ | ------------------------------------------------------------------ | -------------------- |
| Schemas      | `gold`, `index`, `api`, `ops`                                      |                      |
| Dimension    | `dim_<entity>`                                                     | `gold.dim_customer`  |
| Fact         | `fct_<event>`                                                      | `gold.fct_order`     |
| Serving view | `api.v<major>_<name>`                                              | `api.v1_order_daily` |
| Index tables | `index.chunk`, `index.embedding`                                   |                      |
| Ops tables   | `ops.ingestion_watermark`, `ops.run_log`, `ops.quality_violations` |                      |

### Dagster asset keys

```
["bronze", <source_system>, <dataset>]     ["bronze", "erp", "orders"]
["silver", <entity>]                       ["silver", "orders"]
["gold",   <model>]                        ["gold", "fct_order"]
["index",  <collection>]                   ["index", "documents"]
["eval",   <suite>]                        ["eval", "extraction_v1"]
```

The asset key prefix is the layer, so the Dagster UI groups by layer with no extra configuration.

### dbt models

| Stage        | Pattern                        | Example                |
| ------------ | ------------------------------ | ---------------------- |
| Staging      | `stg_<source>__<entity>`       | `stg_erp__orders`      |
| Intermediate | `int_<entity>__<verb>`         | `int_orders__enriched` |
| Mart         | `dim_<entity>` / `fct_<event>` | `fct_order`            |

Double underscore separates the source from the entity; single underscores are word separators within each.

### Branches and columns

- Branches: `data/<type>/<slug>` — `data/feat/orders-ingest`, `data/fix/dedup-key`.
- Timestamps: `<verb>_at`, always UTC, always timezone-aware — `created_at`, `ingested_at`.
- Booleans: `is_` / `has_` — `is_active`.
- Keys: `<entity>_id` for natural keys, `<entity>_key` for surrogate keys.

---

## 16. Testing

Four tiers. The first three are ordinary software testing; the fourth exists because data quality is not a boolean.

```text
tests/
├── unit/          # no network, no DB, no files -- mock adapters. Milliseconds.
├── integration/   # real DuckDB, real Postgres in Docker, real MinIO
├── e2e/           # one partition through every pipeline
└── (evaluation/)  # lives in evaluation/, run as an asset -- see §7.5
```

| Tier        | What it proves                                            | Rule                                                           |
| ----------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| Unit        | policies, transformers, contracts, RRF fusion are correct | if it needs a container, it is not a unit test                 |
| Integration | each adapter really works against its real dependency     | real dependencies, not mocks — mocked drivers hide driver bugs |
| E2E         | the layers compose, on a tiny synthetic dataset           | must run in CI in under a few minutes                          |
| Evaluation  | quality is above threshold                                | `quality >= threshold`, not `expected == actual`               |

**The fourth tier is not optional and it is not a notebook.** Traditional tests assert equality; a retrieval or extraction pipeline has no single correct output, only a measurable quality level. `evaluation/` is therefore a component of the system with the same standing as `application/` — the same argument the agent standard makes in §15.

**Test data is synthetic.** `mock_source` and `mock_embedder` (deterministic) exist so the unit tier stays fast and the whole suite stays free of production data.

---

## 17. Evolution path

Every row here is a real ceiling with a real successor. **The trigger column exists so nobody upgrades early** — each of these upgrades costs operational complexity that is only worth paying once the ceiling is actually hit.

| Today                           | Ceiling / trigger                                                                      | Then                                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Plain Parquet partitions        | concurrent writers, or a genuine need for row-level `MERGE` / time travel              | Apache Iceberg (`pyiceberg` + a REST catalog)                                            |
| DuckDB single-node              | a transform no longer fits one machine, or exceeds the time budget on a large instance | Distributed engine, or push the transform into a warehouse                               |
| Batch ingestion                 | a consumer's value genuinely depends on sub-minute freshness                           | Postgres logical replication first; Debezium + a log broker only if that is insufficient |
| pgvector                        | vector count or QPS degrades recall or latency below target                            | A dedicated vector store — accepting a second store to keep in sync                      |
| Postgres FTS + trigram          | Vietnamese lexical retrieval quality becomes the binding constraint (§12.2)            | A search engine with a real Vietnamese analyzer                                          |
| Full reload                     | reload time or source load becomes a problem                                           | Incremental with a watermark, then CDC                                                   |
| `dagster dev`                   | multiple concurrent users, or scheduled runs must survive a laptop closing             | Dagster deployed as a container, then on K8s                                             |
| Local `ops` tables              | lineage needed across teams and tools                                                  | OpenLineage emission into a catalog                                                      |
| Postgres as the analytics store | analytical queries start competing with serving queries                                | A dedicated columnar warehouse; Postgres keeps only `api`                                |
| Hosted transcription (§4)       | the network dependency becomes unacceptable, Vietnamese transcript quality is the binding constraint, or a customer refuses to let audio leave the machine | `faster-whisper` (base, int8, CPU) behind the existing `Transcriber` port — no torch, ~150 MB of weights baked into the image |
| Captions as the only media signal (§12.4) | an eval **shows** caption retrieval losing to visual similarity — an intuition is not the trigger | A multimodal embedding model, accepting a second vector space and a second retrieval path |
| No perceptual hashing           | near-duplicate detection over a catalog becomes a requirement                          | `imagehash.phash` as a `bigint` column, Hamming distance in SQL — one dependency, one column |
| Synchronous `POST /assets` (§11.4) | extraction on real assets starts exceeding the caller's timeout                     | A job id and a polling endpoint, then a real queue — in that order, and not before        |
| Request-time over one asset     | a consumer's value genuinely depends on continuous analysis of a live stream           | Segment the stream into bounded chunks and keep calling `extract`; a streaming engine only if that proves insufficient |

**Record why, when you do it.** Each of these is an architecture decision worth a short ADR in `docs/decisions/`. The architecture in this document is an engineering hypothesis, not a permanent truth — and the reasoning behind a change is more valuable later than the change itself.

---

## 18. Build order

### The composition root

`orchestration/resources.py` is the **only** place in `data/` allowed to name a concrete implementation — the same rule as `agent/bootstrap/container.py`.

```python
def build_resources(settings: Settings) -> dict[str, object]:
    store = FsspecObjectStore(settings.object_store_url, settings.object_store_credentials)
    catalog = PostgresCatalog(settings.database_url)
    validator = PanderaValidator()
    embedder = create_embedder(settings)          # fastembed | api | mock
    parser = create_parser(settings)              # docling | pymupdf
    transcriber = create_transcriber(settings)    # gemini | mock
    captioner = create_captioner(settings)        # gemini | byteplus | mock

    return {
        "store": store,
        "catalog": catalog,
        "validator": validator,
        "embedder": embedder,
        "parser": parser,
        "transcriber": transcriber,
        "captioner": captioner,
        "retriever": HybridRetriever(
            dense=PgVectorRetriever(settings.database_url, embedder),
            lexical=LexicalRetriever(settings.database_url),
            k=settings.rrf_k,
        ),
    }
```

If `DuckDBEngine(...)`, `FastEmbedEmbedder(...)` or `GeminiCaptioner(...)` appears anywhere else, the layer has grown a hidden dependency.

**Both edges share this one function.** `orchestration/definitions.py` passes the result to Dagster as resources; `interface/api/app.py` builds it once at startup and holds it on the app state. Two edges, two frameworks, one composition root — if the API grows its own way of constructing a captioner, the rule is already broken.

### First cut — build only this

```
one media asset (a short video)
        ↓
ingest ──▶ Bronze assets/       register by reference, content hash
        ↓
extract ──▶ Silver              ffmpeg → Transcriber → FrameCaptioner
        ↓                       + one Pandera contract
        ↓                       + the content-hash cache
index ──▶ Index                 chunks + embeddings in pgvector
        ↓
GET /api/v1/data/query          the shape of §11.4
        ↓
HttpJsonRetriever               returns list[RetrievedDocument], agent unchanged
```

Plus: `Settings`, structured logging, and the mock adapters — `mock_transcriber`, `mock_captioner`, `mock_embedder` — so the whole slice runs in a unit test with no network and no containers.

**The first slice is a media slice, and that is a deliberate change from version 1.0.** A CSV slice through `normalize` and `model` would exercise the same boundaries, but it would prove them for the input type that is easiest and postpone the one that is hardest. The media path has every unknown in it: a system binary, two model calls, a cache, and a cross-layer HTTP contract. Finding out on the last day that one of those does not fit is the failure worth spending the first day preventing.

The structured path — `normalize`, `model`, dbt, `api.v1_*` — is built second, over boundaries the media slice has already proven.

### Do not build yet

Deliberately deferred until a real need appears, in roughly this order: the second source type · the eval harness · dbt (raw SQL in one model is fine at first) · quarantine reprocessing · the four detectors · perceptual hashing · Iceberg · anything in §17.

**Build breadth only after the first slice works end to end.** Six half-built pipelines teach you nothing about whether the design holds; one complete one teaches you everything.

The schedule that turns this into dated work is in [implementation-plan.md](implementation-plan.md).

---

## 19. Review checklist for `data/`

Architecture:

- [ ] `domain/` imports no framework, driver or SDK (§2)
- [ ] Every pipeline in `application/pipelines/` is callable with no `dagster` and no `fastapi` import (§2)
- [ ] Concrete implementations are named only in `orchestration/resources.py`, and both edges use it (§18)
- [ ] Every significant boundary has a `Protocol` port; interfaces are not created for their own sake (§6)
- [ ] `interface/api/` returns DTOs, never domain entities (§2, §11.4)
- [ ] Config comes from `Settings` — no hard-coded paths, URLs, thresholds, frame counts or model names (§7.6, §10)

Data correctness:

- [ ] Bronze is append-only and never mutated (§3, §8)
- [ ] Every write is idempotent for its partition; delete precedes write (§8)
- [ ] Watermarks are in `ops`, not on local disk, and commit after a successful write (§8)
- [ ] A backfill is a partition-range re-run of the same code, not a separate script (§8)
- [ ] No `SELECT *` crossing a layer boundary (§7.2, §9)
- [ ] Unknown upstream columns produce a visible drift event, never silence (§9)
- [ ] Gold never references Bronze column names directly (§9)

Quality and contracts:

- [ ] Checks run at Bronze, Silver _and_ Gold — not only Gold (§10)
- [ ] Bad rows are quarantined with their violation, never dropped (§10)
- [ ] Thresholds are configuration (§10)
- [ ] No broad `except` that swallows a failure and continues (§8)
- [ ] Every contract has a version, an owner, semantics and an SLA (§9)
- [ ] `contracts/jsonschema/` is regenerated and committed when a contract changes (§9, §11)
- [ ] Breaking changes ship as a new version with a grace period (§9)

Serving and retrieval:

- [ ] The backend reads only `api.v1_*`, enforced by its DB grant (§11.1)
- [ ] `Retriever` output stays compatible with the agent layer's `RetrievedDocument` (§12.3)
- [ ] `/api/v1/data/query` answers both GET and POST from one handler (§11.4)
- [ ] `embedder_model_id` is part of the index key (§7.4)
- [ ] Index is fully rebuildable from Silver (§3)

Media:

- [ ] Media blobs land in Bronze unaltered and are never mutated (§3, §7.1)
- [ ] Media bytes never cross a pod boundary over HTTP — pass the path (§4, §11.4)
- [ ] Every derivation is keyed on `content_hash + extractor_version` (§7.6)
- [ ] `extractor_version` covers the prompt, sampling parameters and model ids (§7.6)
- [ ] `extract` runs in a unit test with mock adapters — no ffmpeg, no API key, no network (§6, §16)
- [ ] Transcripts and captions are never logged, only their length (§13)
- [ ] Uploaded media is classified at registration, not later (§14)

Operations:

- [ ] Structured logging only — no `print()` (§13)
- [ ] Mandatory log fields present; no secrets, payloads or PII logged (§13)
- [ ] Every alert links a runbook, and warnings do not page (§13)
- [ ] Every dataset has exactly one named owner (§14)
- [ ] PII is classified at landing (§7.2, §14)
- [ ] No production data on laptops or in CI logs (§14)
- [ ] Names follow §15 without exception
- [ ] Unit tests need no container; integration tests use real dependencies (§16)
- [ ] Evaluation exists as a first-class component, not a notebook (§7.5, §16)

# Data Layer — Platform 1: Data Intelligence

This directory owns the **Sense** step of the platform (`Sense → Understand → Reason → Simulate → Decide → Act → Learn`). It takes messy outside data — CSV, Excel, REST APIs, databases, PDFs, and uploaded video, image and audio — and turns it into two things the rest of the system can trust:

1. **Clean rows** the .NET backend and the simulation layer query.
2. **Searchable text** the `agent/` layer retrieves over.

It never decides anything. It answers *"what do we have?"*, never *"what should we do?"* — that is `agent/`.

## Documents

| Document | What it covers |
|---|---|
| [data-architecture.md](data-architecture.md) | **The standard.** Layering, the six pipelines with worked code, contracts, quality, serving, retrieval, observability, evaluation, naming, testing, evolution triggers, and a review checklist |
| [implementation-plan.md](implementation-plan.md) | The build order: environment, schema, file manifest per stage, one-command gates, the settled decisions register, and the test manifest |
| [tech-stack-evaluation.md](tech-stack-evaluation.md) | Every framework considered per category, what each is good and bad at, which was chosen and why, what was rejected, and the version pins |
| [../docs/architecture/agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) | The equivalent standard for the `agent/` layer |

## Three tools, one job each

| | |
|---|---|
| **Delta Lake** | the storage / table format, every layer |
| **DuckDB** | the transformations expressible in SQL |
| **Polars** | the transformations that need Python — media, documents, validation |

DuckDB never writes Delta. It reads Delta, runs the SQL, and returns Arrow; `deltalake` does the write. One write path, so atomicity and schema enforcement are uniform.

## The one-page picture

```
                EXTERNAL SOURCES
   CSV · Excel · REST API · Database · PDF · Media
                       │
                       ▼  dlt
        ┌──────────────────────────────┐
        │ LANDING   bytes as received  │   the file, the raw JSON, the PDF, the MP4
        │           never parsed       │   append-only. What did they actually send?
        └──────┬────────────────┬──────┘
               ▼                │
        ┌──────────────────┐    │
        │ BRONZE  Delta    │    │ blobs stay in Landing
        │ schema inferred  │    │
        └──────┬───────────┘    │
               │                │
          DuckDB ── SQL     Polars ── Python
               │                │      (Docling · ffmpeg → Gemini)
               └────────┬───────┘
                        ▼
        ┌──────────────────────────────┐
        │ SILVER  Delta                │   typed, deduplicated, contract enforced
        │         bad rows quarantined │
        └──────┬────────────────┬──────┘
               ▼                ▼
    ┌────────────────┐   ┌────────────────────┐
    │ GOLD  Delta    │   │ INDEX  chunks +    │
    │ → Postgres     │   │ vectors (pgvector) │
    └───────┬────────┘   └─────────┬──────────┘
            ▼                      ▼
     api.v1_* SQL views      HTTP JSON on :8002
            │                      │
      .NET backend            agent/ layer
```

Data flows one way. Everything below Landing is deletable and rebuildable.

**Landing and Bronze are two things on purpose.** Landing answers *"what did they actually send us?"* — the original bytes, including the broken encoding and the MP4 nobody can re-upload. Bronze answers *"what records were in it?"* — schema inferred, queryable, still untransformed. Putting a boundary between them means the bytes-to-records conversion is a step you can re-run.

## The six pipelines

Each source type has a complete path to Gold. The four tabular sources differ **only in the dlt source that produces Landing and Bronze** — from Silver onward they run the same function against their own `.sql` file.

| Source | Landing + Bronze | Silver → Gold |
|---|---|---|
| **CSV** | dlt `filesystem` + `read_csv` | a `.sql` file, run by DuckDB |
| **Excel** | dlt `filesystem` + a ~15-line Polars transformer (dlt ships no Excel reader) | the same, its own `.sql` |
| **REST API** | dlt `rest_api_source` — pagination, auth and the incremental cursor are config | the same, its own `.sql` |
| **Database** | dlt `sql_database`, pyarrow backend | the same, its own `.sql` |
| **PDF** | blob, byte-for-byte | Docling parse → chunks → Silver + Index |
| **Media** | blob, byte-for-byte | ffmpeg → Gemini transcript + captions → `MERGE` into Silver + Index |

Plus an **evaluation harness**: labeled cases as JSONL in git → a Dagster asset → a baseline-vs-pipeline accuracy number.

## The stack in one paragraph

**dlt** ingests every source into a **Landing** area of untouched bytes and a **Bronze** layer of **Delta** tables on object storage (**MinIO** locally, S3-compatible in cloud); PDF and media blobs stay in Landing unaltered. **DuckDB** runs plain `.sql` files against those Delta tables to produce **Silver** and then **Gold** — typed, deduplicated, contracts enforced by **Pandera** on the Arrow result before it is written, with failures quarantined rather than dropped — and `deltalake` performs every write, so each one is a single atomic commit. Gold is published into **Postgres 16** and exposed to the .NET backend as versioned `api.v1_*` views. Media takes the parallel route through **Polars** — `imageio-ffmpeg` samples frames and audio, hosted **Gemini** calls turn them into a transcript and frame captions, and the rows are `MERGE`d into Silver by `asset_id` and cached on the blob's content hash so nothing is ever derived twice. Documents and media annotations alike are embedded with **fastembed** and indexed in **pgvector**, retrieved through a hybrid `pg_trgm` + vector query fused with RRF in a single SQL statement — and served to the agent layer over **FastAPI** on `:8002`, because the agent must never learn SQL. **Dagster** orchestrates all of it as assets, with `deps=[...]` giving the dependency order. No JVM anywhere: delta-rs is Rust and Python. Everything runs on a laptop with two containers and two processes.

## How the code is organised

Two Python packages and a directory of SQL. Not four layers.

```text
defs/            what Dagster loads — assets, resources, schedules, checks
lib/             the shared helpers — settings, logging, delta, sql, db, gemini
sql/transforms/  the SQL that produces Silver and Gold
contracts/       Pandera schemas, one per dataset
api.py           the FastAPI edge — four endpoints
```

**The one structural rule: an asset body calls a function; it does not contain one.** That is what lets a Dagster schedule and a live HTTP request run the same extraction. It is a rule about writing a function, not about building a layer.

The function that replaced a whole toolchain, in `lib/sql.py`:

```python
def run_sql_to_delta(sql: str, target: str, *, mode: str = "overwrite") -> pa.Table:
    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta; INSTALL httpfs; LOAD httpfs;")
    table = con.sql(sql).arrow()               # DuckDB does the SQL
    write_deltalake(target, table, mode=mode)  # delta-rs does the write
    return table
```

## Rules that are actually enforced

- **Landing and Bronze are append-only.** Every future bug is fixable by reprocessing instead of re-fetching. For an uploaded video there is no re-fetch at all.
- **Every write is one atomic commit.** Not delete-then-write. A crash mid-run leaves the previous version intact and readable.
- **Per-key updates use `MERGE`**, never a partition rewrite.
- **Every derivation is keyed so a re-run is free** — media on `content_hash + extractor_version`, chunks on `(document_id, chunk_index, embedder_model_id)`. Re-running a processed video makes zero model calls.
- **Bad rows are quarantined with their violation attached, never dropped.** Dropping rows is indistinguishable from never having received them.
- **No `select *` across a layer boundary.** An upstream column change must be a reviewable decision, not a silent one.
- **`schema_mode="merge"` is for a deliberate additive change**, never to silence a failing write.
- **Nothing hard-coded that belongs in `Settings`** — thresholds, paths, model names, `top_k`.
- **Never log a transcript, caption or record payload.** Log the character count and the model id.
- **No `Protocol` without two live implementations.** A protocol with one implementation is a wrapper.

## Two consumers, two doors

| Caller | Gets | How |
|---|---|---|
| The .NET backend | rows | reads `api.v1_*` SQL views with a role that has `SELECT` on `api` and nothing else |
| The `agent/` layer | documents and asset artifacts | four HTTP JSON endpoints on `:8002` — `GET /health`, `GET`\|`POST /api/v1/data/query`, `POST /api/v1/assets`, `GET /api/v1/assets/{id}` |

`POST /api/v1/assets` is synchronous and takes **a path, not bytes** — the upload directory is a shared volume. No queue, no job id, no polling: each omitted mechanism is one fewer thing that can fail during a demo.

## What is deliberately not built yet

`VACUUM`/`OPTIMIZE` schedules · Delta concurrent-write locking · dbt or SQLMesh (again) · column-level lineage · streaming · a dedicated vector store · CDC · local transcription models · multimodal embeddings · perceptual hashing · a job queue behind the assets endpoint · alert detectors. Each has a written trigger in [data-architecture.md](data-architecture.md) §16, so nobody adds it early and nobody forgets it exists.

## Status

**Version 3.0 of the design; implementation at zero.**

- **1.1** specified a four-layer Clean Architecture with 14 ports and a composition root.
- **2.0** deleted that and used the chosen frameworks directly — dlt as the source abstraction, Dagster resources as the dependency injection. Sixty Python files became fifteen.
- **3.0** makes Delta Lake the table format and **removes dbt**. Its jobs move to things already in the stack: `deps=[...]` for ordering, Pandera plus Delta schema enforcement for contracts, the Dagster graph for lineage, `write_deltalake` for materialization. Three dependencies and three config files go. Delta earns its place on `MERGE` and atomic commits — not on multi-writer ACID, which nothing here exercises.

Full mapping in [data-architecture.md](data-architecture.md)'s changelog; the two tool reversals (dbt, and Parquet→Delta) are recorded in [tech-stack-evaluation.md](tech-stack-evaluation.md).

Start at [implementation-plan.md](implementation-plan.md) §7, stage 0 — and run **stage 0.5** first. Its four checks (does dlt write Delta, does `delta_scan` read it, does `MERGE` work, does `dagster-dlt` import) each have a named fallback, so a red result costs a design change rather than a day.

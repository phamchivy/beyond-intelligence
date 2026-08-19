# Data Architecture Standard — Beyond Intelligence

> Architecture and coding standard for the `data/` layer (**Platform 1 — Data Intelligence**).

**Version:** 3.0
**Date:** 19/08/2026
**Applies to:** the `data/` directory
**Companion documents:** [tech-stack-evaluation.md](tech-stack-evaluation.md) — why each tool was chosen · [implementation-plan.md](implementation-plan.md) — the build order and stage gates

---

## Changelog

### 3.0 — Delta Lake as the table format, dbt removed

Three tools, each doing one job:

| | |
| --- | --- |
| **Delta Lake** | the storage / table format for Landing, Bronze, Silver and Gold |
| **DuckDB** | the transformations expressible in SQL |
| **Polars** | the transformations that need Python — media, documents, validation |

**dbt is removed.** It was chosen in
[tech-stack-evaluation.md](tech-stack-evaluation.md) §6 and used in 2.0 for
Silver and Gold. Its responsibilities do not disappear; each moves to something
already in the stack:

| dbt provided | 3.0 uses |
| --- | --- |
| `ref()` dependency ordering | Dagster asset `deps=[...]` — already present, and visible in the UI |
| model contracts (column types) | Delta schema enforcement on write, plus Pandera |
| dbt tests — `not_null`, `unique`, `accepted_values`, `relationships` | Pandera checks on the Arrow result before it is written, plus `@asset_check` |
| the manifest, for lineage | the Dagster asset graph, which §11 already made the primary lineage source |
| `materialized='external'` | `write_deltalake(...)` |
| Jinja macros | plain `.sql` files under `sql/transforms/` |
| `dbt build` | `dagster asset materialize` |

Three dependencies go — `dbt-core`, `dbt-duckdb`, `dagster-dbt` — along with
`dbt_project.yml`, `profiles.yml` and the `schema.yml` files. Contracts collapse
from two mechanisms to one.

**What this costs, stated plainly.** Jinja macros for reusable SQL; column-level
lineage inside the SQL layer; tests running inline with their models the way
`dbt build` does; and dbt's value as a name a judge or a future hire already
recognises. For six datasets, plain `.sql` files run by DuckDB are a fair trade.
At thirty they would not be, and §16 records that as the trigger to reconsider.

**Delta Lake replaces plain Parquet partitions.** [tech-stack-evaluation.md](tech-stack-evaluation.md)
§7 chose plain Parquet with Iceberg as the designated upgrade, and §13 rejected
Delta outright. Both are reversed. What Delta actually buys here:

- **Row-level `MERGE`.** Version 2.0 carried a workaround
  ([implementation-plan.md](implementation-plan.md) §8.9) that existed *only*
  because Parquet partitions cannot upsert: media's unit of work is one asset,
  but deleting the date prefix would destroy every other asset in it. That
  workaround is deleted — it is now an ordinary `MERGE` on `asset_id`.
- **Atomic commits.** Delete-then-write is two steps that can crash in between
  and leave a partition half-gone. A Delta commit is one operation.
- **Schema enforcement on write**, which covers part of what dbt model contracts did.
- **Time travel**, free once Delta is present.

**It does not buy concurrency, and this document does not claim it does.** Polars
writes `asset_artifact` and `document_chunk`; DuckDB writes `stg_*` and the
marts. Different tables, one writer each. Delta's multi-writer ACID is real and
nothing here exercises it.

**Bronze splits in two.** *Landing* holds bytes exactly as received and is never
parsed; *Bronze Delta* holds the same records as a queryable, versioned table.
§3 explains why the split is worth a name.

**One risk 2.0 carried is gone.** 2.0 flagged "can dbt-duckdb *write* Delta?" as
an unknown. With dbt removed the question disappears: **DuckDB never writes
Delta.** It reads Delta, runs SQL, and returns Arrow; `deltalake` does the write.

### 2.0 — ports and adapters removed

Version 1.1 specified a four-layer Clean Architecture: 14 `Protocol` ports in
`domain/`, ~30 adapter files in `infrastructure/`, a framework-free
`application/` layer, and a 200-line composition root. 2.0 deleted all of it and
used the tools directly — dlt as the source abstraction, Dagster resources as the
dependency injection, Pandera called directly instead of behind a `Validator`
port. Roughly fifteen Python files where 1.1 specified sixty.

[tech-stack-evaluation.md](tech-stack-evaluation.md) §12 had already made the
argument, about the one component that never had a port:

> "Media decoding is cheap to reverse despite having no port … **this is the case
> that shows a `Protocol` was never what made a decision reversible — a narrow
> interface did, and two functions are narrower than a protocol.**"

2.0 also reversed 1.1's build order: one worked pipeline per source type, rather
than one vertical slice with breadth deferred.

**Tools that have never changed:** Dagster, dlt, Polars, DuckDB, Pandera,
Pydantic, Docling, fastembed, pgvector, Postgres, FastAPI, `imageio-ffmpeg`,
Gemini. Only the code around them, and now the table format.

---

## 1. Purpose and scope

The `data/` layer owns the **Sense** step of the platform's philosophy
(`Sense → Understand → Reason → Simulate → Decide → Act → Learn`). It takes
messy outside data — CSVs, spreadsheets, API responses, database rows, PDFs,
uploaded video and images — and produces two trusted things:

1. **Structured rows** the .NET backend and the simulation layer can query.
2. **Searchable text** — document chunks and media annotations in a retrieval
   index the `agent/` layer queries over HTTP.

### In scope

| Responsibility | Section |
| --- | --- |
| Ingest CSV, Excel, REST API, database, PDF, media | §6 |
| Validation, contracts and quarantine | §8 |
| Cleaning, typing, deduplication, modelling | §6, §8 |
| Media derivation — frames, audio, transcript, captions | §6.6 |
| Chunking, embedding, indexing | §6.5, §6.6, §10 |
| The SQL contract toward the .NET backend | §9 |
| The HTTP service the agent layer calls | §9 |
| Observability and lineage | §11 |
| The evaluation harness | §12 |

### Out of scope

- **Reasoning over the data.** Planning and decisions belong to `agent/`. This
  layer returns rows, documents and annotations; it never interprets them.
- **Streaming.** Everything is batch, micro-batch, or a synchronous run over one
  asset. §16 states the trigger for genuine streaming.
- **Media generation.** This layer describes media; it does not create it.
- **Being a warehouse migration.** One pipeline per dataset someone asked for.

### Two ways a pipeline starts

| Mode | Started by | Latency | Used for |
| --- | --- | --- | --- |
| **Scheduled** | a Dagster schedule | minutes to hours | reference corpora — catalogs, policy documents, channel history |
| **Request-time** | an HTTP call to `api.py` | seconds | the asset a user just uploaded and is waiting on |

Both call the same Python function. §2 explains the one rule that keeps this true.

---

## 2. Architectural stance

> **Three tools, one job each. Delta stores, DuckDB does SQL, Polars does Python.
> Keep the logic in plain functions so more than one caller can reach it.**

There are two Python packages, one SQL directory, and no layers:

```text
defs/            what Dagster loads: assets, resources, schedules, asset checks
lib/             the shared helpers: settings, logging, delta, sql, db, gemini
sql/transforms/  the SQL that produces Silver and Gold
api.py           the FastAPI edge
```

### The one rule

**An asset body calls a function; it does not contain one.**

```python
# defs/media.py

def extract_asset(uri: str, kind: str, *, gemini, store, db, config) -> AssetArtifacts:
    """The actual work. A plain function -- no Dagster, no FastAPI."""
    ...

@asset(key=["silver", "asset_artifact"])
def silver_asset_artifact(context, gemini: GeminiResource, store: StoreResource):
    stats = extract_asset(..., gemini=gemini, store=store, ...)
    return MaterializeResult(metadata=stats.as_metadata())
```

This is kept for a concrete reason rather than a principle: `POST /api/v1/assets`
(§9) has to run extraction inside an HTTP request, and a Dagster schedule has to
run the same extraction at 2am. One function, two callers. If the logic lived
inside the `@asset` body, the API would have to duplicate it.

Note what this rule is *not*. It does not require a separate package, an
import-restriction test, or a port. It requires that you write a function.

### The division of labour

| Work | Tool | Why |
| --- | --- | --- |
| Joins, aggregation, casting, deduplication, filtering | **DuckDB**, over `.sql` files | SQL is the right language for set operations, and DuckDB reads Delta and object storage natively |
| Anything with a model call, a subprocess, a parser, or branching logic | **Polars**, in Python | media extraction, document parsing, validation splits |
| Every write, from either | **`deltalake`** | one write path, so atomicity and schema enforcement are uniform |

**DuckDB and Polars meet in Arrow, and that handoff is free.** DuckDB's result
converts to an Arrow table with no serialization; Polars wraps Arrow with no
copy. This is why both engines can coexist without a conversion tax — it is the
same reason [tech-stack-evaluation.md](tech-stack-evaluation.md) §5 chose both.

### The function that replaced dbt

```python
# lib/sql.py
def run_sql_to_delta(sql: str, target: str, *, mode: str = "overwrite") -> pa.Table:
    """Run a SQL file against Delta tables and write the result to a Delta table.

    DuckDB never writes Delta -- it reads, computes, and hands back Arrow.
    deltalake does the write, so every write in this layer goes through one path.
    """
    con = duckdb.connect()
    con.execute("INSTALL delta; LOAD delta; INSTALL httpfs; LOAD httpfs;")
    table = con.sql(sql).arrow()
    write_deltalake(target, table, mode=mode, schema_mode="overwrite")
    return table
```

Eight lines, in one file, doing what `dbt-core` + `dbt-duckdb` + `dagster-dbt` +
three config files did. It returns the Arrow table rather than just a row count
so the caller can validate before or after the write (§8).

### What we deliberately do not abstract, and why

| Not abstracted | Because |
| --- | --- |
| dlt sources | dlt *is* the source abstraction. A `Source` port over it is a wrapper over a wrapper. |
| Object storage | fsspec and delta-rs already make local, MinIO, S3, R2 and GCS the same URL. |
| Postgres access | A handful of queries. `psycopg` in `lib/db.py`, called directly. |
| Polars / DuckDB | Compute engines are not I/O. There is nothing to fake. |
| The SQL files | They are SQL. DuckDB runs them; Dagster orders them. |
| Dagster | Assets are already thin. Replacing the orchestrator rewrites `defs/` and nothing else. |

### The one seam that survives

**The Gemini calls, in `lib/gemini.py`.** Transcription and captioning are the
only dependency that costs money, needs a network, and cannot run at a venue with
bad wifi. `lib/gemini.py` exposes two functions and one switch: `transcribe()`
and `caption()` return deterministic fake output when `settings.use_mock_models`
is true, so the whole media pipeline runs in a test with no API key and no
network.

That is a boolean in `Settings`, not a `Protocol` with two adapters and a factory.
It buys the same offline test and the same demo-day insurance.

---

## 3. Medallion layering

Five stages. Landing and Bronze are both "raw", and the split between them is
the one structural addition version 3.0 makes.

```
                        EXTERNAL SOURCES
     CSV · Excel · REST API · Database · PDF · Media
                              │
                              ▼  dlt
┌─────────────────────────────────────────────────────────────┐
│ LANDING — bytes exactly as received, never parsed           │
│  the CSV file, the XLSX file, the raw JSON response,        │
│  the PDF, the MP4. Append-only. No schema, no opinion.      │
└──────────────┬───────────────────────────┬──────────────────┘
               │ records                   │ blobs
               ▼                           ▼
┌──────────────────────────────┐   ┌──────────────────────────┐
│ BRONZE DELTA                 │   │  the blob stays in       │
│ same records, schema         │   │  Landing; §6.5 / §6.6    │
│ inferred by dlt, queryable   │   │  read it from there      │
└──────────────┬───────────────┘   └──────────┬───────────────┘
               │                              │
       DuckDB — SQL (§6)              Polars — Python (§6.5, §6.6)
               │                              │
               └──────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ SILVER DELTA — typed, deduplicated, contract enforced       │
│ Failures quarantined with their violation, never dropped    │
└───────────────┬─────────────────────────┬───────────────────┘
                ▼                         ▼
┌───────────────────────────┐  ┌────────────────────────────┐
│ GOLD DELTA                │  │ INDEX — chunks + vectors   │
│ published to Postgres     │  │ in Postgres pgvector.      │
│ for serving               │  │ Rebuildable from Silver.   │
└───────────┬───────────────┘  └────────────┬───────────────┘
            ▼                               ▼
    api.v1_* views (§9)              HTTP API on :8002 (§9)
            │                               │
      .NET backend                    agent/ layer
```

| Stage | Store | Format | Written by | Mutability |
| --- | --- | --- | --- | --- |
| Landing | Object storage | original bytes / Parquet | dlt, the upload path | append-only |
| Bronze | Object storage | **Delta** | dlt | append |
| Silver | Object storage | **Delta** | `run_sql_to_delta`, or Polars for media and documents | overwrite, or `MERGE` by key |
| Silver frames | Object storage | JPEG | `extract` | overwrite by asset |
| Gold | Object storage | **Delta**, then published to Postgres `gold` | `run_sql_to_delta` | overwrite, then publish |
| Index | Postgres `index` | tables + pgvector HNSW | the index step | upsert by chunk id |
| Quarantine | Object storage | **Delta** | whoever rejected the row | append |

### Why Landing and Bronze are two things

They answer different questions.

**Landing answers "what did they actually send us?"** It is the byte-for-byte
record — the original CSV with its broken encoding, the raw JSON before dlt
flattened it, the MP4 nobody can re-upload. When a transform is wrong, this is
what you reprocess from. When a source disputes what they sent, this is the
evidence.

**Bronze answers "what records were in it?"** dlt has inferred a schema, flattened
nested objects into child tables, and written a Delta table you can query. It is
still untransformed — no business logic has touched it — but it has a shape.

Version 2.0 collapsed these into one Bronze layer with a `records/` and an
`assets/` prefix. Naming them separately is more honest: the conversion from
bytes to records is real work that can be wrong, and putting a boundary there
means you can re-run it. It also gives the dlt-writes-Delta risk (§17) a natural
fallback — if dlt cannot write Delta directly, it writes Parquet to Landing and a
small Polars step produces Bronze Delta, which is a step this layering already
has a name for.

**Bronze is not optional.** It is what makes "the transform had a bug for three
days" a fifteen-minute reprocess instead of a conversation about whether the
source still has the data. For an uploaded video there is no re-fetch at all.

**Index is derived, never authoritative.** Dropping the whole `index` schema and
rebuilding from Silver must always be safe. Nothing may live only in the index.

---

## 4. Stack and topology

| Concern | Tool | Section |
| --- | --- | --- |
| Table format, every layer | **Delta Lake** via `deltalake` (delta-rs) | §3, §7 |
| Orchestration, lineage, quality gating | Dagster (`dagster dev`) | §11 |
| Ingestion connectors | dlt | §6.1–6.4 |
| Dagster ↔ dlt / DuckDB | `dagster-dlt`, `dagster-duckdb` | §6 |
| SQL transformation | DuckDB, over `.sql` files in `sql/transforms/` | §6 |
| Python transformation and validation | Polars | §6.5, §6.6, §8 |
| Contracts | Pandera, plus Delta schema enforcement | §8 |
| Object storage | MinIO local, S3 / R2 / GCS cloud | §3 |
| Serving store | Postgres 16 + pgvector + pg_trgm + unaccent | §9, §10 |
| Serving API | FastAPI + uvicorn on `:8002` | §9 |
| Document parsing | Docling, `pymupdf4llm` as a fast path | §6.5 |
| Media decoding | `imageio-ffmpeg` via `subprocess` | §6.6 |
| Transcription and captioning | Gemini, behind `lib/gemini.py` | §2, §6.6 |
| Embeddings | fastembed (ONNX, no torch) | §6.5, §10 |
| Evaluation metrics | scikit-learn | §12 |
| Config, logging, packaging | pydantic-settings, stdlib logging + JSON, uv, Ruff, pytest | §11 |

Rationale for each choice — including what was rejected, and the two reversals
3.0 makes — is in [tech-stack-evaluation.md](tech-stack-evaluation.md). This
table records only the outcome.

**No JVM.** delta-rs is Rust and Python. Delta Lake does not imply Spark here,
and nothing in this layer runs on a JVM.

### Local topology

```
┌──────────────────────────────────────────────────────────────┐
│  Developer laptop                                            │
│                                                              │
│  ┌────────────────┐        ┌──────────────────────────────┐  │
│  │  dagster dev   │───────▶│  MinIO                       │  │
│  │  assets +      │        │  landing/ bronze/ silver/    │  │
│  │  schedules     │        │  gold/ quarantine/  (Delta)  │  │
│  └───────┬────────┘        └──────────────┬───────────────┘  │
│          │ in-process                     │ delta-rs / httpfs│
│          ▼                                ▼                  │
│  ┌────────────────┐        ┌──────────────────────────────┐  │
│  │ DuckDB         │───────▶│  Postgres 16                 │  │
│  │ + Polars       │ publish│  + pgvector + pg_trgm        │  │
│  │ (libraries)    │        │  gold · index · api · ops    │  │
│  └────────────────┘        └──────────────┬───────────────┘  │
│                                           │                  │
│  ┌────────────────────────────────────────┴───────────────┐  │
│  │  uvicorn :8002 — api.py                                │  │
│  └───────┬──────────────────────────────────┬─────────────┘  │
└──────────┼──────────────────────────────────┼────────────────┘
           │ HTTP JSON (§9)                   │ SQL, read-only role
           ▼                                  ▼
      agent/ layer                     .NET 8 backend
```

Two containers (MinIO, Postgres), two processes (`dagster dev`, `uvicorn`).
DuckDB, Polars and delta-rs are libraries — nothing to run, nothing to keep alive.

**The upload directory is a shared volume, not an HTTP transfer.** The .NET
backend writes uploaded media to `backend/wwwroot/uploads/videos/` and returns
`/uploads/videos/{filename}`. That directory is mounted into the data container,
and `POST /api/v1/assets` receives **a path, never bytes**. This is the one
contract in this document that shipped .NET code already depends on.

### Cloud — the same code

| Local | Cloud | What changes |
| --- | --- | --- |
| MinIO on `:9000` | S3 / R2 / GCS | `OBJECT_STORE_URL`, credentials |
| Postgres container | Neon / Supabase / RDS | `DATABASE_URL` |
| DuckDB in-process | DuckDB in-process | nothing |
| `dagster dev` | Dagster on a container | deployment manifest only |
| Mounted upload directory | shared volume or object-store prefix | `ASSET_ROOT` |

Which is why storage URLs and a single `Settings` object are non-negotiable: the
moment a path is hard-coded to `/home/…` or `localhost`, the cloud path stops
being free.

---

## 5. Directory structure

```text
data/
│
├── defs/                       # everything `dagster dev` loads
│   ├── __init__.py             # the single Definitions object
│   ├── resources.py            # ConfigurableResource subclasses (~40 lines)
│   ├── ingest.py               # §6.1-6.4 — the four dlt sources, as assets
│   ├── transform.py            # assets that run sql/transforms/*.sql
│   ├── documents.py            # §6.5 — PDF: parse -> chunk -> embed -> index
│   ├── media.py                # §6.6 — video/image: ffmpeg -> Gemini -> Silver -> index
│   ├── publish.py              # Gold Delta -> Postgres, for §9's SQL contract
│   ├── evaluate.py             # §12 — the eval asset
│   ├── checks.py               # @asset_check quality gates
│   └── schedules.py
│
├── sql/
│   ├── 001_init.sql            # Postgres: schemas, extensions, index + ops tables
│   └── transforms/             # what used to be the dbt project
│       ├── silver/
│       │   ├── stg_erp__orders.sql
│       │   ├── stg_erp__customers.sql
│       │   ├── stg_shop__catalog.sql
│       │   └── stg_api__channel_history.sql
│       └── gold/
│           ├── dim_customer.sql · dim_asset.sql
│           └── fct_order.sql
│
├── lib/
│   ├── settings.py             # the single Settings object
│   ├── logging.py              # get_logger + log_event, JSON to stdout
│   ├── delta.py                # read/write/merge/vacuum over deltalake; path helpers
│   ├── sql.py                  # run_sql_to_delta() -- §2
│   ├── db.py                   # psycopg helpers + the §10 retrieval query
│   └── gemini.py               # transcribe() + caption(), with the mock switch
│
├── contracts/                  # Pandera schemas -- every layer, not just Python-written
│   ├── orders.py · catalog.py · channel_history.py
│   ├── document_chunk.py
│   └── asset_artifact.py
│
├── api.py                      # FastAPI: the four endpoints of §9
├── evaluation/
│   ├── datasets/*.jsonl        # labeled cases, in git
│   └── reports/                # GENERATED
├── prompts/                    # the caption instruction
└── tests/
    ├── unit/                   # no container, no network
    ├── integration/            # real Postgres, MinIO, ffmpeg
    └── fixtures/
```

Roughly fifteen Python files, plus a directory of SQL. Version 1.1 specified
about sixty Python files; version 2.0 added a dbt project on top of fifteen.

---

## 6. The six pipelines

Every source type gets a complete path to Gold. The four tabular sources
(§6.1–6.4) differ **only in the dlt source that produces Landing and Bronze** —
from Silver onward they run the same `run_sql_to_delta` against their own `.sql`
file, which is the reason to let dlt own ingestion and DuckDB own SQL rather
than writing six pipelines by hand.

> **Verify before relying on the snippets.** dlt's Delta table format on the
> filesystem destination, `dagster-dlt`'s `@dlt_assets` / `DagsterDltResource`,
> DuckDB's `delta_scan`, and `DeltaTable.merge` are the load-bearing integration
> points. Check them against installed versions
> ([implementation-plan.md](implementation-plan.md) stage 0.5) before treating
> the code below as final. §17 gives the fallback if dlt cannot write Delta.

### The shape every tabular source shares

```python
# defs/ingest.py
import dlt
from dagster_dlt import DagsterDltResource, dlt_assets

@dlt_assets(
    dlt_source=orders_csv_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="orders_csv",
        dataset_name="orders",
        destination=dlt.destinations.filesystem(settings.storage.bronze_url),
    ),
)
def orders_csv_assets(context, dlt_resource: DagsterDltResource):
    # table_format="delta" is set on the resource -- see stage 0.5
    yield from dlt_resource.run(context=context)
```

```python
# defs/transform.py -- the same three lines for every tabular dataset
@asset(key=["silver", "orders"], deps=[orders_csv_assets])
def silver_orders(context) -> MaterializeResult:
    stats = transform_to_silver("orders", contract=OrdersSchema, run_id=context.run.run_id)
    return MaterializeResult(metadata=stats.as_metadata())
```

`deps=[...]` is what `ref()` used to do. It is declared in Python rather than
inferred from SQL, which is one line more typing and one fewer tool.

### 6.1 CSV

```python
from dlt.sources.filesystem import filesystem, read_csv

@dlt.source(name="orders_csv")
def orders_csv_source(bucket_url: str = settings.sources.csv_bucket):
    yield (filesystem(bucket_url=bucket_url, file_glob="orders*.csv") | read_csv())
```

dlt infers the schema, evolves it when the source changes, and records the change
as a visible event (§8). For a file too large for memory, swap `read_csv` for
`read_csv_duckdb`.

### 6.2 Excel

**dlt ships no Excel reader** — verified in
[tech-stack-evaluation.md](tech-stack-evaluation.md) §4. This is the one source
type that needs code, and it needs about fifteen lines: `filesystem()` yields file
items, and a `@dlt.transformer` reads each one with Polars (calamine engine, via
`fastexcel`).

```python
import polars as pl
from dlt.sources.filesystem import filesystem

@dlt.transformer(standalone=True)
def read_excel(items, sheet_name: str = "Sheet1"):
    for item in items:
        with item.open() as f:
            yield pl.read_excel(f, sheet_name=sheet_name).to_dicts()

@dlt.source(name="catalog_xlsx")
def catalog_xlsx_source(bucket_url: str = settings.sources.xlsx_bucket):
    yield (filesystem(bucket_url=bucket_url, file_glob="*.xlsx") | read_excel())
```

Everything downstream is identical to §6.1. That is the payoff of letting dlt own
the boundary: the gap in its coverage costs one transformer, not a new pipeline.

### 6.3 REST API

```python
from dlt.sources.rest_api import rest_api_source

def channel_api_source():
    return rest_api_source({
        "client": {
            "base_url": settings.sources.api_base_url,
            "auth": {"type": "bearer", "token": settings.sources.api_token.get_secret_value()},
            "paginator": {"type": "json_link", "next_url_path": "paging.next"},
        },
        "resources": [{
            "name": "channel_history",
            "endpoint": {
                "path": "/v1/channel/history",
                "params": {"updated_since": {"type": "incremental", "cursor_path": "updated_at"}},
            },
        }],
    })
```

Pagination, auth and the incremental cursor are configuration, not code. dlt
stores the cursor state, so the second run fetches only what is new.

### 6.4 Database

```python
from dlt.sources.sql_database import sql_database

def erp_db_source():
    return sql_database(
        credentials=settings.sources.erp_dsn,
        table_names=["orders", "customers"],
        backend="pyarrow",          # stable destination types
    )
```

`backend="pyarrow"` matters: it keeps source types stable through the write
rather than letting Python objects decide them.

### Bronze → Silver → Gold, for all four

A `.sql` file per Silver table, run by DuckDB against Delta and written back to
Delta. This is `sql/transforms/silver/stg_erp__orders.sql`:

```sql
select
    order_id,
    customer_id,
    cast(amount     as decimal(18,2))  as amount,
    cast(ordered_at as timestamptz)    as ordered_at,
    cast(ordered_at as date)           as event_date,
    'confidential'                     as classification
from delta_scan('{bronze}/orders')
qualify row_number() over (partition by order_id order by ordered_at desc) = 1
```

Explicit columns, never `select *` — a new upstream column must be a reviewable
decision, not a silent schema change. `qualify` does the deduplication.

The Python that runs it is the same for every tabular dataset, which is why
adding the second, third and fourth source is configuration rather than code:

```python
# defs/transform.py
def transform_to_silver(entity: str, *, contract, run_id: str) -> RunStats:
    sql   = read_sql(f"silver/stg_{entity}.sql", bronze=settings.storage.bronze_url)
    table = duckdb_arrow(sql)                       # DuckDB does the SQL
    good, bad = split_on_contract(table, contract)  # Pandera decides (§8)
    if bad.num_rows:
        write_deltalake(quarantine_path(entity), bad, mode="append")
        record_violations(entity, bad, run_id=run_id)
    write_deltalake(silver_path(entity), good, mode="overwrite")
    return RunStats(rows_in=table.num_rows, rows_out=good.num_rows,
                    rows_rejected=bad.num_rows, ...)
```

Gold is the same function against `sql/transforms/gold/*.sql`, reading Silver
instead of Bronze:

```sql
-- sql/transforms/gold/fct_order.sql
select o.order_id, o.customer_id, o.amount, o.event_date, c.country
from delta_scan('{silver}/orders')    o
left join delta_scan('{silver}/customers') c using (customer_id)
```

**Publishing to Postgres is a separate step** (`defs/publish.py`), so a half-built
mart is never visible to the backend: Gold rebuilds in Delta, then one narrow
write moves the finished result across into `gold` tables, inside one transaction.

### 6.5 Documents (PDF)

A PDF stays in Landing byte-for-byte, then becomes text — Python work, so Polars:

```python
# defs/documents.py
def parse_and_index(uri: str, *, embedder, db, config) -> RunStats:
    doc    = DocumentConverter().convert(local_path(uri)).document
    chunks = list(HybridChunker().chunk(doc))            # chunks along structure
    df     = pl.DataFrame([{"document_id": ..., "chunk_index": i,
                            "content": c.text, ...} for i, c in enumerate(chunks)])
    good, bad = split_on_contract(df.to_arrow(), DocumentChunkSchema)
    write_deltalake(silver_path("document_chunk"), good, mode="overwrite")
    db.upsert_chunks(good, embedder.embed(good.column("content").to_pylist()))
    return stats
```

Docling parses layout and tables — the part of a policy PDF actually worth
retrieving — and `HybridChunker` chunks along that structure instead of at a fixed
character count. Silver holds one row per chunk, so a document is a queryable
entity in Gold (`dim_document`) as well as a searchable one.

**An unparseable document is a data quality event, not a crash.** It goes to
quarantine with its error, increments a counter, and the run continues.

### 6.6 Media (video, image, audio)

The one pipeline that is genuinely custom, and the one the product depends on.

| | |
| --- | --- |
| **Input** | one blob in Landing |
| **Output** | Silver Delta `asset_artifact`, frame JPEGs under `silver/frames/<asset_id>/`, chunks in Index |
| **Engine** | `imageio-ffmpeg` → `lib/gemini.py` → Polars → Pandera |
| **Unit of work** | one asset |
| **Idempotency** | `sha256(blob) + extractor_version` — a repeat run makes zero model calls |

Steps, in order:

1. Read the blob; compute its content hash.
2. **Look up `(content_hash, extractor_version)`. On a hit, return the stored artifacts and stop.**
3. Sample frames — `fps=1/2`, longest side 512, capped at 8. An image is its own single frame.
4. Extract audio as mono 16 kHz WAV. Skipped for a still image.
5. Transcribe the audio — `lib/gemini.py::transcribe`.
6. Caption **all frames in one batched call** — `lib/gemini.py::caption` — asking for a caption, any on-screen text, and the structured signals the business domain needs.
7. Validate against `contracts/asset_artifact.py`; quarantine what fails.
8. **`MERGE` the rows into Silver on `asset_id`**, then chunk and embed into Index.

```python
# step 8 -- what version 2.0 could not do
DeltaTable(silver_path("asset_artifact")).merge(
    source=good,
    predicate="target.asset_id = source.asset_id AND target.ordinal = source.ordinal",
    source_alias="source", target_alias="target",
).when_matched_update_all().when_not_matched_insert_all().execute()
```

**This `MERGE` is why Delta is here.** Version 2.0 wrote one deterministic object
per asset and overwrote it in place, because deleting the date partition would
have destroyed every other asset in it. That workaround
([implementation-plan.md](implementation-plan.md) §8.9 in 2.0) is gone: one asset
updating its own rows inside a shared table is exactly what `MERGE` is for.

**Step 2 is load-bearing.** It is what makes extraction cheap to re-run, safe to
call from a request handler, and survivable when Gemini is unreachable — an asset
processed once stays processed. It is also why pre-processing the demo assets the
night before is real insurance rather than a superstition.

**The extractor version is part of the key, not metadata.** It covers the prompt,
the frame sampling parameters and the model ids. Change any of them and the
artifacts change; artifacts from two extractor versions must never mix. Bumping it
invalidates the cache deliberately.

**`extract` returns text and numbers, and that is the whole design.** A transcript
is text. A caption is text. On-screen text is text. Once a video has become a
transcript and eight captions, every layer below this one is doing work it already
knew how to do, and none of it learns that a video existed.

---

## 7. Idempotency and recovery

Delta changes how three of these are enforced, and the rules get simpler for it.

1. **Landing and Bronze are append-only.** dlt writes new files and new Delta
   versions; nothing rewrites history.
2. **Silver and Gold overwrite atomically.** `write_deltalake(..., mode="overwrite")`
   is one commit, not delete-then-write. A crash mid-run leaves the previous
   version intact and readable — version 2.0's rule about ordering the delete
   before the write no longer has anything to order.
3. **Per-key updates use `MERGE`.** Media merges on `(asset_id, ordinal)`. No
   partition is touched to update one asset's rows.
4. **Index upserts on `(document_id, chunk_index, embedder_model_id)`.**
   Re-indexing the same content produces the same rows.
5. **A backfill is the same code over a wider range**, run from the Dagster UI —
   never a separate script. A separate backfill script is a second implementation
   that will drift.

**Time travel is available, and is not a recovery plan.** `DeltaTable(...).history()`
and reading a prior version are genuinely useful for "what did this look like
before the run" — but recovery from a bad transform is a reprocess from Landing,
which is the layer that exists for exactly that.

**`VACUUM` is a deliberate operation, not a schedule.** Delta keeps old versions
until vacuumed; leaving them costs storage and buys time travel. Do not add a
vacuum job before storage is an actual problem, and never set a retention shorter
than the longest-running read.

---

## 8. Contracts and data quality

**One mechanism now, where 2.0 had two.** Pandera covers every layer, because
every layer's data passes through Arrow on its way into Delta — and Delta enforces
the schema on write underneath it.

| Layer | Enforced by |
| --- | --- |
| Bronze | dlt's inferred schema, plus a drift record when it changes |
| Silver, Gold (SQL path) | Pandera on the Arrow result of `run_sql_to_delta`, before the write |
| Silver (Python path — media, documents) | the same Pandera call, on the same Arrow |
| Every Delta write | Delta's own schema enforcement — a write whose schema does not match fails rather than corrupting |

```python
# contracts/orders.py
class OrdersSchema(pa.DataFrameModel):
    order_id:       Series[str]   = pa.Field(str_matches=r"^ORD-\d{4}$", unique=True)
    customer_id:    Series[str]
    amount:         Series[float] = pa.Field(ge=0.0)
    event_date:     Series[object]
    classification: Series[str]   = pa.Field(isin=["public","internal","confidential","pii"])
```

One split function, used by every pipeline:

```python
# lib/contracts.py
def split_on_contract(table: pa.Table, schema) -> tuple[pa.Table, pa.Table]:
    """Return (valid, rejected). Never raises on bad data -- §8's whole point."""
    df = pl.from_arrow(table)
    try:
        schema.validate(df, lazy=True)          # one pass, every violation
        return table, table.slice(0, 0)
    except pa_errors.SchemaErrors as exc:
        bad = set(exc.failure_cases["index"].to_list())
        idx = df.with_row_index()
        return (idx.filter(~pl.col("index").is_in(bad)).drop("index").to_arrow(),
                idx.filter(pl.col("index").is_in(bad)).drop("index").to_arrow())
```

No `Validator` port, no `ValidationResult` entity, no `QualityDecision` enum, and
no second contract language in YAML — one function and two tables.

### Quarantine, not drop

Rejected rows are appended to a Delta table under `quarantine/<entity>/` with the
violation, the contract version and the run id attached, and counted in
`ops.quality_violations`. **Dropping rows is indistinguishable from never having
received them.** Quarantine keeps the difference visible, and reprocessing a fixed
batch is an ordinary run over a different table.

### The gate is an asset check

Whether a failure blocks downstream work is a Dagster decision, expressed where
the asset is:

```python
# defs/checks.py
@asset_check(asset=silver_orders, blocking=True)
def no_rejected_rows(context) -> AssetCheckResult:
    rejected = _latest_metadata(context, "rows_rejected")
    return AssetCheckResult(passed=rejected == 0, metadata={"rows_rejected": rejected})
```

`blocking=True` stops downstream assets; the default warns. The decision shows up
in the UI next to the data it is about, which is where someone will look for it.

**Thresholds live in `Settings`, never in code.** A hard-coded `if bad > 100`
breaks the first week real volume passes it, and it breaks by blocking a healthy
pipeline.

### Schema evolution

dlt records Bronze schema changes as events; **never silently drop an unknown
column** — a producer adding a field must produce a logged drift record and a
warning check. Silver and Gold are schema-on-write, so a breaking change is a new
contract version with a grace period, never an edit in place:

| Change | Compatible? | Allowed |
| --- | --- | --- |
| Add a nullable column | backward | yes |
| Add a required column | breaking | new version, with a default during a grace period |
| Widen a type | backward | yes |
| Narrow a type, rename, remove | breaking | new version, only after consumers confirm |

Delta's `schema_mode="merge"` makes an additive change one argument. **Do not
reach for it to silence a failing write** — a write failing on a schema mismatch
is the contract working, and `schema_mode="merge"` on a narrowing change is how
you corrupt a table quietly.

**Never couple Gold to Bronze column names.** Silver exists to absorb source
renames; if a Bronze rename reaches Gold, a layer was skipped.

---

## 9. Serving

Two consumers, two doors.

### The .NET backend reads SQL

Gold Delta is published to Postgres and exposed as **versioned views**, never as
tables: `api.v1_order_daily`, `api.v1_asset_overview`. The view is the contract. A
`gold` table can be refactored freely as long as the view still returns what it
promised; the backend connects with a `backend_reader` role that has `SELECT` on
the `api` schema and nothing else. **That denial is what makes the boundary real**
rather than a convention.

Gold lives in two places on purpose — Delta for analytics and reprocessing,
Postgres for serving. The publish step is one direction only, and Delta is the
source of truth.

### The agent layer calls HTTP

`api.py` — a thin FastAPI app on `:8002`. It holds no state and owns no data: it
reads Postgres and calls the same functions Dagster calls.

```
GET  /health
     → {"status":"ok","db":true,"assets":12}

GET  /api/v1/data/query?q=<text>&top_k=5
POST /api/v1/data/query          {"q":"<text>","top_k":5}
     → {"items":[
          {"id":    "VID-20260821-a1b2c3:frame_caption:07",
           "text":  "Frame at 7s: hand holding the product, on-screen text 'GIAM 50%'",
           "score": 0.83,
           "metadata":{"asset_id":"VID-20260821-a1b2c3","kind":"frame_caption","t_seconds":7}}
        ]}

POST /api/v1/assets              {"uri":"/uploads/videos/x.mp4","kind":"video"}
     → {"asset_id":"VID-20260821-a1b2c3","status":"ready","cached":false,
        "artifacts":{"frames":8,"duration_s":15.2,"has_transcript":true,"chunks":9}}

GET  /api/v1/assets/{asset_id}
     → {"asset_id":"…","kind":"video","duration_s":15.2,"transcript":"…",
        "frames":[{"t":0,"caption":"…","ocr_text":"…"}],"signals":{...}}
```

**The four field names in `items` are dictated, not chosen.**
`agent/infrastructure/retrieval/http_json_retriever.py` is a generic REST-JSON
adapter that issues a `GET` with `q` and `top_k` and maps `items[*].id/text/score`.
Emitting that shape costs nothing and means the agent side needs a four-line
mapper rather than a new adapter.

**One handler answers both GET and POST.** The agent adapter issues GET;
`integration-architecture.md` specifies POST. Both are satisfied by two route
decorators over one function, which is cheaper than a negotiation.

**`POST /api/v1/assets` is synchronous.** It runs extraction and returns when the
artifacts exist — seconds, and free on a cache hit. No queue, no job id, no
polling endpoint. Every one of those omitted mechanisms is a component that can
fail during a demo. §16 records the trigger for adding them.

**It receives a path, never bytes** — see §4, the shared upload volume — and the
path is a trust boundary: resolve it under `ASSET_ROOT` and reject with `400
INVALID_URI` anything that escapes.

**Every error is the same envelope**, matching what the other pods emit:
`{"error": {"code": "...", "message": "...", "request_id": "..."}}`.

**`/health` always returns 200 while the process is alive.** Compose health checks
use `curl -f`, so a 503 on a database outage would stop the other pods from ever
starting. `status` is `"ok"` or `"degraded"` and `db` is a boolean.

---

## 10. Retrieval

Dense-only retrieval misses exact identifiers, rare tokens and misspellings.
Lexical-only misses paraphrase. Both legs run, and their **ranks** are fused with
Reciprocal Rank Fusion — rank, not score, which is why no calibration between the
two scales is needed.

This is **one SQL query** against Postgres, not three adapter classes:

```sql
-- lib/db.py
with dense as (
    select chunk_id, row_number() over (order by embedding <=> %(qvec)s) as rank
    from "index".embedding
    where embedder_model_id = %(model)s
    order by embedding <=> %(qvec)s limit %(leg_k)s
),
lexical as (
    select chunk_id, row_number() over (order by score desc) as rank
    from (
        select chunk_id,
               greatest(
                   similarity(public.immutable_unaccent(content), public.immutable_unaccent(%(q)s)),
                   ts_rank(content_tsv, plainto_tsquery('simple', public.immutable_unaccent(%(q)s)))
               ) as score
        from "index".chunk
    ) s where score > %(threshold)s
    order by score desc limit %(leg_k)s
)
select c.chunk_id, c.content, c.metadata,
       sum(1.0 / (%(rrf_k)s + r.rank)) as score
from (select * from dense union all select * from lexical) r
join "index".chunk c using (chunk_id)
group by 1,2,3 order by score desc limit %(top_k)s
```

**The index stays in Postgres, not Delta.** Delta has no vector index and no
trigram operator; this query is the reason Postgres is still here beyond serving.

**An honest limitation: Postgres ships no Vietnamese full-text configuration.**
There is no `vietnamese` text search dictionary, so stemming and stop-words are
unavailable. The mitigation is `unaccent` plus the `simple` configuration for
tokenization, with `pg_trgm` trigram similarity carrying most of the lexical
weight — trigram matching is diacritic- and typo-tolerant, which covers much of
what a real analyzer would do, without another service. This is a real limitation,
not a solved problem; anyone reporting retrieval quality on Vietnamese text should
say so. §16 names the upgrade.

`unaccent()` is not `IMMUTABLE`, so it cannot appear in a generated column or an
index expression — hence the `public.immutable_unaccent(text)` wrapper used in
both the `content_tsv` column and the trigram index. Dropping the wrapper and
calling `unaccent` directly fails at DDL time, and the natural "fix" is to remove
`unaccent`, which silently deletes the entire Vietnamese mitigation.

**RRF ranks, it does not score.** Fused values cluster near `1/61 ≈ 0.016`, so
normalize to `[0,1]` by the maximum in the returned set before the response leaves
the API. This is presentation only.

**`embedder_model_id` is part of the key, not metadata.** Embeddings from two
models are not comparable, and mixing them degrades retrieval in a way that is
very hard to notice and very easy to prevent. Changing the model means a new index
generation and a rebuild — cheap, because Index is derived.

**Media enters this index as text.** A frame becomes a caption; a caption is text.
Video, image, PDF and CSV-derived text share one vector space and one query path.
The alternative — a multimodal model putting pixels and text in a shared space —
costs a second index, a second retrieval path and a second eval, and produces
vectors where the agent needs words. Where it breaks: caption similarity is
topical similarity, so two visually different creatives described the same way
will collide. That is acceptable for search and not acceptable for near-duplicate
detection over a large catalog; §16 records both triggers, and the cheap fix is a
perceptual-hash column, not CLIP.

---

## 11. Observability

**Structured JSON to stdout. No `print()`.** Collection and routing are the
environment's job.

```python
log_event(logger, "info", "asset_extracted",
          run_id=run_id, asset_id=asset_id, content_hash=h,
          extractor_version=v, cache_hit=False,
          frame_count=8, transcript_char_count=1841, duration_ms=4182)
```

`lib/logging.py` is `get_logger(name)` and `log_event(logger, level, event, **fields)`
— about eighty lines, mirroring `agent/observability/logging.py` so both Python
pods emit the same shape. `log_event`'s keyword-only signature is what forces
structured fields at every call site; that is why structlog was dropped.

Fields that must be present where they apply: `run_id`, `asset_key`, `partition`,
`dataset`, `rows_in`, `rows_out`, `rows_rejected`, `bytes_written`, `duration_ms`,
`contract_version`. For media, four more: `asset_id`, `content_hash`,
`extractor_version`, `cache_hit`.

**`cache_hit` is the one to watch.** A collapsing hit rate means the extractor
version is churning or the same asset is arriving as different bytes — both are
cost problems that stay invisible until the bill arrives.

**Never log** API keys, connection strings, full record payloads, or any column
classified `pii`. **Transcripts and captions count as payload** — a transcript is
a verbatim record of what someone said and routinely contains names and phone
numbers. Log the character count and the model id, never the text. This rule gets
forgotten because a transcript does not look like a database row.

**Lineage is the Dagster asset graph.** With dbt gone there is no manifest and no
column-level lineage inside the SQL layer — the graph is table-to-table, derived
from the `deps=[...]` declarations in `defs/`. That is a real reduction in
fidelity and worth knowing before someone asks which column fed which. **Delta's
commit history is the second half**: `DeltaTable(...).history()` records who wrote
each version and when, which covers "when did this table last change" without any
extra tooling.

`ops.run_log` and `ops.quality_violations` in Postgres hold the durable history
the Dagster UI only shows for recent runs.

---

## 12. Evaluation

A retrieval or extraction pipeline has no single correct output, only a measurable
quality level. Ordinary tests assert equality; this one asserts
`quality >= threshold`.

```
evaluation/datasets/retrieval.jsonl   {"query": "...", "expected_chunk_ids": [...]}
                    ↓
defs/evaluate.py    a Dagster asset -> scikit-learn -> Markdown report
                    ↓
evaluation/reports/ precision, recall, F1, confusion matrix, n, per arm
```

Three properties make this a pipeline rather than a notebook:

1. **Reproducible** — the report names the dataset version, the pipeline version and the config that produced it.
2. **Re-run on change** — it is an asset with upstream dependencies, so it re-runs when they change rather than when someone remembers.
3. **Comparable** — it runs at least two arms, a baseline and the pipeline under test, over identical cases. Two arms over the same cases is the only honest way to claim an improvement.

**Labeled cases live in git, as JSONL.** Not in a database, not in a spreadsheet.
Labels are source code: they get reviewed, they get diffed, and changing them must
be as visible as changing the code they measure.

---

## 13. Security and governance

| Concern | Rule |
| --- | --- |
| Classification | every field carries `public` / `internal` / `confidential` / `pii`, set in the contract |
| PII tagging | applied at landing in Silver, never retrofitted |
| Secrets | environment variables locally, a secret manager in cloud; never in git, never in logs |
| DB roles | `data_writer` (writes `gold`/`index`/`ops`), `backend_reader` (`SELECT` on `api` only) |
| Object storage | per-bucket credentials; the pipeline role cannot delete Landing |
| Production data on laptops | prohibited — the most common avoidable PII leak. Use generated fixtures |
| Uploaded media | classified `confidential` at registration, never after: it may contain identifiable people and was uploaded for one purpose |
| Media leaving the machine | frames and audio go to a hosted model. Say so in the privacy notice; §16 keeps the local-model successor open as the answer when a customer objects |
| Retention | Landing per policy, Silver aligned to it, quarantine 90 days, Index rebuildable so retention is irrelevant |
| **Right to erasure** | a `DELETE` on the Delta table plus a Gold rebuild plus an Index rebuild. Delta makes this a supported operation rather than a partition rewrite — but **`VACUUM` is required afterwards**, or the deleted rows remain readable through time travel |

**Every dataset has exactly one owner**, recorded beside its contract. A dataset
owned by everyone is maintained by no one.

---

## 14. Naming

```
delta tables   <layer>/<dataset>                       landing/orders · bronze/orders
               <layer>/<entity>                        silver/orders · gold/fct_order
               quarantine/<entity>
               layer ∈ {landing, bronze, silver, gold, quarantine}

media          landing/assets/<kind>/<asset_id>.<ext>
               silver/frames/<asset_id>/<NN>.jpg
asset_id       <PREFIX>-<YYYYMMDD>-<6 hex>             VID · IMG · AUD · DOC
chunk id       <document_id>:<kind>:<NN>               VID-20260821-a1b2c3:frame_caption:03

sql files      sql/transforms/silver/stg_<source>__<entity>.sql
               sql/transforms/gold/dim_<entity>.sql · fct_<event>.sql
postgres       gold.dim_<entity> · gold.fct_<event> · api.v<major>_<name>
               index.chunk · index.embedding · ops.run_log · ops.quality_violations
dagster keys   ["bronze", <source>, <dataset>] · ["silver", <entity>] · ["gold", <model>]
timestamps     <verb>_at, always UTC, always timezone-aware
```

**Partition columns are a Delta table property, not a path convention.** Delta
records partitioning in its own metadata, so the Hive-style
`event_date=2026-08-19/` directory naming that version 2.0 specified is now
delta-rs's business rather than something a pipeline constructs. Pass
`partition_by=["event_date"]` on the write and stop thinking about paths.

**The asset-id discriminator is derived, never a counter.** A sequence needs
per-kind-per-day state and is non-deterministic under retry, so the same file
reprocessed gets a second id and a second copy. Two derivations, in order of
preference: reuse the caller's trailing entropy when there is one (the backend's
`ANL-20260821103000-a1b2c3` becomes `VID-20260821-a1b2c3`), otherwise
`sha256(bytes)[:6]`. Both are deterministic, so a retry produces the same id and
the same path, and `UNIQUE(content_hash)` catches genuine duplicate uploads that a
random id would silently admit.

---

## 15. Testing

```text
tests/
├── unit/          no container, no network, no API key. Milliseconds.
├── integration/   real Postgres, real MinIO, real ffmpeg, a real API key
└── fixtures/
```

| Tier | Proves | Rule |
| --- | --- | --- |
| Unit | contracts, chunking, id derivation, RRF, the cache decision, the SQL files against a local Delta fixture | if it needs a container, it is not a unit test |
| Integration | each real dependency behaves as assumed | real dependencies — mocked drivers hide driver bugs |
| Evaluation | quality is above threshold (§12) | `quality >= threshold`, not `expected == actual` |

Two things make the unit tier fast and offline:

- **`settings.use_mock_models = true`** — the media pipeline runs end to end with
  deterministic fake transcripts and captions, no network, no key.
- **Delta is a directory.** A unit test writes a small Delta table to `tmp_path`,
  points a `.sql` file at it, and asserts on the result — no container needed to
  test SQL, which is the part version 2.0 could only test with dbt running.

**There is no architecture-rules test.** Version 1.1 ran AST scans to enforce its
import boundaries. There are no import boundaries left to enforce, and a test that
checks a rule nobody can violate is maintenance with no yield.

---

## 16. Evolution path

Every row is a real ceiling with a real successor. **The trigger column exists so
nobody upgrades early.**

| Today | Trigger | Then |
| --- | --- | --- |
| Delta via delta-rs, single writer | genuine concurrent writers to one table | Delta already handles it — enable the optimistic-concurrency path and a locking provider for S3 |
| No `VACUUM` schedule | storage cost becomes visible, or a compliance delete must actually remove bytes | a scheduled `VACUUM` with a retention longer than the slowest reader |
| No `OPTIMIZE` / compaction | many small files slow reads — likely first on the media table | `OPTIMIZE` with Z-ordering on the common filter column |
| Plain `.sql` files run by DuckDB | more than roughly a dozen models, or real macro reuse across them | reconsider dbt or SQLMesh — 3.0 removed dbt for six datasets, not on principle |
| Table-level lineage only | someone needs to know which column fed which | dbt's manifest, or OpenLineage emission |
| DuckDB single-node | a transform no longer fits one machine | a distributed engine, or push into a warehouse |
| Batch ingestion | a consumer's value depends on sub-minute freshness | Postgres logical replication, then CDC |
| pgvector | vector count or QPS degrades recall or latency | a dedicated vector store, accepting a second store to keep in sync |
| Postgres FTS + trigram | Vietnamese lexical quality becomes the binding constraint (§10) | a search engine with a real Vietnamese analyzer |
| Hosted Gemini transcription | the network dependency becomes unacceptable, Vietnamese quality binds, or a customer refuses to let audio leave the machine | `faster-whisper` (base, int8, CPU) — no torch, ~150 MB, one file changes |
| Captions as the only media signal | an eval **shows** caption retrieval losing — an intuition is not the trigger | a multimodal embedding model, accepting a second vector space |
| No perceptual hashing | near-duplicate detection over a catalog becomes a requirement | `imagehash.phash` as a `bigint` column, Hamming distance in SQL |
| Synchronous `POST /assets` | extraction starts exceeding the caller's timeout | a job id and a polling endpoint, then a real queue — in that order |
| `dagster dev` | scheduled runs must survive a laptop closing | Dagster in a container, then on K8s |

**And the trigger for reintroducing an abstraction a previous version removed:** a
second implementation that actually exists. A `Protocol` with one implementation is
a wrapper; with two live implementations it is a seam. `lib/gemini.py`'s mock
switch is the current answer for the only boundary that needs one.

**Record why, when you do it.** Each of these is worth a short ADR. The
architecture in this document is an engineering hypothesis, not a permanent truth,
and the reasoning behind a change is worth more later than the change. Two
decisions have already been reversed this way — structlog, and now dbt and the
table format — and each reversal is recorded rather than quietly applied.

---

## 17. Build order

Stage gates and the file manifest are in
[implementation-plan.md](implementation-plan.md). The order in one line:

```
environment → CSV to Gold → the other three tabular sources → documents →
media → index + retrieval → API → publish to Postgres → eval
```

**CSV first, and all the way to Gold before the second source type.** The four
tabular sources share every step after Bronze, so proving the shared path once
makes the next three configuration rather than construction. Media comes late
because it is the only pipeline with genuinely custom code, and it should be built
against boundaries the others have already exercised.

**Verify these four before writing code against them:**

| Claim | Why it matters | If it fails |
| --- | --- | --- |
| dlt's filesystem destination writes Delta | it is how Bronze gets its format | dlt writes Parquet to **Landing**; a small Polars step produces Bronze Delta. §3's Landing/Bronze split makes this a step the architecture already names, not a patch |
| DuckDB's `delta_scan` reads Delta on object storage | every `.sql` file depends on it | read Delta with Polars and register the Arrow table into DuckDB — one extra line per transform |
| `DeltaTable.merge` works as §6.6 uses it | it is why Delta is here at all | fall back to 2.0's per-asset object, and re-open whether Delta is earning its place |
| `dagster-dlt`'s `@dlt_assets` signature | how ingestion becomes assets | call the dlt pipeline inside a plain `@asset` — it is a normal Python call |

These are the integration points this architecture leans on, their signatures move
between releases, and finding out at hour 14 is expensive.
[tech-stack-evaluation.md](tech-stack-evaluation.md) §14 applies the same "verify
before pinning" rule to the media and serving wheels.

---

## 18. Review checklist

Architecture:

- [ ] Every asset body calls a function; no asset contains the logic (§2)
- [ ] DuckDB never writes Delta — it returns Arrow, and `deltalake` writes (§2)
- [ ] No `Protocol` exists without two live implementations (§16)
- [ ] Nothing is hard-coded that belongs in `Settings` — thresholds, paths, model names, `top_k` (§8)
- [ ] No `print()`; every step emits one structured event (§11)

Data:

- [ ] Landing and Bronze are append-only (§7)
- [ ] Silver and Gold writes are one atomic commit, not delete-then-write (§7)
- [ ] Per-key updates use `MERGE`, never a partition rewrite (§7)
- [ ] Every `.sql` file names its columns explicitly — no `select *` across a layer (§6)
- [ ] Bad rows are quarantined with their violation attached, never dropped (§8)
- [ ] `schema_mode="merge"` is used for a genuine additive change, never to silence a failing write (§8)
- [ ] Every derivation is keyed so a re-run is free — `content_hash + extractor_version`, `(document_id, chunk_index, embedder_model_id)` (§6.6, §7)
- [ ] Gold is never coupled to a Bronze column name (§8)

Boundaries:

- [ ] The backend reads `api.v1_*` views, never `gold` tables (§9)
- [ ] `/api/v1/data/query` returns `items[*].{id,text,score,metadata}` (§9)
- [ ] `POST /api/v1/assets` takes a path, resolved under `ASSET_ROOT` (§9)
- [ ] `/health` returns 200 even when the database is down (§9)

Governance:

- [ ] No transcript, caption or record payload appears in a log (§11)
- [ ] Every field carries a classification; PII is tagged at landing (§13)
- [ ] A deletion is followed by `VACUUM`, or the rows are still readable (§13)
- [ ] Every dataset names one owner (§13)

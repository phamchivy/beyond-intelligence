# Data Layer — Framework & Tool Evaluation

> The candidates considered for each category of the `data/` layer, what each is genuinely good and bad at, and which one was chosen. This is a decision record: it exists so nobody re-opens a settled question under time pressure, and so a future reader can tell whether a decision was reasoned or inherited.

**Version:** 1.1
**Date:** 18/08/2026
**Companion documents:** [data-architecture.md](data-architecture.md) — the architecture these tools implement · [implementation-plan.md](implementation-plan.md) — the build order
**Versions verified against PyPI:** 12/08/2026 for the original table; the media and serving packages added in §14 are **unverified and must be checked before pinning**

**Changes in 1.1.** Four new categories, all forced by media becoming a first-class source type: decoding (§15), transcription (§16), frame understanding (§17) and the serving API framework (§18). §2, §12, §13 and §14 are updated to match. No decision from 1.0 was reversed.

---

## 1. How these were judged

Five criteria come from the project brief ([../README.md](../README.md) §3: *"the initial implementation should favor lightweight components that are easy to deploy locally"*):

| # | Criterion | The test applied |
|---|---|---|
| 1 | **Lightweight** | How many processes must be running for a developer to do useful work? Fewer is better; zero is best. |
| 2 | **Code-first** | Is the primary authoring surface Python (or SQL), reviewable in a pull request? YAML-as-programming-language is disqualifying. |
| 3 | **Widely recognised** | Would a data engineer already know it, and is there an answer on the internet when it breaks at 2am? |
| 4 | **Local and cloud** | Does the same code run on a laptop and in a deployment, with only configuration differing? |
| 5 | **Scales with the workload** | Is there a credible path from "one CSV" to real volume that does not require a rewrite? |

Two more come from the project's own architecture standard:

| # | Criterion | The test applied |
|---|---|---|
| 6 | **Swappable behind a port** | Can it live in `infrastructure/` as one adapter, so replacing it touches one file? A tool that must be imported throughout the codebase fails this. |
| 7 | **No JVM, no cluster, for the first cut** | Does it add a runtime, a coordinator or a broker before there is data volume to justify one? |

**Criterion 6 is the one that lowers the cost of being wrong.** Most decisions below are reversible precisely because the tool sits behind a `Protocol`. §12 identifies the three that are not.

---

## 2. Decisions at a glance

| Category | Chosen | Runner-up | The deciding reason |
|---|---|---|---|
| Orchestration | **Dagster** | Prefect | Assets, not tasks — lineage, a catalog and quality checks come from the model itself instead of a bolt-on |
| Ingestion | **dlt** | Sling | A library, not a platform; schema inference, evolution and incremental state for free |
| Python compute | **Polars** | DuckDB alone | Multi-core, Arrow-native, lazy, with typed expressions that fail at build time |
| SQL / analytics engine | **DuckDB** | ClickHouse | Zero-infrastructure OLAP over Parquet, reads object storage directly |
| SQL modelling | **dbt-core** | SQLMesh | Its tests double as quality gates and its manifest gives column lineage; the team already knows it |
| Record contracts | **Pydantic v2** | attrs + cattrs | Already the project idiom; one model does validation *and* JSON Schema export |
| Frame contracts | **Pandera** | Great Expectations | Code-first schemas that read like Pydantic, with a first-class Polars backend |
| Quality gating | **Dagster asset checks** | Soda Core | The gate belongs with the asset, visible in the same UI, with no second tool |
| Document parsing | **Docling** | `unstructured` | Fully local, layout- and table-aware, with its own chunkers; permissive licence |
| Media decoding | **`imageio-ffmpeg`** | `apt-get install ffmpeg` | A pip-installed static binary — no apt layer, no root, no image bloat |
| Transcription | **Gemini audio** | `faster-whisper` | No local weights and no torch; the network dependency is paid down by the cache, not by a model |
| Frame understanding | **one batched VLM call** | CLIP + a separate OCR | Caption, on-screen text and structured signals in a single request; deletes an entire pipeline stage |
| Serving API | **FastAPI + uvicorn** | Litestar | Matches the other three pods; its generated `/docs` is how the pods keep schemas in sync |
| Embeddings | **fastembed** | sentence-transformers | ONNX, no PyTorch, fast on CPU, multilingual models available |
| Vector + lexical search | **Postgres + pgvector + pg_trgm** | Qdrant | One store instead of two, transactionally consistent with Gold, and .NET can read it with SQL |
| Object storage | **MinIO** → S3/R2/GCS via `fsspec` | direct boto3 | One adapter covers local and every cloud |
| File format | **Parquet + zstd** | Avro | Columnar with pushdown in every engine here |
| Table format | **plain Parquet now** | Iceberg | Nothing yet needs ACID, `MERGE` or time travel — see §12 |
| Evaluation | **JSONL in git → asset → scikit-learn → report** | promptfoo | Full control over metrics, and reproducibility comes from being an asset |
| Logging | **stdlib `logging` + JSON formatter**, mirroring `agent/` | structlog | The agent's `log_event(**fields)` already forces structured fields; zero dependencies and one log shape across both pods (§11, reversed) |
| Packaging | **uv** + **Ruff** | Poetry + Black + Flake8 | One fast tool for dependencies, one for lint and format |
| Config | **pydantic-settings** | dynaconf | Typed, validated at startup, matches the agent layer |

---

## 3. Orchestration

### Candidates

**Apache Airflow**

| Good at | Bad at |
|---|---|
| The most widely recognised orchestrator; the largest operator ecosystem; managed everywhere (MWAA, Cloud Composer) | Heavy locally — a scheduler, a webserver and a metadata database before anything runs |
| Battle-tested at very large scale; every failure mode has been written about | Task-centric: it orchestrates *work*, not *data*, so "which table is stale" is not a question it answers natively |
| Every data engineer has used it | Lineage requires OpenLineage as a bolt-on; data-awareness has improved but is not the core model |
| | Backfill is real but operationally fiddly; DAG authoring carries noticeable boilerplate |

**Dagster**

| Good at | Bad at |
|---|---|
| Asset-oriented: you declare the table that should exist, and lineage, a catalog and freshness follow from the declaration | Smaller ecosystem than Airflow; fewer pre-built integrations |
| `dagster dev` is one process — no scheduler, broker or metadata service needed locally | The asset mental model takes an afternoon to learn if you come from Airflow |
| Assets, checks, partitions and resources are plain Python and directly unit-testable | Opinionated: fighting the asset model is unpleasant, so imperative task graphs feel awkward |
| Partitions and backfills are first-class rather than bolted on | The richest operational features sit in the paid tier, though OSS is fully usable |
| Native `dagster-dlt`, `dagster-dbt`, `dagster-duckdb` integrations | |

**Prefect**

| Good at | Bad at |
|---|---|
| The lightest developer experience — decorate a function and it is a flow | Weaker data-asset model, so lineage and "is this table fresh" need more manual work |
| Excellent dynamic and conditional workflows; genuinely Pythonic | The OSS server is an execution UI more than a data catalog |
| Very low ceremony for small projects | Partition-based backfill is less structured than Dagster's |

**Kestra / Windmill**

| Good at | Bad at |
|---|---|
| Fast to start; good UIs; language-agnostic | **YAML-first authoring** — fails criterion 2 outright |
| Kestra's declarative model is genuinely clean | Smaller communities; logic ends up split between YAML and code |

**Plain Python + cron / Makefile**

| Good at | Bad at |
|---|---|
| Zero dependencies, zero learning curve, total control | You will hand-write retries, partitions, backfill, scheduling, run history and lineage — badly, and while under time pressure |
| Honest for a genuinely tiny project | No UI, so "did it run and was it correct" becomes a manual question |

### Chosen: Dagster

**Why it suits this project specifically.** The architecture requires lineage (§13), a quality gate attached to each dataset (§10), partitioned idempotent runs (§8) and an evaluation step that re-runs when its inputs change (§7.5). With Dagster, all four are consequences of the asset model rather than four separate pieces of work. With Airflow or Prefect they are four separate pieces of work — and the platform is meant to be *explainable and traceable*, which makes lineage a requirement rather than a nice-to-have.

The local footprint decides the rest. `dagster dev` is a single process next to two containers, satisfying "easy to deploy locally" in a way Airflow does not. And because the architecture forbids business logic inside assets (§2), the assets stay thin enough that this choice remains reversible.

**Trade-off accepted.** Airflow would be the safer answer for recognisability, and a data engineer joining this project is more likely to know Airflow than Dagster. Accepted because the asset model buys features this specific architecture needs, and because §2's rule — assets are thin callers of plain functions — means a migration to Airflow would rewrite `orchestration/` only, not the pipelines.

**Trigger to switch:** the team standardises on Airflow elsewhere, or an Airflow-only operator becomes essential.

---

## 4. Ingestion

### Candidates

**dlt (data load tool)**

| Good at | Bad at |
|---|---|
| A `pip install`, not a platform — runs in-process, inside any orchestrator | Younger than the alternatives; fewer pre-built connectors than a connector marketplace |
| Automatic schema inference *and* evolution, with the changes recorded | Its normalization conventions must be learned, and they are opinionated (nested JSON becomes child tables) |
| Incremental loading with managed state, so watermarks are not hand-rolled | Very large volumes eventually want a specialised engine |
| Core sources cover REST APIs, 30+ SQL databases and object storage/filesystem | **No built-in Excel reader** — verified against the source tree |
| Destinations include DuckDB, Postgres and filesystem/Parquet | |

**Airbyte**

| Good at | Bad at |
|---|---|
| Hundreds of connectors; a real UI; a large community | Heavy — a container per connector, plus a control plane. Fails criteria 1 and 7 |
| Excellent when you need many SaaS sources and nobody wants to write code | Configuration-first, so pipelines live outside your repository |
| | Overkill for six source *types* rather than sixty source *systems* |

**Meltano / Singer**

| Good at | Bad at |
|---|---|
| The open Singer tap/target spec; a genuine plugin ecosystem | YAML-first configuration; the tap ecosystem varies a lot in quality and maintenance |
| Lighter than Airbyte | Singer's per-record JSON protocol is slow, and much of the ecosystem has lost momentum |

**Sling**

| Good at | Bad at |
|---|---|
| A single fast Go binary; excellent for database-to-database and file-to-database | YAML/CLI-first; not a Python library, so it cannot sit behind a Python port cleanly |
| Genuinely lightweight | Weaker REST API support; less control over schema evolution |

**Fivetran / managed SaaS**

| Good at | Bad at |
|---|---|
| Zero maintenance; excellent reliability | Paid, per-row pricing; a cloud dependency; fails "runs locally" outright |

**Fully custom Python**

| Good at | Bad at |
|---|---|
| Total control; no dependency to learn | You reimplement pagination, retries, schema inference, evolution and incremental state — the exact features that are boring to write and embarrassing to get wrong |

### Chosen: dlt

**Why it suits this project specifically.** The requirement is six *source types*, not sixty source systems — and dlt's three core sources cover five of them directly (`rest_api`, `sql_database`, and `filesystem` with its `read_csv` / `read_jsonl` / `read_parquet` / `read_csv_duckdb` readers). Because it is a library, it sits inside a Dagster asset and behind a `Source` port with no separate service, which is exactly what criteria 1, 6 and 7 ask for.

The decisive feature is schema evolution. §9 requires that an upstream column addition produce a *visible event* rather than silence. dlt does that by default; a custom loader would need it built deliberately, and it is the kind of thing that gets deferred and then forgotten.

**The Excel gap, stated plainly.** dlt ships no Excel reader — verified by reading `dlt/sources/filesystem/readers.py`, which provides only CSV, JSONL, Parquet and a DuckDB-backed CSV reader. Excel therefore needs a small custom transformer (`polars.read_excel`, calamine engine via `fastexcel`) fed by `filesystem()` file items. This is roughly twenty lines, and the architecture already anticipates it as its own adapter (`infrastructure/sources/excel_source.py`). Worth knowing before someone assumes Excel is free.

**Trigger to switch:** dozens of SaaS sources appear and connector maintenance becomes the bottleneck — then Airbyte or a managed platform earns its weight.

---

## 5. Compute and transformation

### Candidates

**Polars**

| Good at | Bad at |
|---|---|
| Multi-core by default; Arrow-native; lazy evaluation with real query optimisation | A smaller ecosystem than pandas; some library still expects a pandas frame |
| Typed expressions catch errors at plan time rather than mid-run | The API is different enough from pandas to need genuine learning |
| A streaming engine for larger-than-memory work on one machine | Single-machine only |
| Explicit null handling — no silent `NaN`/`None` conflation | |

**DuckDB**

| Good at | Bad at |
|---|---|
| Full SQL OLAP with no server; reads Parquet on S3/MinIO directly via `httpfs` | Single-process; not a concurrent multi-writer database |
| Zero-copy interop with Arrow and Polars | Row-by-row procedural logic is awkward — that is what Polars is for |
| Excellent at joins and aggregation over Parquet; can attach Postgres | Memory limits on very large joins, though it spills to disk |
| SQL is the most transferable skill on any data team | |

**pandas**

| Good at | Bad at |
|---|---|
| The most widely known dataframe API; unmatched ecosystem | Single-threaded; memory-hungry (frequently several times the data size) |
| The right escape hatch for `openpyxl`, scikit-learn and plotting | Weak typing; silent coercions; `SettingWithCopyWarning` as a way of life |

**Apache Spark / PySpark**

| Good at | Bad at |
|---|---|
| The genuine answer above single-machine scale; mature; ubiquitous in enterprises | JVM, cluster, configuration; tens of seconds of startup before any work happens |
| One API for batch and streaming | Fails criteria 1 and 7 decisively. For gigabytes it is slower end-to-end than DuckDB |

**Daft**

| Good at | Bad at |
|---|---|
| Distributed Python-native dataframes; strong at multimodal data | Much smaller community; fails criterion 3 today |

### Chosen: Polars for Python transforms, DuckDB for SQL and analytics

**Why both, and why this split.** They are complementary rather than competing, and they share Arrow so passing data between them is free. The split follows the shape of the work:

- **Polars** for `normalize` (§7.2) — per-column casting, deduplication, named transformer steps, and the valid/quarantine split. This is procedural row-shaping work, and typed expressions catch mistakes before the data moves.
- **DuckDB** for `model` (§7.3) — joins and aggregation across Silver Parquet on object storage. This is what SQL is for, and it keeps the modelling layer in the most transferable language on the team.

Both are libraries. Neither adds a process, and both run identically on a laptop and in a container.

**On Spark.** The project brief lists it as a candidate and the team has production experience with it, which makes it the tempting choice. Rejected for the first cut: at the data volumes this platform will see, a JVM and a cluster cost more in startup latency and operational complexity than they return, and DuckDB will finish first in wall-clock time. §17 of the architecture names the trigger for revisiting.

**On pandas.** Kept as a deliberate escape hatch, never as the primary engine — `openpyxl` for awkward Excel files, scikit-learn interop in the eval harness. Both Polars and DuckDB convert to pandas in one call when a library demands it.

---

## 6. SQL modelling layer

### Candidates

**dbt-core**

| Good at | Bad at |
|---|---|
| The de facto standard for SQL transformation; enormous community | Jinja-templated SQL becomes hard to read as macros accumulate |
| Built-in tests (`unique`, `not_null`, `relationships`, `accepted_values`) that double as quality gates | Model-level lineage by default; column-level is a newer and less complete story |
| Its manifest produces lineage and documentation automatically | Python models exist but are second-class |
| Adapters for DuckDB and Postgres; native `dagster-dbt` integration | Another tool with its own project layout and conventions |

**SQLMesh**

| Good at | Bad at |
|---|---|
| Real column-level lineage; virtual data environments; understands SQL rather than templating strings | Much smaller community — fails criterion 3 today |
| Incremental models and backfills are more rigorous than dbt's | Fewer engineers know it; fewer answers when it breaks |
| Less Jinja | |

**Raw SQL files + a runner**

| Good at | Bad at |
|---|---|
| No dependency, complete transparency | No tests, no lineage, no documentation, no dependency resolution — all of which you then write yourself |

### Chosen: dbt-core (with `dbt-duckdb`, and `dbt-postgres` available)

**Why it suits this project specifically.** Two of the architecture's requirements are satisfied as by-products: dbt tests *are* the Gold-layer quality gates from §10, and the manifest *is* the SQL-layer lineage from §13. Nothing extra is built for either. The team also has existing dbt experience, which under a short timeline is worth more than any technical margin SQLMesh holds.

**Genuinely better on the merits: SQLMesh.** Its column-level lineage and virtual environments are ahead of dbt's, and it avoids Jinja's readability cost. Rejected on criterion 3 alone — recognisability and existing team fluency, which is a legitimate reason and not a technical one. Worth revisiting for a project without a deadline.

**Deferred, not skipped.** §18 of the architecture puts dbt after the first vertical slice: one raw SQL model is fine until there is a second one to depend on it.

---

## 7. Storage, file format and table format

### Object storage

| Candidate | Good at | Bad at |
|---|---|---|
| **MinIO** | S3-compatible, one container, identical API to production | An extra container locally; a real service to operate if self-hosted in production |
| **Local filesystem only** | Nothing to run at all | Diverges from the cloud path — the exact divergence that breaks a deployment |
| **S3 / R2 / GCS directly** | Zero operations | Every developer needs credentials and network; slow local iteration; egress costs |

**Chosen: MinIO locally, S3-compatible storage in cloud, both through one `fsspec` adapter.** `fsspec` makes `s3://…` work identically against MinIO, S3, R2 and GCS, so the "local and cloud" criterion is met by configuration rather than by a code branch. The `ObjectStore` port (§6) means even `fsspec` is replaceable.

### File format

| Candidate | Good at | Bad at |
|---|---|---|
| **Parquet** | Columnar, compressed, with statistics enabling predicate and column pushdown; read natively by every engine here | Not human-readable; poor for row-by-row updates |
| **CSV** | Universal, readable | No types, no compression, no pushdown, ambiguous escaping |
| **JSONL** | Flexible, schema-free, good for API responses | Verbose, slow to parse, no pushdown |
| **Avro** | Row-based binary with excellent schema evolution | Row orientation is wrong for analytical scans; the evolution advantage matters mainly with a streaming registry |

**Chosen: Parquet with zstd compression, Hive-style partitioning.** Pushdown is what makes DuckDB fast over object storage, and zstd gives a better ratio than Snappy at comparable speed. JSONL is acceptable for a raw API response *inside* Bronze when preserving the exact payload matters more than query speed.

### Table format — the one worth arguing about

| Candidate | Good at | Bad at |
|---|---|---|
| **Plain Parquet + partition directories** | Nothing to operate; every engine reads it; trivially inspectable | No ACID, no `MERGE`, no time travel; concurrent writers are unsafe; partition layout becomes the contract |
| **Apache Iceberg** | The industry's converging standard; ACID, time travel, hidden partitioning, schema evolution, engine-neutral | Needs a catalog service; `pyiceberg` is capable but younger than the JVM implementation; real conceptual overhead |
| **Delta Lake** | `delta-rs` gives a JVM-free Python path; simpler than Iceberg to start | Historically Databricks-centric; the open ecosystem is converging on Iceberg |
| **Apache Hudi** | Strong upsert and incremental-pull story | The most complex to operate; smallest community of the three |

**Chosen: plain Parquet now, Iceberg named as the designated upgrade.**

The honest reasoning: ACID, `MERGE` and time travel are what table formats buy, and right now nothing needs them. There is one writer per dataset, Bronze is append-only, Silver overwrites whole partitions, and Gold is a full rebuild published by `MERGE` into Postgres — a database that already has transactions. Adopting Iceberg today would add a catalog service to operate in exchange for capabilities nothing uses.

**But this is flagged as a one-way door** (§12), because the partition layout chosen now determines the cost of migrating later. Which is why §15 of the architecture fixes the object-path convention up front: a clean `<layer>/<source>/<dataset>/<partition_col>=<value>/` layout is what makes an Iceberg migration a metadata operation rather than a rewrite.

**Trigger to switch:** a second concurrent writer, a genuine need for row-level `MERGE` in the lake, or a compliance requirement for time travel.

---

## 8. Validation and contracts

### Candidates

**Pydantic v2**

| Good at | Bad at |
|---|---|
| The Python standard for typed validation; Rust core, so fast | Record-at-a-time — validating ten million rows through Pydantic is the wrong tool |
| JSON Schema export built in, which §11 needs for the .NET side | Not a dataframe validator |
| Already the project idiom in `agent/` and the backend DTOs | |

**Pandera**

| Good at | Bad at |
|---|---|
| Code-first dataframe schemas that read like Pydantic models | Smaller community than Great Expectations |
| First-class **Polars** backend (a documented extra), plus pandas, PySpark, Ibis | Fewer built-in check types than GE's library |
| `lazy=True` collects every violation in one pass — exactly what the quarantine split in §7.2 needs | Less of a data *profiling* tool and more a validation one |
| Composes with pytest naturally; coercion built in | |

**Great Expectations**

| Good at | Bad at |
|---|---|
| The most comprehensive check library; profiling; data docs; the best-known name | Heavy: contexts, stores, checkpoints, datasources — a large amount of configuration surface |
| Excellent HTML reporting | Slow, and awkward to run in-process inside a pipeline step |
| | Its own mental model to learn; repeated breaking API changes across major versions |

**Soda Core**

| Good at | Bad at |
|---|---|
| Clean YAML check language (SodaCL); a good CLI; pleasant to read | **YAML-first** — fails criterion 2 |
| Genuinely lightweight compared with GE | The richer capabilities pull toward the paid cloud product |

**dbt tests**

| Good at | Bad at |
|---|---|
| Free with the modelling layer; the natural place for SQL-layer assertions | SQL-layer only — cannot validate a Polars frame mid-pipeline |
| Runs in CI; failures block a build | Fires after the data is written, not before |

**Hand-written assertions**

| Good at | Bad at |
|---|---|
| No dependency; obvious | No schema as a declarative artifact; no reusable reports; drifts from the contract immediately |

### Chosen: Pydantic v2 (records) + Pandera (frames) + dbt tests (SQL) + Dagster asset checks (gating)

Four tools sounds like too many. They occupy four distinct positions and none overlaps:

| Tool | Position |
|---|---|
| Pydantic | record boundaries — config, API payloads, and the JSON Schema export for .NET |
| Pandera | frame boundaries — the Silver and Gold contracts, and the quarantine split |
| dbt tests | SQL-layer assertions after a Gold model builds |
| Dagster asset checks | the *decision* — does a failure block downstream materialization or only warn |

**Why Pandera over Great Expectations.** GE is more thorough and better known, and it would work. Rejected because its configuration surface and in-process awkwardness cost more than they return at this scale, while Pandera's schemas are ordinary Python objects that a `Validator` adapter can call directly and a unit test can exercise without a database. GE also pulls toward being a separate system with its own state; Pandera stays a library.

**Why Soda Core lost.** Its check language is genuinely pleasant, and on any project without criterion 2 it would be a reasonable pick. YAML as the authoring surface for logic is what ruled it out.

---

## 9. Document processing

### Candidates

**Docling**

| Good at | Bad at |
|---|---|
| Very broad input support — PDF, DOCX/XLSX/PPTX, legacy Office, ODF, EPUB, HTML, Markdown, AsciiDoc, LaTeX, CSV, images, and audio/video with the `asr` extra | Heavier and slower than a plain text extractor; layout models cost CPU |
| Layout- and table-aware, producing a structured document model rather than a text blob | A large dependency tree |
| Runs fully locally — no API, no data leaving the machine | Younger than Tika or PyMuPDF |
| Ships its own chunkers (`HybridChunker`, `HierarchicalChunker`, `LineBasedTokenChunker`) | |
| Actively developed; permissive licence | |

**`unstructured`**

| Good at | Bad at |
|---|---|
| The widest format coverage; a well-known name in RAG pipelines | A very heavy dependency tree, with system packages for the good paths |
| Good element-typing model | The best parsing quality sits behind their hosted API |
| | Slow, and its open-source quality on complex PDFs trails Docling |

**PyMuPDF / `pymupdf4llm`**

| Good at | Bad at |
|---|---|
| Extremely fast; small; excellent Markdown output for text-based PDFs | PDF-centric — no DOCX, PPTX or XLSX |
| Very reliable at what it covers | Weaker table extraction; no OCR without help |
| | **AGPL** unless commercially licensed — worth confirming against how this project ships |

**Apache Tika**

| Good at | Bad at |
|---|---|
| Enormous format coverage; extremely mature | JVM — fails criterion 7 |
| | Returns flat text; loses layout and table structure |

**LlamaParse / hosted parsers**

| Good at | Bad at |
|---|---|
| Very good quality on hard documents; zero setup | A paid API; documents leave the machine; fails "runs locally" |

### Chosen: Docling, with `pymupdf4llm` as a fast path

**Why it suits this project specifically.** Platform 1 requires "Documents" as a first-class source type, and Docling covers every format that phrase realistically means with one dependency. Two properties decide it:

1. **Structure survives.** A parser that flattens a document to text destroys the tables, which are usually the part worth retrieving. Docling returns a document model with structure intact, and its `HybridChunker` chunks along that structure rather than at arbitrary character counts.
2. **It runs locally.** No document leaves the machine, which keeps document handling inside §14's governance rules rather than turning every parse into a third-party data transfer.

`pymupdf4llm` stays available behind the same `DocumentParser` port for simple text PDFs where Docling's layout analysis is wasted cost — dispatch happens through `supports()`. **Check PyMuPDF's AGPL terms before shipping it**, since that is a licence question rather than a technical one.

**Trigger to switch:** scanned documents needing serious OCR, or a hosted parser measurably beating Docling on the actual document mix.

---

## 10. Embeddings and vector search

### Embedding runtime

| Candidate | Good at | Bad at |
|---|---|---|
| **fastembed** | ONNX runtime, no PyTorch — a small install and fast CPU inference; multilingual models available; quantised variants | Fewer models than the full Hugging Face catalogue; no fine-tuning path |
| **sentence-transformers** | The largest model selection; the reference implementation; supports fine-tuning | Pulls in PyTorch — a heavy install; slower on CPU without tuning |
| **API embeddings** (any provider) | Best quality; no local compute; no model files | Network dependency, per-call cost, data leaves the machine, and it breaks the demo when the provider does |

**Chosen: fastembed locally, an API embedder available behind the same port.** The install is small, CPU inference is fast enough for the volumes here, and multilingual models cover Vietnamese and English text in one index. Because §6 puts this behind an `Embedder` port with `model_id` and `dimensions` exposed, switching is one adapter and one index rebuild.

`mock_embedder` — deterministic, no model — exists so retrieval unit tests are stable and instant.

**Note:** `fastembed`'s most recent release is older than most other packages here (§14). It is maintained rather than abandoned, but worth checking before committing, and it is the single easiest component to replace if that changes.

### Vector store

| Candidate | Good at | Bad at |
|---|---|---|
| **pgvector** | Lives in the database you already run; HNSW indexing; SQL-joinable against Gold; transactional with the rest of Postgres; readable by the .NET backend | Slower than a dedicated engine at very large scale; index builds compete with serving load |
| **Qdrant** | Excellent performance; sophisticated payload filtering; easy single container; good hybrid support | A second store to keep in sync; unjoinable from SQL; another service in the demo path |
| **Milvus / Weaviate** | Very capable at large scale | Materially heavier to operate; over-provisioned for this |
| **Chroma** | The simplest developer experience for prototypes | Weaker operational story; less suited to a serving path |
| **LanceDB** | Embedded, no server, excellent local DX; strong multimodal story | Younger; no SQL join against Gold; a separate store from Postgres |

**Chosen: Postgres + pgvector (HNSW) + `pg_trgm` + `unaccent`.**

**Why it suits this project specifically.** Three reasons, in order of weight:

1. **It is not a second store.** The index shares transactions, backups, credentials and operations with Gold. One fewer service in the demo path is one fewer thing that can fail.
2. **Both retrieval legs live in one query.** §12's hybrid design needs lexical *and* dense retrieval. Postgres has `pg_trgm` and full-text search alongside `pgvector`, so RRF fusion happens in the database instead of by shipping two result sets to Python and merging them.
3. **The .NET backend can read it.** Under §11's Postgres-as-contract-surface decision, an index the backend can query with SQL preserves an option a separate vector service would remove.

Qdrant is genuinely faster and filters better. That advantage starts to matter at a scale this platform has not reached, and §17 records the trigger.

---

## 11. Evaluation, observability and tooling

### Evaluation harness

| Candidate | Good at | Bad at |
|---|---|---|
| **Custom: JSONL in git → Dagster asset → scikit-learn → report** | Total control over metrics; reproducible because it is an asset; labels reviewed in pull requests | You write the reporting; no UI |
| **promptfoo** | Fast to set up; good matrix comparison across prompts and models | YAML-configured; oriented to prompt comparison rather than pipeline metrics |
| **RAGAS** | Purpose-built RAG metrics (faithfulness, context precision/recall) | Requires an LLM as judge — cost, latency and non-determinism; narrower than general classification metrics |
| **DeepEval** | pytest-style LLM assertions; pleasant developer experience | Younger; also leans on LLM judges |
| **MLflow** | Mature experiment tracking and model registry | Built around model training runs; heavy for measuring a pipeline |
| **Langfuse** | Excellent LLM tracing, datasets and scoring | Trace-first, and another service; the AI layer's tool more than the data layer's |

**Chosen: the custom harness — labeled cases as JSONL in git, run as a Dagster asset, metrics from scikit-learn, a Markdown report.**

**Why it suits this project specifically.** The output is a number that has to be defensible: *"n cases, baseline X, pipeline Y, measured this way."* That needs precision, recall, F1 and a confusion matrix over a fixed dataset — which is thirty lines of scikit-learn, not a framework. What actually matters is the properties around the number, and those come from the harness being an asset (§7.5): reproducible, re-run on change, and comparable across two arms.

Keeping the labels as JSONL in git is the load-bearing decision. Labels are source code — reviewed, diffed, and versioned alongside what they measure.

**RAGAS stays available** for retrieval-specific metrics once retrieval quality itself needs measuring; it complements rather than replaces this. Langfuse belongs to the agent layer for LLM tracing.

### Logging

| Candidate | Good at | Bad at |
|---|---|---|
| **structlog** | Structured events are the default; clean context binding; readable in development, JSON in production | A dependency, and its configuration takes one sitting to understand |
| **stdlib `logging` + JSON formatter** | No dependency | Structured fields require discipline every single call; `extra={}` is easy to forget |
| **loguru** | The nicest ergonomics | Less structured-first; a less standard choice for production JSON logs |

**Chosen: structlog — reversed in 1.1. See below.**

The original argument: the architecture's §13 mandates a fixed set of fields on every event. structlog makes that the path of least resistance, whereas stdlib `logging` makes it something to remember at each call site. Output is JSON to stdout — collection is the environment's job.

> **Reversal, 18/08/2026 — mirror `agent/observability/logging.py` instead.**
>
> The argument above assumed stdlib `logging` leaves structured fields to discipline at each call site. That turned out to be false *for this repository*: `agent/` already ships an 83-line module — stdlib `logging` plus a JSON formatter — exposing `get_logger(name)`, `log_event(logger, level, event, **fields)` and a `log_duration` context manager. `log_event`'s signature makes `**fields` the only way to log anything, so the benefit structlog was chosen for is already obtained, with no dependency.
>
> Two further reasons decide it. The two Python pods emit **identical log shapes**, which matters when correlating a request across them. And the module is already proven in this codebase rather than needing a configuration session.
>
> Recorded here rather than silently changed, so nobody re-opens the question. The implementation is specified in [implementation-plan.md](implementation-plan.md) §8.1 and §16.22.

Metrics and tracing stay as interfaces only (`observability/`) until there is somewhere to send them; Prometheus, Grafana and OpenTelemetry are named in §17 as the upgrade.

### Packaging and quality tooling

| Concern | Chosen | Alternatives considered | Reason |
|---|---|---|---|
| Dependencies | **uv** | Poetry, pip-tools, pdm | Dramatically faster, with a real lockfile; now a mainstream choice |
| Lint + format | **Ruff** | Black + Flake8 + isort | One tool replacing three, and fast enough to run on save |
| Tests | **pytest** | unittest | The standard; fixtures and parametrisation matter for the four-tier structure of §16 |
| Types | **mypy** or **pyright** | none | Optional but recommended; the ports in §6 only pay off if `Protocol` conformance is actually checked |
| Config | **pydantic-settings** | dynaconf, plain `os.environ` | Typed, validated at startup, and identical to the agent layer's `Settings` |

---

## 12. One-way doors

Most decisions above are cheap to reverse because §6's ports confine each tool to one adapter. Three are not, and they deserve the extra thought up front.

### Expensive to reverse

| Decision | Why it binds | How the cost was reduced |
|---|---|---|
| **Object-storage partition layout** | Bronze is append-only and never rewritten, so every historical file keeps whatever layout it was written with. Changing the scheme means rewriting history or maintaining two readers. | §15 fixes the convention before the first byte lands, and chooses a layout Iceberg can adopt as a metadata operation |
| **Postgres as the serving contract** | The .NET backend will build against `api.v1_*`. Moving to an HTTP data service later means changing another team's code. | §11's versioned views make the *shape* evolvable even though the *mechanism* is fixed |
| **No table format initially** | Adopting Iceberg later means migrating existing data. | The partition layout above is chosen to make that migration cheap, and §17 records the trigger so the decision gets revisited deliberately |
| **Media understood as text, not pixels** | Every downstream artifact — chunks, embeddings, contracts, Gold columns — is derived from captions. Adopting visual embeddings later means a second vector space and re-deriving everything that assumed text. | The Index is rebuildable from Silver and `Embedder` is a port, so the *mechanism* is one adapter and one rebuild. What is expensive is the accumulated Gold modelling built on caption-shaped columns |

### Cheap to reverse — all behind a port

Orchestrator (assets are thin callers, §2) · embedder (`Embedder`, one adapter + a rebuild) · document parser (`DocumentParser`, dispatched by `supports()`) · transcriber (`Transcriber`, one adapter + a cache invalidation) · captioner (`FrameCaptioner`, likewise) · vector store (`Retriever`) · validator (`Validator`) · object-storage backend (`ObjectStore`, a URL change) · compute engine (confined to `application/`).

**Media decoding is cheap to reverse despite having no port.** Swapping `imageio-ffmpeg` for apt-installed ffmpeg or PyAV changes one file of plain functions and no call site, because the functions return paths. This is the case that shows a `Protocol` was never what made a decision reversible — a narrow interface did, and two functions are narrower than a protocol.

**This asymmetry is the point of the architecture.** The three expensive decisions got argued about; the rest can be changed by whoever needs to change them.

---

## 13. Rejected outright

Each of these was considered and set aside. Recorded so the question does not get re-opened at hour 20 of a build.

| Tool | Why not |
|---|---|
| **Apache Airflow** | Task-centric rather than data-centric, and needs a scheduler, webserver and metadata DB before anything runs |
| **Prefect** | A fine second choice, but a weaker data-asset model, so lineage and freshness become manual work |
| **Kestra / Windmill** | YAML-first authoring — fails the code-first criterion |
| **Apache Spark** | JVM and a cluster for data that DuckDB handles faster end-to-end; revisit only past single-machine scale |
| **pandas as the primary engine** | Single-threaded, memory-hungry, weakly typed. Retained only as an interop escape hatch |
| **Great Expectations** | Far more configuration surface than this scale justifies, and awkward in-process |
| **Soda Core** | YAML-first check authoring |
| **`unstructured`** | A heavy dependency tree, and its best parsing quality is API-gated |
| **Apache Tika** | JVM, and it flattens away the document structure worth keeping |
| **Airbyte** | A container per connector plus a control plane — the wrong shape for six source types |
| **Meltano / Singer** | YAML-first, a slow per-record protocol, and a tap ecosystem that has lost momentum |
| **Fivetran and other managed SaaS ingestion** | Paid, and it cannot run locally |
| **Qdrant** | Excellent, but a second store to synchronise for a scale advantage not yet needed |
| **Kafka / Redpanda + Debezium** | Nothing here needs streaming. Named in §17 as the CDC path if freshness ever becomes the binding constraint |
| **Feast (feature store)** | Feature serving with online/offline skew is a problem this platform does not have; a Gold table is the right answer today |
| **MLflow** | Oriented to model training runs; the eval harness needs pipeline metrics, not an experiment tracker |
| **Delta Lake** | A reasonable JVM-free table format, but the ecosystem is converging on Iceberg, so that is the designated upgrade |
| **Confluent Schema Registry** | A registry is for streaming producers and consumers. Contracts here live in git, which is better for a batch platform |
| **SQLMesh** | Technically ahead of dbt on lineage and environments, but loses on team fluency and recognisability today |
| **DataHub / OpenMetadata** | A catalog for many teams and many tools. Dagster's asset graph plus dbt's manifest cover a single-team platform |
| **CLIP and multimodal embeddings** | Produces vectors where the agent layer needs words, and buys a second vector space plus a torch dependency. §17 above; the trigger to revisit is an eval, not an intuition |
| **tesseract** | Weak precisely where this platform's text lives — stylised, low-contrast social-video overlays, in Vietnamese. A VLM absorbs the stage for free |
| **PaddleOCR** | Better than tesseract, but a deep-learning runtime for a capability already covered by a call that is being made anyway |
| **PyAV** | A C-extension wheel matrix for a job that is two `subprocess` calls. Fails at import time on the platform you did not test |
| **moviepy** | An editing library used as an extraction library; slower and larger than the requirement |
| **`apt-get install ffmpeg`** | ~250 MB and an apt layer on a slim image, for codec coverage this workload does not need. The static wheel is the same tool at a third of the size |
| **Docling's `asr` extra for media** | Would unify document and media parsing behind one dependency, which is genuinely appealing — but it drags torch in, taking the image past 4 GB and the build past half an hour |
| **A queue for asset extraction** | Celery, ARQ or a broker for a call that finishes in seconds and fits the caller's existing timeout. §17 of the architecture names the trigger; until then it is a component that can fail during a demo and buys nothing |
| **Litestar** | A well-designed framework, rejected only because the other pods run FastAPI and consistency wins here |

---

## 14. Version pins

Latest released versions on PyPI, **verified 12/08/2026**. Treat these as a starting point and re-verify before pinning — do not trust this table's freshness in six months.

| Package | Version | Latest release |
|---|---|---|
| `dlt` | 1.30.0 | 2026-08-11 |
| `dagster` | 1.13.17 | 2026-08-07 |
| `dagster-dlt` / `dagster-dbt` / `dagster-duckdb` | 0.29.17 | 2026-08-07 |
| `dagster-webserver` | 1.13.17 | 2026-08-07 |
| `polars` | 1.43.2 | 2026-08-01 |
| `duckdb` | 1.5.5 | 2026-07-22 |
| `dbt-core` | 1.12.1 | 2026-08-12 |
| `dbt-duckdb` | 1.11.0 | 2026-08-07 |
| `dbt-postgres` | 1.11.0 | 2026-07-16 |
| `pandera` | 0.32.1 | 2026-06-29 |
| `pydantic` | 2.13.4 | 2026-05-06 |
| `pydantic-settings` | 2.15.0 | 2026-08-07 |
| `docling` | 2.119.0 | 2026-08-10 |
| `pymupdf4llm` | 1.28.2 | 2026-08-06 |
| `fastembed` | 0.8.0 | 2026-03-23 ⚠️ |
| `fastexcel` | 0.20.2 | — |
| `structlog` | 26.1.0 | 2026-06-06 |
| `psycopg` | 3.3.4 | 2026-05-01 |
| `pgvector` (Python client) | 0.5.0 | — |
| `s3fs` | 2026.7.0 | 2026-07-28 |
| `pyarrow` | 25.0.1 | 2026-08-10 |
| `scikit-learn` | 1.9.0 | 2026-06-02 |
| `ruff` | 0.16.2 | 2026-08-07 |
| `pytest` | 9.1.1 | 2026-06-19 |

Non-Python components: **Postgres 16+**, **pgvector extension 0.8.6** (HNSW available since 0.5.0), **MinIO** (current release), **DuckDB** as a library only.

⚠️ **`fastembed` is the one package with a noticeably older release** (about five months at time of writing). Maintained, not abandoned — but verify before committing, and note it is the easiest component here to swap (§10).

### Verified integration claims

These were checked rather than recalled, because the architecture depends on them:

| Claim | Status |
|---|---|
| `dlt` core sources include `rest_api`, `sql_database`, `filesystem` | ✅ confirmed in the source tree |
| `dlt` filesystem readers: `read_csv`, `read_jsonl`, `read_parquet`, `read_csv_duckdb` | ✅ confirmed in `dlt/sources/filesystem/readers.py` |
| `dlt` ships **no** Excel reader | ✅ confirmed — needs the custom adapter of §7.1 |
| `dlt` extras include `duckdb`, `postgres`, `filesystem`, `s3`, `parquet` | ✅ confirmed |
| Pandera has a `polars` extra | ✅ confirmed in its PyPI metadata |
| Dagster asset checks: `@asset_check`, `@multi_asset_check`, `blocking=True` | ✅ confirmed in current Dagster docs |
| Docling provides `HybridChunker` (`from docling.chunking import HybridChunker`) | ✅ confirmed |
| Docling input formats include PDF, DOCX/XLSX/PPTX, ODF, EPUB, HTML, Markdown, CSV, images | ✅ confirmed |
| Postgres has **no** Vietnamese full-text search configuration | ⚠️ true — the limitation documented in §12.2 of the architecture |

### Media and serving packages — added in 1.1, NOT yet verified

These have not been checked against PyPI. **Verify each before pinning**, and do it early: a wheel that does not exist for Python 3.12 is the kind of thing that costs an evening.

| Package | Needed for | What to check |
|---|---|---|
| `imageio-ffmpeg` | frame sampling, audio extraction (§15) | that `get_ffmpeg_exe()` returns a working binary on Linux x86-64, and that the wheel is not source-only |
| `google-genai` | transcription and captioning (§16, §17) | already a dependency of `agent/` at `>=1.0` — match the version, and confirm inline image parts work |
| `fastapi` · `uvicorn[standard]` | the serving API (§18) | nothing unusual; pin both |
| `python-multipart` | only if the API ever accepts an upload directly | probably unnecessary — the architecture passes paths, not bytes |
| `Pillow` | frame resizing if ffmpeg's scaler is not enough | likely unnecessary; do not add speculatively |
| `imagehash` | perceptual dedupe | **deferred** — do not install until §17 of the architecture triggers it |

---

## 15. Media decoding

Extracting frames and an audio track from a video file. Purely mechanical work with one correct answer per input, which is why the architecture gives it plain functions rather than a port ([data-architecture.md](data-architecture.md) §6).

### Candidates

**`imageio-ffmpeg`**

| Good at | Bad at |
|---|---|
| Ships a statically linked ffmpeg binary inside the wheel — `pip install` and it is there | Ships `ffmpeg` but **not `ffprobe`**, so metadata inspection needs another route |
| No `apt-get`, no root, no system package layer in the image | A pinned ffmpeg build; you take the codecs it was compiled with |
| Roughly 70 MB, against ~250 MB for the apt route | A thin wrapper, so you drive it with `subprocess` yourself |
| Works identically on a laptop and in a slim container | |

**`apt-get install ffmpeg`**

| Good at | Bad at |
|---|---|
| The real thing, every codec, the version the distribution ships | ~250 MB plus an apt layer on `python:3.12-slim`, and a longer build |
| What every ffmpeg answer on the internet assumes | Requires root at build time; a second package manager in the Dockerfile |
| | The version differs between a developer's laptop and the image |

**PyAV**

| Good at | Bad at |
|---|---|
| Real Python bindings to libav — frame-accurate access without shelling out | A C-extension wheel matrix; when it fails it fails at import time on a specific platform |
| No subprocess, no temporary files | A heavier API than "give me eight JPEGs"; more code for this use case |
| Efficient for frame-by-frame work | The debugging is genuinely unpleasant under time pressure |

**moviepy**

| Good at | Bad at |
|---|---|
| The friendliest API; good for editing and composition | Built for editing, not extraction; slow, and it pulls in more than is needed |
| | Historically loose about its own ffmpeg dependency |

### Chosen: `imageio-ffmpeg`, driven by `subprocess.run`

**Why it suits this project specifically.** Two commands are needed, forever:

```
-vf fps=1/2,scale=512:-1 -frames:v 8   → eight JPEGs
-ac 1 -ar 16000 -vn                     → mono 16 kHz WAV
```

That is the entire requirement. A binary that arrives with `pip install` and two `subprocess` calls is a smaller surface than a bindings library, it keeps the Dockerfile to one package manager, and it fails in a way that is legible — a non-zero exit code and stderr, rather than a segfault inside a shared library.

The apt route is the safer answer on codec coverage and would be the right call for a service that ingests arbitrary user media at scale. For a bounded set of consumer video formats, the static build covers it, and 180 MB of image and several minutes of build time are worth more here.

**The missing `ffprobe`, handled rather than worked around.** [data-architecture.md](data-architecture.md) §7.6 takes duration from the extracted WAV instead, and never collects fps, codec or bitrate — because no consumer of this platform has asked for them. If a consumer does, that is the moment to add `ffprobe`, not before.

**Trigger to switch:** codec failures on real user uploads, or a genuine need for frame-accurate seeking that shelling out cannot give.

---

## 16. Transcription

Turning a video's audio track into text. The most valuable single signal for every media problem this platform serves — what was said usually matters more than what was shown.

### Candidates

**Gemini audio input**

| Good at | Bad at |
|---|---|
| No local weights, no model download, no torch — the container stays small | A hard network dependency on the critical path |
| Strong multilingual quality, Vietnamese included | Per-call cost, and it scales with usage rather than being fixed |
| The same SDK and the same key already used for captioning | Audio leaves the machine, which is a governance question ([data-architecture.md](data-architecture.md) §14) |
| One less component to operate and version | Latency is the provider's, not yours; a slow day is your slow day |

**`faster-whisper`**

| Good at | Bad at |
|---|---|
| Fully offline once the weights are baked into the image | ~150 MB of weights for `base`, plus the `ctranslate2` runtime |
| CTranslate2, so **no torch** — the install stays under control | Wheels depend on prebuilt `ctranslate2` binaries for the platform |
| `base` at `int8` runs roughly 8–12× realtime on a laptop CPU | Quality below a frontier hosted model, especially on Vietnamese |
| Fixed cost — no per-call charge | A model to choose, a size to tune, a warm-up to manage |

**`whisper.cpp`**

| Good at | Bad at |
|---|---|
| Extremely small; excellent on constrained hardware | A binary to build or vendor; bindings are a third-party concern |
| No Python ML stack at all | Another build step in the Dockerfile |

**OpenAI or another hosted ASR API**

| Good at | Bad at |
|---|---|
| Excellent quality; no local compute | A second provider, a second key, a second bill |
| | Adds nothing over the provider already integrated |

### Chosen: Gemini audio, behind the `Transcriber` port

**Why it suits this project specifically.** The captioner is already a hosted call ([§17](#17-frame-understanding)), so transcription being hosted adds no *new* class of dependency — it adds a second call to a provider already on the critical path. In exchange the container carries no model weights, the build stays minutes rather than tens of minutes, and there is one less thing to warm up before a demo.

**The trade is real and is not hidden.** A network failure takes out transcription, and unlike an embedding model there is no local fallback in the image. The mitigation is architectural rather than infrastructural: [data-architecture.md](data-architecture.md) §7.6 caches every derivation on `content_hash + extractor_version`, so any asset processed once is immune, and a known set of demo assets can be processed in advance. That covers the realistic failure — the venue network dying — while leaving genuinely novel input exposed. Stating which failure is covered and which is not is the honest version of this decision.

**`faster-whisper` is the designated successor, not a rejected option.** It sits behind the same port, so adopting it is one adapter and a Dockerfile line. [data-architecture.md](data-architecture.md) §17 names three triggers: the network dependency becoming unacceptable, Vietnamese quality becoming the binding constraint, or a customer refusing to let audio leave the machine. Any one of them is sufficient.

---

## 17. Frame understanding

Turning sampled frames into something searchable: what is in the frame, what text is on screen, and whatever structured signals the business domain needs.

### Candidates

**A vision-language model, one batched call per asset**

| Good at | Bad at |
|---|---|
| Caption, on-screen text and structured signals arrive in **one** response | A hosted call — cost, latency and a network dependency |
| Reads Vietnamese overlay text well, including stylised and low-contrast cases | Non-deterministic; the same frames can yield different words |
| The prompt is the only place business logic lives, so retargeting is a string change | Quality depends on prompt quality, which is real work |
| Output is text, so the existing index, contracts and retrieval all apply unchanged | Per-request image limits constrain the frame count |

**CLIP or another multimodal embedding model**

| Good at | Bad at |
|---|---|
| Genuine visual similarity — matches how a frame *looks*, not how it is described | A second vector space, a second index and a second retrieval path |
| Deterministic and cheap once the model is loaded | Pulls torch into a slim image: gigabytes, and a long build |
| Excellent for near-duplicate and style matching | Produces no text, so it cannot feed the agent's context or a report |

**tesseract**

| Good at | Bad at |
|---|---|
| Mature, offline, free; the default answer for OCR | Weak on stylised overlay text, gradients and low contrast — which is what social video *is* |
| Small | Vietnamese diacritics need the right traineddata and still degrade |
| | A system package, and a whole pipeline stage that a VLM absorbs for free |

**PaddleOCR**

| Good at | Bad at |
|---|---|
| Materially better than tesseract on hard text, good multilingual coverage | Drags in a deep-learning runtime — the image-size problem again |
| | A second model to manage for a capability already covered |

### Chosen: one batched VLM call per asset

**Why it suits this project specifically.** The decisive property is not caption quality, it is **collapse**. One request returns the caption, the on-screen text and the structured signals, which means one network round trip per asset, one place to change when the business question changes, and no OCR stage in the pipeline at all. Against tesseract plus a captioner plus a signal extractor, this deletes two dependencies and two stages.

Batching all frames into a single call is what makes it fit a request-time budget. Eight frames at one request is a few seconds; eight frames at eight requests is not, and it multiplies the failure surface by eight.

**Why CLIP was rejected — and what would reverse it.** Rejected because it produces vectors, not words, and the agent layer needs words: a caption goes into a prompt, a report and a retrieved document; an embedding goes only into a similarity search. Adopting it means running both anyway, since the captions would still be needed. [data-architecture.md](data-architecture.md) §12.4 records where the caption-only choice breaks — near-duplicate detection over a catalog — and names the trigger as **an eval showing caption retrieval losing**, not a suspicion that it might. The cheap answer to that specific failure is a perceptual hash and a `bigint` column, not a second embedding space.

**On determinism.** A VLM will not return identical text for identical frames, which is uncomfortable for a data layer. The content-hash cache makes it a non-issue in practice: an asset is captioned once and the stored result is what everything downstream sees, so the pipeline is deterministic even though the model is not. Re-deriving is an explicit act — bumping `extractor_version`.

**Trigger to switch:** on-screen text extraction becoming the binding constraint on quality, at which point a dedicated OCR model earns its stage.

---

## 18. Serving API framework

The HTTP process that serves the agent layer on `:8002` ([data-architecture.md](data-architecture.md) §11.4). Four handlers, no state.

### Candidates

| Candidate | Good at | Bad at |
|---|---|---|
| **FastAPI** | Pydantic-native, so request and response models are the contract; generates OpenAPI at `/docs`; the most widely known Python API framework; async throughout | Heavier than the four handlers strictly need; brings starlette and uvicorn |
| **Litestar** | Cleaner DI, arguably better structured for large applications; comparable performance | A smaller community; a second framework idiom for the team to hold |
| **Flask** | Everybody knows it; minimal | Sync by default, no typed models, no schema generation — all three of which are load-bearing here |
| **A plain ASGI app** | No dependency at all | Hand-written routing, validation and error handling, done badly under time pressure |

### Chosen: FastAPI + uvicorn

**Why it suits this project specifically.** Two reasons, both about the surrounding system rather than the framework.

First, **the other pods are FastAPI**. [integration-architecture.md](../docs/architecture/integration-architecture.md) §2 specifies it for the agent pod, and §4.1 makes the auto-generated `/docs` the mechanism by which pods keep their schemas in sync without sharing code. A data pod that generated no OpenAPI would break that mechanism for its own contract.

Second, **Pydantic is already the record-contract tool** (§8). The response DTOs in `interface/api/schemas.py` are Pydantic models like every other record contract in the layer, which means one validation idiom rather than two.

Litestar would work and is arguably the better-designed framework. Rejected on the same criterion 3 that decided dbt over SQLMesh: recognisability and consistency with what is already running beat a design margin.

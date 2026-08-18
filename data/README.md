# Data Layer — Platform 1: Data Intelligence

This directory owns the **Sense** step of the platform (`Sense → Understand → Reason → Simulate → Decide → Act → Learn`). It turns heterogeneous external data — CSV, Excel, JSON, REST APIs, databases, documents, and uploaded video, image and audio — into two products the rest of the system can trust:

1. **Structured data** the backend and simulation layers query with confidence.
2. **Retrievable knowledge** the `agent/` layer searches over.

## Documents

| Document | What it covers |
|---|---|
| [data-architecture-summary.md](data-architecture-summary.md) | **Start here.** The whole design in ten minutes: the picture, the four layers, the six pipelines, how media works, and the rules that matter |
| [data-architecture.md](data-architecture.md) | The architecture standard: layering, ports, the six pipelines, idempotency, contracts, quality, serving, retrieval, observability, naming, testing, build order, and a review checklist |
| [tech-stack-evaluation.md](tech-stack-evaluation.md) | Every framework considered per category, what each is good and bad at, which was chosen and why, plus what was rejected and the version pins |
| [implementation-plan.md](implementation-plan.md) | The dated build plan: the vertical slice, what is built before the event and what during it, verification steps, and the risks |
| [../docs/architecture/agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) | The equivalent standard for the `agent/` layer. This layer deliberately mirrors its structure |

## The stack in one paragraph

**dlt** ingests into a **Bronze** layer of Parquet on object storage (**MinIO** locally, S3-compatible in cloud); media and document blobs land there unaltered beside it. **Polars** normalizes Bronze records into **Silver** with contracts enforced by **Pandera**; rows that fail are quarantined, never dropped. Media takes the parallel route — `imageio-ffmpeg` samples frames and audio, then hosted **Gemini** calls behind the `Transcriber` and `FrameCaptioner` ports turn them into a transcript and frame annotations, cached on the blob's content hash so nothing is ever derived twice. **DuckDB** with **dbt** models Silver into **Gold**, published into **Postgres 16** and exposed to the .NET backend as versioned `api.v1_*` views. Documents and media annotations alike are embedded with **fastembed** and indexed in **pgvector**, retrieved through a hybrid `pg_trgm` + vector query fused with RRF behind the same `Retriever` port the agent layer already defines — and served to that layer over **FastAPI** on `:8002`, because the agent must never learn SQL. **Dagster** orchestrates the scheduled half as assets, which is where lineage and quality gates come from. Everything runs on a laptop with two containers and two processes.

## Architectural rules that are not negotiable

- `domain/` imports no framework, driver or SDK — see [data-architecture.md](data-architecture.md) §2.
- Every pipeline is callable from a plain `pytest` with no `dagster` and no `fastapi` import. Both are edges, not the core — which is what lets a schedule and an HTTP request call the same function.
- Bronze is append-only and never mutated. Every write is idempotent for its partition.
- Every media derivation is keyed on `content_hash + extractor_version`, so it is never computed twice.
- Bad rows are quarantined with their violation attached, never silently dropped.
- Concrete implementations are named in exactly one place: `orchestration/resources.py`.

Full checklist: [data-architecture.md](data-architecture.md) §19.

## Status

Design complete; implementation not started. The first thing to build is the vertical slice in [data-architecture.md](data-architecture.md) §18 — **one video through Bronze, extract, index and the API** — not breadth across source types. The schedule is in [implementation-plan.md](implementation-plan.md).

# Data Layer — Platform 1: Data Intelligence

This directory owns the **Sense** step of the platform (`Sense → Understand → Reason → Simulate → Decide → Act → Learn`). It turns heterogeneous external data — CSV, Excel, JSON, REST APIs, databases and documents — into two products the rest of the system can trust:

1. **Structured data** the backend and simulation layers query with confidence.
2. **Retrievable knowledge** the `agent/` layer searches over.

## Documents

| Document | What it covers |
|---|---|
| [data-architecture.md](data-architecture.md) | The architecture standard: layering, ports, the five pipelines, idempotency, contracts, quality, serving, retrieval, observability, naming, testing, build order, and a review checklist |
| [tech-stack-evaluation.md](tech-stack-evaluation.md) | Every framework considered per category, what each is good and bad at, which was chosen and why, plus what was rejected and the version pins |
| [../docs/architecture/agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) | The equivalent standard for the `agent/` layer. This layer deliberately mirrors its structure |

## The stack in one paragraph

**dlt** ingests into a **Bronze** layer of Parquet on object storage (**MinIO** locally, S3-compatible in cloud). **Polars** normalizes Bronze into **Silver** with contracts enforced by **Pandera**; rows that fail are quarantined, never dropped. **DuckDB** with **dbt** models Silver into **Gold**, which is published into **Postgres 16** and exposed to the .NET backend as versioned `api.v1_*` views — Postgres is the contract surface between the two layers. Documents are parsed by **Docling**, embedded with **fastembed**, and indexed in **pgvector**, retrieved through a hybrid `pg_trgm` + vector query fused with RRF behind the same `Retriever` port the agent layer already defines. **Dagster** orchestrates all of it as assets, which is where lineage and quality gates come from. Everything runs on a laptop with two containers and one process.

## Architectural rules that are not negotiable

- `domain/` imports no framework, driver or SDK — see [data-architecture.md](data-architecture.md) §2.
- Every pipeline is callable from a plain `pytest` with no `dagster` import. Orchestration is an edge, not the core.
- Bronze is append-only and never mutated. Every write is idempotent for its partition.
- Bad rows are quarantined with their violation attached, never silently dropped.
- Concrete implementations are named in exactly one place: `orchestration/resources.py`.

Full checklist: [data-architecture.md](data-architecture.md) §19.

## Status

Design complete; implementation not started. The first thing to build is the vertical slice in [data-architecture.md](data-architecture.md) §18 — one source through all five layers — not breadth across source types.

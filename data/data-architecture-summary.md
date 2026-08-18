# Data Architecture — Summary

> The short version of [data-architecture.md](data-architecture.md), for getting the shape of the thing in ten minutes. Every claim here is stated more carefully in the full document; section numbers point at where.

---

## 1. What this layer is for

Everything outside the system is messy: spreadsheets, API responses, database rows, PDFs, and videos somebody uploaded from a phone. This layer turns all of that into **two things the rest of the system can trust**:

1. **Rows** — typed, validated, queryable. The backend and the simulation layer use these.
2. **Searchable text** — chunks with embeddings. The agent layer searches these.

That is the whole job. It does not decide anything, and it does not generate anything. It answers *"what do we have?"*, never *"what should we do?"* — that is `agent/`'s job (§1).

---

## 2. The one-page picture

```
       CSV · Excel · JSON · API · Database · Documents · Video/Image/Audio
                                    │
                                    ▼
   ┌────────────────────────────────────────────────────────────┐
   │  BRONZE — the raw bytes, never touched again               │
   │  records/ (Parquet)          assets/ (the original files)  │
   └──────────────┬────────────────────────────┬────────────────┘
                  │                            │
          normalize│                     extract│
          (Polars) │                    (ffmpeg │ + AI)
                  ▼                            ▼
   ┌────────────────────────────────────────────────────────────┐
   │  SILVER — clean, typed, validated rows                     │
   │  Bad rows go to quarantine, never silently dropped         │
   └──────────────┬────────────────────────────┬────────────────┘
                  │                            │
             model│                       index│
      (DuckDB+dbt)│                  (embeddings)
                  ▼                            ▼
        ┌──────────────────┐        ┌──────────────────────┐
        │  GOLD            │        │  INDEX               │
        │  business tables │        │  chunks + vectors    │
        └────────┬─────────┘        └──────────┬───────────┘
                 │                             │
                 ▼                             ▼
        api.v1_* SQL views            FastAPI on :8002
                 │                             │
                 ▼                             ▼
          .NET backend                   agent/ layer
```

**Read it top to bottom: data only ever flows downward.** Each layer is built from the one above it, so anything below Bronze can be deleted and rebuilt. That is the property that makes bugs cheap — you fix the code and re-run, instead of asking whether the source still has the data.

---

## 3. The four storage layers, in plain terms

| Layer | Think of it as | Rule |
|---|---|---|
| **Bronze** | The inbox. Exactly what arrived, unedited. | Append-only. Never modified, ever. |
| **Silver** | The clean version. Typed, deduplicated, validated. | One table per thing. Bad rows quarantined with the reason. |
| **Gold** | The business answer. Joined, aggregated, ready to serve. | Rebuilt whole; consumers never see it half-built. |
| **Index** | The search index. Text chunks and their vectors. | Fully rebuildable from Silver — nothing lives only here. |

**Why Bronze exists even when it feels redundant** (§3): the day you find a three-day-old bug in the cleaning code, Bronze turns that into a fifteen-minute re-run instead of a conversation about whether the source still has the data. For an uploaded video it is stronger still — the user uploaded it once and left, so there is no re-fetch at all.

---

## 4. The six pipelines

Each is a plain Python function. Each takes one partition or one asset, and each can be run twice safely.

| Pipeline | Does what | Tool |
|---|---|---|
| `ingest` | outside world → Bronze | dlt |
| `normalize` | Bronze records → Silver | Polars + Pandera |
| `extract` | Bronze media → Silver | ffmpeg, then AI transcription + captioning |
| `model` | Silver → Gold | DuckDB + dbt |
| `index` | Silver text → searchable chunks | fastembed + pgvector |
| `evaluate` | labeled cases → a quality number | scikit-learn |

`normalize` and `extract` sit in the same position and do the same job — take Bronze bytes, produce clean Silver rows. They differ only in what the bytes happen to be (§7).

---

## 5. How media works (the part that is new)

A video is not a special case in the storage layers. It is special in exactly one pipeline.

```
video.mp4
   │
   ├─ ffmpeg samples 8 frames  ──▶  AI describes each frame:
   │                                caption + on-screen text + signals
   │
   └─ ffmpeg extracts audio    ──▶  AI transcribes it
                                          │
                                          ▼
                          transcript + 8 captions  =  TEXT
                                          │
                                          ▼
                    from here it is an ordinary text pipeline
```

**The key idea: `extract` converts pixels and sound into text and numbers.** Once a video has become a transcript and eight captions, every layer downstream is doing work it already knew how to do — same contracts, same quarantine, same chunking, same embeddings, same search. Nothing below `extract` knows a video existed (§7.6, §12.4).

The alternative was putting images and text in a shared vector space (CLIP). Rejected: it produces vectors where the agent needs *words*, and it would mean a second index and a second search path. Where the text approach breaks is near-duplicate detection — two different t-shirt designs both caption "white tee with a graphic print" — and the fix for that is a perceptual hash column, not a second AI model.

### Nothing is ever processed twice

Transcribing and captioning cost money, take seconds, and need the network. So every result is stored against a key of **`hash of the file` + `version of the extractor`**. Run the same video again and there are zero AI calls (§7.6).

This is what makes the whole thing safe to call from a web request, and it is the demo-day insurance: process the demo videos the night before, and a dead venue network on stage changes nothing.

---

## 6. Two consumers, two doors

The layer serves two very different callers, so it has two surfaces (§11):

| Caller | Gets | How |
|---|---|---|
| **.NET backend** | rows | reads `api.v1_*` SQL views directly |
| **`agent/` layer** | documents and asset artifacts | calls HTTP JSON on port 8002 |

The agent cannot use SQL — its own architecture standard forbids importing a database driver, and the pods are not allowed to share code. So it gets a small FastAPI process instead.

**Four endpoints, that is all:**

```
GET  /health
GET  /api/v1/data/query?q=...&top_k=5     "what do we know about X?"
POST /api/v1/assets                        "process this video, now"
GET  /api/v1/assets/{id}                   "what did you find in it?"
```

`POST /api/v1/assets` runs and returns in the same request — a few seconds, or instantly on a cache hit. No queue, no polling, no job status. Each of those omitted mechanisms is one more thing that can fail during a demo (§11.4).

---

## 7. The one architectural idea worth understanding

Everything else follows from this. The layer is split into four parts, and **dependencies only point inward**:

```
orchestration/  (Dagster)      interface/api/  (FastAPI)
        └──────────┬───────────────────┘
                   ▼
             application/     the six pipelines — the actual steps
                   ▼
               domain/        what the concepts mean, and what is valid
                   ▲
                   │ plugs into
           infrastructure/    the real tools: dlt, DuckDB, MinIO, Gemini
```

**`domain/` is not allowed to import any tool.** No dlt, no Dagster, no Postgres driver, no Polars. It only describes what a valid dataset looks like and what capabilities the pipelines need. The tools plug into it from the outside.

Two things fall out of this, and both matter more than they sound:

1. **Tests are fast and offline.** Swap in a fake transcriber and a fake embedder, and the whole media pipeline runs in a unit test with no ffmpeg, no API key and no containers.
2. **A schedule and a web request can call the same function.** Because pipelines never import Dagster, a FastAPI route can call them too. This is the entire reason "process this video now" needed no new architecture — just another caller (§1, §2).

**The composition root.** Exactly one file — `orchestration/resources.py` — is allowed to name real implementations (`GeminiCaptioner`, `FsspecObjectStore`). Everywhere else sees only the capability. If a concrete class name appears anywhere else, a hidden dependency has grown (§18).

---

## 8. The rules that are actually enforced

Short list. These are the ones that cause real damage when broken.

- **Bronze is never modified.** Not corrected, not cleaned in place. (§3)
- **Delete then write, never write then delete.** A crash between the two leaves an empty partition, which a check catches. The other order leaves duplicates, which nothing catches. (§8)
- **Bad rows are quarantined with the violation attached, never dropped.** A dropped row is indistinguishable from one that never arrived. (§10)
- **No `SELECT *` across a layer boundary.** Naming columns turns an upstream change into a visible decision instead of a silent one. (§7.2)
- **Never catch a broad exception and continue.** Bad *records* are routed to quarantine deliberately; bad *runs* fail loudly. (§8)
- **No hard-coded thresholds, paths or model names** — all of it comes from `Settings`. (§10)
- **Never log transcripts, payloads, or anything marked PII.** Log the count and the reason. (§13)
- **A backfill is the same code over a date range**, not a separate script. A second implementation drifts from the first. (§8)

---

## 9. What is deliberately not built yet

Each of these has a written trigger in §17, so nobody adds it early and nobody forgets it exists:

Streaming · Iceberg · a dedicated vector database · CDC · local transcription models · multimodal embeddings · perceptual hashing · a job queue behind the assets endpoint · a distributed compute engine.

The principle: **each costs operational complexity that is only worth paying once the ceiling is actually hit.** The trigger column exists so the decision gets revisited on evidence rather than on a hunch.

---

## 10. Where to read more

| Question | Document |
|---|---|
| How exactly does X work? | [data-architecture.md](data-architecture.md) — the full standard |
| Why this tool and not that one? | [tech-stack-evaluation.md](tech-stack-evaluation.md) |
| What am I building, and when? | [implementation-plan.md](implementation-plan.md) |
| How does this connect to the other services? | [../docs/architecture/integration-architecture.md](../docs/architecture/integration-architecture.md) |
| What are the same rules for the AI layer? | [../docs/architecture/agent-architecture-standard.md](../docs/architecture/agent-architecture-standard.md) |

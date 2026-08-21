# Data API Reference

FastAPI edge for the data layer ([api.py](api.py)). Stateless: reads Postgres, calls the
same functions Dagster calls, owns no data of its own. Default bind: `0.0.0.0:8002`
(`API_HOST` / `API_PORT`).

Every error, on any endpoint, comes back as:

```json
{"error": {"code": "...", "message": "...", "request_id": "..."}}
```

---

## GET /health

Liveness probe. Always returns **HTTP 200** while the process is alive — a Postgres
blip is reported through the body, not the status code, so it can't fail the compose
healthcheck and block the other pods from starting.

**Response**

```json
{"status": "ok", "db": true, "chunks": 1532}
```

`status` is `"degraded"` and `db` is `false` if the chunk count query fails.

---

## GET /api/v1/data/query

## POST /api/v1/data/query

Hybrid dense + lexical retrieval over the whole index (documents and video
storyboards together). This is what `agent/`'s `HttpJsonRetriever` calls.

**Query params (GET)** / **Body (POST)**

| field   | type | default                  | notes                          |
|---------|------|--------------------------|---------------------------------|
| `q`     | str  | required                 | query text                     |
| `top_k` | int  | `settings.retrieval.top_k` (5) | clamped to `max_top_k` (50) |

**Response**

```json
{
  "items": [
    {
      "id": "chunk-id",
      "text": "chunk content",
      "score": 1.0,
      "metadata": {"...": "..."}
    }
  ]
}
```

`score` is Reciprocal Rank Fusion (RRF) output, normalised into `[0, 1]` against the
max score in the returned set — presentation only, not a calibrated confidence.

---

## GET /api/v1/videos/trending

## POST /api/v1/videos/trending

Product/category name in, ranked TikTok video storyboards out. Retrieval is
restricted to `source_type = "video_storyboard"` — video chunks never compete with
document chunks here.

**Query params (GET)** / **Body (POST)**

| field   | type | default | notes                     |
|---------|------|---------|----------------------------|
| `q`     | str  | required | a product or category name |
| `top_k` | int  | `5`     | clamped to `max_top_k` (50) |

**Response**

```json
{
  "meta": {
    "query": "electric shaver",
    "currency": "USD",
    "metrics_window": "last30Day",
    "candidates_considered": 50,
    "relevance_gated": false
  },
  "items": [
    {
      "id": "7...",
      "video_id": "7...",
      "title": "...",
      "url": "https://www.tiktok.com/@handle/video/7...",
      "category_name": "Beauty & Personal Care",
      "product_name": "electric shaver",
      "matched_keyword": "electric shaver",
      "revenue_usd": 12345.0,
      "views_30d": 98765,
      "ai_video": 0,
      "is_ad": false,
      "engagement_rate": 0.0182,
      "duration_s": 62.0,
      "age_days": 1.4,
      "relevance": 0.985,
      "rerank_score": 4.21,
      "trending_score": 8123.4,
      "text": "## Trending reference — Beauty & Personal Care\nRevenue $12,345 (USD, last 30d) · 98,765 views (last 30d) · human-shot · organic post · 62s\n\nHOOK: ...\n\n| # | time | shot | visual | on-screen text | voiceover |\n|---|------|------|--------|----------------|-----------|\n| 1 | 0s | close-up | ... | ... | ... |\n\nCTA: ...",
      "storyboard": {
        "hook": "...",
        "hook_style": "...",
        "cta": "...",
        "summary": "...",
        "scenes": [
          {"scene_no": 0, "t_start": 0.0, "t_end": 3.2, "shot_type": "...",
           "visual": "...", "on_screen_text": "...", "voiceover": "..."}
        ]
      }
    }
  ]
}
```

| field | meaning |
|---|---|
| `id` / `video_id` | same value, `id` added for parity with `/api/v1/data/query`'s shape |
| `text` | the same content as `storyboard`, rendered as one Markdown block ([lib/storyboard.py](lib/storyboard.py)) — for a caller (an LLM prompt, `agent/`'s `HttpJsonRetriever`) that wants a string, not nested fields |
| `matched_keyword` | the search keyword this video was originally ranked under — **not** a claim that the video is about `product_name`; a thin category can surface an off-topic video (see [rag-trending-video.md](rag-trending-video.md)) |
| `revenue_usd` / `views_30d` | Kalodata metrics, always USD over a trailing 30-day window (`meta.currency` / `meta.metrics_window` state this explicitly) |
| `ai_video` | Kalodata's AI-generated-content flag, raw `0`/`1` (not the ad/paid-promotion flag — see `is_ad`) |
| `is_ad` | `true` if this was a paid ad, `false` if organic reach — a paid video's revenue proves ad spend converted, not that the storyboard itself is a good creative reference |
| `engagement_rate` | `(likes + shares + comments) / views`, revenue-independent signal of whether the storyboard resonated; `null` if `views` is unknown |
| `age_days` | days since the video's real publish date (`creator_debut`), falling back to our fetch time only for rows indexed before `creator_debut` was captured |
| `relevance` | the cross-encoder's `rerank_score` mapped through a sigmoid into `[0, 1]` — the raw logit has no fixed scale, this does |
| `rerank_score` / `trending_score` | kept for debugging; prefer `relevance` / `age_days` for reasoning |

Ordering: retrieval candidates (`candidate_k` = 50) are reranked by a cross-encoder,
then ties broken by `trending_score` (revenue decayed by real video age). `relevance_gated`
is always `false` today — nothing is dropped for scoring low, a low-`relevance` result is
still returned and the caller is expected to filter on that field itself. See
[rag-trending-video.md](rag-trending-video.md) for the full pipeline behind this
endpoint.

---

## Config reference

All settings are env vars read once at startup ([lib/settings.py](lib/settings.py)),
`.env`-backed. Relevant ones for these endpoints:

| var                              | default | meaning                              |
|-----------------------------------|---------|----------------------------------------|
| `RETRIEVAL_TOP_K`                 | 5       | default result count                  |
| `RETRIEVAL_MAX_TOP_K`             | 50      | hard cap on `top_k`                   |
| `RETRIEVAL_CANDIDATE_K`           | 50      | candidates fetched before reranking    |
| `RETRIEVAL_LEG_K`                 | 50      | candidates per retrieval leg (dense/lexical) before RRF fusion |
| `RETRIEVAL_RRF_K`                 | 60      | RRF smoothing constant                 |
| `RETRIEVAL_TRIGRAM_THRESHOLD`     | 0.2     | min lexical-leg score to count as a candidate |
| `RETRIEVAL_TRENDING_HALF_LIFE_DAYS` | 14.0  | days for a video's revenue score to halve |
| `RETRIEVAL_RERANK_MIN_SCORE`      | 0.0     | defined, not yet applied (reorder only, no relevance gate) |

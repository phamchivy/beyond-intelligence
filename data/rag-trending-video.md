# RAG: Trending Video Storyboards

How `GET/POST /api/v1/videos/trending` turns a product/category keyword into ranked,
scene-by-scene TikTok video references. Two halves: an offline pipeline that builds
the index (run by hand, not yet Dagster-scheduled), and the online query the API
serves.

## Offline: building the index

```
kalodata_top_videos.py → kalodata_download_videos.py → kalodata_analyze_videos.py → index_storyboards.py
    (rank)                    (fetch .mp4)                  (Gemini storyboard)         (embed + upsert)
```

1. **Rank** — [scripts/kalodata_top_videos.py](scripts/kalodata_top_videos.py) calls
   the Kalodata Open API (TikTok Shop analytics). A product keyword resolves to a
   product id and its category ids, then videos are ranked by revenue in three
   narrowing tiers (exact product → category + keyword → category alone), whichever
   tier finds results first.

2. **Fetch** — [scripts/kalodata_download_videos.py](scripts/kalodata_download_videos.py)
   downloads each ranked video's `.mp4` via `yt-dlp` into Landing, and appends one row
   per video to Bronze `tiktok_video`: revenue, views, `ai_video` flag, `ad` flag
   (paid vs organic), `digg_count`/`share_count`/`comment_count`, `creator_debut` (the
   video's real publish date), category/product name, and `fetched_at` (when *we*
   downloaded it — not the same thing as `creator_debut`). Already-fetched videos
   (matched by `video_id`) are skipped.

3. **Analyze** — [scripts/kalodata_analyze_videos.py](scripts/kalodata_analyze_videos.py)
   sends each new video's bytes and known duration to Gemini ([lib/gemini.py](lib/gemini.py)),
   which watches the video and returns a storyboard: `hook` (the opening line, quoted
   verbatim), `hook_style` (a one-sentence description of what that hook does), `cta`,
   `summary`, and a list of scenes (`shot_type`, `visual`, `on_screen_text`,
   `voiceover`, timestamps). Passing the known duration into the prompt keeps Gemini's
   scene timestamps from running past the end of the video; if they do anyway, that
   video's rows are quarantined rather than written to Silver (`storyboard_timestamps_out_of_range`).
   One row per scene is validated against
   [contracts/video_storyboard.py](contracts/video_storyboard.py) and appended to
   Silver `video_storyboard`; rejects go to quarantine. A video already analyzed at
   the current `GEMINI_PROMPT_VERSION` is skipped — changing the prompt or model
   forces re-analysis rather than silently mixing storyboard versions.

4. **Index** — [scripts/index_storyboards.py](scripts/index_storyboards.py) filters
   Silver to the *current* `GEMINI_PROMPT_VERSION` before grouping — Silver is
   append-only, so without this filter a video re-analyzed under a newer prompt would
   have both versions' scenes interleave into one chunk. It then joins the surviving
   scenes back to their Bronze `tiktok_video` row (for revenue/views/etc.) and builds
   **one chunk per video** (not per scene — the endpoint returns videos, so the video
   is the retrieval unit). The chunk's searchable text is title + product + category +
   hook + summary, followed by every scene's shot type/visual/on-screen text/voiceover,
   then the CTA — title/product/category lead because a query is a product or category
   name far more often than a line of dialogue, and the dense embedding leg weights
   early tokens. The full storyboard and ranking fields (`revenue`, `views`,
   `ai_video`, `ad`, engagement counts, `creator_debut`, `duration_s`, `matched_keyword`,
   etc.) are stashed in the chunk's `metadata` JSON, so the API needs no S3/Delta read
   per request. Chunks are embedded ([lib/embedding.py](lib/embedding.py), a local
   fastembed ONNX model, 384-dim) and upserted into `index.chunk` / `index.embedding`
   (`ON CONFLICT DO UPDATE`, so re-running refreshes rather than duplicating). The
   index is then snapshotted to Delta on S3 as a Postgres backup.

## Online: serving a query

`_run_trending` in [api.py](api.py) (called by both the GET and POST routes):

1. **Retrieve** — the query is embedded with the same model, then
   [lib/db.py](lib/db.py)`.search(...)` runs hybrid retrieval filtered to
   `source_type = "video_storyboard"`:
   - **dense leg**: cosine distance over `index.embedding`, top `leg_k` (50)
   - **lexical leg**: `pg_trgm` similarity + `ts_rank` full-text, top `leg_k` (50),
     candidates below `trigram_threshold` (0.2) dropped
   - both legs are fused by **rank** (Reciprocal Rank Fusion, `rrf_k` = 60) — RRF
     fuses ranks rather than raw scores because the two legs' scores live on
     different, uncalibrated scales
   - up to `candidate_k` (50) fused candidates come back

2. **Rerank** — every candidate's chunk text is scored against the query by a local
   cross-encoder ([lib/rerank.py](lib/rerank.py)). RRF only knows a chunk placed well
   on both legs, not whether its text actually answers the query; the cross-encoder
   score does, and unlike RRF has an absolute scale (a relevance-cutoff `rerank_min_score`
   setting exists for this, but is not applied yet — everything is reordered, nothing
   is dropped for scoring low).

3. **Rank by (relevance, trending)** — candidates are sorted by `(rerank_score,
   trending_score)` descending. `rerank_score` decides order first; `trending_score`
   only breaks ties among equally-relevant candidates. `trending_score` is
   `revenue * 0.5 ** (age_days / trending_half_life_days)` — revenue halved every
   `trending_half_life_days` (14 by default). `age_days` is computed from
   `creator_debut` (the video's real publish date), falling back to `fetched_at`
   (our download time) only for rows indexed before `creator_debut` existed — decaying
   off fetch time would make a video published a year ago but fetched yesterday read
   as brand-new. This is a **decay**, not a hard "last N days" cutoff: a strict date
   filter returns nothing at all once the bucket is thin, which reads to a caller as a
   broken endpoint, whereas decay always returns *something*, just weighted toward
   what's recent.

4. **Shape the response** — the top `top_k` (default 5, capped at `max_top_k` = 50)
   ranked chunks are flattened into `items`, each carrying `id`/`video_id`, `title`,
   `url`, `category_name`, `product_name`, `matched_keyword`, `revenue_usd`,
   `views_30d`, `ai_video`, `is_ad`, `engagement_rate`, `duration_s`, `age_days`,
   `relevance` (the cross-encoder logit mapped through a sigmoid into `[0, 1]`,
   since the raw logit has no fixed scale to reason from), `rerank_score`,
   `trending_score`, a `text` rendition of the whole reference block
   ([lib/storyboard.py](lib/storyboard.py), shared with the offline markdown preview),
   and the full nested `storyboard` (hook/hook_style/cta/summary/scenes) — everything
   a caller (an LLM prompt, or `agent/`'s `HttpJsonRetriever`) needs to both rank and
   actually reason about what the video does, without a second round trip. A sibling
   `meta` object (`query`, `currency`, `metrics_window`, `candidates_considered`,
   `relevance_gated: false`) states plainly what the numbers mean and that nothing was
   dropped on relevance — see [api-reference.md](api-reference.md) for the full field
   table.

## Why this shape

- **Revenue-decay over date-cutoff** — see step 3; a thin trending bucket must still
  answer, not 404.
- **Relevance before trending** — an irrelevant video must never outrank a relevant
  one purely because it made more money; trending is a tiebreak, not the primary
  sort key.
- **`is_ad` and `engagement_rate`, not just `revenue_usd`** — revenue alone conflates
  "this storyboard converted" with "this storyboard was paid to be seen." A paid ad
  can win on spend with a mediocre hook; an organic top performer with a high
  engagement rate is actual proof its hook and pacing worked unassisted. Both signals
  come from the same Kalodata `video/rank` call `to_row()` was already discarding them
  from.
- **`age_days` off `creator_debut`, not `fetched_at`** — `fetched_at` is our download
  time, unrelated to how old the video actually is; a year-old video fetched
  yesterday must not read as new.
- **`matched_keyword` is a caveat field, not a content label** — `top_videos()`'s
  narrowing tiers (see step 1) can fall back to "top revenue anywhere in the
  category," which can surface a video about a different product than the one
  searched for. `matched_keyword` names what was searched so a caller (or an LLM)
  doesn't assume `product_name` describes what's actually in the storyboard.
- **`relevance` as a sigmoid, not the raw rerank logit** — a cross-encoder logit's
  scale is model-specific; `relevance` gives every caller (human or LLM) the same
  `[0, 1]` reading regardless of which reranker model is pinned.
- **One chunk per video** — keeps the trending endpoint's retrieval unit aligned with
  what it returns; no post-hoc de-duplication across a video's scenes.
- **Metadata carries the whole storyboard** — the query path never touches S3 or
  Delta; everything needed to answer is already sitting in Postgres `index.chunk`.
- **Not Dagster-scheduled** — the four offline scripts are run by hand
  (`python -m scripts.<name>`); nothing in [defs/](defs/) currently schedules the
  Kalodata fetch → analyze → index chain.

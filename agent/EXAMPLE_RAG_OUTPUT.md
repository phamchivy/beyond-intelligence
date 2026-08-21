# RAG Retrieval Example Output

Complete end-to-end example showing task → retrieval → prompt building.

## Step 1: Agent Task

```python
task = Task.create(
    goal="Generate a storyboard plan for a 30-second video ad for 'Electric Shaver Pro' "
         "targeting professional men aged 25-45 with emphasis on time-saving and precision"
)
```

## Step 2: Retrieval Query

```python
# ContextBuilder.build(task) calls:
documents = await retriever.retrieve(
    query="Generate a storyboard plan for a 30-second video ad for 'Electric Shaver Pro' "
          "targeting professional men aged 25-45 with emphasis on time-saving and precision",
    top_k=5
)

# Which hits: GET http://data:8000/api/v1/videos/trending?q=<query>&top_k=5
```

## Step 3: Retrieval Response (from data/api.py)

**HTTP Response 200 OK (top_k=5, all 5 results shown):**
```json
{
  "meta": {
    "query": "Generate a storyboard plan...",
    "candidates_considered": 143,
    "relevance_gated": false
  },
  "items": [  // ← 5 items returned (top_k=5)
    {
      "id": "chunk_v1",
      "video_id": "v1_shaver_demo",
      "title": "Gillette SkinGuard Speed Shave",
      "url": "https://www.tiktok.com/@gillette/video/...",
      "category_name": "Men's Personal Care",
      "product_name": "Gillette SkinGuard",
      "matched_keyword": "electric shaver",
      "revenue_usd": 5200,
      "views_30d": 245000,
      "ai_video": true,
      "is_ad": true,
      "engagement_rate": 0.0184,
      "duration_s": 29,
      "age_days": 3.2,
      "relevance": 0.94,
      "rerank_score": 2.8341,
      "trending_score": 4891.20,
      "text": "**Category:** Men's Personal Care | **Revenue:** $5,200 | **Views:** 245,000\n**Hook:** \"Skip the morning routine chaos - 30 seconds to perfect\"\n**Style:** \"Effortless precision for the busy professional\"\n**CTA:** \"Get Gillette SkinGuard Now\"\n\n**Scenes:**\n| Timestamp | Action | Voiceover |\n|-----------|--------|----------|\n| 0-3s | Split screen: messy bathroom vs clean mirror | \"Most shaving routines waste 15 minutes\" |\n| 3-8s | Close-up of SkinGuard tech | \"Precision sensors adjust to your skin in 0.3 seconds\" |\n| 8-15s | Quick shave demo (side angle) | \"30 seconds. That's all you need.\" |\n| 15-22s | Before/after comparison | \"Smooth. No cuts. No irritation.\" |\n| 22-29s | Product shot + guy checking mirror | \"30-second shave. Professional results.\" |",
      "storyboard": {
        "hook": "Skip the morning routine chaos - 30 seconds to perfect",
        "hook_style": "Effortless precision for the busy professional",
        "cta": "Get Gillette SkinGuard Now",
        "scenes": [
          {
            "t_start": 0,
            "t_end": 3,
            "action": "Split screen: messy bathroom vs clean mirror",
            "voiceover": "Most shaving routines waste 15 minutes"
          },
          {
            "t_start": 3,
            "t_end": 8,
            "action": "Close-up of SkinGuard tech",
            "voiceover": "Precision sensors adjust to your skin in 0.3 seconds"
          },
          {
            "t_start": 8,
            "t_end": 15,
            "action": "Quick shave demo (side angle)",
            "voiceover": "30 seconds. That's all you need."
          },
          {
            "t_start": 15,
            "t_end": 22,
            "action": "Before/after comparison",
            "voiceover": "Smooth. No cuts. No irritation."
          },
          {
            "t_start": 22,
            "t_end": 29,
            "action": "Product shot + guy checking mirror",
            "voiceover": "30-second shave. Professional results."
          }
        ]
      }
    },
    {
      "id": "chunk_v2",
      "video_id": "v2_braun_routine",
      "title": "Braun Series 9 Time-Saver",
      "url": "https://www.tiktok.com/@braun/video/...",
      "category_name": "Men's Personal Care",
      "product_name": "Braun Series 9",
      "matched_keyword": "electric shaver precision",
      "revenue_usd": 4800,
      "views_30d": 198000,
      "ai_video": false,
      "is_ad": true,
      "engagement_rate": 0.0167,
      "duration_s": 30,
      "age_days": 1.8,
      "relevance": 0.87,
      "rerank_score": 2.4156,
      "trending_score": 4520.50,
      "text": "**Category:** Men's Personal Care | **Revenue:** $4,800 | **Views:** 198,000\n**Hook:** \"Busy schedule? Braun does the work in 40 seconds\"\n**Style:** \"The intelligent shaver for modern professionals\"\n**CTA:** \"Shop Braun Series 9\"\n\n**Scenes:**\n| Timestamp | Action | Voiceover |\n|-----------|--------|----------|\n| 0-5s | Quick montage of morning rush | \"Running late again?\" |\n| 5-12s | Braun device with AI animation | \"AI learns your beard pattern in seconds\" |\n| 12-22s | Shaving demo (front & side) | \"One pass. Perfect. Every time.\" |\n| 22-28s | Finished look, office setting | \"Ready in 40 seconds\" |\n| 28-30s | Product + QR code | \"Braun Series 9. For the professional you.\" |",
      "storyboard": {
        "hook": "Busy schedule? Braun does the work in 40 seconds",
        "hook_style": "The intelligent shaver for modern professionals",
        "cta": "Shop Braun Series 9",
        "scenes": [...]
      }
    },
    {
      "id": "chunk_v3",
      "video_id": "v3_panasonic_arc",
      "title": "Panasonic Arc5 Executive Shave",
      "category_name": "Men's Personal Care",
      "product_name": "Panasonic Arc5",
      "relevance": 0.79,
      "revenue_usd": 3900,
      "views_30d": 156000,
      "text": "**Category:** Men's Personal Care | **Revenue:** $3,900 | **Views:** 156,000\n**Hook:** \"Five-blade precision meets 45-minute battery\"\n**Style:** \"The executive's choice for business-ready grooming\"\n\n**Scenes:**\n| 0-4s | Executive boardroom setting | \"First impression happens in seconds\" |\n| 4-10s | Panasonic Arc5 close-up | \"Five-blade synchronization technology\" |\n| 10-18s | Shaving demo, multiple angles | \"Leaves no stubble. Zero irritation.\" |\n| 18-26s | Polished look, ready for meeting | \"Meeting ready in 5 minutes\" |"
    },
    {
      "id": "chunk_v4",
      "video_id": "v4_philips_norelco",
      "title": "Philips Norelco S9000 Premium",
      "category_name": "Men's Personal Care",
      "product_name": "Philips Norelco S9000",
      "relevance": 0.72,
      "revenue_usd": 3400,
      "views_30d": 134000,
      "text": "**Category:** Men's Personal Care | **Revenue:** $3,400 | **Views:** 134,000\n**Hook:** \"Smart shave that adapts to your beard\"\n**Style:** \"Intelligence meets precision grooming\"\n\n**Scenes:**\n| 0-6s | Problem: patchy shaving results | \"Uneven beard growth? Not anymore\" |\n| 6-14s | Philips Norelco shaver with sensors lit up | \"8 adaptive sensors read your beard\" |\n| 14-22s | Real-time demo | \"Adjusts power 200x per second\" |\n| 22-28s | Perfect result, confident look | \"Perfect every single time\" |"
    },
    {
      "id": "chunk_v5",
      "video_id": "v5_remington_pro",
      "title": "Remington F5 Professional Cut",
      "category_name": "Men's Personal Care",
      "product_name": "Remington F5",
      "relevance": 0.68,
      "revenue_usd": 2800,
      "views_30d": 98000,
      "text": "**Category:** Men's Personal Care | **Revenue:** $2,800 | **Views:** 98,000\n**Hook:** \"Barber quality. Home price. 60-second trim\"\n**Style:** \"Professional grooming without the salon cost\"\n\n**Scenes:**\n| 0-4s | Quick split: expensive salon vs home | \"Skip the $40 barber appointment\" |\n| 4-12s | Remington F5 detailed shots | \"Precision cutting guide. 18 settings.\" |\n| 12-20s | DIY demo: actual haircut | \"Barber precision in 60 seconds\" |\n| 20-28s | Final result: salon-quality cut | \"$199 investment. Unlimited cuts.\" |"
    }
  ]
}
```

## Step 4: Response Mapping

```python
# _map_trending_videos_response() transforms each of 5 items:
documents = [
  RetrievedDocument(
    content=item["text"],                          # The rendered storyboard block
    source=item["video_id"],                       # v1_shaver_demo, v2_braun_routine, v3_panasonic_arc, v4_philips_norelco, v5_remington_pro
    score=item["relevance"],                       # 0.94, 0.87, 0.79, 0.72, 0.68 (sigmoid-calibrated)
    metadata={
      "title": item["title"],
      "product_name": item["product_name"]
    }
  )
  for item in response["items"]  # All 5 items
]
```

## Step 5: Built LLM Prompt

```
═══════════════════════════════════════════════════════════════════════════════
[MESSAGE 1] Role: SYSTEM
───────────────────────────────────────────────────────────────────────────────
You are a creative director specializing in short-form video content for 
e-commerce brands. Your role is to generate compelling 15-60 second storyboard 
plans that showcase products in ways that resonate with target audiences and 
drive conversions. Consider pacing, hook strength, visual variety, and clear 
product value proposition.

═══════════════════════════════════════════════════════════════════════════════
[MESSAGE 2] Role: SYSTEM (← NEW: Retrieved trending videos, relevance 0.94-0.87)
───────────────────────────────────────────────────────────────────────────────
Reference trending videos (RAG):

**Category:** Men's Personal Care | **Revenue:** $5,200 | **Views:** 245,000
**Hook:** "Skip the morning routine chaos - 30 seconds to perfect"
**Style:** "Effortless precision for the busy professional"
**CTA:** "Get Gillette SkinGuard Now"

**Scenes:**
| Timestamp | Action | Voiceover |
|-----------|--------|-----------|
| 0-3s | Split screen: messy bathroom vs clean mirror | "Most shaving routines waste 15 minutes" |
| 3-8s | Close-up of SkinGuard tech | "Precision sensors adjust to your skin in 0.3 seconds" |
| 8-15s | Quick shave demo (side angle) | "30 seconds. That's all you need." |
| 15-22s | Before/after comparison | "Smooth. No cuts. No irritation." |
| 22-29s | Product shot + guy checking mirror | "30-second shave. Professional results." |

**Category:** Men's Personal Care | **Revenue:** $4,800 | **Views:** 198,000
**Hook:** "Busy schedule? Braun does the work in 40 seconds"
**Style:** "The intelligent shaver for modern professionals"
**CTA:** "Shop Braun Series 9"

**Scenes:**
| Timestamp | Action | Voiceover |
|-----------|--------|-----------|
| 0-5s | Quick montage of morning rush | "Running late again?" |
| 5-12s | Braun device with AI animation | "AI learns your beard pattern in seconds" |
| 12-22s | Shaving demo (front & side) | "One pass. Perfect. Every time." |
| 22-28s | Finished look, office setting | "Ready in 40 seconds" |
| 28-30s | Product + QR code | "Braun Series 9. For the professional you." |

**Category:** Men's Personal Care | **Revenue:** $3,900 | **Views:** 156,000
**Hook:** "Five-blade precision meets 45-minute battery"
**Style:** "The executive's choice for business-ready grooming"

**Scenes:**
| 0-4s | Executive boardroom setting | "First impression happens in seconds" |
| 4-10s | Panasonic Arc5 close-up | "Five-blade synchronization technology" |
| 10-18s | Shaving demo, multiple angles | "Leaves no stubble. Zero irritation." |
| 18-26s | Polished look, ready for meeting | "Meeting ready in 5 minutes" |

**Category:** Men's Personal Care | **Revenue:** $3,400 | **Views:** 134,000
**Hook:** "Smart shave that adapts to your beard"
**Style:** "Intelligence meets precision grooming"

**Scenes:**
| 0-6s | Problem: patchy shaving results | "Uneven beard growth? Not anymore" |
| 6-14s | Philips Norelco shaver with sensors lit up | "8 adaptive sensors read your beard" |
| 14-22s | Real-time demo | "Adjusts power 200x per second" |
| 22-28s | Perfect result, confident look | "Perfect every single time" |

**Category:** Men's Personal Care | **Revenue:** $2,800 | **Views:** 98,000
**Hook:** "Barber quality. Home price. 60-second trim"
**Style:** "Professional grooming without the salon cost"

**Scenes:**
| 0-4s | Quick split: expensive salon vs home | "Skip the $40 barber appointment" |
| 4-12s | Remington F5 detailed shots | "Precision cutting guide. 18 settings." |
| 12-20s | DIY demo: actual haircut | "Barber precision in 60 seconds" |
| 20-28s | Final result: salon-quality cut | "$199 investment. Unlimited cuts." |

═══════════════════════════════════════════════════════════════════════════════
[MESSAGE 3] Role: USER (← Task goal)
───────────────────────────────────────────────────────────────────────────────
Generate a storyboard plan for a 30-second video ad for 'Electric Shaver Pro' 
targeting professional men aged 25-45 with emphasis on time-saving and precision.
```

## Step 6: LLM Response (Example)

The LLM, having seen the FIVE reference storyboards (Gillette, Braun, Panasonic, Philips, Remington), generates:

```
**STORYBOARD PLAN: Electric Shaver Pro**

**Hook Strategy:** "Professional shave. Zero compromise. 30 seconds."
- Why: Similar to Gillette/Braun, time is a key pain point for busy professionals
- Tone: Confident, aspirational, no-nonsense

**Target Audience Resonance:** Professional men, 25-45
- Related to: Time-consciousness, precision, polish
- Learned from reference: Split-screen "before chaos / after perfect" hooks work well

**Recommended Scene Sequence (30s total):**

| Timestamp | Scene | Voiceover | Camera | Why |
|-----------|-------|-----------|--------|-----|
| 0-2s | Problem: Professional in mirror, stubble visible | "Stubble kills first impressions" | Close-up, morning lighting | Hook attention fast (Gillette pattern) |
| 2-7s | Product reveal + tech showcase | "3-stage precision system. One pass." | Clean product shot, glowing accent lighting | Show differentiator (Braun AI pattern) |
| 7-20s | Live demo: shave sequence | "Smooth. Confidence. In 28 seconds." | Side angle of shaving, multiple passes | Demonstrate speed advantage |
| 20-26s | Result: professional look, office ready | "Before your first meeting" | Full face, mirror shot, subtle smile | Aspirational payoff |
| 26-30s | Product + CTA | "Electric Shaver Pro. Precision. Speed. Always." | Product on desk with tie/watch | Clear call-to-action |

**Key Decisions Influenced by RAG:**
- Time-saving is the primary hook (both references lead with speed)
- Before/after structure works (Gillette success pattern)
- Technical credibility matters (Braun's AI approach)
- Professional setting/aftermath, not just shaving (both references)
```

## Code That Built This

```python
# From ReasoningService._build_request (application/reasoning/reasoning_service.py:106-113)
if state.context.retrieved_documents:
    reference_block = "\n\n".join(doc.content for doc in state.context.retrieved_documents)
    messages.append(
        LLMMessage(
            role=MessageRole.SYSTEM,
            content=f"Reference trending videos (RAG):\n\n{reference_block}",
        )
    )
```

## Key Observations

1. **Relevance Scores (0.94 → 0.68):** All 5 results ranked by sigmoid-calibrated relevance. Gillette (0.94) most relevant to query, Remington (0.68) still useful but lower match. Each storyboard brings different angle: speed (Gillette), AI-tech (Braun/Philips), executive polish (Panasonic), cost efficiency (Remington).

2. **Message Order Matters:** System prompt → Reference docs (all 5) → User goal. LLM sees ALL trending examples BEFORE the task.

3. **Content Reusability:** Same `item["text"]` blocks already rendered for API responses are reused in prompt without reformatting — text field is pre-rendered by `lib/storyboard.py::render_block()`.

4. **Full Context Window:** With 5 storyboards, LLM sees:
   - 2 time-saving hooks (Gillette, Braun)
   - 1 executive setting hook (Panasonic)
   - 1 tech-forward hook (Philips AI)
   - 1 value/ROI hook (Remington)
   All within one SYSTEM message (joined by `"\n\n"`)

5. **Graceful Degradation:** If `RETRIEVAL_BASE_URL` unset, `_build_retriever` returns `None`, reference message never inserted, prompt falls back to just system+goal. Every existing test/environment works unchanged.

6. **Configurable Top-K:** With `RETRIEVAL_TOP_K=5`, retriever returns top 5. Change in `.env`:
   - `RETRIEVAL_TOP_K=3` → only top 3 videos in prompt (smaller context, fewer tokens)
   - `RETRIEVAL_TOP_K=10` → up to 10 videos (more context, higher token cost)
   Default 5 is sweet spot: enough diversity, reasonable token budget.

## Testing Locally

To test without a running `data/` pod:

```bash
# 1. Use MOCK LLM (no API cost)
export LLM_PROVIDER=mock
export RETRIEVAL_TOP_K=5

# 2. Leave RETRIEVAL_BASE_URL unset (gracefully degrades)
# RETRIEVAL_BASE_URL commented in .env

# 3. Run tests
pytest tests/unit/application/reasoning/test_reasoning_service.py::TestReasoningServiceWithRetrievedDocuments -xvs
pytest tests/unit/bootstrap/test_container.py::TestMapTrendingVideosResponse -xvs

# 4. Full suite (all tests pass with or without RAG)
pytest tests/unit/ -q
```

No external dependencies or real API calls needed to verify the prompt building logic.

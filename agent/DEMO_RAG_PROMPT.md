# RAG Prompt Demonstration

This demonstrates how the agent's prompt is built when RAG-retrieved trending videos are integrated.

## Setup

**Retrieved Documents** (from `data/api.py:/api/v1/videos/trending`):
```
Chunk 1 (relevance: 0.95, video_id: v1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category: Beauty Devices | Revenue: $4,200 | Views: 12,500

Hook: "This mister transforms your skincare routine instantly"
Style: "Transform your routine in seconds"
CTA: "Shop Mesh Nebulizer Now"

Scenes:
| Timestamp | Action                    | Voiceover                         |
|-----------|---------------------------|-----------------------------------|
| 0-2s      | Close-up of device        | "Say goodbye to manual application"|
| 2-5s      | Demo misting              | "Ultra-fine mist reaches every pore"|
| 5-8s      | Happy user                | "See results in just 3 uses"      |

Chunk 2 (relevance: 0.88, video_id: v2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category: Face Care | Revenue: $3,800 | Views: 9,200

Hook: "No more dry skin - this serum does the magic"
Style: "One serum, infinite glow"
CTA: "Get Your Glow Back"

Scenes:
| Timestamp | Action                    | Voiceover                         |
|-----------|---------------------------|-----------------------------------|
| 0-3s      | Before/after split        | "Hydration depletes in dry climate"|
| 3-6s      | Product close-up          | "3 botanical extracts + hyaluronic"|
| 6-9s      | Application demo          | "3 drops = 24-hour hydration"     |
```

## Built Prompt (as seen by the LLM)

```
[MESSAGE 1] Role: SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are a creative director specializing in short-form video content for 
e-commerce. Your job is to generate compelling storyboard plans that showcase 
products in ways that resonate with target audiences.

[MESSAGE 2] Role: SYSTEM (← NEW: Retrieved trending video reference material)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reference trending videos (RAG):

Category: Beauty Devices | Revenue: $4,200 | Views: 12,500

Hook: "This mister transforms your skincare routine instantly"
Style: "Transform your routine in seconds"
CTA: "Shop Mesh Nebulizer Now"

Scenes:
| Timestamp | Action                    | Voiceover                         |
|-----------|---------------------------|-----------------------------------|
| 0-2s      | Close-up of device        | "Say goodbye to manual application"|
| 2-5s      | Demo misting              | "Ultra-fine mist reaches every pore"|
| 5-8s      | Happy user                | "See results in just 3 uses"      |

Category: Face Care | Revenue: $3,800 | Views: 9,200

Hook: "No more dry skin - this serum does the magic"
Style: "One serum, infinite glow"
CTA: "Get Your Glow Back"

Scenes:
| Timestamp | Action                    | Voiceover                         |
|-----------|---------------------------|-----------------------------------|
| 0-3s      | Before/after split        | "Hydration depletes in dry climate"|
| 3-6s      | Product close-up          | "3 botanical extracts + hyaluronic"|
| 6-9s      | Application demo          | "3 drops = 24-hour hydration"     |

[MESSAGE 3] Role: USER (← Task goal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a storyboard plan for a 30-second ad video for 'Electric Shaver Pro' 
targeting men aged 25-40 with focus on time-saving.
```

## Code Path

**Step 1: Query Execution**
```python
# Agent.run() receives a task
task = Task.create(goal="Generate a storyboard plan for...")

# ContextBuilder calls Retriever
context = await context_builder.build(task)
  ↓
# Retriever calls data/api.py endpoint
documents = await retriever.retrieve(task.goal, top_k=5)
  ↓
# Response mapper transforms API response
RetrievedDocument(
    content=item["text"],           # Pre-rendered storyboard block
    source=item["video_id"],        # v1, v2, etc.
    score=item["relevance"],        # 0.95, 0.88, etc.
    metadata={...}                  # title, product_name
)
  ↓
# Context populated with documents
context = Context().with_documents(documents)
```

**Step 2: Prompt Building**
```python
# ReasoningService._build_request() constructs messages
messages = []

# Add system prompt if configured
if self._system_prompt:
    messages.append(SYSTEM("You are a creative director..."))

# ← NEW: Add retrieved documents as context
if state.context.retrieved_documents:
    reference_block = "\n\n".join(doc.content for doc in documents)
    messages.append(SYSTEM(f"Reference trending videos (RAG):\n\n{reference_block}"))

# Add task goal as the user's request
messages.append(USER(state.task.goal))

# Add any prior observations (tool results, etc.)
for observation in state.observations:
    messages.append(ASSISTANT(f"[{observation.source}] {observation.content}"))

# Return the full LLMRequest
return LLMRequest(messages=tuple(messages), tools=available_tools)
```

**Step 3: LLM Call**
```python
# The LLM sees all three messages and generates a response
response = await llm.generate(request)
# ↓
# LLM has context from:
#   - System prompt (role/style)
#   - Trending video examples (what's working now)  ← RAG
#   - Task goal (what to create)
# ↓
# Result: storyboard plan informed by real viral content
```

## Key Points

1. **Graceful Degradation**: If `RETRIEVAL_BASE_URL` is not set, `_build_retriever` returns `None`, and the reference message is never added—every existing test and environment works unchanged.

2. **Message Order**: System prompt → Reference docs → Task goal → Observations. This ensures the LLM sees grounding material before the ask.

3. **One Message, Not N**: All retrieved documents are joined into a single SYSTEM message (not one per document), keeping the message count minimal and the references self-contained.

4. **Data Format**: The `text` field from `data/api.py` response is already rendered by `lib/storyboard.py::render_block()` as a prompt-ready Markdown block—no further formatting needed.

## Testing

Run unit tests to verify the prompt building:

```bash
pytest tests/unit/application/reasoning/test_reasoning_service.py -xvs
pytest tests/unit/application/context/test_context_builder.py -xvs
pytest tests/unit/bootstrap/test_container.py::TestMapTrendingVideosResponse -xvs
```

All tests use hand-rolled fakes (no external mocking libs), matching the codebase convention.

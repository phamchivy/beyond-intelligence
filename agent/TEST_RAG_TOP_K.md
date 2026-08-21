# Test: RAG Retrieval Returns 5 Chunks (top_k=5)

New integration test verifies the complete RAG retrieval chain returns exactly 5 storyboards and includes all of them in the LLM prompt.

## Test File

`tests/unit/application/context/test_rag_retrieval_integration.py`

## What It Tests

### 1. Response Mapping (5 → 5)
```python
def test_maps_5_items_to_5_documents():
    """Verify all 5 items are mapped when top_k=5."""
```

**Input:** HTTP response from `data/api.py` with 5 items (Gillette, Braun, Panasonic, Philips, Remington)

**Process:**
```python
docs = _map_trending_videos_response(response_payload)
```

**Assertions:**
- ✓ Returns exactly 5 `RetrievedDocument` objects
- ✓ Ordered by relevance (0.94 → 0.87 → 0.79 → 0.72 → 0.68)
- ✓ All 5 video_ids present (v1, v2, v3, v4, v5)
- ✓ Each doc has non-empty content and metadata

### 2. Fewer Results Than top_k
```python
def test_handles_fewer_than_top_k_results():
    """Verify retrieval gracefully handles when API returns <top_k results."""
```

**Scenario:** Index has only 2 videos, but top_k=5

**Assertions:**
- ✓ Returns 2 docs (not padded to 5)
- ✓ No errors, graceful fallback

### 3. Empty Response
```python
def test_empty_response_returns_empty_list():
    """Verify retrieval returns empty list when no results."""
```

**Scenario:** Query matches no videos

**Assertions:**
- ✓ Returns empty list `[]`
- ✓ Downstream prompt building handles it (MESSAGE 2 skipped)

### 4. All 5 Docs in Prompt (End-to-End)
```python
def test_all_5_docs_included_in_prompt():
    """Verify all 5 retrieved docs are joined into a single prompt message."""
```

**Complete flow:**
```
5 RetrievedDocuments
  ↓
Context.with_documents(docs)
  ↓
AgentState(context=context)
  ↓
ReasoningService._build_request(state)
  ↓
LLM sees MESSAGE 2: "Reference trending videos (RAG):\n\n[all 5 storyboards]"
```

**Assertions:**
- ✓ Exactly 1 "Reference trending videos" message
- ✓ All 5 storyboards present in that message
- ✓ All 5 are in one message, not 5 separate messages
- ✓ Message is role=SYSTEM (grounding, not user turn)

## Running the Tests

```bash
# Run all RAG retrieval tests
pytest tests/unit/application/context/test_rag_retrieval_integration.py -xvs

# Run specific test
pytest tests/unit/application/context/test_rag_retrieval_integration.py::TestRetrievalTopK::test_maps_5_items_to_5_documents -xvs

# Run all context-builder tests (including RAG)
pytest tests/unit/application/context/ -xvs

# Full suite (all tests)
pytest tests/unit/ -q
```

## Expected Output

```
tests/unit/application/context/test_rag_retrieval_integration.py::TestRetrievalTopK::test_maps_5_items_to_5_documents PASSED
tests/unit/application/context/test_rag_retrieval_integration.py::TestRetrievalTopK::test_handles_fewer_than_top_k_results PASSED
tests/unit/application/context/test_rag_retrieval_integration.py::TestRetrievalTopK::test_empty_response_returns_empty_list PASSED
tests/unit/application/context/test_rag_retrieval_integration.py::TestRetrievalTopK::test_all_5_docs_included_in_prompt PASSED

========================== 4 passed in 0.12s ==========================
```

## Code Paths Tested

### Path 1: Mapper
```python
bootstrap/container.py::_map_trending_videos_response()
  ↓
Takes: {"items": [5 items from data/api.py]}
  ↓
Returns: [5 RetrievedDocument(content=item["text"], score=item["relevance"])]
```

### Path 2: Context Builder
```python
application/context/context_builder.py::ContextBuilder.build()
  ↓
Calls: retriever.retrieve(query, top_k=5)
  ↓
Returns: Context().with_documents([5 docs])
```

### Path 3: Prompt Building
```python
application/reasoning/reasoning_service.py::_build_request()
  ↓
If state.context.retrieved_documents:
  ↓
Joins all docs with "\n\n"
  ↓
Adds MESSAGE 2: "Reference trending videos (RAG):\n\n[5 storyboards]"
```

## Verification: 5-Chunk Output

Test data simulates real `data/api.py` response:

| Video | Relevance | Hook | 
|-------|-----------|------|
| Gillette | 0.94 | "Skip the morning routine chaos - 30 seconds to perfect" |
| Braun | 0.87 | "Busy schedule? Braun does the work in 40 seconds" |
| Panasonic | 0.79 | "Five-blade precision meets 45-minute battery" |
| Philips | 0.72 | "Smart shave that adapts to your beard" |
| Remington | 0.68 | "Barber quality. Home price. 60-second trim" |

All 5 are mapped → all 5 end up in context → all 5 appear in prompt MESSAGE 2.

## Configuration

Top-K is configurable via env (no code change needed):

```bash
# Change top_k in .env
RETRIEVAL_TOP_K=3   # Get 3 storyboards
RETRIEVAL_TOP_K=5   # Get 5 (default)
RETRIEVAL_TOP_K=10  # Get 10 (if more references wanted)
```

If `RETRIEVAL_BASE_URL` is unset, retriever returns `None`, ContextBuilder gracefully returns empty Context, MESSAGE 2 is never added. All tests still pass with zero changes.

## Next Steps

To test against **live `data/` pod** (real API call):

1. Start compose stack:
   ```bash
   cd /path/to/data && docker compose up -d postgres api
   ```

2. Set env in agent/:
   ```bash
   export RETRIEVAL_BASE_URL=http://localhost:8000/api/v1/videos/trending
   export RETRIEVAL_TOP_K=5
   ```

3. Run `ContextBuilder` directly (manual test):
   ```python
   from application.context.context_builder import ContextBuilder
   from bootstrap.container import _build_context_builder
   from config.settings import Settings
   
   config = Settings()  # Reads .env
   builder = _build_context_builder(config)
   
   task = Task.create(goal="Electric shaver professional time-saving")
   context = await builder.build(task)
   
   print(f"Retrieved {len(context.retrieved_documents)} documents")
   for doc in context.retrieved_documents:
       print(f"  - {doc.source}: relevance {doc.score}")
   ```

This will hit the real `/api/v1/videos/trending?q=...&top_k=5` endpoint and show actual retrieval results.

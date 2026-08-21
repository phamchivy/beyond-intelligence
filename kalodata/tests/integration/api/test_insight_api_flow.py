"""
Vi tri file nay: data/tests/integration/api/test_insight_api_flow.py

Test toan bo luong HTTP qua ASGITransport (khong can uvicorn that),
dung Mock nen chay nhanh -- cung pattern nhu agent/tests/integration/api/.
"""
from __future__ import annotations

import httpx
import pytest

from application.services.insight_service import InsightService
from domain.ports.llm import LLMResponse
from domain.ports.market_data_provider import MarketDataDomain, RankingItem
from infrastructure.kalodata.mock_kalodata_client import MockKalodataClient
from infrastructure.llm.mock_llm import MockLLM
from interface.api.insight_routes import get_insight_service
from interface.api.main import app

_SAMPLE_BRIEF = {
    "product_info": {"name": "Giay the thao ABC", "category": "footwear"},
    "target_audience": {"who": "gen Z"},
    "ad_objective": "conversion",
    "key_message": "Ben, nhe, gia tot",
    "channel": "tiktok",
    "creative_reference": None,
    "constraints": {"duration_seconds": 15},
}


@pytest.fixture
def mock_service() -> InsightService:
    kalodata = MockKalodataClient(
        ranking_response=[
            RankingItem(domain=MarketDataDomain.VIDEO, item_id="v1", raw={"video_id": "v1", "revenue": 5000})
        ],
        detail_response={"video_id": "v1"},
    )
    llm = MockLLM(
        response_queue=[
            LLMResponse(content='{"keyword": "giay", "sort_field": "revenue"}'),
            LLMResponse(content="insight ban dau"),
            LLMResponse(content='{"keyword": "giay cao cap", "sort_field": "revenue"}'),
            LLMResponse(content="insight da sua"),
        ]
    )
    return InsightService(llm=llm, market_data_provider=kalodata)


@pytest.fixture
async def client(mock_service: InsightService):
    app.dependency_overrides[get_insight_service] = lambda: mock_service
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestInsightApiFlow:
    async def test_full_flow(self, client: httpx.AsyncClient) -> None:
        start = await client.post(
            "/data/insights", json={"task_id": "task-1", "brief": _SAMPLE_BRIEF}
        )
        assert start.status_code == 200
        body = start.json()
        assert body["revision_number"] == 1
        assert body["insight_text"] == "insight ban dau"

        revise = await client.post(
            "/data/insights/revise",
            json={"task_id": "task-1", "feedback": "tap trung giay cao cap"},
        )
        assert revise.status_code == 200
        assert revise.json()["revision_number"] == 2

        error = await client.post(
            "/data/insights/revise", json={"task_id": "khong-ton-tai", "feedback": "x"}
        )
        assert error.status_code == 404
        assert "error" in error.json()
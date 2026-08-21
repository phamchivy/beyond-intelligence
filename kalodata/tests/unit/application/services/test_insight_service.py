"""
Vi tri file nay: data/tests/unit/application/services/test_insight_service.py

Unit test cho InsightService -- dung MockLLM + MockKalodataClient, khong
goi mang. Xac nhan: input Brief co cau truc, va query DONG THOI nhieu
nhom du lieu Kalodata (khong chi 1 domain).
"""
from __future__ import annotations

import pytest

from application.services.insight_service import (
    InsightService,
    MaxRevisionsExceededError,
    SessionNotFoundError,
)
from domain.ports.llm import LLMResponse
from domain.ports.market_data_provider import MarketDataDomain, RankingItem
from infrastructure.kalodata.mock_kalodata_client import MockKalodataClient
from infrastructure.llm.mock_llm import MockLLM

_SAMPLE_BRIEF = {
    "product_info": {"name": "Giay the thao ABC", "category": "footwear", "price": 500000},
    "target_audience": {"who": "gen Z", "pain_point": "gia dep khong ben"},
    "ad_objective": "conversion",
    "key_message": "Ben, nhe, gia tot",
    "channel": "tiktok",
    "creative_reference": None,
    "constraints": {"duration_seconds": 15, "aspect_ratio": "9:16"},
}


def _sample_ranking(domain: MarketDataDomain) -> list[RankingItem]:
    return [RankingItem(domain=domain, item_id="x1", raw={"id": "x1", "revenue": 5000})]


def _make_service(llm: MockLLM | None = None, domains=None) -> InsightService:
    kalodata = MockKalodataClient(
        ranking_response=_sample_ranking(MarketDataDomain.VIDEO), detail_response={"revenue": 5000}
    )
    return InsightService(
        llm=llm
        or MockLLM(
            response_queue=[
                LLMResponse(content='{"keyword": "giay the thao", "sort_field": "revenue"}'),
                LLMResponse(content="Insight: video ngan, hook manh trong 3s dau."),
            ]
        ),
        market_data_provider=kalodata,
        domains=domains,
    )


class TestStartSession:
    async def test_returns_insight_result_from_structured_brief(self) -> None:
        service = _make_service()

        result = await service.start_session("task-1", _SAMPLE_BRIEF)

        assert result.task_id == "task-1"
        assert result.revision_number == 1
        assert result.insight_text != ""
        assert result.criteria["keyword"] == "giay the thao"

    async def test_queries_multiple_domains_by_default(self) -> None:
        kalodata = MockKalodataClient(
            ranking_response=_sample_ranking(MarketDataDomain.VIDEO), detail_response={"id": "x1"}
        )
        llm = MockLLM(
            response_queue=[
                LLMResponse(content='{"keyword": "x", "sort_field": "revenue"}'),
                LLMResponse(content="insight"),
            ]
        )
        service = InsightService(llm=llm, market_data_provider=kalodata)  # domains mac dinh: video+product

        await service.start_session("task-1", _SAMPLE_BRIEF)

        # 2 domain mac dinh (video, product) -> moi domain 1 lan ranking
        # + 1 lan detail (vi ranking_response luon co 1 item)
        assert kalodata.ranking_call_count == 2
        assert kalodata.detail_call_count == 2

    async def test_respects_custom_domain_list(self) -> None:
        kalodata = MockKalodataClient(
            ranking_response=_sample_ranking(MarketDataDomain.VIDEO), detail_response={"id": "x1"}
        )
        llm = MockLLM(
            response_queue=[
                LLMResponse(content='{"keyword": "x", "sort_field": "revenue"}'),
                LLMResponse(content="insight"),
            ]
        )
        service = InsightService(
            llm=llm,
            market_data_provider=kalodata,
            domains=[MarketDataDomain.VIDEO, MarketDataDomain.PRODUCT, MarketDataDomain.CATEGORY],
        )

        await service.start_session("task-1", _SAMPLE_BRIEF)

        assert kalodata.ranking_call_count == 3  # video + product + category

    async def test_falls_back_gracefully_when_llm_returns_invalid_json(self) -> None:
        llm = MockLLM(
            response_queue=[
                LLMResponse(content="khong phai JSON hop le"),
                LLMResponse(content="insight van tao duoc"),
            ]
        )
        kalodata = MockKalodataClient(ranking_response=[], detail_response={})
        service = InsightService(llm=llm, market_data_provider=kalodata)

        result = await service.start_session("task-1", _SAMPLE_BRIEF)

        assert result.criteria == {}
        assert result.insight_text == "insight van tao duoc"


class TestReviseSession:
    async def test_revision_increments(self) -> None:
        llm = MockLLM(
            response_queue=[
                LLMResponse(content='{"keyword": "giay", "sort_field": "revenue"}'),
                LLMResponse(content="insight ban dau"),
                LLMResponse(content='{"keyword": "giay cao cap", "sort_field": "revenue"}'),
                LLMResponse(content="insight da dieu chinh"),
            ]
        )
        service = _make_service(llm=llm)

        first = await service.start_session("task-1", _SAMPLE_BRIEF)
        assert first.revision_number == 1

        second = await service.revise_session("task-1", feedback="tap trung vao giay cao cap hon")

        assert second.revision_number == 2
        assert second.insight_text == "insight da dieu chinh"

    async def test_revise_without_start_raises(self) -> None:
        service = _make_service()

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-khong-ton-tai", feedback="x")

    async def test_raises_when_exceeding_max_revisions(self) -> None:
        llm = MockLLM(fixed_response='{"keyword": "x", "sort_field": "revenue"}')
        kalodata = MockKalodataClient(ranking_response=[], detail_response={})
        service = InsightService(llm=llm, market_data_provider=kalodata, max_revisions=2)

        await service.start_session("task-1", _SAMPLE_BRIEF)
        await service.revise_session("task-1", feedback="sua 1")

        with pytest.raises(MaxRevisionsExceededError):
            await service.revise_session("task-1", feedback="sua 2")


class TestFinalizeSession:
    async def test_finalize_removes_session(self) -> None:
        service = _make_service()
        await service.start_session("task-1", _SAMPLE_BRIEF)

        service.finalize_session("task-1")

        with pytest.raises(SessionNotFoundError):
            await service.revise_session("task-1", feedback="x")
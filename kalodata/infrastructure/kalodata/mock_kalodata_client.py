"""
Vi tri file nay: data/infrastructure/kalodata/mock_kalodata_client.py

MockKalodataClient -- implementation gia cua MarketDataProvider port,
khong goi mang, dung cho unit test.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from domain.ports.market_data_provider import DetailQuery, RankingItem, RankingQuery


@dataclass
class MockKalodataClient:
    ranking_response: list[RankingItem] = field(default_factory=list)
    detail_response: dict = field(default_factory=dict)
    ranking_call_count: int = field(default=0, init=False)
    detail_call_count: int = field(default=0, init=False)

    async def get_ranking(self, query: RankingQuery) -> list[RankingItem]:
        self.ranking_call_count += 1
        return self.ranking_response

    async def get_detail(self, query: DetailQuery) -> dict:
        self.detail_call_count += 1
        return self.detail_response
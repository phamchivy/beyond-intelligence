"""
Vi tri file nay: data/tests/unit/infrastructure/kalodata/test_kalodata_client.py

Unit test cho KalodataClient -- dung httpx.MockTransport, khong goi mang that.
"""
from __future__ import annotations

import httpx
import pytest

from config.settings import KalodataSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.market_data_provider import DetailQuery, MarketDataDomain, MarketDataProvider, RankingQuery
from infrastructure.kalodata.kalodata_client import KalodataClient


def _client_returning(json_body: dict, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=json_body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _config() -> KalodataSettings:
    return KalodataSettings(api_key="fake-key")


class TestConformsToPort:
    def test_satisfies_protocol(self) -> None:
        client = KalodataClient(config=_config())
        assert isinstance(client, MarketDataProvider)


class TestGetRanking:
    async def test_maps_response_to_ranking_items(self) -> None:
        http_client = _client_returning(
            {"data": [{"video_id": "v1", "revenue": 5000}, {"video_id": "v2", "revenue": 3000}]}
        )
        client = KalodataClient(config=_config(), client=http_client)

        items = await client.get_ranking(RankingQuery(domain=MarketDataDomain.VIDEO))

        assert len(items) == 2
        assert items[0].item_id == "v1"
        assert items[0].raw["revenue"] == 5000

    async def test_sends_auth_header(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"data": []})

        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = KalodataClient(config=_config(), client=http_client)

        await client.get_ranking(RankingQuery(domain=MarketDataDomain.PRODUCT))

        assert captured["auth"] == "Bearer fake-key"

    async def test_uses_correct_id_field_per_domain(self) -> None:
        http_client = _client_returning({"data": [{"product_id": "p1", "revenue": 100}]})
        client = KalodataClient(config=_config(), client=http_client)

        items = await client.get_ranking(RankingQuery(domain=MarketDataDomain.PRODUCT))

        assert items[0].item_id == "p1"


class TestGetDetail:
    async def test_returns_detail_data(self) -> None:
        http_client = _client_returning({"data": {"video_id": "v1", "revenue": 5000}})
        client = KalodataClient(config=_config(), client=http_client)

        detail = await client.get_detail(DetailQuery(domain=MarketDataDomain.VIDEO, item_id="v1"))

        assert detail["video_id"] == "v1"


class TestErrorHandling:
    async def test_5xx_raises_retryable(self) -> None:
        http_client = _client_returning({}, status_code=503)
        client = KalodataClient(config=_config(), client=http_client)

        with pytest.raises(RetryableError):
            await client.get_ranking(RankingQuery(domain=MarketDataDomain.VIDEO))

    async def test_4xx_raises_non_retryable(self) -> None:
        http_client = _client_returning({}, status_code=401)
        client = KalodataClient(config=_config(), client=http_client)

        with pytest.raises(NonRetryableError):
            await client.get_ranking(RankingQuery(domain=MarketDataDomain.VIDEO))
"""
Vi tri file nay: data/infrastructure/kalodata/kalodata_client.py

KalodataClient -- implementation THAT cua MarketDataProvider port, goi
Kalodata API qua httpx. Day la noi DUY NHAT trong data/ duoc phep biet
URL/format cu the cua Kalodata.

Ca 6 nhom du lieu (video/product/shop/creator/category/livestream) dung
chung 1 pattern endpoint: POST {base_url}/{domain}/rank hoac
{base_url}/{domain}/detail -- nen chi can 1 client xu ly tat ca, khong
can 6 class rieng.
"""
from __future__ import annotations

import httpx

from config.settings import KalodataSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.market_data_provider import DetailQuery, MarketDataDomain, RankingItem, RankingQuery
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)

_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

# Ten field dung lam "id" cho tung domain khac nhau trong response cua
# Kalodata (video_id, product_id...) -- xem tai lieu goc.
_ID_FIELD_BY_DOMAIN: dict[MarketDataDomain, str] = {
    MarketDataDomain.VIDEO: "video_id",
    MarketDataDomain.PRODUCT: "product_id",
    MarketDataDomain.SHOP: "shop_id",
    MarketDataDomain.CREATOR: "creator_id",
    MarketDataDomain.CATEGORY: "category_id",
    MarketDataDomain.LIVESTREAM: "livestream_id",
}


class KalodataClient:
    """
    Adapter goi Kalodata API that, implement dung Protocol MarketDataProvider.

    Khong tu doc `settings` global -- nhan `KalodataSettings` qua
    constructor (Dependency Injection), giong het GeminiProvider.
    """

    def __init__(self, config: KalodataSettings, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client

    def _get_client(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient()

    def _headers(self) -> dict[str, str]:
        api_key = self._config.require_api_key().get_secret_value()
        return {
            self._config.auth_header_name: f"{self._config.auth_header_prefix}{api_key}",
            "Content-Type": "application/json",
        }

    def _default_params(self) -> dict:
        return {
            "region": self._config.default_region,
            "language": self._config.default_language,
            "currency": self._config.default_currency,
            "date_range": "last7Day",
        }

    async def get_ranking(self, query: RankingQuery) -> list[RankingItem]:
        url = f"{self._config.base_url}/{query.domain.value}/rank"
        body = {
            **self._default_params(),
            "sort_field": {"field": query.sort_field, "type": "DESC"},
            "page_size": query.page_size,
            "page_number": query.page_number,
            **query.filters,
        }

        response_data = await self._post(url, body, event="kalodata_ranking_fetched")

        id_field = _ID_FIELD_BY_DOMAIN[query.domain]
        items = response_data.get("data", []) or []
        return [
            RankingItem(domain=query.domain, item_id=str(item.get(id_field, "")), raw=item)
            for item in items
        ]

    async def get_detail(self, query: DetailQuery) -> dict:
        url = f"{self._config.base_url}/{query.domain.value}/detail"
        id_field = _ID_FIELD_BY_DOMAIN[query.domain]
        body = {**self._default_params(), id_field: query.item_id}

        response_data = await self._post(url, body, event="kalodata_detail_fetched")
        return response_data.get("data", {}) or {}

    async def _post(self, url: str, body: dict, event: str) -> dict:
        try:
            with log_duration(logger, event, url=url):
                response = await self._get_client().post(
                    url, json=body, headers=self._headers(), timeout=self._config.timeout_seconds
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise self._translate_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise RetryableError(f"Kalodata API timeout: {exc}") from exc

        return response.json()

    @staticmethod
    def _translate_error(exc: httpx.HTTPStatusError) -> Exception:
        status_code = exc.response.status_code
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"Kalodata API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(f"Kalodata API loi khong the retry (status={status_code}): {exc}")
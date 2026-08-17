"""
HttpJsonRetriever -- adapter TONG QUAT cho Retriever port khi nguon du
lieu la mot REST API tra ve JSON (vd: API du lieu lich su kenh tu ban
to chuc -- Kalodata hoac nguon tuong duong, chua xac nhan duoc dinh
dang chinh xac tai thoi diem viet file nay).

Thay vi viet cung mot adapter rieng cho tung nha cung cap (KalodataRetriever,
XRetriever...), adapter nay nhan mot ham `map_response` TU BEN NGOAI de
dich JSON tra ve thanh RetrievedDocument -- khi biet API that, chi can
viet 1 ham map ngan, KHONG can viet lai toan bo adapter (HTTP call,
retry, timeout, logging deu da co san o day).
"""
from __future__ import annotations

from typing import Any, Callable

import httpx

from domain.entities.context import RetrievedDocument
from domain.policies.retry_policy import NonRetryableError, RetryableError
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)

# Cung quy uoc phan loai loi retry-duoc nhu GeminiProvider (xem
# infrastructure/llm/gemini_provider.py) -- dong bo cach xu ly loi HTTP
# giua cac adapter trong toan he thong.
_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

ResponseMapper = Callable[[dict[str, Any]], list[RetrievedDocument]]


class HttpJsonRetriever:
    """
    Goi mot REST API (GET, query param `q` + `top_k`), dich JSON tra ve
    thanh list[RetrievedDocument] qua `map_response` do noi khoi tao
    truyen vao.

    Khong tu doc settings/api_key tu dau -- nhan qua constructor
    (Dependency Injection), dung nguyen tac "khong hardcode" da thong
    nhat. Noi tao instance nay (bootstrap/container.py sau nay, hoac
    business/domains/.../composition rieng) chiu trach nhiem doc
    settings that va truyen vao day.
    """

    def __init__(
        self,
        base_url: str,
        map_response: ResponseMapper,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        query_param_name: str = "q",
        extra_headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._map_response = map_response
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._query_param_name = query_param_name
        self._extra_headers = extra_headers or {}
        # Cho phep truyen san 1 httpx.AsyncClient (vd: dung
        # httpx.MockTransport khi test) -- neu khong truyen, tu tao
        # client that moi lan retrieve() (don gian, chap nhan duoc cho
        # tan suat goi khong qua cao cua Retriever).
        self._client = client

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        headers = dict(self._extra_headers)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        params = {self._query_param_name: query, "top_k": top_k}

        try:
            with log_duration(logger, "retrieval_http_call_completed", base_url=self._base_url):
                response = await self._get_client().get(
                    self._base_url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise self._translate_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise RetryableError(f"Retrieval API timeout: {exc}") from exc

        documents = self._map_response(response.json())
        log_event(
            logger,
            "info",
            "retrieval_result",
            base_url=self._base_url,
            document_count=len(documents),
        )
        return documents[:top_k]

    def _get_client(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient()

    @staticmethod
    def _translate_error(exc: httpx.HTTPStatusError) -> Exception:
        status_code = exc.response.status_code
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"Retrieval API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(f"Retrieval API loi khong the retry (status={status_code}): {exc}")
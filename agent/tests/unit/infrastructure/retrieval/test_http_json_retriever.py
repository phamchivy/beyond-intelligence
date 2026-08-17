"""
Unit test cho HttpJsonRetriever -- dung httpx.MockTransport de gia lap
API that ma KHONG can mang that. Day la cach test chuan cua httpx,
khong can them thu vien mock rieng.
"""
from __future__ import annotations

import httpx
import pytest

from domain.entities.context import RetrievedDocument
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.retriever import Retriever
from infrastructure.retrieval.http_json_retriever import HttpJsonRetriever


def _client_returning(json_body: dict, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=json_body)

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def _default_map_response(payload: dict) -> list[RetrievedDocument]:
    return [
        RetrievedDocument(content=item["text"], source=item["id"], score=item.get("score", 0.0))
        for item in payload.get("items", [])
    ]


class TestConformsToPort:
    def test_satisfies_retriever_protocol(self) -> None:
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api", map_response=_default_map_response
        )
        assert isinstance(retriever, Retriever)


class TestRetrieveSuccess:
    async def test_maps_json_response_to_retrieved_documents(self) -> None:
        client = _client_returning(
            {"items": [{"id": "v1", "text": "video A", "score": 0.9}]}
        )
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api",
            map_response=_default_map_response,
            client=client,
        )

        results = await retriever.retrieve("query test", top_k=5)

        assert len(results) == 1
        assert results[0].source == "v1"
        assert results[0].content == "video A"

    async def test_respects_top_k_after_mapping(self) -> None:
        client = _client_returning(
            {"items": [{"id": f"v{i}", "text": f"video {i}"} for i in range(10)]}
        )
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api",
            map_response=_default_map_response,
            client=client,
        )

        results = await retriever.retrieve("query", top_k=3)

        assert len(results) == 3

    async def test_sends_api_key_as_bearer_header(self) -> None:
        captured_headers: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(request.headers)
            return httpx.Response(200, json={"items": []})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api",
            map_response=_default_map_response,
            api_key="secret-key-123",
            client=client,
        )

        await retriever.retrieve("query", top_k=5)

        assert captured_headers.get("authorization") == "Bearer secret-key-123"


class TestRetrieveErrors:
    async def test_5xx_status_raises_retryable_error(self) -> None:
        client = _client_returning({"error": "server error"}, status_code=503)
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api", map_response=_default_map_response, client=client
        )

        with pytest.raises(RetryableError):
            await retriever.retrieve("query", top_k=5)

    async def test_4xx_status_raises_non_retryable_error(self) -> None:
        client = _client_returning({"error": "bad request"}, status_code=400)
        retriever = HttpJsonRetriever(
            base_url="https://example.com/api", map_response=_default_map_response, client=client
        )

        with pytest.raises(NonRetryableError):
            await retriever.retrieve("query", top_k=5)
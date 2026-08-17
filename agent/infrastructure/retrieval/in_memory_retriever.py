"""
InMemoryRetriever -- implementation don gian nhat cua Retriever port
(domain/ports/retriever.py). Xep hang tai lieu bang keyword overlap
don gian (khong can model embedding/vector DB), hoat dong tren mot
danh sach tai lieu da nap san trong bo nho.

Dung lam:
  - Fallback khi chua co API du lieu that (vd: chua xac nhan duoc API
    lich su kenh tu ban to chuc) -- dung dung y tuong "graceful
    degradation" da thong nhat trong tai lieu san pham.
  - Adapter test/dev nhanh, khong can dung Qdrant/pgvector that.

Hoan toan tong quat: khong biet gi ve loai tai lieu dang truy xuat
(video cu, quy tac chinh sach, san pham...) -- chi lam viec tren
RetrievedDocument da chuan hoa.
"""
from __future__ import annotations

from domain.entities.context import RetrievedDocument


class InMemoryRetriever:
    """
    Retriever hoat dong tren danh sach RetrievedDocument nap san.

    Thuat toan xep hang: ty le tu khoa trung nhau giua query va noi
    dung tai lieu (khong phan biet hoa/thuong). Don gian, khong can
    dependency ML, nhung du dung de demo va co the thay the truc tiep
    bang PGVectorRetriever/QdrantRetriever that sau nay ma KHONG doi
    Retriever port -- Agent/Workflow dung no khong can sua gi.
    """

    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self._documents = documents

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scored = [
            RetrievedDocument(
                content=doc.content,
                source=doc.source,
                score=self._overlap_score(query_terms, doc.content),
                metadata=doc.metadata,
            )
            for doc in self._documents
        ]

        relevant = [doc for doc in scored if doc.score > 0]
        relevant.sort(key=lambda doc: doc.score, reverse=True)
        return relevant[:top_k]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(text.lower().split())

    @classmethod
    def _overlap_score(cls, query_terms: set[str], content: str) -> float:
        content_terms = cls._tokenize(content)
        if not content_terms or not query_terms:
            return 0.0
        overlap = len(query_terms & content_terms)
        return overlap / len(query_terms)
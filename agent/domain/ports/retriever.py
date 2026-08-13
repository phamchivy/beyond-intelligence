"""
Retriever Port -- "hop dong" cho kha nang truy xuat tai lieu/du lieu lien
quan (RAG kien thuc noi bo, du lieu thi truong, du lieu doi thu...) dua
tren mot truy van.

Tai su dung RetrievedDocument da dinh nghia o domain/entities/context.py
de tranh trung lap dinh nghia du lieu -- Retriever la noi SAN SINH ra
RetrievedDocument, Context la noi CHUA no.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from agent.domain.entities.context import RetrievedDocument


@runtime_checkable
class Retriever(Protocol):
    """
    Port cho kha nang truy xuat tai lieu lien quan toi mot truy van.

    Co the la vector search (RAG kien thuc noi bo), hoac truy xuat du
    lieu thi truong/doi thu tu API ben ngoai -- Agent khong can biet
    su khac biet nay, chi can goi retrieve(query, top_k).
    """

    async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        ...
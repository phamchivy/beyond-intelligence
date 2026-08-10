"""
Context -- ngu canh duoc xay dung cho Agent truoc khi reasoning.

Context la anh chup (snapshot) tai mot thoi diem cua: hoi thoai, tai lieu
truy xuat duoc (retrieval), va rang buoc nghiep vu. ContextBuilder (o
application layer) la noi build ra Context; entity nay chi mo ta hinh dang
du lieu, khong chua logic build (goi Retriever, goi DB...).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    """Mot tai lieu duoc truy xuat tu Retriever, kem diem lien quan."""

    content: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Context:
    """
    Ngu canh day du de Agent thuc hien reasoning cho mot buoc xu ly.

    Bat bien (immutable) -- moi lan them thong tin moi (them document,
    them message) se tao ra Context moi thay vi sua Context cu. Dung
    tuple (khong phai list) cho cac truong nhieu phan tu de dam bao
    hashable / khong the mutate nham tu ben ngoai.
    """

    conversation_history: tuple[str, ...] = field(default_factory=tuple)
    retrieved_documents: tuple[RetrievedDocument, ...] = field(default_factory=tuple)
    business_constraints: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def with_documents(self, documents: list[RetrievedDocument]) -> "Context":
        return replace(
            self, retrieved_documents=self.retrieved_documents + tuple(documents)
        )

    def with_message(self, message: str) -> "Context":
        return replace(self, conversation_history=self.conversation_history + (message,))

    def is_empty(self) -> bool:
        return not self.conversation_history and not self.retrieved_documents
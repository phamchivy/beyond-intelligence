"""
Tool Port -- "hop dong" cho moi hanh dong ma Agent co the thuc thi ra
ben ngoai (goi API, truy van DB, tinh toan, lay du lieu thi truong...).

Voi kien truc "AI Decision & Execution System", Tool chinh la noi Agent
"cham" vao the gioi thuc: lay market signal, goi API doi thu, thuc thi
hanh dong (vd: tao de xuat gia, gui canh bao...). Domain/Application chi
biet Protocol nay, khong biet tool cu the goi API nao / thu vien nao.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Ket qua tra ve sau khi mot Tool thuc thi xong."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def ok(output: Any, metadata: dict[str, Any] | None = None) -> "ToolResult":
        return ToolResult(success=True, output=output, metadata=metadata or {})

    @staticmethod
    def fail(error: str, metadata: dict[str, Any] | None = None) -> "ToolResult":
        return ToolResult(success=False, error=error, metadata=metadata or {})


@runtime_checkable
class Tool(Protocol):
    """
    Port cho mot hanh dong/kha nang cu the ma Agent co the goi.

    `name` va `description` duoc dung de mo ta cho LLM biet ve tool nay
    (function calling) -- nen viet description ro rang, vi LLM se dua
    vao do de quyet dinh co goi tool hay khong va goi voi tham so gi.
    """

    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema mo ta cac tham so ma execute() can nhan."""
        ...

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        ...
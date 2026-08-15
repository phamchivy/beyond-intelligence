"""
MockLLM -- implementation gia cua LLM port, khong goi mang, dung cho:
  - Unit test Agent/Planner/Reasoner ma khong can Gemini that (nhanh, mien phi)
  - Phat trien local khi chua co API key
  - Demo/CI khong phu thuoc ket noi mang / rate limit

Implement DUNG Protocol LLM (domain/ports/llm.py) nen co the "cam" thang
vao Agent ma khong sua gi ca -- day chinh la bai kiem tra thuc te cho
viec thiet ke port o domain/ports/llm.py co dung khong.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from domain.ports.llm import LLMRequest, LLMResponse
from domain.value_objects.token_usage import TokenUsage


@dataclass
class MockLLM:
    """
    LLM gia, tra ve cau tra loi da cau hinh san thay vi goi API that.

    Cach dung don gian nhat (mot cau tra loi co dinh cho moi lan goi):
        llm = MockLLM(fixed_response="Xin chao")

    Cach dung nang cao (mo phong nhieu buoc reasoning tuan tu -- moi lan
    goi generate() se tra ve mot response khac nhau, dung dung thu tu
    trong hang doi -- rat hop voi test pipeline nhieu buoc):
        llm = MockLLM(response_queue=[
            LLMResponse(content="Phat hien 1 co hoi tai Singapore"),
            LLMResponse(content="Doi thu manh nhat la X, Y"),
            LLMResponse(content="De xuat chien luoc: dinh gia thap hon 10%%"),
        ])

    Mo phong loi (dung de test RetryPolicy o tang application, khong can
    goi Gemini that de tao loi):
        llm = MockLLM(raise_error=RetryableError("timeout gia lap"))
    """

    fixed_response: str | None = None
    response_queue: list[LLMResponse] = field(default_factory=list)
    raise_error: Exception | None = None
    model_name: str = "mock-llm"

    # Luu lai lich su goi de assert trong test (vd: kiem tra prompt gui
    # vao co dung noi dung mong doi khong). init=False -- khong phai
    # tham so khoi tao, luon bat dau rong.
    call_history: list[LLMRequest] = field(default_factory=list, init=False)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_history.append(request)

        if self.raise_error is not None:
            raise self.raise_error

        if self.response_queue:
            return self.response_queue.pop(0)

        content = self.fixed_response if self.fixed_response is not None else "mock response"
        return LLMResponse(
            content=content,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
            model=self.model_name,
        )

    @property
    def call_count(self) -> int:
        return len(self.call_history)

    def reset(self) -> None:
        """Xoa lich su goi -- dung giua cac test case de tranh anh huong lan nhau."""
        self.call_history.clear()
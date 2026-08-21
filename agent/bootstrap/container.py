"""
Vi tri file nay: agent/bootstrap/container.py

Composition Root DUY NHAT cua toan bo agent/.

Day la noi DUY NHAT trong toan bo du an duoc phep:
  - Import ca GeminiProvider/DeepSeekProvider/MockLLM/SeedanceRenderer/
    MockVideoRenderer cung luc (moi noi khac chi biet Protocol tuong ung).
  - Doc `settings` truc tiep de lay gia tri cau hinh that (moi noi
    khac nhan gia tri qua constructor -- Dependency Injection).

Neu sau nay them provider moi (OpenAI, Anthropic...) hoac Tool/Retriever
that, CHI sua o day -- khong dung vao Agent/ReasoningService/Executor/
StoryboardSessionService.
"""
from __future__ import annotations

from application.agent.agent import Agent
from application.agent.agent_factory import build_agent
from application.services.decision_service import DecisionService
from application.services.storyboard_session_service import StoryboardSessionService
from config.settings import LLMProvider, Settings, VideoProvider
from config.settings import settings as _default_settings
from domain.policies.decision_policy import DecisionPolicy
from domain.policies.retry_policy import RetryPolicy
from domain.policies.tool_policy import ToolPolicy
from domain.ports.llm import LLM
from domain.ports.memory import Memory
from domain.ports.video_renderer import VideoRenderer
from infrastructure.llm.deepseek_provider import DeepSeekProvider
from infrastructure.llm.gemini_provider import GeminiProvider
from infrastructure.llm.mock_llm import MockLLM
from infrastructure.memory.in_memory_memory import InMemoryMemory
from infrastructure.video.mock_video_renderer import MockVideoRenderer
from infrastructure.video.seedance_renderer import SeedanceRenderer

# Memory dung chung 1 instance cho toan bo tien trinh (module-level
# singleton) -- KHONG tao moi instance moi lan build service, vi
# InMemoryMemory se mat sach du lieu neu tao lai (moi lan tao la 1 dict
# rong moi). Day la ly do session storyboard "song sot" duoc qua nhieu
# request HTTP khac nhau trong cung 1 tien trinh server.
_shared_memory = InMemoryMemory()


def _build_llm(config: Settings) -> LLM:
    """
    Noi DUY NHAT trong toan he thong re nhanh theo LLM_PROVIDER. Them
    provider moi (vd: OpenAI) thi chi sua ham nay.
    """
    if config.llm.provider == LLMProvider.MOCK:
        return MockLLM()
    if config.llm.provider == LLMProvider.GEMINI:
        return GeminiProvider(config=config.llm)
    if config.llm.provider == LLMProvider.DEEPSEEK:
        return DeepSeekProvider(config=config.llm)
    raise ValueError(
        f"LLM provider '{config.llm.provider.value}' chua duoc ho tro trong container. "
        f"Them nhanh xu ly tuong ung trong bootstrap/container.py::_build_llm()."
    )


def _build_video_renderer(config: Settings) -> VideoRenderer:
    """Noi DUY NHAT re nhanh theo VIDEO_PROVIDER, giong het _build_llm()."""
    if config.video.provider == VideoProvider.MOCK:
        return MockVideoRenderer()
    if config.video.provider == VideoProvider.SEEDANCE:
        return SeedanceRenderer(config=config.video)
    raise ValueError(
        f"Video provider '{config.video.provider.value}' chua duoc ho tro trong container. "
        f"Them nhanh xu ly tuong ung trong bootstrap/container.py::_build_video_renderer()."
    )


def _build_memory(config: Settings) -> Memory:
    """
    Hien chi co InMemoryMemory (dung chung 1 instance -- xem ghi chu o
    _shared_memory). Khi them RedisMemory/PostgresMemory that, re nhanh
    o day giong het 2 ham tren, khong doi noi goi.
    """
    return _shared_memory


def _build_retry_policy(config: Settings) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=config.retry_policy.max_attempts,
        base_delay_seconds=config.retry_policy.base_delay_seconds,
        max_delay_seconds=config.retry_policy.max_delay_seconds,
        backoff_multiplier=config.retry_policy.backoff_multiplier,
    )


def _build_tool_policy(config: Settings) -> ToolPolicy:
    return ToolPolicy(auto_deny_unknown_tools=config.tool_policy.auto_deny_unknown_tools)


def _build_decision_policy(config: Settings) -> DecisionPolicy:
    return DecisionPolicy(
        auto_execute_threshold=config.decision_policy.auto_execute_threshold,
        reject_threshold=config.decision_policy.reject_threshold,
        allow_high_risk_auto_execute=config.decision_policy.allow_high_risk_auto_execute,
    )


def build_agent_from_settings(config: Settings | None = None) -> Agent:
    """
    Lap rap mot Agent hoan chinh tu settings.

    `config` co the truyen tuong minh (dung khi test, hoac khi can cau
    hinh khac mac dinh) -- neu bo trong, dung `settings` toan cuc doc
    tu .env/bien moi truong that.

    Chua co Tool that (se bo sung khi lam infrastructure/tools/) --
    Agent hien tai chi co the tra loi bang reasoning thuan, chua goi
    duoc tool nao.
    """
    cfg = config or _default_settings

    return build_agent(
        llm=_build_llm(cfg),
        tools={},
        tool_definitions=(),
        retry_policy=_build_retry_policy(cfg),
        tool_policy=_build_tool_policy(cfg),
        max_iterations=cfg.max_iterations,
    )


def build_decision_service(config: Settings | None = None) -> DecisionService:
    cfg = config or _default_settings
    return DecisionService(decision_policy=_build_decision_policy(cfg))


def build_storyboard_session_service(config: Settings | None = None) -> StoryboardSessionService:
    """
    Lap rap StoryboardSessionService hoan chinh tu settings -- dung cho
    interface/api/ (route HTTP) goi vao.
    """
    cfg = config or _default_settings

    return StoryboardSessionService(
        llm=_build_llm(cfg),
        video_renderer=_build_video_renderer(cfg),
        memory=_build_memory(cfg),
        retry_policy=_build_retry_policy(cfg),
        max_revisions=cfg.max_storyboard_revisions,
    )


def build_video_renderer(config: Settings | None = None) -> VideoRenderer:
    """
    Public wrapper cua _build_video_renderer() -- dung khi interface/api/
    can truc tiep VideoRenderer (vd: endpoint kiem tra trang thai render)
    ma khong di qua StoryboardSessionService.
    """
    return _build_video_renderer(config or _default_settings)
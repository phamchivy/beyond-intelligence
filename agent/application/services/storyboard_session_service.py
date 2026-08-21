"""
Vi tri file nay: agent/application/services/storyboard_session_service.py

StoryboardSessionService -- dieu phoi vong lap Human-in-the-Loop cho
storyboard, DUNG THEO DUNG luong da chot trong system-integration-flow.md:

  - Sua storyboard (start_session / revise_session) CHI la van ban --
    KHONG goi Seedance moi lan sua, tranh ton quota/thoi gian cho
    nhung ban nhap chua chac da duyet.
  - Render video CHI xay ra MOT LAN, sau khi storyboard da duoc APPROVE
    (goi render_final()) -- dung dung buoc 9 trong flow.

Khong dung ReasoningService (thiet ke rieng cho vong lap Agent, gan
voi AgentState) -- goi thang LLM port qua call_llm_with_retry (dung
chung voi ReasoningService, xem application/reasoning/llm_call.py).

Luu Context (Brief + anh tham chieu + lich su revision) vao Memory
port, key theo task_id -- de moi lan sua chi can gui `feedback`, va de
render_final() sau nay tu doc lai storyboard + anh da duyet, KHONG can
Backend gui lai du lieu goc.

CHUA co StoryboardPlan schema chinh thuc (se lam khi code business/
domains/.../schemas/) -- storyboard hien la VAN BAN TU DO do LLM sinh
ra (hook, cac shot, cta duoc mo ta bang loi), dung truc tiep lam prompt
render video. Se thay bang cau truc JSON Schema chat che hon sau.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from domain.policies.retry_policy import RetryPolicy
from domain.ports.llm import LLM, ImagePart, LLMMessage, LLMRequest, MessageRole
from domain.ports.memory import Memory, MemoryItem
from domain.ports.video_renderer import ReferenceImage, RenderJob, RenderRequest, VideoRenderer
from observability.logging import get_logger, log_event
from application.reasoning.llm_call import call_llm_with_retry

logger = get_logger(__name__)

_SESSION_NAMESPACE = "storyboard_sessions"

_DEFAULT_SYSTEM_PROMPT = (
    "Ban la chuyen gia sang tao noi dung quang cao ngan cho TikTok/Reels. "
    "Tu Brief san pham duoc cung cap, hay viet mot storyboard ro rang gom: "
    "(1) Hook mo dau trong 2-3 giay dau, (2) Cac canh quay mo ta san pham/loi ich "
    "theo thu tu, (3) Cau Call-to-Action ket thuc. Mo ta chi tiet tung canh quay "
    "(goc may, chuyen dong, chu de xuat hien tren man hinh) de co the dung truc "
    "tiep lam huong dan sinh video."
)


class MaxRevisionsExceededError(Exception):
    """Vuot qua so lan sua storyboard toi da cho phep (settings.max_storyboard_revisions)."""


class SessionNotFoundError(Exception):
    """Khong tim thay storyboard session cho task_id da cho (chua start hoac da finalize)."""


@dataclass(frozen=True, slots=True)
class StoryboardRevision:
    """Mot phien ban storyboard (CHI van ban), sinh tu revision truoc + feedback (neu co)."""

    revision_number: int
    storyboard_text: str
    feedback: str | None  # feedback dan den revision NAY -- None cho revision 1


@dataclass(frozen=True, slots=True)
class StorySession:
    """
    Toan bo boi canh can nho qua nhieu lan sua storyboard cho MOT task.

    Luu nguyen vao Memory (namespace _SESSION_NAMESPACE, key = task_id)
    -- immutable, moi lan cap nhat tao instance moi (dung pattern da ap
    dung cho AgentState).
    """

    task_id: str
    brief: dict
    reference_images: tuple[ReferenceImage, ...]
    revisions: tuple[StoryboardRevision, ...]

    @property
    def latest(self) -> StoryboardRevision:
        return self.revisions[-1]

    def with_new_revision(self, revision: StoryboardRevision) -> "StorySession":
        return replace(self, revisions=self.revisions + (revision,))


@dataclass(frozen=True, slots=True)
class StoryboardResult:
    """Ket qua tra ve cho Backend sau moi lan sinh/sua storyboard (KHONG kem render)."""

    task_id: str
    revision_number: int
    storyboard_text: str


class StoryboardSessionService:
    """
    Dieu phoi vong lap: sinh storyboard (text) -> nguoi dung review ->
    sua lai (text, lap lai neu can) -> APPROVED -> render_final() goi
    Seedance DUY NHAT MOT LAN.
    """

    def __init__(
        self,
        llm: LLM,
        video_renderer: VideoRenderer,
        memory: Memory,
        retry_policy: RetryPolicy | None = None,
        max_revisions: int = 3,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._llm = llm
        self._video_renderer = video_renderer
        self._memory = memory
        self._retry_policy = retry_policy or RetryPolicy()
        self._max_revisions = max_revisions
        self._system_prompt = system_prompt

    async def start_session(
        self,
        task_id: str,
        brief: dict,
        reference_images: tuple[ReferenceImage, ...] = (),
    ) -> StoryboardResult:
        """Sinh storyboard lan dau (revision 1) tu Brief -- CHI van ban, khong render."""
        storyboard_text = await self._generate_storyboard_text(
            brief, reference_images, feedback=None, previous_storyboard=None
        )
        revision = StoryboardRevision(revision_number=1, storyboard_text=storyboard_text, feedback=None)
        session = StorySession(
            task_id=task_id,
            brief=brief,
            reference_images=reference_images,
            revisions=(revision,),
        )
        await self._save_session(session)
        log_event(logger, "info", "storyboard_session_started", task_id=task_id, revision=1)

        return StoryboardResult(task_id=task_id, revision_number=1, storyboard_text=storyboard_text)

    async def revise_session(self, task_id: str, feedback: str) -> StoryboardResult:
        """
        Sinh lai storyboard (CHI van ban, khong render) dua tren feedback
        -- CHI can task_id + feedback, Brief/asset tu dong lay lai tu
        Memory (khong can Backend gui lai).
        """
        session = await self._load_session(task_id)
        next_revision_number = session.latest.revision_number + 1

        if next_revision_number > self._max_revisions:
            log_event(
                logger,
                "warning",
                "storyboard_max_revisions_exceeded",
                task_id=task_id,
                max_revisions=self._max_revisions,
            )
            raise MaxRevisionsExceededError(
                f"Task '{task_id}' da vuot qua {self._max_revisions} lan sua storyboard. "
                f"Can chuyen sang xu ly thu cong (needs_manual_review)."
            )

        storyboard_text = await self._generate_storyboard_text(
            session.brief,
            session.reference_images,
            feedback=feedback,
            previous_storyboard=session.latest.storyboard_text,
        )
        revision = StoryboardRevision(
            revision_number=next_revision_number, storyboard_text=storyboard_text, feedback=feedback
        )
        updated_session = session.with_new_revision(revision)
        await self._save_session(updated_session)
        log_event(
            logger, "info", "storyboard_session_revised", task_id=task_id, revision=next_revision_number
        )

        return StoryboardResult(
            task_id=task_id, revision_number=next_revision_number, storyboard_text=storyboard_text
        )

    async def render_final(self, task_id: str) -> RenderJob:
        """
        Render video THAT, DUY NHAT MOT LAN -- goi sau khi storyboard da
        duoc nguoi dung APPROVE (Backend tu quyet dinh khi nao goi ham
        nay, dung theo buoc 9 trong system-integration-flow.md).

        Dung storyboard cua REVISION MOI NHAT trong session (gia dinh
        Backend chi goi ham nay sau khi da approve dung revision cuoi
        cung nguoi dung xem).
        """
        session = await self._load_session(task_id)
        request = RenderRequest(
            prompt=session.latest.storyboard_text,
            reference_images=session.reference_images,
        )
        render_job = await self._video_renderer.submit(request)
        log_event(
            logger,
            "info",
            "storyboard_render_final_submitted",
            task_id=task_id,
            revision=session.latest.revision_number,
            render_job_id=render_job.job_id,
        )
        return render_job

    async def finalize_session(self, task_id: str) -> None:
        """Don Memory sau khi task hoan tat (da render xong) hoac bi huy -- goi sau cung."""
        await self._memory.delete(task_id, namespace=_SESSION_NAMESPACE)
        log_event(logger, "info", "storyboard_session_finalized", task_id=task_id)

    # ------------------------------------------------------------------
    # Noi bo
    # ------------------------------------------------------------------

    async def _generate_storyboard_text(
        self,
        brief: dict,
        reference_images: tuple[ReferenceImage, ...],
        feedback: str | None,
        previous_storyboard: str | None,
    ) -> str:
        prompt = self._build_prompt(brief, feedback, previous_storyboard)
        images = tuple(
            ImagePart(image_bytes=img.image_bytes, mime_type=img.mime_type)
            for img in reference_images
        )

        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=self._system_prompt),
                LLMMessage(role=MessageRole.USER, content=prompt, images=images),
            )
        )
        response = await call_llm_with_retry(self._llm, request, self._retry_policy, logger)
        return response.content

    @staticmethod
    def _build_prompt(brief: dict, feedback: str | None, previous_storyboard: str | None) -> str:
        if feedback is None:
            return f"Brief san pham:\n{brief}"

        return (
            f"Storyboard truoc do:\n{previous_storyboard}\n\n"
            f"Phan hoi cua nguoi dung can dieu chinh:\n{feedback}\n\n"
            f"Hay viet lai storyboard, giu nguyen phan nguoi dung hai long, "
            f"chi sua theo dung phan hoi tren."
        )

    async def _save_session(self, session: StorySession) -> None:
        await self._memory.save(
            MemoryItem(key=session.task_id, value=session, namespace=_SESSION_NAMESPACE)
        )

    async def _load_session(self, task_id: str) -> StorySession:
        item = await self._memory.get(task_id, namespace=_SESSION_NAMESPACE)
        if item is None:
            raise SessionNotFoundError(
                f"Khong tim thay storyboard session cho task_id='{task_id}'. "
                f"Can goi start_session() truoc."
            )
        return item.value
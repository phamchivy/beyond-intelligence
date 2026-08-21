"""
Vi tri file nay: agent/application/services/storyboard_session_service.py

StoryboardSessionService -- dieu phoi vong lap Human-in-the-Loop cho
storyboard, DUNG THEO DUNG luong da chot trong system-integration-flow.md:

  - Sua storyboard (start_session / revise_session) CHI la du lieu CO
    CAU TRUC (StoryboardPlan) -- KHONG goi Seedance moi lan sua, tranh
    ton quota/thoi gian cho nhung ban nhap chua chac da duyet.
  - Render video CHI xay ra MOT LAN, sau khi storyboard da duoc APPROVE
    (goi render_final()) -- dung dung buoc 9 trong flow.

LLM duoc BAT BUOC tra ve JSON dung StoryboardPlan.model_json_schema()
(gan truc tiep vao prompt, luon dong bo voi schema, khong bao gio lech)
-- thay vi van ban tu do (markdown) nhu ban truoc, de Frontend co du
lieu ro rang render UI (timeline canh quay, chu overlay...) thay vi
phai tu parse text.

Khong dung ReasoningService (thiet ke rieng cho vong lap Agent, gan
voi AgentState) -- goi thang LLM port qua call_llm_with_retry (dung
chung voi ReasoningService, xem application/reasoning/llm_call.py).

Luu Context (Brief + anh tham chieu + lich su revision) vao Memory
port, key theo task_id -- de moi lan sua chi can gui `feedback`, va de
render_final() sau nay tu doc lai storyboard + anh da duyet, KHONG can
Backend gui lai du lieu goc.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace

import pydantic

from business.domains.ai_ads_video_generator.schemas.storyboard_plan import StoryboardPlan
from domain.policies.retry_policy import RetryPolicy
from domain.ports.llm import LLM, ImagePart, LLMMessage, LLMRequest, MessageRole
from domain.ports.memory import Memory, MemoryItem
from domain.ports.video_renderer import ReferenceImage, RenderJob, RenderRequest, VideoRenderer
from observability.logging import get_logger, log_event
from application.reasoning.llm_call import call_llm_with_retry

logger = get_logger(__name__)

_SESSION_NAMESPACE = "storyboard_sessions"

_STORYBOARD_SCHEMA_JSON = json.dumps(StoryboardPlan.model_json_schema(), ensure_ascii=False)

_DEFAULT_SYSTEM_PROMPT = (
    "Ban la chuyen gia sang tao noi dung quang cao ngan cho TikTok/Reels. "
    "Tu Brief san pham duoc cung cap, hay tao mot storyboard ro rang gom "
    "Hook mo dau, cac Scene mo ta san pham/loi ich theo thu tu, va Call-to-Action "
    "ket thuc. Moi doan can co thoi diem bat dau/ket thuc (giay), mo ta canh quay "
    "chi tiet (goc may, chuyen dong), chu tren man hinh (neu co), va ghi chu am thanh.\n\n"
    "BAT BUOC: chi tra ve MOT DOI TUONG JSON DUY NHAT, dung CHINH XAC JSON Schema "
    "sau day -- KHONG duoc bao boc trong markdown code fence, KHONG giai thich gi them:\n"
    f"{_STORYBOARD_SCHEMA_JSON}"
)

# Prompt DICH RIENG cho VideoRenderer -- KHONG dung thang StoryboardPlan
# (co the co noi dung tieng Viet trong scene_description/on_screen_text)
# lam prompt render truc tiep. Model sinh video (Seedance) huan luyen
# chu yeu tren du lieu tieng Anh -- dua noi dung tieng Viet vao de bi
# loi chinh ta/font chu tren video, khong hieu dung y do. Buoc nay dich
# StoryboardPlan.to_render_prompt_context() thanh 1 doan mo ta VIDEO
# PROMPT bang tieng Anh, sinh dong RIENG, chi dung luc render_final().
_RENDER_PROMPT_SYSTEM_PROMPT = (
    "You are a professional prompt writer for AI video generation models. "
    "Translate and rewrite the given storyboard (which may contain Vietnamese "
    "text) into a single, vivid ENGLISH video generation prompt. Requirements: "
    "(1) Write ENTIRELY in English -- do not include any Vietnamese text, "
    "(2) Any on-screen text/caption/CTA mentioned must be translated to English, "
    "(3) Explicitly state the total video duration in seconds as given, and "
    "describe pacing per scene using the exact time ranges provided so the video "
    "is NOT sped up or compressed -- each scene must get its full described "
    "duration, (4) Describe camera angle, motion, and product focus clearly for "
    "each scene. Output ONLY the prompt text, no explanation."
)


class StoryboardParseError(Exception):
    """LLM tra ve JSON khong hop le hoac khong khop StoryboardPlan schema."""


@dataclass(frozen=True, slots=True)
class StoryboardRevision:
    revision_number: int
    plan: StoryboardPlan
    feedback: str | None


@dataclass(frozen=True, slots=True)
class StorySession:
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
    """Ket qua tra ve cho Backend sau moi lan sinh/sua storyboard -- CO CAU TRUC, khong con la text tu do."""

    task_id: str
    revision_number: int
    plan: StoryboardPlan


class StoryboardSessionService:
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
        """Sinh storyboard lan dau (revision 1) tu Brief -- tra ve StoryboardPlan co cau truc."""
        plan = await self._generate_storyboard_plan(
            brief, reference_images, feedback=None, previous_plan=None
        )
        revision = StoryboardRevision(revision_number=1, plan=plan, feedback=None)
        session = StorySession(
            task_id=task_id,
            brief=brief,
            reference_images=reference_images,
            revisions=(revision,),
        )
        await self._save_session(session)
        log_event(logger, "info", "storyboard_session_started", task_id=task_id, revision=1)

        return StoryboardResult(task_id=task_id, revision_number=1, plan=plan)

    async def revise_session(self, task_id: str, feedback: str) -> StoryboardResult:
        """
        Sinh lai storyboard (co cau truc) dua tren feedback -- CHI can
        task_id + feedback, Brief/asset tu dong lay lai tu Memory.
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

        plan = await self._generate_storyboard_plan(
            session.brief,
            session.reference_images,
            feedback=feedback,
            previous_plan=session.latest.plan,
        )
        revision = StoryboardRevision(
            revision_number=next_revision_number, plan=plan, feedback=feedback
        )
        updated_session = session.with_new_revision(revision)
        await self._save_session(updated_session)
        log_event(
            logger, "info", "storyboard_session_revised", task_id=task_id, revision=next_revision_number
        )

        return StoryboardResult(task_id=task_id, revision_number=next_revision_number, plan=plan)

    async def render_final(self, task_id: str) -> RenderJob:
        """
        Render video THAT, DUY NHAT MOT LAN -- goi sau khi storyboard da
        duoc nguoi dung APPROVE.

        duration_seconds lay TRUC TIEP tu brief.constraints (uu tien) --
        neu khong co, lay tu plan.duration_seconds (LLM da tu dien khi
        sinh storyboard, thuong khop voi brief nhung brief la nguon tin
        cay hon vi la yeu cau goc cua nguoi dung).
        """
        session = await self._load_session(task_id)
        plan = session.latest.plan

        render_prompt = await self._translate_to_render_prompt(plan)
        duration_seconds = (
            self._extract_duration_seconds(session.brief) or plan.duration_seconds
        )

        request = RenderRequest(
            prompt=render_prompt,
            reference_images=session.reference_images,
            duration_seconds=duration_seconds,
        )
        render_job = await self._video_renderer.submit(request)
        log_event(
            logger,
            "info",
            "storyboard_render_final_submitted",
            task_id=task_id,
            revision=session.latest.revision_number,
            render_job_id=render_job.job_id,
            duration_seconds=duration_seconds,
        )
        return render_job

    async def finalize_session(self, task_id: str) -> None:
        await self._memory.delete(task_id, namespace=_SESSION_NAMESPACE)
        log_event(logger, "info", "storyboard_session_finalized", task_id=task_id)

    # ------------------------------------------------------------------
    # Noi bo
    # ------------------------------------------------------------------

    async def _generate_storyboard_plan(
        self,
        brief: dict,
        reference_images: tuple[ReferenceImage, ...],
        feedback: str | None,
        previous_plan: StoryboardPlan | None,
    ) -> StoryboardPlan:
        prompt = self._build_prompt(brief, feedback, previous_plan)
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
        return self._parse_storyboard_plan(response.content)

    @staticmethod
    def _parse_storyboard_plan(raw_content: str) -> StoryboardPlan:
        """
        Parse + validate JSON tra ve tu LLM thanh StoryboardPlan. Bao
        loi RO RANG (StoryboardParseError) neu that bai, KHONG fallback
        am tham ve gia tri rong -- storyboard rong se lam Frontend/
        VideoRenderer hong hoan toan, khac voi truong hop InsightService
        (data/) co the chap nhan criteria rong.
        """
        cleaned = raw_content.strip()
        # LLM doi khi van boc JSON trong markdown code fence du da duoc
        # yeu cau khong lam vay -- go bo neu co, tang do ben cua parser.
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise StoryboardParseError(
                f"LLM khong tra ve JSON hop le cho storyboard: {exc}. Raw: {raw_content[:200]}"
            ) from exc

        try:
            return StoryboardPlan.model_validate(data)
        except pydantic.ValidationError as exc:
            raise StoryboardParseError(
                f"JSON tra ve khong khop StoryboardPlan schema: {exc}"
            ) from exc

    @staticmethod
    def _build_prompt(
        brief: dict, feedback: str | None, previous_plan: StoryboardPlan | None
    ) -> str:
        if feedback is None:
            return f"Brief san pham:\n{json.dumps(brief, ensure_ascii=False)}"

        return (
            f"Storyboard truoc do (JSON):\n{previous_plan.model_dump_json()}\n\n"
            f"Phan hoi cua nguoi dung can dieu chinh:\n{feedback}\n\n"
            f"Hay tra ve StoryboardPlan JSON MOI, giu nguyen phan nguoi dung hai long, "
            f"chi sua theo dung phan hoi tren."
        )

    async def _translate_to_render_prompt(self, plan: StoryboardPlan) -> str:
        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=_RENDER_PROMPT_SYSTEM_PROMPT),
                LLMMessage(
                    role=MessageRole.USER,
                    content=(
                        f"Storyboard:\n{plan.to_render_prompt_context()}\n\n"
                        f"Total duration required: {plan.duration_seconds} seconds."
                    ),
                ),
            )
        )
        response = await call_llm_with_retry(self._llm, request, self._retry_policy, logger)
        return response.content

    @staticmethod
    def _extract_duration_seconds(brief: dict) -> float | None:
        constraints = brief.get("constraints") or {}
        duration = constraints.get("duration_seconds")
        if duration is None:
            return None
        try:
            return float(duration)
        except (TypeError, ValueError):
            log_event(logger, "warning", "invalid_duration_seconds_in_brief", raw_value=duration)
            return None

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


class MaxRevisionsExceededError(Exception):
    """Vuot qua so lan sua storyboard toi da cho phep (settings.max_storyboard_revisions)."""


class SessionNotFoundError(Exception):
    """Khong tim thay storyboard session cho task_id da cho (chua start hoac da finalize)."""
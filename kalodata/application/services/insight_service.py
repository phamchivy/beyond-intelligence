"""
Vi tri file nay: data/application/services/insight_service.py

InsightService -- dieu phoi luong: doc Brief co cau truc (khop dung
bang `briefs` cua Backend: product_info, target_audience, ad_objective,
key_message, channel, creative_reference, constraints) -> LLM suy ra
tieu chi tim kiem (tu khoa, sort_field theo ad_objective) -> query
DONG THOI nhieu nhom du lieu Kalodata (video/product/category, mo rong
duoc qua settings.insight_domains) -> LLM tong hop TOAN BO thanh mot
Insight Report duy nhat -> nguoi dung xem, co the yeu cau dieu chinh
(HITL, cung co che voi StoryboardSessionService ben agent/).

Khong render gi ca (day la Data, khong phai Agent) -- Insight Report
cuoi cung se duoc Backend dua vao brief.creative_reference khi goi
Agent (POST /agent/reasoning/storyboard), dung nguyen co che da co san,
KHONG sua gi ben agent/.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace

from domain.policies.retry_policy import NonRetryableError, RetryableError, RetryPolicy
from domain.ports.llm import LLM, LLMMessage, LLMRequest, MessageRole
from domain.ports.market_data_provider import (
    DetailQuery,
    MarketDataDomain,
    MarketDataProvider,
    RankingQuery,
)
from observability.logging import get_logger, log_event

logger = get_logger(__name__)

_EXTRACT_CRITERIA_PROMPT = (
    "Ban la chuyen gia phan tich du lieu TikTok Shop. Duoi day la Brief san "
    "pham (product_info, target_audience, ad_objective, channel...). Hay doc "
    "va tra ve CHI mot dong JSON voi 2 truong: "
    "\"keyword\" (tu khoa nganh hang/san pham, rut tu product_info va "
    "target_audience, dung de tim kiem noi dung lien quan), "
    "\"sort_field\" (\"revenue\" neu ad_objective la conversion/lead, "
    "\"views\" neu la awareness/traffic). Khong giai thich gi them."
)

_SYNTHESIZE_INSIGHT_PROMPT = (
    "Ban la chuyen gia phan tich xu huong TikTok Shop. Duoi day la du lieu "
    "xep hang + chi tiet tu NHIEU nguon (video hieu suat cao, san pham ban "
    "chay, xu huong nganh hang) lien quan toi san pham cua nguoi dung. Hay "
    "tong hop thanh mot ban goi y ngan gon gom: "
    "(1) Dac diem chung cua noi dung/san pham hieu qua (do dai video, phong "
    "cach, hook, muc gia canh tranh), "
    "(2) Muc doanh thu/luot xem trung binh de tham khao, "
    "(3) Vi tri nganh hang nay dang o dau ve xu huong chung, "
    "(4) De xuat huong lam video cho san pham cua nguoi dung, bam sat "
    "ad_objective va key_message da cho. "
    "KHONG trich dan nguyen van tieu de/loi thoai cu the tu bat ky video "
    "nao -- chi tong hop pattern chung tu nhieu nguon."
)


@dataclass(frozen=True, slots=True)
class InsightRevision:
    revision_number: int
    criteria: dict
    insight_text: str
    feedback: str | None


@dataclass(frozen=True, slots=True)
class InsightSession:
    task_id: str
    brief: dict
    revisions: tuple[InsightRevision, ...]

    @property
    def latest(self) -> InsightRevision:
        return self.revisions[-1]

    def with_new_revision(self, revision: InsightRevision) -> "InsightSession":
        return replace(self, revisions=self.revisions + (revision,))


@dataclass(frozen=True, slots=True)
class InsightResult:
    task_id: str
    revision_number: int
    criteria: dict
    insight_text: str


class MaxRevisionsExceededError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class InsightService:
    def __init__(
        self,
        llm: LLM,
        market_data_provider: MarketDataProvider,
        retry_policy: RetryPolicy | None = None,
        max_revisions: int = 3,
        ranking_page_size: int = 20,
        top_n_for_detail: int = 10,
        domains: list[MarketDataDomain] | None = None,
    ) -> None:
        self._llm = llm
        self._market_data_provider = market_data_provider
        self._retry_policy = retry_policy or RetryPolicy()
        self._max_revisions = max_revisions
        self._ranking_page_size = ranking_page_size
        self._top_n_for_detail = top_n_for_detail
        # Danh sach nhom du lieu duoc query DONG THOI moi lan tong hop
        # -- mac dinh video+product neu khong truyen gi, de linh hoat
        # mo rong (vd: them CATEGORY, CREATOR) ma khong doi logic ben
        # duoi, chi doi danh sach nay (thuong truyen tu settings qua
        # bootstrap/container.py).
        self._domains = domains or [MarketDataDomain.VIDEO, MarketDataDomain.PRODUCT]
        self._sessions: dict[str, InsightSession] = {}

    async def start_session(self, task_id: str, brief: dict) -> InsightResult:
        criteria = await self._extract_criteria(brief)
        insight_text = await self._gather_and_synthesize(brief, criteria)

        revision = InsightRevision(
            revision_number=1, criteria=criteria, insight_text=insight_text, feedback=None
        )
        session = InsightSession(task_id=task_id, brief=brief, revisions=(revision,))
        self._sessions[task_id] = session

        log_event(
            logger,
            "info",
            "insight_session_started",
            task_id=task_id,
            revision=1,
            domains=[d.value for d in self._domains],
        )
        return InsightResult(
            task_id=task_id, revision_number=1, criteria=criteria, insight_text=insight_text
        )

    async def revise_session(self, task_id: str, feedback: str) -> InsightResult:
        session = self._sessions.get(task_id)
        if session is None:
            raise SessionNotFoundError(f"Khong tim thay insight session cho task_id='{task_id}'.")

        next_revision_number = session.latest.revision_number + 1
        if next_revision_number > self._max_revisions:
            raise MaxRevisionsExceededError(
                f"Task '{task_id}' da vuot qua {self._max_revisions} lan dieu chinh tieu chi."
            )

        criteria = await self._extract_criteria(session.brief, feedback=feedback)
        insight_text = await self._gather_and_synthesize(session.brief, criteria)

        revision = InsightRevision(
            revision_number=next_revision_number,
            criteria=criteria,
            insight_text=insight_text,
            feedback=feedback,
        )
        self._sessions[task_id] = session.with_new_revision(revision)

        log_event(
            logger, "info", "insight_session_revised", task_id=task_id, revision=next_revision_number
        )
        return InsightResult(
            task_id=task_id,
            revision_number=next_revision_number,
            criteria=criteria,
            insight_text=insight_text,
        )

    def finalize_session(self, task_id: str) -> None:
        self._sessions.pop(task_id, None)
        log_event(logger, "info", "insight_session_finalized", task_id=task_id)

    # ------------------------------------------------------------------
    # Noi bo
    # ------------------------------------------------------------------

    async def _extract_criteria(self, brief: dict, feedback: str | None = None) -> dict:
        prompt = f"Brief:\n{json.dumps(brief, ensure_ascii=False)}"
        if feedback is not None:
            prompt += f"\n\nDieu chinh them tu nguoi dung: {feedback}"

        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=_EXTRACT_CRITERIA_PROMPT),
                LLMMessage(role=MessageRole.USER, content=prompt),
            )
        )
        response = await self._call_llm(request)

        try:
            return json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            log_event(logger, "warning", "criteria_extraction_parse_failed", raw=response.content)
            return {}

    async def _gather_and_synthesize(self, brief: dict, criteria: dict) -> str:
        keyword = criteria.get("keyword", "")
        sort_field = criteria.get("sort_field", "revenue")

        gathered_by_domain: dict[str, dict] = {}

        for domain in self._domains:
            filters: dict = {}
            # CATEGORY ranking cua Kalodata khong ho tro loc theo keyword
            # (chi co category_ids/category_level/revenue_range theo tai
            # lieu goc) -- bo qua keyword rieng cho domain nay, van huu
            # ich vi cho biet xu huong chung cua toan nganh.
            if keyword and domain != MarketDataDomain.CATEGORY:
                filters["keyword"] = keyword

            ranking = await self._market_data_provider.get_ranking(
                RankingQuery(
                    domain=domain,
                    filters=filters,
                    sort_field=sort_field,
                    page_size=self._ranking_page_size,
                )
            )

            top_items = ranking[: self._top_n_for_detail]
            details = []
            for item in top_items:
                detail = await self._market_data_provider.get_detail(
                    DetailQuery(domain=domain, item_id=item.item_id)
                )
                details.append(detail)

            gathered_by_domain[domain.value] = {
                "ranking_summary": [item.raw for item in top_items],
                "details": details,
            }

        prompt = (
            f"Brief san pham:\n{json.dumps(brief, ensure_ascii=False)}\n\n"
            f"Du lieu thi truong theo tung nhom:\n"
            f"{json.dumps(gathered_by_domain, ensure_ascii=False)}"
        )

        request = LLMRequest(
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=_SYNTHESIZE_INSIGHT_PROMPT),
                LLMMessage(role=MessageRole.USER, content=prompt),
            )
        )
        response = await self._call_llm(request)
        return response.content

    async def _call_llm(self, request: LLMRequest):
        attempt = 0
        while True:
            attempt += 1
            try:
                return await self._llm.generate(request)
            except (RetryableError, NonRetryableError) as exc:
                if not self._retry_policy.should_retry(attempt, exc):
                    raise
                continue
"""
Vi tri file nay: agent/application/reasoning/llm_call.py

call_llm_with_retry -- ham DUNG CHUNG de goi LLM port co ap dung
RetryPolicy + logging, tach rieng tu ReasoningService (truoc day la
method rieng _call_with_retry ben trong ReasoningService).

Ly do tach: ReasoningService duoc thiet ke rieng cho vong lap ReAct cua
Agent (nhan AgentState + tool definitions) -- khong phu hop de tai su
dung cho cac application service khac chi can "goi LLM voi 1 prompt,
co retry" (vd: StoryboardSessionService). Tach logic retry-goi-LLM ra
ham dung chung nay de tranh trung lap, ca ReasoningService lan
StoryboardSessionService deu goi qua day.
"""
from __future__ import annotations

import logging

from domain.policies.retry_policy import NonRetryableError, RetryableError, RetryPolicy
from domain.ports.llm import LLM, LLMRequest, LLMResponse
from observability.logging import log_duration, log_event


async def call_llm_with_retry(
    llm: LLM,
    request: LLMRequest,
    retry_policy: RetryPolicy,
    logger: logging.Logger,
) -> LLMResponse:
    """
    Goi llm.generate(request), tu dong retry theo RetryPolicy khi gap
    RetryableError, dung ngay khi gap NonRetryableError hoac het luot.

    `logger` truyen vao tu noi goi (moi noi goi dung logger rieng cua
    module minh, giu dung quy uoc `logger = get_logger(__name__)` da
    ap dung xuyen suot du an).
    """
    attempt = 0
    last_error: Exception | None = None

    while True:
        attempt += 1
        try:
            with log_duration(logger, "llm_call_completed", attempt=attempt):
                response = await llm.generate(request)
            log_event(
                logger,
                "info",
                "llm_call_result",
                model=response.model,
                prompt_tokens=response.token_usage.prompt_tokens,
                completion_tokens=response.token_usage.completion_tokens,
                finish_reason=response.finish_reason,
                tool_call_count=len(response.tool_calls),
            )
            return response
        except (RetryableError, NonRetryableError) as exc:
            last_error = exc
            log_event(
                logger,
                "warning",
                "llm_call_failed",
                attempt=attempt,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            if not retry_policy.should_retry(attempt, exc):
                log_event(logger, "error", "llm_call_gave_up", attempt=attempt)
                raise
            delay = retry_policy.next_delay_seconds(attempt)
            log_event(logger, "info", "llm_call_retrying", attempt=attempt, delay_seconds=delay)
            continue

    raise last_error  # khong bao gio toi day, giu de type-checker yen tam
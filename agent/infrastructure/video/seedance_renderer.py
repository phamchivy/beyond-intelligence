"""
SeedanceRenderer -- implementation THAT cua VideoRenderer port
(domain/ports/video_renderer.py), goi model Seedance qua BytePlus
ModelArk (Ark SDK).

Day la noi DUY NHAT trong toan bo `agent/` duoc phep import
`byteplussdkarkruntime` cho muc dich sinh video. Domain/Application
khong biet Seedance/BytePlus ton tai -- chi biet Protocol VideoRenderer.

Sinh video la tac vu BAT DONG BO (co the mat vai chuc giay den vai
phut) -- submit() chi tao task va tra ve job_id ngay, get_status()
dung de poll dinh ky, dung y het pattern polling da mo ta trong tai
lieu API cua Seedance (client.content_generation.tasks.create/get).
"""
from __future__ import annotations

import base64

from byteplussdkarkruntime import AsyncArk
from byteplussdkarkruntime._exceptions import ArkAPIError, ArkAPIStatusError

from config.settings import VideoRendererSettings
from domain.policies.retry_policy import NonRetryableError, RetryableError
from domain.ports.video_renderer import (
    ReferenceImage,
    RenderJob,
    RenderJobStatus,
    RenderRequest,
)
from observability.logging import get_logger, log_duration, log_event

logger = get_logger(__name__)

_RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}

# Dich trang thai text tra ve tu Ark SDK ("succeeded"/"failed"/...) sang
# RenderJobStatus chuan hoa cua domain -- chi noi nay biet ten trang
# thai rieng cua Seedance.
_STATUS_MAP = {
    "queued": RenderJobStatus.QUEUED,
    "running": RenderJobStatus.PROCESSING,
    "succeeded": RenderJobStatus.COMPLETED,
    "failed": RenderJobStatus.FAILED,
    "cancelled": RenderJobStatus.FAILED,
}


class SeedanceRenderer:
    """
    Adapter implement dung Protocol VideoRenderer bang cach goi Seedance
    that qua BytePlus ModelArk.

    Khong tu doc `settings` global -- nhan `VideoRendererSettings` qua
    constructor (Dependency Injection), giong het GeminiProvider/
    DeepSeekProvider.
    """

    def __init__(self, config: VideoRendererSettings) -> None:
        self._config = config
        model, base_url, api_key = config.require_config()
        self._model = model
        self._client = AsyncArk(base_url=base_url, api_key=api_key.get_secret_value())

    async def submit(self, request: RenderRequest) -> RenderJob:
        content = self._to_task_content(request)

        try:
            with log_duration(logger, "video_render_submitted", model=self._model):
                result = await self._client.content_generation.tasks.create(
                    model=self._model,
                    content=content,
                )
        except ArkAPIError as exc:
            raise self._translate_error(exc) from exc

        log_event(logger, "info", "video_render_task_created", job_id=result.id)
        return RenderJob(job_id=result.id, status=RenderJobStatus.QUEUED)

    async def get_status(self, job_id: str) -> RenderJob:
        try:
            result = await self._client.content_generation.tasks.get(task_id=job_id)
        except ArkAPIError as exc:
            raise self._translate_error(exc) from exc

        status = _STATUS_MAP.get(result.status, RenderJobStatus.PROCESSING)

        if status == RenderJobStatus.COMPLETED:
            log_event(logger, "info", "video_render_completed", job_id=job_id)
            return RenderJob(
                job_id=job_id, status=status, video_url=result.content.video_url
            )
        if status == RenderJobStatus.FAILED:
            error_message = result.error.message if result.error else "khong ro loi"
            log_event(logger, "error", "video_render_failed", job_id=job_id, error=error_message)
            return RenderJob(job_id=job_id, status=status, error=error_message)

        return RenderJob(job_id=job_id, status=status)

    # ------------------------------------------------------------------
    # Dich RenderRequest -> dinh dang `content` cua Seedance task
    # ------------------------------------------------------------------

    def _to_task_content(self, request: RenderRequest) -> list[dict]:
        # Seedance nhan prompt dang text kem "flag" ngay trong chuoi
        # (vd: --ratio, --resolution, --duration) theo dung tai lieu
        # API -- gop lai o day, mot noi duy nhat biet quy uoc nay.
        prompt_with_flags = request.prompt
        prompt_with_flags += f" --ratio {request.aspect_ratio}"
        if request.duration_seconds is not None:
            prompt_with_flags += f" --duration {int(request.duration_seconds)}"

        content: list[dict] = [{"type": "text", "text": prompt_with_flags}]

        for image in request.reference_images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._to_data_url(image)},
                }
            )

        return content

    @staticmethod
    def _to_data_url(image: ReferenceImage) -> str:
        encoded = base64.b64encode(image.image_bytes).decode("ascii")
        return f"data:{image.mime_type};base64,{encoded}"

    # ------------------------------------------------------------------
    # Phan loai loi -- cung nguyen tac Anti-Corruption Layer nhu
    # GeminiProvider/DeepSeekProvider.
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_error(exc: ArkAPIError) -> Exception:
        status_code = exc.status_code if isinstance(exc, ArkAPIStatusError) else None
        if status_code in _RETRYABLE_HTTP_STATUS:
            return RetryableError(f"Seedance API loi tam thoi (status={status_code}): {exc}")
        return NonRetryableError(f"Seedance API loi khong the retry (status={status_code}): {exc}")
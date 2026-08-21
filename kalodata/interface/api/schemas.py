"""
Vi tri file nay: data/interface/api/schemas.py

Pydantic request/response cho interface/api/ cua data/.
"""
from __future__ import annotations

from pydantic import BaseModel


class StartInsightRequest(BaseModel):
    """
    Body cho POST /data/insights -- khop dung cau truc bang `briefs` cua
    Backend (docs/architecture/system-data-schemas.md).
    """

    task_id: str
    brief: dict  # {product_info, target_audience, ad_objective, key_message, channel, creative_reference, constraints}


class ReviseInsightRequest(BaseModel):
    task_id: str
    feedback: str


class InsightResponse(BaseModel):
    task_id: str
    revision_number: int
    criteria: dict
    insight_text: str
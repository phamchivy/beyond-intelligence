"""
Vi tri file nay: agent/business/domains/ai_ads_video_generator/schemas/storyboard_plan.py

StoryboardPlan -- schema CO CAU TRUC cho storyboard, thay the van ban
tu do (markdown) truoc day. Day la schema DAC THU NGHIEP VU cua bai
toan AI Ads Video Generator (BUP-01) -- dat trong business/, KHONG
phai domain/entities/, dung nguyen tac da thong nhat: domain/ chi giu
khai niem TONG QUAT (Task, Decision...), con cau truc storyboard cu
the (hook/scene/cta) la dac thu 1 nghiep vu, khong nen ep vao domain/.

Dung Pydantic (khong phai dataclass thuan) vi day la DTO can validate
chat che du lieu tu LLM tra ve (LLM co the tra sai dinh dang, thieu
field...) -- Pydantic bao loi ro rang ngay khi parse, thay vi de loi
am tham lan xuong Frontend.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SceneSegment(BaseModel):
    """
    Mot doan thoi gian trong video (dung chung cho Hook/Scene/CTA) --
    co diem bat dau/ket thuc ro rang, MOI doan la mot don vi Frontend
    co the hien thi thanh 1 the (card) rieng trong timeline.
    """

    time_start_seconds: float = Field(ge=0)
    time_end_seconds: float = Field(gt=0)
    scene_description: str = Field(description="Mo ta canh quay: goc may, chuyen dong, dien vien")
    on_screen_text: str = Field(default="", description="Chu xuat hien tren man hinh, neu co")
    audio_note: str = Field(default="", description="Ghi chu am thanh/nhac nen cho doan nay")


class Scene(SceneSegment):
    """Mot canh trong phan than bai (sau Hook, truoc CTA), co thu tu ro rang."""

    order: int = Field(ge=1)
    title: str = Field(description="Ten ngan gon cua canh, vd 'Hybrid ANC', 'Gia san pham'")


class ProductionNotes(BaseModel):
    """Ghi chu san xuat chung cho toan bo video, khong gan voi canh cu the nao."""

    music_style: str = Field(default="")
    color_palette: str = Field(default="")
    pacing_note: str = Field(default="")


class StoryboardPlan(BaseModel):
    """
    Storyboard hoan chinh, co cau truc -- KET QUA CHINH THUC tra ve cho
    Frontend hien thi va cho VideoRenderer dung de dung prompt render.

    `duration_seconds` o day la TONG thoi luong video (lay tu Brief),
    dung de doi chieu voi tong (time_end_seconds cua CTA) khi validate.
    """

    title: str
    duration_seconds: float = Field(gt=0)
    aspect_ratio: str = Field(default="9:16")
    objective: str = Field(description="vd: conversion, awareness")
    target_audience: str
    key_message: str

    hook: SceneSegment
    scenes: list[Scene] = Field(min_length=1)
    call_to_action: SceneSegment

    production_notes: ProductionNotes = Field(default_factory=ProductionNotes)

    def to_render_prompt_context(self) -> str:
        """
        Dung khi can chuyen StoryboardPlan thanh 1 doan mo ta tuyen tinh
        (dung lam input cho buoc dich sang tieng Anh truoc khi render) --
        thay the viec dung truc tiep storyboard_text tu do nhu truoc day.
        """
        parts = [
            f"Title: {self.title}",
            f"Duration: {self.duration_seconds}s, Aspect ratio: {self.aspect_ratio}",
            f"Objective: {self.objective}, Target audience: {self.target_audience}",
            f"Key message: {self.key_message}",
            f"HOOK ({self.hook.time_start_seconds}-{self.hook.time_end_seconds}s): "
            f"{self.hook.scene_description} | On-screen text: {self.hook.on_screen_text} "
            f"| Audio: {self.hook.audio_note}",
        ]
        for scene in self.scenes:
            parts.append(
                f"SCENE {scene.order} - {scene.title} "
                f"({scene.time_start_seconds}-{scene.time_end_seconds}s): "
                f"{scene.scene_description} | On-screen text: {scene.on_screen_text} "
                f"| Audio: {scene.audio_note}"
            )
        parts.append(
            f"CTA ({self.call_to_action.time_start_seconds}-{self.call_to_action.time_end_seconds}s): "
            f"{self.call_to_action.scene_description} | On-screen text: "
            f"{self.call_to_action.on_screen_text} | Audio: {self.call_to_action.audio_note}"
        )
        if self.production_notes.music_style:
            parts.append(f"Music style: {self.production_notes.music_style}")
        if self.production_notes.color_palette:
            parts.append(f"Color palette: {self.production_notes.color_palette}")
        if self.production_notes.pacing_note:
            parts.append(f"Pacing: {self.production_notes.pacing_note}")
        return "\n".join(parts)
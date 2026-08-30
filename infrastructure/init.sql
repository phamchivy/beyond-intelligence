CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 1. POSTGRESQL CỦA BACKEND / PIPELINE (SCHEMA PUBLIC)
-- ==========================================

CREATE TABLE IF NOT EXISTS public.tasks (
    id              UUID PRIMARY KEY,
    status          TEXT NOT NULL CHECK (status IN (
                        'brief_submitted', 'asset_processing', 'storyboard_pending',
                        'storyboard_review', 'render_pending', 'render_processing',
                        'completed', 'failed', 'cancelled', 'needs_manual_review'
                    )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.briefs (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    product_info        JSONB NOT NULL,
    target_audience     JSONB NOT NULL,
    ad_objective        TEXT NOT NULL,
    key_message         TEXT NOT NULL,
    channel             TEXT NOT NULL,
    creative_reference  JSONB,
    constraints         JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.asset_refs (
    id              UUID PRIMARY KEY,
    task_id         UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    data_object_ref TEXT NOT NULL,
    asset_type      TEXT NOT NULL CHECK (asset_type IN ('image', 'video', 'logo')),
    asset_role      TEXT NOT NULL,
    mime_type       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.storyboards (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    revision_number     INT NOT NULL DEFAULT 1,
    plan                JSONB NOT NULL,
    compliance_report   JSONB,
    confidence          NUMERIC(3,2) NOT NULL,
    review_status       TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN (
                            'pending', 'approved', 'needs_revision', 'rejected'
                        )),
    user_feedback       TEXT,
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, revision_number)
);

CREATE TABLE IF NOT EXISTS public.render_jobs (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    storyboard_id       UUID NOT NULL REFERENCES public.storyboards(id) ON DELETE CASCADE,
    agent_job_id        TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN (
                            'queued', 'processing', 'completed', 'failed'
                        )),
    temp_video_url      TEXT,
    final_object_ref    TEXT,
    qa_report           JSONB,
    error_message       TEXT,
created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

-- ==========================================
-- 2. POSTGRESQL CỦA DATA SERVICE (SCHEMA DATA)
-- ==========================================

CREATE SCHEMA IF NOT EXISTS data;

CREATE TABLE IF NOT EXISTS data.raw_assets (
    id                  UUID PRIMARY KEY,
    external_task_ref   TEXT NOT NULL,
    object_key          TEXT NOT NULL,
    mime_type           TEXT NOT NULL,
    size_bytes          BIGINT NOT NULL,
    checksum            TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('uploaded', 'processing', 'processed', 'failed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data.processed_assets (
    id                  UUID PRIMARY KEY,
    raw_asset_id        UUID NOT NULL REFERENCES data.raw_assets(id) ON DELETE CASCADE,
    object_key          TEXT NOT NULL,
    asset_role          TEXT NOT NULL,
    metadata            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data.rendered_videos (
    id                  UUID PRIMARY KEY,
    external_task_ref   TEXT NOT NULL,
    source_temp_url     TEXT NOT NULL,
    object_key          TEXT NOT NULL,
    duration_seconds    NUMERIC(5,2),
    resolution          TEXT,
    checksum            TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
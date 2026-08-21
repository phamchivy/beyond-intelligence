-- Backend orchestration schema (system-data-schemas.md)

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY,
    status          TEXT NOT NULL CHECK (status IN (
                        'brief_submitted', 'asset_processing', 'storyboard_pending',
                        'storyboard_review', 'render_pending', 'render_processing',
                        'completed', 'failed', 'cancelled', 'needs_manual_review'
                    )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS briefs (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES tasks(id),
    product_info        JSONB NOT NULL,
    target_audience     JSONB NOT NULL,
    ad_objective        TEXT NOT NULL,
    key_message         TEXT NOT NULL,
    channel             TEXT NOT NULL,
    creative_reference  JSONB,
    constraints         JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS asset_refs (
    id              UUID PRIMARY KEY,
    task_id         UUID NOT NULL REFERENCES tasks(id),
    data_object_ref TEXT NOT NULL,
    asset_type      TEXT NOT NULL CHECK (asset_type IN ('image', 'video', 'logo')),
    asset_role      TEXT NOT NULL,
    mime_type       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS storyboards (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES tasks(id),
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

CREATE TABLE IF NOT EXISTS render_jobs (
    id                  UUID PRIMARY KEY,
    task_id             UUID NOT NULL REFERENCES tasks(id),
    storyboard_id       UUID NOT NULL REFERENCES storyboards(id),
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

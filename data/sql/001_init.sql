-- Postgres schema for the data layer. Silver and Gold themselves live in
-- Delta on object storage; what lands here is the retrieval index, the
-- operational tables, and a published copy of Gold for serving.
--
-- Every statement is IF NOT EXISTS / OR REPLACE, so this file is safe to
-- apply twice: once from the container's initdb mount, once from the API
-- on startup (lib.db.apply_init_sql).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS "index";
CREATE SCHEMA IF NOT EXISTS api;
CREATE SCHEMA IF NOT EXISTS ops;
-- "source" holds the seeded ERP tables the Database ingestion pipeline
-- reads from -- it stands in for an external ERP database at hackathon
-- scale, and is never read by anything downstream of Bronze.
CREATE SCHEMA IF NOT EXISTS source;

-- unaccent() is not IMMUTABLE, so it cannot appear in a generated column
-- or an index expression. This wrapper is what makes the Vietnamese
-- lexical mitigation legal. Do not remove it to "simplify" a failing
-- index build -- the natural-looking fix is to call unaccent() directly,
-- and that silently deletes the entire Vietnamese mitigation described in
-- data-architecture.md §10.
CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
$$ SELECT public.unaccent('public.unaccent', $1) $$;

-- ============================================================ retrieval index
-- Derived, never authoritative: dropping this schema and rebuilding from
-- Silver must always be safe. Nothing may live only here.
CREATE TABLE IF NOT EXISTS "index".chunk (
    chunk_id     text PRIMARY KEY,
    document_id  text NOT NULL,
    source_type  text NOT NULL,             -- currently always 'document'
    chunk_index  int  NOT NULL,
    content      text NOT NULL,
    metadata     jsonb NOT NULL DEFAULT '{}',
    content_tsv  tsvector GENERATED ALWAYS AS (
                     to_tsvector('simple', public.immutable_unaccent(content))
                 ) STORED,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chunk_tsv_idx  ON "index".chunk USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS chunk_trgm_idx ON "index".chunk
    USING gin (public.immutable_unaccent(content) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS "index".embedding (
    chunk_id          text NOT NULL REFERENCES "index".chunk(chunk_id) ON DELETE CASCADE,
    embedder_model_id text NOT NULL,
    dimensions        int  NOT NULL CHECK (dimensions = 384),
    embedding         vector(384) NOT NULL,
    PRIMARY KEY (chunk_id, embedder_model_id)
);
-- HNSW cannot be a composite index, so embedder_model_id is filtered in the
-- query's WHERE clause rather than the index itself (decision 8.10).
CREATE INDEX IF NOT EXISTS embedding_hnsw_idx ON "index".embedding
    USING hnsw (embedding vector_cosine_ops);

-- ============================================================ ops
CREATE TABLE IF NOT EXISTS ops.run_log (
    run_id        text NOT NULL,
    asset_key     text NOT NULL,
    pipeline      text NOT NULL,
    dataset       text,
    status        text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    rows_in       bigint NOT NULL DEFAULT 0,
    rows_out      bigint NOT NULL DEFAULT 0,
    rows_rejected bigint NOT NULL DEFAULT 0,
    duration_ms   integer,
    delta_version bigint,                   -- the Delta commit this run produced
    error_code    text,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    PRIMARY KEY (run_id, asset_key)
);

CREATE TABLE IF NOT EXISTS ops.quality_violations (
    violation_id     bigserial PRIMARY KEY,
    run_id           text NOT NULL,
    dataset          text NOT NULL,
    contract_version text NOT NULL,
    check_name       text NOT NULL,
    column_name      text,
    violation_code   text NOT NULL,
    severity         text NOT NULL DEFAULT 'error' CHECK (severity IN ('warning','error')),
    failure_count    bigint NOT NULL DEFAULT 1,
    quarantine_table text,                  -- the Delta table the rows went to
    detail           text,                  -- NEVER a row payload
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.schema_drift (
    drift_id    bigserial PRIMARY KEY,
    run_id      text NOT NULL,
    dataset     text NOT NULL,
    change_type text NOT NULL CHECK (change_type IN ('column_added','column_removed','type_changed')),
    column_name text NOT NULL,
    from_type   text,
    to_type     text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- One row per (run, arm) of the evaluation harness -- keeping results in
-- Postgres alongside run_log is what makes "did the change help?" a query
-- instead of a diff between two Markdown reports.
CREATE TABLE IF NOT EXISTS ops.eval_run (
    eval_id          bigserial PRIMARY KEY,
    run_id           text NOT NULL,
    dataset_version  text NOT NULL,
    pipeline_version text NOT NULL,
    arm              text NOT NULL,
    n_cases          int NOT NULL,
    precision        double precision,
    recall           double precision,
    f1               double precision,
    recall_at_k      double precision,
    mrr              double precision,
    report_path      text,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- ============================================================ source (seeded ERP)
-- Stands in for an external ERP database. Read only by the Database
-- ingestion pipeline (defs/ingest.py::erp_db_source) via dlt's
-- sql_database source -- nothing downstream of Bronze touches this schema.
CREATE TABLE IF NOT EXISTS source.orders (
    order_id    text NOT NULL,
    customer_id text NOT NULL,
    amount      numeric(18,2) NOT NULL,
    ordered_at  timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS source.customers (
    customer_id text PRIMARY KEY,
    name        text NOT NULL,
    country     text NOT NULL
);

-- ============================================================ roles
DO $$ BEGIN
    CREATE ROLE backend_reader LOGIN PASSWORD 'backend_reader';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA api TO backend_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT SELECT ON TABLES TO backend_reader;
-- Deliberately NOT granted on gold. That denial is what makes the §9
-- serving boundary real rather than a convention.

-- gold.* tables and the api.v1_* views over them are created by the
-- publish step (defs/publish.py), not here -- their columns follow
-- whatever the Gold Delta tables actually contain.

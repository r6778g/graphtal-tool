CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    module TEXT NOT NULL CHECK (module IN ('upstream', 'formulation')),
    version INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    data_format TEXT NOT NULL CHECK (data_format IN ('csv', 'xls', 'xlsx')),
    row_count INTEGER NOT NULL,
    feature_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_id, module, version)
);

CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    module TEXT NOT NULL CHECK (module IN ('upstream', 'formulation')),
    dataset_id UUID NOT NULL REFERENCES datasets(id),
    status TEXT NOT NULL CHECK (status IN ('queued', 'training', 'candidate', 'failed')),
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    message TEXT NOT NULL DEFAULT '',
    candidate_ids UUID[] NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY,
    training_job_id UUID NOT NULL REFERENCES training_jobs(id),
    owner_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    module TEXT NOT NULL CHECK (module IN ('upstream', 'formulation')),
    target TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    version INTEGER NOT NULL,
    dataset_id UUID NOT NULL REFERENCES datasets(id),
    artifact_key TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    feature_schema JSONB NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    training_config JSONB NOT NULL DEFAULT '{}',
    metrics JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('candidate', 'active', 'rejected', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    approved_by TEXT,
    activated_at TIMESTAMPTZ,
    activated_by TEXT,
    UNIQUE (module, target, algorithm, version),
    UNIQUE (training_job_id, module, target, algorithm)
);

CREATE INDEX IF NOT EXISTS model_versions_tenant_created
    ON model_versions (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS model_versions_scope_status
    ON model_versions (module, target, algorithm, status);

CREATE TABLE IF NOT EXISTS active_models (
    module TEXT NOT NULL,
    target TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    model_id UUID NOT NULL REFERENCES model_versions(id),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (module, target, algorithm)
);

CREATE TABLE IF NOT EXISTS model_audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('promote', 'rollback')),
    model_id UUID NOT NULL REFERENCES model_versions(id),
    previous_model_id UUID REFERENCES model_versions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

# Database schema for Tenant Portal

-- Organisations table
CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    admin_email VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'provisioning', -- provisioning, active, suspended, deprovisioned
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Setup tokens for secure initial setup
CREATE TABLE setup_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

-- Provisioning logs for audit trail
CREATE TABLE provisioning_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    step VARCHAR(100) NOT NULL, -- creating_docker, waiting_db, registering_dns, sending_email
    status VARCHAR(50) NOT NULL, -- pending, success, failed
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- DNS registry for routing
CREATE TABLE dns_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    cluster_ip VARCHAR(45) NOT NULL,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    removed_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX idx_organisations_status ON organisations(status);
CREATE INDEX idx_organisations_slug ON organisations(slug);
CREATE INDEX idx_setup_tokens_organisation ON setup_tokens(organisation_id);
CREATE INDEX idx_setup_tokens_token ON setup_tokens(token_hash);
CREATE INDEX idx_setup_tokens_expires ON setup_tokens(expires_at);
CREATE INDEX idx_provisioning_logs_organisation ON provisioning_logs(organisation_id);
CREATE INDEX idx_provisioning_logs_step ON provisioning_logs(step);
CREATE INDEX idx_dns_records_slug ON dns_records(slug);

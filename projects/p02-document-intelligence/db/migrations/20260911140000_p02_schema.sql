-- migrate:up

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS p02;

CREATE TABLE p02.documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sha256 text NOT NULL UNIQUE,
    original_filename text NOT NULL,
    mime_type text NOT NULL
        CHECK (mime_type IN ('application/pdf', 'image/png', 'image/jpeg')),
    size_bytes integer NOT NULL
        CHECK (size_bytes > 0 AND size_bytes <= 10485760),
    pages integer
        CHECK (pages IS NULL OR pages >= 1),
    storage_path text NOT NULL,
    source text NOT NULL DEFAULT 'upload'
        CHECK (source IN ('upload', 'email')),
    status text NOT NULL DEFAULT 'received'
        CHECK (status IN (
            'received',
            'processing',
            'extracted',
            'needs_review',
            'approved',
            'exported',
            'rejected',
            'failed',
            'needs_manual'
        )),
    doc_type text
        CHECK (doc_type IS NULL OR doc_type IN (
            'invoice',
            'receipt',
            'other',
            'unknown'
        )),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE p02.documents IS
    'Uploaded files. Retention purge (P02-T14) deletes files and text; invoices stay.';

CREATE INDEX documents_status_created_at_idx
    ON p02.documents (status, created_at);

CREATE TABLE p02.document_text (
    document_id uuid NOT NULL REFERENCES p02.documents (id),
    page integer NOT NULL CHECK (page >= 1),
    method text NOT NULL CHECK (method IN ('text_layer', 'ocr')),
    text text NOT NULL,
    ocr_mean_confidence numeric
        CHECK (
            ocr_mean_confidence IS NULL
            OR (ocr_mean_confidence >= 0 AND ocr_mean_confidence <= 1)
        ),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (document_id, page, method)
);

COMMENT ON TABLE p02.document_text IS
    'Extracted page text. Purged with the file. Do not store real invoices.';

CREATE TABLE p02.extractions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES p02.documents (id),
    prompt_version text NOT NULL,
    model text NOT NULL,
    fields jsonb NOT NULL,
    valid_schema boolean NOT NULL,
    tokens_in integer,
    tokens_out integer,
    latency_ms integer,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX extractions_document_id_idx ON p02.extractions (document_id);

CREATE TABLE p02.validations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id uuid NOT NULL REFERENCES p02.extractions (id),
    rule text NOT NULL,
    field text NOT NULL,
    passed boolean NOT NULL,
    details jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX validations_extraction_id_idx ON p02.validations (extraction_id);

CREATE TABLE p02.decisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES p02.documents (id),
    decision text NOT NULL
        CHECK (decision IN ('auto_approve', 'review')),
    confidence numeric NOT NULL
        CHECK (confidence >= 0 AND confidence <= 1),
    reasons jsonb NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX decisions_document_id_idx ON p02.decisions (document_id);

CREATE TABLE p02.suppliers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    business_id text NOT NULL UNIQUE,
    vat_id text,
    iban text NOT NULL,
    bic text,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE p02.invoices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL UNIQUE REFERENCES p02.documents (id),
    supplier_id uuid NOT NULL REFERENCES p02.suppliers (id),
    invoice_number text NOT NULL,
    invoice_date date NOT NULL,
    due_date date,
    currency text NOT NULL,
    net_total numeric NOT NULL,
    vat_total numeric NOT NULL,
    gross_total numeric NOT NULL,
    iban text NOT NULL,
    reference text,
    line_items jsonb,
    approved_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (supplier_id, invoice_number)
);

CREATE TABLE p02.exports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id uuid NOT NULL REFERENCES p02.invoices (id),
    target text NOT NULL
        CHECK (target IN ('erp_api', 'csv')),
    status text NOT NULL
        CHECK (status IN ('pending', 'sent', 'failed')),
    external_id text,
    exported_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (invoice_id, target)
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend') THEN
        GRANT USAGE ON SCHEMA p02 TO app_backend;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA p02 TO app_backend;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA p02 TO app_backend;
        ALTER DEFAULT PRIVILEGES IN SCHEMA p02
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_backend;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'n8n_app') THEN
        GRANT USAGE ON SCHEMA p02 TO n8n_app;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA p02 TO n8n_app;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly') THEN
        GRANT USAGE ON SCHEMA p02 TO readonly;
        GRANT SELECT ON ALL TABLES IN SCHEMA p02 TO readonly;
    END IF;
END
$$;

-- migrate:down

DROP SCHEMA IF EXISTS p02 CASCADE;

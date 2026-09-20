-- Migration: Add general-purpose token storage for event registrations
-- Date: September 20, 2026
-- Description: Generalizes test.tokens and adds matching token storage to prod
-- Applies to: BOTH test and prod schemas
-- Depends on: Existing event_registrations tables

BEGIN;

-- ============================================================================
-- PHASE 1: GENERALIZE TEST TOKEN STORAGE
-- ============================================================================

-- Rename the older registration-specific token type column
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'test'
          AND table_name = 'tokens'
          AND column_name = 'token_type'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'test'
          AND table_name = 'tokens'
          AND column_name = 'type'
    ) THEN
        ALTER TABLE test.tokens RENAME COLUMN token_type TO type;
    END IF;
END;
$$;

-- Remove the registration-specific token type allow-list
DO $$
DECLARE
    v_constraint text;
BEGIN
    FOR v_constraint IN
        SELECT constraint_row.conname
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS table_row
          ON table_row.oid = constraint_row.conrelid
        JOIN pg_namespace AS schema_row
          ON schema_row.oid = table_row.relnamespace
        JOIN unnest(constraint_row.conkey) AS constrained_column(attnum)
          ON true
        JOIN pg_attribute AS column_row
          ON column_row.attrelid = table_row.oid
         AND column_row.attnum = constrained_column.attnum
        WHERE schema_row.nspname = 'test'
          AND table_row.relname = 'tokens'
          AND constraint_row.contype = 'c'
          AND column_row.attname = 'type'
    LOOP
        EXECUTE format('ALTER TABLE test.tokens DROP CONSTRAINT %I', v_constraint);
    END LOOP;
END;
$$;

ALTER TABLE test.tokens
ADD CONSTRAINT tokens_expiration_check
CHECK (expires_at > created_at);

-- ============================================================================
-- PHASE 2: CREATE PROD TOKEN STORAGE
-- ============================================================================

CREATE TABLE prod.tokens (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    type text NOT NULL,
    token_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    revoked_at timestamptz,
    revoked_reason text,
    last_verified_at timestamptz,
    verification_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT tokens_pkey PRIMARY KEY (id),
    CONSTRAINT tokens_hash_unique UNIQUE (token_hash),
    CONSTRAINT tokens_hash_not_empty CHECK (length(token_hash) > 0),
    CONSTRAINT tokens_expiration_check CHECK (expires_at > created_at),
    CONSTRAINT tokens_verification_count_check CHECK (verification_count >= 0)
);

-- ============================================================================
-- PHASE 3: ADD PROD REGISTRATION TOKEN REFERENCES
-- ============================================================================

ALTER TABLE prod.event_registrations
    ADD COLUMN email text,
    ADD COLUMN verification_token uuid,
    ADD COLUMN management_token uuid,
    ADD COLUMN rsvp_token uuid,
    ADD COLUMN ticket_token uuid,
    ADD CONSTRAINT event_registrations_verification_token_fkey
        FOREIGN KEY (verification_token) REFERENCES prod.tokens(id),
    ADD CONSTRAINT event_registrations_management_token_fkey
        FOREIGN KEY (management_token) REFERENCES prod.tokens(id),
    ADD CONSTRAINT event_registrations_rsvp_token_fkey
        FOREIGN KEY (rsvp_token) REFERENCES prod.tokens(id),
    ADD CONSTRAINT event_registrations_ticket_token_fkey
        FOREIGN KEY (ticket_token) REFERENCES prod.tokens(id);

-- ============================================================================
-- PHASE 4: CONFIGURE TOKEN TABLE ACCESS
-- ============================================================================

ALTER TABLE test.tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE prod.tokens ENABLE ROW LEVEL SECURITY;

-- Tokens are accessed only by the backend service role
REVOKE ALL ON TABLE test.tokens, prod.tokens FROM anon, authenticated;
GRANT ALL ON TABLE test.tokens, prod.tokens TO service_role;

COMMIT;

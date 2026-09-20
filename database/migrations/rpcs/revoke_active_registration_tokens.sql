-- Migration: Revoke active registration tokens helper
-- Date: September 20, 2026
-- Description: Revokes every active token referenced by a registration
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql

-- TEST SCHEMA

CREATE OR REPLACE FUNCTION test.revoke_active_registration_tokens(
    p_registration_id uuid,
    p_reason text,
    p_revoked_at timestamptz DEFAULT now()
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    UPDATE test.tokens
    SET revoked_at = p_revoked_at,
        revoked_reason = p_reason
    WHERE id IN (
        SELECT token_id
        FROM test.event_registrations registration
        CROSS JOIN LATERAL unnest(ARRAY[
            registration.verification_token,
            registration.management_token,
            registration.rsvp_token,
            registration.ticket_token
        ]) AS tokens(token_id)
        WHERE registration.id = p_registration_id
    )
      AND used_at IS NULL
      AND revoked_at IS NULL
      AND expires_at > p_revoked_at;
END;
$$;

REVOKE ALL ON FUNCTION test.revoke_active_registration_tokens(uuid, text, timestamptz)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.revoke_active_registration_tokens(uuid, text, timestamptz)
TO service_role;

-- PROD SCHEMA

CREATE OR REPLACE FUNCTION prod.revoke_active_registration_tokens(
    p_registration_id uuid,
    p_reason text,
    p_revoked_at timestamptz DEFAULT now()
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    UPDATE prod.tokens
    SET revoked_at = p_revoked_at,
        revoked_reason = p_reason
    WHERE id IN (
        SELECT token_id
        FROM prod.event_registrations registration
        CROSS JOIN LATERAL unnest(ARRAY[
            registration.verification_token,
            registration.management_token,
            registration.rsvp_token,
            registration.ticket_token
        ]) AS tokens(token_id)
        WHERE registration.id = p_registration_id
    )
      AND used_at IS NULL
      AND revoked_at IS NULL
      AND expires_at > p_revoked_at;
END;
$$;

REVOKE ALL ON FUNCTION prod.revoke_active_registration_tokens(uuid, text, timestamptz)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.revoke_active_registration_tokens(uuid, text, timestamptz)
TO service_role;

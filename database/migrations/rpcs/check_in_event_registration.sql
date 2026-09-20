-- Migration: Check in event registration RPC
-- Date: September 20, 2026
-- Description: Consumes a ticket token and marks a confirmed registration checked in atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and add_event_registration_flow_statuses.sql

CREATE OR REPLACE FUNCTION test.check_in_event_registration(
    p_registration_id uuid,
    p_ticket_token_hash text,
    p_checked_in_by uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_registration test.event_registrations%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'confirmed'
       OR v_registration.ticket_token IS NULL
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = ''
       OR p_checked_in_by IS NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_ticket_token
    FROM test.tokens
    WHERE id = v_registration.ticket_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_ticket_token.type <> 'ticket'
       OR v_ticket_token.token_hash <> p_ticket_token_hash
       OR v_ticket_token.expires_at <= v_now
       OR v_ticket_token.used_at IS NOT NULL
       OR v_ticket_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    UPDATE test.tokens SET used_at = v_now WHERE id = v_ticket_token.id;

    UPDATE test.event_registrations
    SET status = 'checked_in'::public.registration_status,
        checked_in = true,
        checked_in_at = v_now,
        checked_in_by = p_checked_in_by,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

REVOKE ALL ON FUNCTION test.check_in_event_registration(uuid, text, uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.check_in_event_registration(uuid, text, uuid)
TO service_role;

CREATE OR REPLACE FUNCTION prod.check_in_event_registration(
    p_registration_id uuid,
    p_ticket_token_hash text,
    p_checked_in_by uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_registration prod.event_registrations%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'confirmed'
       OR v_registration.ticket_token IS NULL
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = ''
       OR p_checked_in_by IS NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_ticket_token
    FROM prod.tokens
    WHERE id = v_registration.ticket_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_ticket_token.type <> 'ticket'
       OR v_ticket_token.token_hash <> p_ticket_token_hash
       OR v_ticket_token.expires_at <= v_now
       OR v_ticket_token.used_at IS NOT NULL
       OR v_ticket_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    UPDATE prod.tokens SET used_at = v_now WHERE id = v_ticket_token.id;

    UPDATE prod.event_registrations
    SET status = 'checked_in'::public.registration_status,
        checked_in = true,
        checked_in_at = v_now,
        checked_in_by = p_checked_in_by,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

REVOKE ALL ON FUNCTION prod.check_in_event_registration(uuid, text, uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.check_in_event_registration(uuid, text, uuid)
TO service_role;

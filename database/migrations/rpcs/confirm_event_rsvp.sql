-- Migration: Confirm event RSVP RPC
-- Date: September 20, 2026
-- Description: Confirms RSVP, rotates management access, and issues the ticket atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and set_event_registration_pending_default.sql

-- TEST SCHEMA

CREATE OR REPLACE FUNCTION test.confirm_event_rsvp(
    p_registration_id uuid,
    p_rsvp_token_hash text,
    p_management_token_hash text,
    p_ticket_token_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_rsvp_token test.tokens%ROWTYPE;
    v_old_management_token test.tokens%ROWTYPE;
    v_new_management_token test.tokens%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM test.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM test.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_new_management_token;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
    RETURNING * INTO v_ticket_token;

    UPDATE test.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE test.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$$;

REVOKE ALL ON FUNCTION test.confirm_event_rsvp(uuid, text, text, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.confirm_event_rsvp(uuid, text, text, text)
TO service_role;

-- PROD SCHEMA

CREATE OR REPLACE FUNCTION prod.confirm_event_rsvp(
    p_registration_id uuid,
    p_rsvp_token_hash text,
    p_management_token_hash text,
    p_ticket_token_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_rsvp_token prod.tokens%ROWTYPE;
    v_old_management_token prod.tokens%ROWTYPE;
    v_new_management_token prod.tokens%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM prod.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM prod.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_new_management_token;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
    RETURNING * INTO v_ticket_token;

    UPDATE prod.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE prod.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$$;

REVOKE ALL ON FUNCTION prod.confirm_event_rsvp(uuid, text, text, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.confirm_event_rsvp(uuid, text, text, text)
TO service_role;


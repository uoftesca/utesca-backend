-- Migration: Verify event registration RPC
-- Date: September 20, 2026
-- Description: Consumes the verification token and assigns waitlist, submitted, or confirmed status atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and set_event_registration_pending_default.sql

-- TEST SCHEMA

DROP FUNCTION IF EXISTS test.verify_event_registration(uuid, text);

CREATE OR REPLACE FUNCTION test.verify_event_registration(
    p_registration_id uuid,
    p_token_hash text,
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
    v_verification_token test.tokens%ROWTYPE;
    v_management_token test.tokens%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_auto_accept boolean;
    v_has_capacity boolean := true;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent concurrent requests from verifying the same registration.
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'pending_verification' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent the one-time verification token from being consumed twice.
    SELECT * INTO v_verification_token
    FROM test.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_verification_token.type <> 'verification'
       OR v_verification_token.token_hash <> p_token_hash
       OR v_verification_token.expires_at <= v_now
       OR v_verification_token.used_at IS NOT NULL
       OR v_verification_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM test.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        v_has_capacity := v_attendee_count < v_event.max_capacity;
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_management_token;

    IF v_auto_accept AND v_has_capacity THEN
        INSERT INTO test.tokens (type, token_hash, expires_at)
        VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
        RETURNING * INTO v_ticket_token;
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_verification_token.id;

    UPDATE test.event_registrations
    SET status = CASE
            WHEN NOT v_has_capacity THEN 'waitlist'::public.registration_status
            WHEN v_auto_accept THEN 'confirmed'::public.registration_status
            ELSE 'submitted'::public.registration_status
        END,
        management_token = v_management_token.id,
        ticket_token = CASE WHEN v_auto_accept AND v_has_capacity THEN v_ticket_token.id ELSE NULL END,
        confirmed_at = CASE WHEN v_auto_accept AND v_has_capacity THEN v_now ELSE NULL END,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$$;

REVOKE ALL ON FUNCTION test.verify_event_registration(uuid, text, text, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.verify_event_registration(uuid, text, text, text)
TO service_role;

-- PROD SCHEMA

DROP FUNCTION IF EXISTS prod.verify_event_registration(uuid, text);

CREATE OR REPLACE FUNCTION prod.verify_event_registration(
    p_registration_id uuid,
    p_token_hash text,
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
    v_verification_token prod.tokens%ROWTYPE;
    v_management_token prod.tokens%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_auto_accept boolean;
    v_has_capacity boolean := true;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent concurrent requests from verifying the same registration.
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'pending_verification' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent the one-time verification token from being consumed twice.
    SELECT * INTO v_verification_token
    FROM prod.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_verification_token.type <> 'verification'
       OR v_verification_token.token_hash <> p_token_hash
       OR v_verification_token.expires_at <= v_now
       OR v_verification_token.used_at IS NOT NULL
       OR v_verification_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM prod.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        v_has_capacity := v_attendee_count < v_event.max_capacity;
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_management_token;

    IF v_auto_accept AND v_has_capacity THEN
        INSERT INTO prod.tokens (type, token_hash, expires_at)
        VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
        RETURNING * INTO v_ticket_token;
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_verification_token.id;

    UPDATE prod.event_registrations
    SET status = CASE
            WHEN NOT v_has_capacity THEN 'waitlist'::public.registration_status
            WHEN v_auto_accept THEN 'confirmed'::public.registration_status
            ELSE 'submitted'::public.registration_status
        END,
        management_token = v_management_token.id,
        ticket_token = CASE WHEN v_auto_accept AND v_has_capacity THEN v_ticket_token.id ELSE NULL END,
        confirmed_at = CASE WHEN v_auto_accept AND v_has_capacity THEN v_now ELSE NULL END,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$$;

REVOKE ALL ON FUNCTION prod.verify_event_registration(uuid, text, text, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.verify_event_registration(uuid, text, text, text)
TO service_role;


-- Migration: Accept event registration RPC
-- Date: September 20, 2026
-- Description: Accepts a submitted application and issues its RSVP token atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and set_event_registration_pending_default.sql

-- TEST SCHEMA

CREATE OR REPLACE FUNCTION test.accept_event_registration(
    p_registration_id uuid,
    p_reviewer_id uuid,
    p_rsvp_token_hash text
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
    v_token test.tokens%ROWTYPE;
    v_rsvp_expires_at timestamptz;
    v_attendee_count integer;
BEGIN
    IF p_rsvp_token_hash IS NULL OR btrim(p_rsvp_token_hash) = '' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'submitted' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    v_rsvp_expires_at := v_event.date_time - interval '24 hours';
    IF v_rsvp_expires_at <= v_now THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM test.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        IF v_attendee_count >= v_event.max_capacity THEN
            RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
        END IF;
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('rsvp', p_rsvp_token_hash, v_rsvp_expires_at)
    RETURNING * INTO v_token;

    UPDATE test.event_registrations
    SET status = 'accepted'::public.registration_status,
        rsvp_token = v_token.id,
        reviewed_by = p_reviewer_id,
        reviewed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'token', to_jsonb(v_token)
    );
END;
$$;

REVOKE ALL ON FUNCTION test.accept_event_registration(uuid, uuid, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.accept_event_registration(uuid, uuid, text)
TO service_role;

-- PROD SCHEMA

CREATE OR REPLACE FUNCTION prod.accept_event_registration(
    p_registration_id uuid,
    p_reviewer_id uuid,
    p_rsvp_token_hash text
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
    v_token prod.tokens%ROWTYPE;
    v_rsvp_expires_at timestamptz;
    v_attendee_count integer;
BEGIN
    IF p_rsvp_token_hash IS NULL OR btrim(p_rsvp_token_hash) = '' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'submitted' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    v_rsvp_expires_at := v_event.date_time - interval '24 hours';
    IF v_rsvp_expires_at <= v_now THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM prod.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        IF v_attendee_count >= v_event.max_capacity THEN
            RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
        END IF;
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('rsvp', p_rsvp_token_hash, v_rsvp_expires_at)
    RETURNING * INTO v_token;

    UPDATE prod.event_registrations
    SET status = 'accepted'::public.registration_status,
        rsvp_token = v_token.id,
        reviewed_by = p_reviewer_id,
        reviewed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'token', to_jsonb(v_token)
    );
END;
$$;

REVOKE ALL ON FUNCTION prod.accept_event_registration(uuid, uuid, text)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.accept_event_registration(uuid, uuid, text)
TO service_role;


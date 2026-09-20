-- Migration: Add atomic event registration verification functions
-- Date: September 20, 2026
-- Description: Creates registrations and verifies email tokens transactionally
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and set_event_registration_pending_default.sql

-- ============================================================================
-- TEST SCHEMA FUNCTIONS
-- ============================================================================

-- Create a pending registration and its verification token atomically
CREATE OR REPLACE FUNCTION test.create_pending_event_registration(
    p_event_id uuid,
    p_form_data jsonb,
    p_email text,
    p_upload_session_id text,
    p_token_hash text,
    p_token_expires_at timestamptz
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_event test.events%ROWTYPE;
    v_token test.tokens%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
BEGIN
    IF p_email IS NULL
       OR btrim(p_email) = ''
       OR p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_token_expires_at IS NULL
       OR p_token_expires_at <= now() THEN
        RAISE EXCEPTION 'invalid registration verification data' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = p_event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'event not found' USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('verification', p_token_hash, p_token_expires_at)
    RETURNING * INTO v_token;

    INSERT INTO test.event_registrations (
        event_id,
        form_data,
        email,
        status,
        verification_token
    )
    VALUES (
        p_event_id,
        p_form_data,
        btrim(p_email),
        'pending_verification'::public.registration_status,
        v_token.id
    )
    RETURNING * INTO v_registration;

    UPDATE test.registration_files
    SET registration_id = v_registration.id,
        scheduled_deletion_date = v_event.date_time::date + 30
    WHERE upload_session_id = p_upload_session_id
      AND event_id = p_event_id
      AND registration_id IS NULL;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'token', to_jsonb(v_token)
    );
END;
$$;

-- Consume a verification token and advance the registration status atomically
CREATE OR REPLACE FUNCTION test.verify_event_registration(
    p_registration_id uuid,
    p_token_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_token test.tokens%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_next_status public.registration_status;
    v_auto_accept boolean;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL OR btrim(p_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

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

    IF NOT FOUND THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_token
    FROM test.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_token.type <> 'verification'
       OR v_token.token_hash <> p_token_hash
       OR v_token.expires_at <= v_now
       OR v_token.used_at IS NOT NULL
       OR v_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF NOT v_auto_accept THEN
        v_next_status := 'submitted'::public.registration_status;
    ELSE
        SELECT count(*) INTO v_attendee_count
        FROM test.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        IF v_event.max_capacity IS NOT NULL AND v_attendee_count >= v_event.max_capacity THEN
            v_next_status := 'waitlist'::public.registration_status;
        ELSE
            v_next_status := 'accepted'::public.registration_status;
        END IF;
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_token.id;

    UPDATE test.event_registrations
    SET status = v_next_status,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

-- Restrict test functions to the backend service role
REVOKE ALL ON FUNCTION test.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION test.verify_event_registration(uuid, text)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION test.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
TO service_role;
GRANT EXECUTE ON FUNCTION test.verify_event_registration(uuid, text)
TO service_role;

-- ============================================================================
-- PROD SCHEMA FUNCTIONS
-- ============================================================================

-- Create a pending registration and its verification token atomically
CREATE OR REPLACE FUNCTION prod.create_pending_event_registration(
    p_event_id uuid,
    p_form_data jsonb,
    p_email text,
    p_upload_session_id text,
    p_token_hash text,
    p_token_expires_at timestamptz
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_event prod.events%ROWTYPE;
    v_token prod.tokens%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
BEGIN
    IF p_email IS NULL
       OR btrim(p_email) = ''
       OR p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_token_expires_at IS NULL
       OR p_token_expires_at <= now() THEN
        RAISE EXCEPTION 'invalid registration verification data' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = p_event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'event not found' USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('verification', p_token_hash, p_token_expires_at)
    RETURNING * INTO v_token;

    INSERT INTO prod.event_registrations (
        event_id,
        form_data,
        email,
        status,
        verification_token
    )
    VALUES (
        p_event_id,
        p_form_data,
        btrim(p_email),
        'pending_verification'::public.registration_status,
        v_token.id
    )
    RETURNING * INTO v_registration;

    UPDATE prod.registration_files
    SET registration_id = v_registration.id,
        scheduled_deletion_date = v_event.date_time::date + 30
    WHERE upload_session_id = p_upload_session_id
      AND event_id = p_event_id
      AND registration_id IS NULL;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'token', to_jsonb(v_token)
    );
END;
$$;

-- Consume a verification token and advance the registration status atomically
CREATE OR REPLACE FUNCTION prod.verify_event_registration(
    p_registration_id uuid,
    p_token_hash text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_token prod.tokens%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_next_status public.registration_status;
    v_auto_accept boolean;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL OR btrim(p_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

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

    IF NOT FOUND THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_token
    FROM prod.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_token.type <> 'verification'
       OR v_token.token_hash <> p_token_hash
       OR v_token.expires_at <= v_now
       OR v_token.used_at IS NOT NULL
       OR v_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF NOT v_auto_accept THEN
        v_next_status := 'submitted'::public.registration_status;
    ELSE
        SELECT count(*) INTO v_attendee_count
        FROM prod.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed', 'checked_in');

        IF v_event.max_capacity IS NOT NULL AND v_attendee_count >= v_event.max_capacity THEN
            v_next_status := 'waitlist'::public.registration_status;
        ELSE
            v_next_status := 'accepted'::public.registration_status;
        END IF;
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_token.id;

    UPDATE prod.event_registrations
    SET status = v_next_status,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

-- Restrict prod functions to the backend service role
REVOKE ALL ON FUNCTION prod.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION prod.verify_event_registration(uuid, text)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION prod.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
TO service_role;
GRANT EXECUTE ON FUNCTION prod.verify_event_registration(uuid, text)
TO service_role;

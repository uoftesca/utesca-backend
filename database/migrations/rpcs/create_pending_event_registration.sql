-- Migration: Create pending event registration RPC
-- Date: September 20, 2026
-- Description: Creates a pending registration and its verification token atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: add_registration_token_storage.sql and set_event_registration_pending_default.sql

-- TEST SCHEMA

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
    FOR SHARE;

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

REVOKE ALL ON FUNCTION test.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
TO service_role;

-- PROD SCHEMA

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
    FOR SHARE;

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

REVOKE ALL ON FUNCTION prod.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.create_pending_event_registration(uuid, jsonb, text, text, text, timestamptz)
TO service_role;


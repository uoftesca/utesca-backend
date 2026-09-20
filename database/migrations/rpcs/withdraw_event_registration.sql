-- Migration: Withdraw event registration RPC
-- Date: September 20, 2026
-- Description: Withdraws an application and revokes its active tokens atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: revoke_active_registration_tokens.sql

-- TEST SCHEMA

CREATE OR REPLACE FUNCTION test.withdraw_event_registration(p_registration_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_registration test.event_registrations%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('submitted', 'waitlist') THEN
        RAISE EXCEPTION 'registration cannot be withdrawn' USING ERRCODE = 'P0001';
    END IF;

    PERFORM test.revoke_active_registration_tokens(
        p_registration_id,
        'registration_withdrawn',
        v_now
    );

    UPDATE test.event_registrations
    SET status = 'withdrawn'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

REVOKE ALL ON FUNCTION test.withdraw_event_registration(uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.withdraw_event_registration(uuid)
TO service_role;

-- PROD SCHEMA

CREATE OR REPLACE FUNCTION prod.withdraw_event_registration(p_registration_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_registration prod.event_registrations%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('submitted', 'waitlist') THEN
        RAISE EXCEPTION 'registration cannot be withdrawn' USING ERRCODE = 'P0001';
    END IF;

    PERFORM prod.revoke_active_registration_tokens(
        p_registration_id,
        'registration_withdrawn',
        v_now
    );

    UPDATE prod.event_registrations
    SET status = 'withdrawn'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$$;

REVOKE ALL ON FUNCTION prod.withdraw_event_registration(uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.withdraw_event_registration(uuid)
TO service_role;

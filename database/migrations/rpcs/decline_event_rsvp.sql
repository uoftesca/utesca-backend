-- Migration: Decline event RSVP RPC
-- Date: September 20, 2026
-- Description: Declines an RSVP and revokes its active tokens atomically
-- Applies to: BOTH test and prod schemas
-- Depends on: revoke_active_registration_tokens.sql

-- TEST SCHEMA

CREATE OR REPLACE FUNCTION test.decline_event_rsvp(p_registration_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_previous_status text;
    v_registration test.event_registrations%ROWTYPE;
    v_event test.events%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('accepted', 'confirmed') THEN
        RAISE EXCEPTION 'RSVP cannot be declined' USING ERRCODE = 'P0001';
    END IF;

    v_previous_status := v_registration.status::text;

    PERFORM test.revoke_active_registration_tokens(
        p_registration_id,
        'rsvp_declined',
        v_now
    );

    UPDATE test.event_registrations
    SET status = 'not_attending'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'previous_status', v_previous_status
    );
END;
$$;

REVOKE ALL ON FUNCTION test.decline_event_rsvp(uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION test.decline_event_rsvp(uuid)
TO service_role;

-- PROD SCHEMA

CREATE OR REPLACE FUNCTION prod.decline_event_rsvp(p_registration_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_now timestamptz := now();
    v_previous_status text;
    v_registration prod.event_registrations%ROWTYPE;
    v_event prod.events%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('accepted', 'confirmed') THEN
        RAISE EXCEPTION 'RSVP cannot be declined' USING ERRCODE = 'P0001';
    END IF;

    v_previous_status := v_registration.status::text;

    PERFORM prod.revoke_active_registration_tokens(
        p_registration_id,
        'rsvp_declined',
        v_now
    );

    UPDATE prod.event_registrations
    SET status = 'not_attending'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'previous_status', v_previous_status
    );
END;
$$;

REVOKE ALL ON FUNCTION prod.decline_event_rsvp(uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION prod.decline_event_rsvp(uuid)
TO service_role;

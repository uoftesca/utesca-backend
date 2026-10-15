-- Migration: Remove checked_in from registration_status enum type
-- Date: October 15, 2026
-- Description:
-- Applies to: BOTH test.event_registrations and prod.event_registrations schemas

UPDATE test.event_registrations
SET status = 'confirmed'::public.registration_status
WHERE status::text = 'checked_in';

UPDATE prod.event_registrations
SET status = 'confirmed'::public.registration_status
WHERE status::text = 'checked_in';

ALTER TYPE public.registration_status RENAME TO registration_status_old;

CREATE TYPE public.registration_status as ENUM (
    'pending_verification',
    'submitted',
    'withdrawn',
    'accepted',
    'rejected',
    'confirmed',
    'not_attending',
    'waitlist'
);

ALTER TABLE test.event_registrations
    ALTER COLUMN status TYPE public.registration_status
    USING status::text::public.registration_status;

ALTER TABLE prod.event_registrations
    ALTER COLUMN status TYPE public.registration_status
    USING status::text::public.registration_status;

DROP TYPE public.registration_status_old;

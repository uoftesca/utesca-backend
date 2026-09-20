-- Migration: Set pending verification as the registration default
-- Date: September 20, 2026
-- Description: Requires new registrations to complete email verification
-- Applies to: BOTH test.event_registrations and prod.event_registrations schemas
-- Depends on: add_event_registration_flow_statuses.sql committed separately

-- Set the default status in the test schema
ALTER TABLE test.event_registrations
ALTER COLUMN status
SET DEFAULT 'pending_verification'::public.registration_status;

-- Set the default status in the prod schema
ALTER TABLE prod.event_registrations
ALTER COLUMN status
SET DEFAULT 'pending_verification'::public.registration_status;

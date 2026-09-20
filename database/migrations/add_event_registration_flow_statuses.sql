-- Migration: Add event registration flow statuses
-- Date: September 20, 2026
-- Description: Adds statuses for identity verification, withdrawal, and check-in
-- Applies to: Shared public.registration_status enum used by BOTH test and prod schemas

-- ============================================================================
-- ADD REGISTRATION STATUSES
-- ============================================================================

ALTER TYPE public.registration_status
ADD VALUE IF NOT EXISTS 'pending_verification'
BEFORE 'submitted';

ALTER TYPE public.registration_status
ADD VALUE IF NOT EXISTS 'withdrawn'
AFTER 'submitted';

ALTER TYPE public.registration_status
ADD VALUE IF NOT EXISTS 'checked_in'
AFTER 'not_attending';

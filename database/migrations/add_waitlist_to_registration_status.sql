-- Migration: Add waitlist to registration_status enum type
-- Date: February 16, 2026
-- Description: 
-- Applies to: BOTH test.event_registrations and prod.event_registrations schemas
-- Ticket: UTESCA-62

-- Add acceptance_email_template column to test schema
ALTER TYPE public.registration_status
ADD VALUE 'waitlist';
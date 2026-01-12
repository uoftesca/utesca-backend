-- Migration: Add email template columns to events table
-- Date: January 12, 2026
-- Description: Adds acceptance_email_template and rejection_email_template JSONB columns for customizable email notifications
-- Applies to: BOTH test.events and prod.events schemas
-- Ticket: UTESCA-71

-- ============================================================================
-- PHASE 1: ADD JSONB COLUMNS
-- ============================================================================

-- Add acceptance_email_template column to test schema
ALTER TABLE test.events
ADD COLUMN acceptance_email_template JSONB NULL;

-- Add rejection_email_template column to test schema
ALTER TABLE test.events
ADD COLUMN rejection_email_template JSONB NULL;

-- Add acceptance_email_template column to prod schema
ALTER TABLE prod.events
ADD COLUMN acceptance_email_template JSONB NULL;

-- Add rejection_email_template column to prod schema
ALTER TABLE prod.events
ADD COLUMN rejection_email_template JSONB NULL;

-- ============================================================================
-- NOTES
-- ============================================================================

-- IMPORTANT:
-- 1. These columns are nullable - NULL values mean "use system default template"
-- 2. No data migration needed - existing events will use default templates
-- 3. Expected JSONB structure: {"subject": "...", "body": "..."}
-- 4. Template variables supported: {{full_name}}, {{event_title}}, {{event_datetime}}, {{event_location}}, {{rsvp_link}}
-- 5. No indexes needed - templates loaded with event object, not queried independently
-- 6. Validation handled at application level via Pydantic models

-- Example template value:
-- {
--   "subject": "You're Accepted for {{event_title}}!",
--   "body": "Hi {{full_name}},\n\nGreat news! Your application for {{event_title}} has been accepted.\n\nPlease confirm your attendance: {{rsvp_link}}"
-- }

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify columns were added (run manually after migration)
-- SELECT column_name, data_type, is_nullable FROM information_schema.columns
-- WHERE table_schema = 'test' AND table_name = 'events'
-- AND column_name IN ('acceptance_email_template', 'rejection_email_template');

-- SELECT column_name, data_type, is_nullable FROM information_schema.columns
-- WHERE table_schema = 'prod' AND table_name = 'events'
-- AND column_name IN ('acceptance_email_template', 'rejection_email_template');

-- ============================================================================
-- ROLLBACK SCRIPT (run only if migration fails)
-- ============================================================================

-- ALTER TABLE test.events DROP COLUMN IF EXISTS acceptance_email_template;
-- ALTER TABLE test.events DROP COLUMN IF EXISTS rejection_email_template;
-- ALTER TABLE prod.events DROP COLUMN IF EXISTS acceptance_email_template;
-- ALTER TABLE prod.events DROP COLUMN IF EXISTS rejection_email_template;

-- ============================================================================
-- Announcements System - Database Schema
-- ============================================================================
-- This migration creates the announcements and announcement_reads tables
-- for the UTESCA portal's announcement management system.
--
-- Environments: applied to both test and prod schemas
-- Depends on: auth.users table, {schema}.users table with role column
-- ============================================================================

-- ============================================================================
-- Announcements Table
-- ============================================================================
-- Stores announcement records created by co-presidents/VPs
-- Row Level Security (RLS) policies control access

CREATE TABLE IF NOT EXISTS {schema}.announcements (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    title text NOT NULL,
    content text NOT NULL,
    priority text NOT NULL CHECK (priority IN ('urgent', 'normal')),
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcements_pkey PRIMARY KEY (id),
    CONSTRAINT announcements_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES {schema}.users (id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_{schema}_announcements_created_by
    ON {schema}.announcements USING btree (created_by);

CREATE INDEX IF NOT EXISTS idx_{schema}_announcements_priority
    ON {schema}.announcements USING btree (priority);

CREATE INDEX IF NOT EXISTS idx_{schema}_announcements_created_at
    ON {schema}.announcements USING btree (created_at DESC);

-- Trigger to auto-update updated_at timestamp
CREATE TRIGGER update_announcements_updated_at
    BEFORE UPDATE ON {schema}.announcements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Announcement Reads Table
-- ============================================================================
-- Tracks which users have marked which announcements as read
-- Used for calculating read statistics and user read status

CREATE TABLE IF NOT EXISTS {schema}.announcement_reads (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    announcement_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcement_reads_pkey PRIMARY KEY (id),
    CONSTRAINT announcement_reads_announcement_id_fkey
        FOREIGN KEY (announcement_id) REFERENCES {schema}.announcements (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES {schema}.users (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_unique UNIQUE (announcement_id, user_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_{schema}_announcement_reads_announcement_id
    ON {schema}.announcement_reads USING btree (announcement_id);

CREATE INDEX IF NOT EXISTS idx_{schema}_announcement_reads_user_id
    ON {schema}.announcement_reads USING btree (user_id);


-- ============================================================================
-- Enable Row Level Security
-- ============================================================================

ALTER TABLE {schema}.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.announcement_reads ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- RLS Policies - Announcements Table
-- ============================================================================

-- Policy: All authenticated users can SELECT (read) announcements
DROP POLICY IF EXISTS "announcements_select_authenticated" ON {schema}.announcements;
CREATE POLICY "announcements_select_authenticated"
    ON {schema}.announcements FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Co-presidents can INSERT announcements
DROP POLICY IF EXISTS "announcements_insert_copresidents" ON {schema}.announcements;
CREATE POLICY "announcements_insert_copresidents"
    ON {schema}.announcements FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM {schema}.users
            WHERE user_id = auth.uid()
            AND role = 'co-president'
        )
    );

-- Policy: Co-presidents or announcement creator can UPDATE
DROP POLICY IF EXISTS "announcements_update_copresidents_or_creator" ON {schema}.announcements;
CREATE POLICY "announcements_update_copresidents_or_creator"
    ON {schema}.announcements FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM {schema}.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co-president' OR {schema}.announcements.created_by = users.id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM {schema}.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co-president' OR {schema}.announcements.created_by = users.id)
        )
    );

-- Policy: Co-presidents or announcement creator can DELETE
DROP POLICY IF EXISTS "announcements_delete_copresidents_or_creator" ON {schema}.announcements;
CREATE POLICY "announcements_delete_copresidents_or_creator"
    ON {schema}.announcements FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM {schema}.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co-president' OR {schema}.announcements.created_by = users.id)
        )
    );


-- ============================================================================
-- RLS Policies - Announcement Reads Table
-- ============================================================================

-- Policy: Users can mark announcements as read (insert their own read records)
DROP POLICY IF EXISTS "announcement_reads_insert_own" ON {schema}.announcement_reads;
CREATE POLICY "announcement_reads_insert_own"
    ON {schema}.announcement_reads FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id IN (
            SELECT id FROM {schema}.users WHERE user_id = auth.uid()
        )
    );

-- Policy: Users can only view their own read status
DROP POLICY IF EXISTS "announcement_reads_select_own" ON {schema}.announcement_reads;
CREATE POLICY "announcement_reads_select_own"
    ON {schema}.announcement_reads FOR SELECT
    TO authenticated
    USING (
        user_id IN (
            SELECT id FROM {schema}.users WHERE user_id = auth.uid()
        )
    );


-- ============================================================================
-- Grant Permissions
-- ============================================================================
-- (Assuming anon and authenticated roles exist in your Supabase setup)

-- For test schema
GRANT SELECT ON {schema}.announcements TO authenticated;
GRANT INSERT ON {schema}.announcements TO authenticated;
GRANT UPDATE ON {schema}.announcements TO authenticated;
GRANT DELETE ON {schema}.announcements TO authenticated;

GRANT INSERT ON {schema}.announcement_reads TO authenticated;
GRANT SELECT ON {schema}.announcement_reads TO authenticated;

-- Add service_role permissions (for background tasks)
GRANT ALL ON {schema}.announcements TO service_role;
GRANT ALL ON {schema}.announcement_reads TO service_role;

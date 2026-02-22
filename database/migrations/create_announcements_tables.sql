-- ============================================================================
-- Announcements System - Database Schema
-- ============================================================================
-- This migration creates the announcements and announcement_reads tables
-- for the UTESCA portal's announcement management system.
--
-- Environments: applied to both test and prod schemas
-- Depends on: auth.users table, test.users and prod.users tables with role column
-- ============================================================================

-- ============================================================================
-- Announcements Table - Test Schema
-- ============================================================================
-- Stores announcement records created by co-presidents/VPs
-- Row Level Security (RLS) policies control access

CREATE TABLE IF NOT EXISTS test.announcements (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    title text NOT NULL,
    content text NOT NULL,
    priority text NOT NULL CHECK (priority IN ('urgent', 'normal')),
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcements_pkey PRIMARY KEY (id),
    CONSTRAINT announcements_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES test.users (id) ON DELETE CASCADE
);

-- Indexes for common queries (test schema)
CREATE INDEX IF NOT EXISTS idx_test_announcements_created_by
    ON test.announcements USING btree (created_by);

CREATE INDEX IF NOT EXISTS idx_test_announcements_priority
    ON test.announcements USING btree (priority);

CREATE INDEX IF NOT EXISTS idx_test_announcements_created_at
    ON test.announcements USING btree (created_at DESC);

-- Trigger to auto-update updated_at timestamp (test schema)
CREATE TRIGGER update_announcements_updated_at
    BEFORE UPDATE ON test.announcements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Announcements Table - Prod Schema
-- ============================================================================

CREATE TABLE IF NOT EXISTS prod.announcements (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    title text NOT NULL,
    content text NOT NULL,
    priority text NOT NULL CHECK (priority IN ('urgent', 'normal')),
    created_by uuid NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcements_pkey PRIMARY KEY (id),
    CONSTRAINT announcements_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES auth.users (id) ON DELETE CASCADE
);

-- Indexes for common queries (prod schema)
CREATE INDEX IF NOT EXISTS idx_prod_announcements_created_by
    ON prod.announcements USING btree (created_by);

CREATE INDEX IF NOT EXISTS idx_prod_announcements_priority
    ON prod.announcements USING btree (priority);

CREATE INDEX IF NOT EXISTS idx_prod_announcements_created_at
    ON prod.announcements USING btree (created_at DESC);

-- Trigger to auto-update updated_at timestamp (prod schema)
CREATE TRIGGER update_announcements_updated_at
    BEFORE UPDATE ON prod.announcements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Announcement Reads Table - Test Schema
-- ============================================================================
-- Tracks which users have marked which announcements as read
-- Used for calculating read statistics and user read status

CREATE TABLE IF NOT EXISTS test.announcement_reads (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    announcement_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcement_reads_pkey PRIMARY KEY (id),
    CONSTRAINT announcement_reads_announcement_id_fkey
        FOREIGN KEY (announcement_id) REFERENCES test.announcements (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES test.users (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_unique UNIQUE (announcement_id, user_id)
);

-- Indexes for common queries (test schema)
CREATE INDEX IF NOT EXISTS idx_test_announcement_reads_announcement_id
    ON test.announcement_reads USING btree (announcement_id);

CREATE INDEX IF NOT EXISTS idx_test_announcement_reads_user_id
    ON test.announcement_reads USING btree (user_id);


-- ============================================================================
-- Announcement Reads Table - Prod Schema
-- ============================================================================

CREATE TABLE IF NOT EXISTS prod.announcement_reads (
    id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
    announcement_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT announcement_reads_pkey PRIMARY KEY (id),
    CONSTRAINT announcement_reads_announcement_id_fkey
        FOREIGN KEY (announcement_id) REFERENCES prod.announcements (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE,
    CONSTRAINT announcement_reads_unique UNIQUE (announcement_id, user_id)
);

-- Indexes for common queries (prod schema)
CREATE INDEX IF NOT EXISTS idx_prod_announcement_reads_announcement_id
    ON prod.announcement_reads USING btree (announcement_id);

CREATE INDEX IF NOT EXISTS idx_prod_announcement_reads_user_id
    ON prod.announcement_reads USING btree (user_id);


-- ============================================================================
-- Enable Row Level Security - Test Schema
-- ============================================================================

ALTER TABLE test.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE test.announcement_reads ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- Enable Row Level Security - Prod Schema
-- ============================================================================

ALTER TABLE prod.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE prod.announcement_reads ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- RLS Policies - Announcements Table (Test Schema)
-- ============================================================================

-- Policy: All authenticated users can SELECT (read) announcements
DROP POLICY IF EXISTS "announcements_select_authenticated" ON test.announcements;
CREATE POLICY "announcements_select_authenticated"
    ON test.announcements FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Co-presidents and VPs can INSERT announcements
DROP POLICY IF EXISTS "announcements_insert_copresidents" ON test.announcements;
CREATE POLICY "announcements_insert_copresidents"
    ON test.announcements FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM test.users
            WHERE user_id = auth.uid()
            AND role IN ('co_president', 'vp')
        )
    );

-- Policy: Co-presidents or announcement creator can UPDATE
DROP POLICY IF EXISTS "announcements_update_copresidents_or_creator" ON test.announcements;
CREATE POLICY "announcements_update_copresidents_or_creator"
    ON test.announcements FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM test.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR test.announcements.created_by = users.id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM test.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR test.announcements.created_by = users.id)
        )
    );

-- Policy: Co-presidents or announcement creator can DELETE
DROP POLICY IF EXISTS "announcements_delete_copresidents_or_creator" ON test.announcements;
CREATE POLICY "announcements_delete_copresidents_or_creator"
    ON test.announcements FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM test.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR test.announcements.created_by = users.id)
        )
    );


-- ============================================================================
-- RLS Policies - Announcements Table (Prod Schema)
-- ============================================================================

-- Policy: All authenticated users can SELECT (read) announcements
DROP POLICY IF EXISTS "announcements_select_authenticated" ON prod.announcements;
CREATE POLICY "announcements_select_authenticated"
    ON prod.announcements FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Co-presidents and VPs can INSERT announcements
DROP POLICY IF EXISTS "announcements_insert_copresidents" ON prod.announcements;
CREATE POLICY "announcements_insert_copresidents"
    ON prod.announcements FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM prod.users
            WHERE user_id = auth.uid()
            AND role IN ('co_president', 'vp')
        )
    );

-- Policy: Co-presidents or announcement creator can UPDATE
DROP POLICY IF EXISTS "announcements_update_copresidents_or_creator" ON prod.announcements;
CREATE POLICY "announcements_update_copresidents_or_creator"
    ON prod.announcements FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM prod.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR prod.announcements.created_by = users.id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM prod.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR prod.announcements.created_by = users.id)
        )
    );

-- Policy: Co-presidents or announcement creator can DELETE
DROP POLICY IF EXISTS "announcements_delete_copresidents_or_creator" ON prod.announcements;
CREATE POLICY "announcements_delete_copresidents_or_creator"
    ON prod.announcements FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM prod.users
            WHERE user_id = auth.uid()
            AND (users.role = 'co_president' OR prod.announcements.created_by = users.id)
        )
    );


-- ============================================================================
-- RLS Policies - Announcement Reads Table (Test Schema)
-- ============================================================================

-- Policy: Users can mark announcements as read (insert their own read records)
DROP POLICY IF EXISTS "announcement_reads_insert_own" ON test.announcement_reads;
CREATE POLICY "announcement_reads_insert_own"
    ON test.announcement_reads FOR INSERT
    TO authenticated
    WITH CHECK (
        user_id IN (
            SELECT id FROM test.users WHERE user_id = auth.uid()
        )
    );

-- Policy: Users can only view their own read status
DROP POLICY IF EXISTS "announcement_reads_select_own" ON test.announcement_reads;
CREATE POLICY "announcement_reads_select_own"
    ON test.announcement_reads FOR SELECT
    TO authenticated
    USING (
        user_id IN (
            SELECT id FROM test.users WHERE user_id = auth.uid()
        )
    );


-- ============================================================================
-- RLS Policies - Announcement Reads Table (Prod Schema)
-- ============================================================================

-- Policy: Users can mark announcements as read (insert their own read records)
DROP POLICY IF EXISTS "announcement_reads_insert_own" ON prod.announcement_reads;
CREATE POLICY "announcement_reads_insert_own"
    ON prod.announcement_reads FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can only view their own read status
DROP POLICY IF EXISTS "announcement_reads_select_own" ON prod.announcement_reads;
CREATE POLICY "announcement_reads_select_own"
    ON prod.announcement_reads FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());


-- ============================================================================
-- Grant Permissions - Test Schema
-- ============================================================================

GRANT SELECT ON test.announcements TO authenticated;
GRANT INSERT ON test.announcements TO authenticated;
GRANT UPDATE ON test.announcements TO authenticated;
GRANT DELETE ON test.announcements TO authenticated;

GRANT INSERT ON test.announcement_reads TO authenticated;
GRANT SELECT ON test.announcement_reads TO authenticated;

-- Add service_role permissions (for background tasks)
GRANT ALL ON test.announcements TO service_role;
GRANT ALL ON test.announcement_reads TO service_role;


-- ============================================================================
-- Grant Permissions - Prod Schema
-- ============================================================================

GRANT SELECT ON prod.announcements TO authenticated;
GRANT INSERT ON prod.announcements TO authenticated;
GRANT UPDATE ON prod.announcements TO authenticated;
GRANT DELETE ON prod.announcements TO authenticated;

GRANT INSERT ON prod.announcement_reads TO authenticated;
GRANT SELECT ON prod.announcement_reads TO authenticated;

-- Add service_role permissions (for background tasks)
GRANT ALL ON prod.announcements TO service_role;
GRANT ALL ON prod.announcement_reads TO service_role;

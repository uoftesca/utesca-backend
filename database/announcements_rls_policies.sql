-- ============================================================================
-- RLS Policies for Announcements
-- ============================================================================
-- This file contains Row Level Security policies for the announcements
-- and announcement_reads tables.
--
-- Requirements:
-- 1. Co-presidents can create/edit/delete announcements
-- 2. All authenticated users can read announcements
-- 3. Users can only mark their own announcements as read
-- ============================================================================

-- Oracle Virtual Private Database (VPD) Implementation
-- Using DBMS_RLS package for Row Level Security

-- ============================================================================
-- Announcements Table Policies
-- ============================================================================

-- Policy: All authenticated users can SELECT (read) announcements
BEGIN
  DBMS_RLS.add_policy(
    object_schema => 'PUBLIC',
    object_name => 'announcements',
    policy_name => 'announcements_select_authenticated',
    function_schema => 'PUBLIC',
    policy_function => 'announcements_select_auth_fn',
    statement_types => 'SELECT'
  );
END;
/

-- Policy: Co-presidents can INSERT announcements
CREATE POLICY "announcements_insert_copresidents"
ON announcements
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.role = 'co-president'
    )
);

-- Policy: Co-presidents can UPDATE any announcement, creators can update their own
CREATE POLICY "announcements_update_copresidents_or_creator"
ON announcements
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND (users.role = 'co-president' OR announcements.created_by = users.id)
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND (users.role = 'co-president' OR announcements.created_by = users.id)
    )
);

-- Policy: Co-presidents can DELETE any announcement, creators can delete their own
CREATE POLICY "announcements_delete_copresidents_or_creator"
ON announcements
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND (users.role = 'co-president' OR announcements.created_by = users.id)
    )
);

-- ============================================================================
-- Announcement Reads Table Policies
-- ============================================================================

-- Policy: Users can SELECT their own read records
CREATE POLICY "announcement_reads_select_own"
ON announcement_reads
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- Policy: Users can INSERT their own read records
CREATE POLICY "announcement_reads_insert_own"
ON announcement_reads
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- Policy: Users cannot UPDATE read records (read_at is set once)
-- No UPDATE policy = no updates allowed

-- Policy: Users can DELETE their own read records (if needed)
CREATE POLICY "announcement_reads_delete_own"
ON announcement_reads
FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- ============================================================================
-- Notes:
-- ============================================================================
-- 1. auth.uid() returns the authenticated user's UUID from JWT token
-- 2. Co-presidents are identified by users.role = 'co-president'
-- 3. Creators are identified by announcements.created_by matching users.id
-- 4. All policies require authentication (TO authenticated)
-- 5. announcement_reads has no UPDATE policy - reads are immutable once created
-- ============================================================================

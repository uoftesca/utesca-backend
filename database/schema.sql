-- ============================================================================
-- UTESCA Portal Database Schema
-- ============================================================================
-- This schema uses PostgreSQL schemas (namespaces) to separate test and prod data
-- in a single Supabase database
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CREATE SCHEMAS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS test;
CREATE SCHEMA IF NOT EXISTS prod;

-- ============================================================================
-- ENUMS (in public schema, shared across test and prod)
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('co_president', 'vp', 'director');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE event_status AS ENUM ('draft', 'pending_approval', 'published');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE announcement_priority AS ENUM ('normal', 'urgent');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE application_status AS ENUM ('new', 'under_review', 'accepted', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE email_notification_preference AS ENUM ('all', 'urgent_only', 'none');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- HELPER FUNCTION TO CREATE TABLES IN BOTH SCHEMAS
-- ============================================================================

DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY['test', 'prod']) LOOP

        -- ========================================================================
        -- TABLES
        -- ========================================================================

        -- Departments Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.departments (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )', schema_name);

        -- Users Table (extends Supabase Auth)
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                role user_role NOT NULL,
                department_id UUID REFERENCES %I.departments(id) ON DELETE SET NULL,
                preferred_name VARCHAR(255),
                photo_base64 TEXT,
                announcement_email_preference email_notification_preference DEFAULT ''all'',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )', schema_name, schema_name);

        -- Events Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.events (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                date_time TIMESTAMPTZ NOT NULL,
                location VARCHAR(255),
                registration_deadline TIMESTAMPTZ,
                status event_status DEFAULT ''draft'',
                created_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                registration_form_schema JSONB,
                max_capacity INTEGER,
                thumbnail_url TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                approved_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                approved_at TIMESTAMPTZ
            )', schema_name, schema_name, schema_name);

        -- Event Revisions Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.event_revisions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_id UUID REFERENCES %I.events(id) ON DELETE CASCADE NOT NULL,
                title VARCHAR(255),
                description TEXT,
                date_time TIMESTAMPTZ,
                location VARCHAR(255),
                registration_deadline TIMESTAMPTZ,
                registration_form_schema JSONB,
                max_capacity INTEGER,
                thumbnail_url TEXT,
                status event_status DEFAULT ''pending_approval'',
                created_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                approved_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                approved_at TIMESTAMPTZ,
                rejected_reason TEXT
            )', schema_name, schema_name, schema_name, schema_name);

        -- Event Registrations Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.event_registrations (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_id UUID REFERENCES %I.events(id) ON DELETE CASCADE NOT NULL,
                user_email VARCHAR(255) NOT NULL,
                user_name VARCHAR(255) NOT NULL,
                form_responses JSONB,
                registered_at TIMESTAMPTZ DEFAULT NOW(),
                attended BOOLEAN DEFAULT FALSE,
                UNIQUE(event_id, user_email)
            )', schema_name, schema_name);

        -- Event Photos Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.event_photos (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_id UUID REFERENCES %I.events(id) ON DELETE CASCADE NOT NULL,
                album_thumbnail_base64 TEXT,
                photo_url TEXT NOT NULL,
                uploaded_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                uploaded_at TIMESTAMPTZ DEFAULT NOW()
            )', schema_name, schema_name, schema_name);

        -- Announcements Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.announcements (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                priority announcement_priority DEFAULT ''normal'',
                created_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )', schema_name, schema_name);

        -- Announcement Reads Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.announcement_reads (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                announcement_id UUID REFERENCES %I.announcements(id) ON DELETE CASCADE NOT NULL,
                user_id UUID REFERENCES %I.users(id) ON DELETE CASCADE NOT NULL,
                read_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(announcement_id, user_id)
            )', schema_name, schema_name, schema_name);

        -- Application Cycles Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.application_cycles (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(255) NOT NULL,
                role_description TEXT,
                start_date TIMESTAMPTZ NOT NULL,
                end_date TIMESTAMPTZ NOT NULL,
                additional_info_schema JSONB,
                created_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )', schema_name, schema_name);

        -- Applications Table
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I.applications (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                application_cycle_id UUID REFERENCES %I.application_cycles(id) ON DELETE CASCADE NOT NULL,
                applicant_name VARCHAR(255) NOT NULL,
                applicant_email VARCHAR(255) NOT NULL,
                position_applied VARCHAR(255) NOT NULL,
                department_id UUID REFERENCES %I.departments(id) ON DELETE SET NULL,
                resume_url TEXT,
                additional_info JSONB,
                status application_status DEFAULT ''new'',
                submitted_at TIMESTAMPTZ DEFAULT NOW(),
                reviewed_by UUID REFERENCES %I.users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMPTZ
            )', schema_name, schema_name, schema_name, schema_name);

        -- ========================================================================
        -- INDEXES FOR PERFORMANCE
        -- ========================================================================

        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_users_role ON %I.users(role)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_users_department ON %I.users(department_id)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_events_status ON %I.events(status)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_events_created_by ON %I.events(created_by)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_events_date_time ON %I.events(date_time)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_event_revisions_event ON %I.event_revisions(event_id)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_event_revisions_status ON %I.event_revisions(status)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_event_registrations_event ON %I.event_registrations(event_id)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_event_registrations_email ON %I.event_registrations(user_email)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_announcements_created_at ON %I.announcements(created_at DESC)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_applications_status ON %I.applications(status)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_applications_cycle ON %I.applications(application_cycle_id)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_applications_department ON %I.applications(department_id)', schema_name, schema_name);

    END LOOP;
END $$;

-- ============================================================================
-- UPDATED_AT TRIGGER FUNCTION (shared in public schema)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at in both schemas
DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY['test', 'prod']) LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_users_updated_at ON %I.users;
            CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON %I.users
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        ', schema_name, schema_name);

        EXECUTE format('
            DROP TRIGGER IF EXISTS update_events_updated_at ON %I.events;
            CREATE TRIGGER update_events_updated_at
                BEFORE UPDATE ON %I.events
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        ', schema_name, schema_name);
    END LOOP;
END $$;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY['test', 'prod']) LOOP

        -- Enable RLS on all tables
        EXECUTE format('ALTER TABLE %I.users ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.departments ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.events ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.event_revisions ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.event_registrations ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.event_photos ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.announcements ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.announcement_reads ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.application_cycles ENABLE ROW LEVEL SECURITY', schema_name);
        EXECUTE format('ALTER TABLE %I.applications ENABLE ROW LEVEL SECURITY', schema_name);

        -- ====================================================================
        -- USERS TABLE POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can read all profiles" ON %I.users;
            CREATE POLICY "Users can read all profiles"
                ON %I.users FOR SELECT
                TO authenticated
                USING (true)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can update own profile" ON %I.users;
            CREATE POLICY "Users can update own profile"
                ON %I.users FOR UPDATE
                TO authenticated
                USING (auth.uid() = user_id)
                WITH CHECK (auth.uid() = user_id)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can update team profiles" ON %I.users;
            CREATE POLICY "VPs can update team profiles"
                ON %I.users FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users AS vp
                        WHERE vp.user_id = auth.uid()
                        AND vp.role = ''vp''
                        AND vp.department_id = %I.users.department_id
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can update all profiles" ON %I.users;
            CREATE POLICY "Co-presidents can update all profiles"
                ON %I.users FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- DEPARTMENTS TABLE POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Anyone can read departments" ON %I.departments;
            CREATE POLICY "Anyone can read departments"
                ON %I.departments FOR SELECT
                TO authenticated
                USING (true)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can manage departments" ON %I.departments;
            CREATE POLICY "Co-presidents can manage departments"
                ON %I.departments FOR ALL
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- EVENTS TABLE POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can read published events" ON %I.events;
            CREATE POLICY "Users can read published events"
                ON %I.events FOR SELECT
                TO authenticated
                USING (status = ''published'')
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can read own events" ON %I.events;
            CREATE POLICY "Users can read own events"
                ON %I.events FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND %I.users.id = %I.events.created_by
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can read all events" ON %I.events;
            CREATE POLICY "Co-presidents can read all events"
                ON %I.events FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can create events" ON %I.events;
            CREATE POLICY "VPs can create events"
                ON %I.events FOR INSERT
                TO authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND (role = ''vp'' OR role = ''co_president'')
                    )
                )
        ', schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Creators can update own events" ON %I.events;
            CREATE POLICY "Creators can update own events"
                ON %I.events FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND %I.users.id = %I.events.created_by
                        AND %I.events.status != ''published''
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can manage all events" ON %I.events;
            CREATE POLICY "Co-presidents can manage all events"
                ON %I.events FOR ALL
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- EVENT REVISIONS TABLE POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Creators can read own event revisions" ON %I.event_revisions;
            CREATE POLICY "Creators can read own event revisions"
                ON %I.event_revisions FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND %I.users.id = %I.event_revisions.created_by
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can read all revisions" ON %I.event_revisions;
            CREATE POLICY "Co-presidents can read all revisions"
                ON %I.event_revisions FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can create event revisions" ON %I.event_revisions;
            CREATE POLICY "VPs can create event revisions"
                ON %I.event_revisions FOR INSERT
                TO authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        JOIN %I.events ON %I.events.created_by = %I.users.id
                        WHERE user_id = auth.uid()
                        AND %I.events.id = %I.event_revisions.event_id
                        AND (role = ''vp'' OR role = ''co_president'')
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can manage revisions" ON %I.event_revisions;
            CREATE POLICY "Co-presidents can manage revisions"
                ON %I.event_revisions FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- EVENT REGISTRATIONS POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Anyone can register for events" ON %I.event_registrations;
            CREATE POLICY "Anyone can register for events"
                ON %I.event_registrations FOR INSERT
                TO anon, authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.events
                        WHERE %I.events.id = %I.event_registrations.event_id
                        AND %I.events.status = ''published''
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Event creators can view registrations" ON %I.event_registrations;
            CREATE POLICY "Event creators can view registrations"
                ON %I.event_registrations FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.events
                        JOIN %I.users ON %I.users.id = %I.events.created_by
                        WHERE %I.events.id = %I.event_registrations.event_id
                        AND (%I.users.user_id = auth.uid() OR %I.users.role = ''co_president'')
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can update registrations" ON %I.event_registrations;
            CREATE POLICY "VPs can update registrations"
                ON %I.event_registrations FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND (role = ''vp'' OR role = ''co_president'')
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- EVENT PHOTOS POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can view event photos" ON %I.event_photos;
            CREATE POLICY "Users can view event photos"
                ON %I.event_photos FOR SELECT
                TO authenticated, anon
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.events
                        WHERE %I.events.id = %I.event_photos.event_id
                        AND %I.events.status = ''published''
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can upload photos" ON %I.event_photos;
            CREATE POLICY "VPs can upload photos"
                ON %I.event_photos FOR INSERT
                TO authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND (role = ''vp'' OR role = ''co_president'')
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- ANNOUNCEMENTS POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can read announcements" ON %I.announcements;
            CREATE POLICY "Users can read announcements"
                ON %I.announcements FOR SELECT
                TO authenticated
                USING (true)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can create announcements" ON %I.announcements;
            CREATE POLICY "Co-presidents can create announcements"
                ON %I.announcements FOR INSERT
                TO authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- ANNOUNCEMENT READS POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can read own read receipts" ON %I.announcement_reads;
            CREATE POLICY "Users can read own read receipts"
                ON %I.announcement_reads FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND %I.users.id = %I.announcement_reads.user_id
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Users can mark announcements read" ON %I.announcement_reads;
            CREATE POLICY "Users can mark announcements read"
                ON %I.announcement_reads FOR INSERT
                TO authenticated
                WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND %I.users.id = %I.announcement_reads.user_id
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can view all read receipts" ON %I.announcement_reads;
            CREATE POLICY "Co-presidents can view all read receipts"
                ON %I.announcement_reads FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        -- ====================================================================
        -- APPLICATIONS POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Anyone can submit applications" ON %I.applications;
            CREATE POLICY "Anyone can submit applications"
                ON %I.applications FOR INSERT
                TO anon, authenticated
                WITH CHECK (true)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can view all applications" ON %I.applications;
            CREATE POLICY "Co-presidents can view all applications"
                ON %I.applications FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "VPs can view department applications" ON %I.applications;
            CREATE POLICY "VPs can view department applications"
                ON %I.applications FOR SELECT
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''vp''
                        AND %I.users.department_id = %I.applications.department_id
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can update applications" ON %I.applications;
            CREATE POLICY "Co-presidents can update applications"
                ON %I.applications FOR UPDATE
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND (
                            role = ''co_president''
                            OR (role = ''vp'' AND %I.users.department_id = %I.applications.department_id)
                        )
                    )
                )
        ', schema_name, schema_name, schema_name, schema_name, schema_name);

        -- ====================================================================
        -- APPLICATION CYCLES POLICIES
        -- ====================================================================

        EXECUTE format('
            DROP POLICY IF EXISTS "Anyone can read application cycles" ON %I.application_cycles;
            CREATE POLICY "Anyone can read application cycles"
                ON %I.application_cycles FOR SELECT
                TO authenticated, anon
                USING (true)
        ', schema_name, schema_name);

        EXECUTE format('
            DROP POLICY IF EXISTS "Co-presidents can manage cycles" ON %I.application_cycles;
            CREATE POLICY "Co-presidents can manage cycles"
                ON %I.application_cycles FOR ALL
                TO authenticated
                USING (
                    EXISTS (
                        SELECT 1 FROM %I.users
                        WHERE user_id = auth.uid()
                        AND role = ''co_president''
                    )
                )
        ', schema_name, schema_name, schema_name);

    END LOOP;
END $$;

-- ============================================================================
-- SEED DATA - DEPARTMENTS (in both schemas)
-- ============================================================================

DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY['test', 'prod']) LOOP
        EXECUTE format('
            INSERT INTO %I.departments (name) VALUES
                (''Marketing''),
                (''Events''),
                (''Outreach''),
                (''CEP''),
                (''O&IA''),
                (''Web''),
                (''Finance'')
            ON CONFLICT (name) DO NOTHING
        ', schema_name);
    END LOOP;
END $$;

-- ============================================================================
-- NOTES
-- ============================================================================
--
-- Schema-based Environment Separation:
-- - This uses PostgreSQL schemas (namespaces) to separate test and prod data
-- - Both schemas exist in the same Supabase database
-- - Your FastAPI app will set the search_path based on ENVIRONMENT variable
--   - ENVIRONMENT=test → SET search_path TO test, public
--   - ENVIRONMENT=production → SET search_path TO prod, public
--
-- Event Revision Workflow:
-- 1. VP edits a published event → creates a new record in event_revisions
-- 2. Original event stays published and unchanged
-- 3. Co-president reviews revision → approves or rejects
-- 4. On approval: Apply changes from event_revisions to events table
-- 5. On rejection: Delete or mark revision with rejection reason
--
-- Base64 Image Handling:
-- - Frontend converts images to base64 using FileReader API
-- - Keep images small (profile: ~200x200px, thumbnails: ~300x200px)
-- - Store directly in photo_base64 and album_thumbnail_base64 columns
--
-- To set up:
-- 1. Create ONE Supabase project
-- 2. Run this schema in the SQL editor
-- 3. Configure environment variables in your FastAPI app:
--    - ENVIRONMENT=test or ENVIRONMENT=production
--    - SUPABASE_URL (same for both environments)
--    - SUPABASE_KEY (same for both environments)
-- 4. The FastAPI config will set search_path based on ENVIRONMENT
--
-- Remember to:
-- - Set up Supabase Auth
-- - Configure email templates for auth and notifications
-- - Set up storage buckets if using Supabase Storage instead of Google APIs
-- ============================================================================

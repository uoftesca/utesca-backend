SET local check_function_bodies = off;

CREATE SCHEMA "prod";

CREATE SCHEMA "security";

CREATE SCHEMA "test";

CREATE TABLE "prod"."announcement_reads" (
  "id"              uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "announcement_id" uuid                     NOT NULL,
  "user_id"         uuid                     NOT NULL,
  "read_at"         timestamp with time zone DEFAULT now(),
  CONSTRAINT "announcement_reads_announcement_id_user_id_key" UNIQUE (announcement_id, user_id),
  CONSTRAINT "announcement_reads_pkey" PRIMARY KEY (id)
);

ALTER TABLE "prod"."announcement_reads"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."announcements" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "title"      character varying(255)   NOT NULL,
  "content"    text                     NOT NULL,
  "created_by" uuid,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "announcements_pkey" PRIMARY KEY (id)
);

ALTER TABLE "prod"."announcements"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."departments" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "name"       character varying(100)   NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  "year"       smallint                 NOT NULL DEFAULT '2026'::smallint,
  CONSTRAINT "departments_name_key" UNIQUE (name),
  CONSTRAINT "departments_pkey" PRIMARY KEY (id),
  CONSTRAINT "departments_year_check" CHECK ((year >= 2025))
);

ALTER TABLE "prod"."departments"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."event_registrations" (
  "id"                 uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "event_id"           uuid                     NOT NULL,
  "form_data"          jsonb                    NOT NULL,
  "submitted_at"       timestamp with time zone NOT NULL DEFAULT now(),
  "reviewed_by"        uuid,
  "reviewed_at"        timestamp with time zone,
  "confirmed_at"       timestamp with time zone,
  "checked_in"         boolean                  NOT NULL DEFAULT false,
  "checked_in_at"      timestamp with time zone,
  "checked_in_by"      uuid,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  "updated_at"         timestamp with time zone NOT NULL DEFAULT now(),
  "email"              text,
  "verification_token" uuid,
  "management_token"   uuid,
  "rsvp_token"         uuid,
  "ticket_token"       uuid,
  CONSTRAINT "event_registrations_pkey" PRIMARY KEY (id)
);

ALTER TABLE "prod"."event_registrations"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."events" (
  "id"                        uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "title"                     character varying(255)   NOT NULL,
  "description"               text,
  "date_time"                 timestamp with time zone NOT NULL,
  "location"                  character varying(255),
  "registration_deadline"     timestamp with time zone,
  "created_by"                uuid,
  "registration_form_schema"  jsonb,
  "max_capacity"              integer,
  "created_at"                timestamp with time zone DEFAULT now(),
  "updated_at"                timestamp with time zone DEFAULT now(),
  "category"                  text,
  "image_position"            text,
  "album_link"                text,
  "registration_link"         text,
  "image_url"                 text,
  "slug"                      text                     NOT NULL,
  "acceptance_email_template" jsonb,
  "rejection_email_template"  jsonb,
  CONSTRAINT "events_pkey" PRIMARY KEY (id)
);

ALTER TABLE "prod"."events"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."registration_files" (
  "id"                      uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "registration_id"         uuid,
  "event_id"                uuid                     NOT NULL,
  "field_name"              text                     NOT NULL,
  "file_url"                text                     NOT NULL,
  "file_name"               text                     NOT NULL,
  "file_size"               integer                  NOT NULL,
  "mime_type"               text                     NOT NULL,
  "upload_session_id"       text                     NOT NULL,
  "uploaded_at"             timestamp with time zone NOT NULL DEFAULT now(),
  "scheduled_deletion_date" date,
  "deleted"                 boolean                  NOT NULL DEFAULT false,
  "deleted_at"              timestamp with time zone,
  CONSTRAINT "registration_files_pkey" PRIMARY KEY (id)
);

ALTER TABLE "prod"."registration_files"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."tokens" (
  "id"                 uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "type"               text                     NOT NULL,
  "token_hash"         text                     NOT NULL,
  "expires_at"         timestamp with time zone NOT NULL,
  "used_at"            timestamp with time zone,
  "revoked_at"         timestamp with time zone,
  "revoked_reason"     text,
  "last_verified_at"   timestamp with time zone,
  "verification_count" integer                  NOT NULL DEFAULT 0,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "tokens_expiration_check" CHECK ((expires_at > created_at)),
  CONSTRAINT "tokens_hash_not_empty" CHECK ((length(token_hash) > 0)),
  CONSTRAINT "tokens_hash_unique" UNIQUE (token_hash),
  CONSTRAINT "tokens_pkey" PRIMARY KEY (id),
  CONSTRAINT "tokens_verification_count_check" CHECK ((verification_count >= 0))
);

ALTER TABLE "prod"."tokens"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "prod"."users" (
  "id"                       uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"                  uuid                     NOT NULL,
  "email"                    character varying(255)   NOT NULL,
  "department_id"            uuid,
  "preferred_name"           character varying(255),
  "photo_url"                text,
  "created_at"               timestamp with time zone DEFAULT now(),
  "updated_at"               timestamp with time zone DEFAULT now(),
  "first_name"               text,
  "last_name"                text,
  "display_role"             text,
  "invited_by"               uuid,
  "linkedin_url"             text                     DEFAULT ''::text,
  "notification_preferences" jsonb                    NOT NULL,
  CONSTRAINT "notification_preferences_valid"
    CHECK
    (((notification_preferences ? 'announcements'::text) AND (notification_preferences ? 'rsvp_changes'::text) AND (notification_preferences ? 'new_application_submitted'::text))),
  CONSTRAINT "users_email_key" UNIQUE (email),
  CONSTRAINT "users_pkey" PRIMARY KEY (id),
  CONSTRAINT "users_user_id_key" UNIQUE (user_id)
);

ALTER TABLE "prod"."users"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."announcement_reads" (
  "id"              uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "announcement_id" uuid                     NOT NULL,
  "user_id"         uuid                     NOT NULL,
  "read_at"         timestamp with time zone DEFAULT now(),
  CONSTRAINT "announcement_reads_announcement_id_user_id_key" UNIQUE (announcement_id, user_id),
  CONSTRAINT "announcement_reads_pkey" PRIMARY KEY (id)
);

ALTER TABLE "test"."announcement_reads"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."announcements" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "title"      character varying(255)   NOT NULL,
  "content"    text                     NOT NULL,
  "created_by" uuid,
  "created_at" timestamp with time zone DEFAULT now(),
  CONSTRAINT "announcements_pkey" PRIMARY KEY (id)
);

ALTER TABLE "test"."announcements"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."departments" (
  "id"         uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "name"       character varying(100)   NOT NULL,
  "created_at" timestamp with time zone DEFAULT now(),
  "year"       smallint                 NOT NULL DEFAULT '2026'::smallint,
  CONSTRAINT "departments_pkey" PRIMARY KEY (id),
  CONSTRAINT "departments_year_check" CHECK ((year >= 2025))
);

ALTER TABLE "test"."departments"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."event_registrations" (
  "id"                 uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "event_id"           uuid                     NOT NULL,
  "submitted_at"       timestamp with time zone NOT NULL DEFAULT now(),
  "reviewed_by"        uuid,
  "reviewed_at"        timestamp with time zone,
  "confirmed_at"       timestamp with time zone,
  "checked_in"         boolean                  NOT NULL DEFAULT false,
  "checked_in_at"      timestamp with time zone,
  "checked_in_by"      uuid,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  "updated_at"         timestamp with time zone NOT NULL DEFAULT now(),
  "form_data"          jsonb                    NOT NULL,
  "email"              text,
  "verification_token" uuid,
  "management_token"   uuid,
  "rsvp_token"         uuid,
  "ticket_token"       uuid,
  CONSTRAINT "event_registrations_pkey" PRIMARY KEY (id)
);

ALTER TABLE "test"."event_registrations"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."events" (
  "id"                        uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "title"                     text                     NOT NULL,
  "description"               text,
  "date_time"                 timestamp with time zone NOT NULL,
  "location"                  text,
  "registration_deadline"     timestamp with time zone,
  "created_by"                uuid,
  "registration_form_schema"  jsonb,
  "max_capacity"              integer,
  "image_url"                 text,
  "created_at"                timestamp with time zone DEFAULT now(),
  "updated_at"                timestamp with time zone DEFAULT now(),
  "category"                  text,
  "image_position"            text,
  "album_link"                text,
  "registration_link"         text,
  "slug"                      text                     NOT NULL,
  "acceptance_email_template" jsonb,
  "rejection_email_template"  jsonb,
  CONSTRAINT "events_pkey" PRIMARY KEY (id)
);

ALTER TABLE "test"."events"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."registration_files" (
  "id"                      uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "registration_id"         uuid,
  "event_id"                uuid                     NOT NULL,
  "field_name"              text                     NOT NULL,
  "file_url"                text                     NOT NULL,
  "file_name"               text                     NOT NULL,
  "file_size"               integer                  NOT NULL,
  "mime_type"               text                     NOT NULL,
  "upload_session_id"       text                     NOT NULL,
  "uploaded_at"             timestamp with time zone NOT NULL DEFAULT now(),
  "scheduled_deletion_date" date,
  "deleted"                 boolean                  NOT NULL DEFAULT false,
  "deleted_at"              timestamp with time zone,
  CONSTRAINT "registration_files_pkey" PRIMARY KEY (id)
);

ALTER TABLE "test"."registration_files"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."tokens" (
  "id"                 uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "type"               text                     NOT NULL,
  "token_hash"         text                     NOT NULL,
  "expires_at"         timestamp with time zone NOT NULL,
  "used_at"            timestamp with time zone,
  "revoked_at"         timestamp with time zone,
  "revoked_reason"     text,
  "last_verified_at"   timestamp with time zone,
  "verification_count" integer                  NOT NULL DEFAULT 0,
  "created_at"         timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "registration_tokens_expiration_check" CHECK ((expires_at > created_at)),
  CONSTRAINT "registration_tokens_hash_not_empty" CHECK ((length(token_hash) > 0)),
  CONSTRAINT "registration_tokens_hash_unique" UNIQUE (token_hash),
  CONSTRAINT "registration_tokens_pkey" PRIMARY KEY (id),
  CONSTRAINT "registration_tokens_verification_count_check" CHECK ((verification_count >= 0)),
  CONSTRAINT "tokens_expiration_check" CHECK ((expires_at > created_at))
);

ALTER TABLE "test"."tokens"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "test"."users" (
  "id"                       uuid                     NOT NULL DEFAULT extensions.uuid_generate_v4(),
  "user_id"                  uuid                     NOT NULL,
  "email"                    character varying(255)   NOT NULL,
  "department_id"            uuid,
  "preferred_name"           character varying(255),
  "photo_url"                text,
  "created_at"               timestamp with time zone DEFAULT now(),
  "updated_at"               timestamp with time zone DEFAULT now(),
  "display_role"             text,
  "first_name"               text,
  "last_name"                text,
  "invited_by"               uuid,
  "linkedin_url"             text,
  "notification_preferences" jsonb                    NOT NULL,
  CONSTRAINT "notification_preferences_valid"
    CHECK
    (((notification_preferences ? 'announcements'::text) AND (notification_preferences ? 'rsvp_changes'::text) AND (notification_preferences ? 'new_application_submitted'::text))),
  CONSTRAINT "users_email_key" UNIQUE (email),
  CONSTRAINT "users_pkey" PRIMARY KEY (id),
  CONSTRAINT "users_user_id_key" UNIQUE (user_id)
);

ALTER TABLE "test"."users"
  ENABLE ROW LEVEL SECURITY;

CREATE TYPE "public"."announcement_priority" AS ENUM (
  'normal',
  'urgent'
);

ALTER TABLE "prod"."announcements"
  ADD COLUMN "priority" public.announcement_priority DEFAULT 'normal'::public.announcement_priority;

ALTER TABLE "test"."announcements"
  ADD COLUMN "priority" public.announcement_priority DEFAULT 'normal'::public.announcement_priority;

CREATE TYPE "public"."application_status" AS ENUM (
  'new',
  'under_review',
  'accepted',
  'rejected'
);

CREATE TYPE "public"."email_notification_preference" AS ENUM (
  'all',
  'urgent_only',
  'none'
);

CREATE TYPE "public"."event_status" AS ENUM (
  'draft',
  'pending_approval',
  'published',
  'sent_back'
);

ALTER TABLE "prod"."events"
  ADD COLUMN "status" public.event_status DEFAULT 'draft'::public.event_status;

ALTER TABLE "test"."events"
  ADD COLUMN "status" public.event_status DEFAULT 'draft'::public.event_status;

CREATE TYPE "public"."registration_mode" AS ENUM (
  'automatic',
  'manual'
);

ALTER TABLE "test"."events"
  ADD COLUMN "registration_mode" public.registration_mode NOT NULL DEFAULT 'manual'::public.registration_mode;

CREATE TYPE "public"."registration_status" AS ENUM (
  'pending_verification',
  'submitted',
  'withdrawn',
  'accepted',
  'rejected',
  'confirmed',
  'not_attending',
  'waitlist'
);

ALTER TABLE "prod"."event_registrations"
  ADD COLUMN "status" public.registration_status NOT NULL DEFAULT 'pending_verification'::public.registration_status;

ALTER TABLE "test"."event_registrations"
  ADD COLUMN "status" public.registration_status NOT NULL DEFAULT 'pending_verification'::public.registration_status;

CREATE TYPE "public"."user_role" AS ENUM (
  'co_president',
  'vp',
  'director'
);

ALTER TABLE "prod"."users"
  ADD COLUMN "role" public.user_role NOT NULL;

ALTER TABLE "test"."users"
  ADD COLUMN "role" public.user_role NOT NULL;

CREATE OR REPLACE FUNCTION prod.accept_event_registration (
  p_registration_id uuid,
  p_reviewer_id     uuid,
  p_rsvp_token_hash text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_token prod.tokens%ROWTYPE;
    v_rsvp_expires_at timestamptz;
    v_attendee_count integer;
BEGIN
    IF p_rsvp_token_hash IS NULL OR btrim(p_rsvp_token_hash) = '' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'submitted' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    v_rsvp_expires_at := v_event.date_time - interval '24 hours';
    IF v_rsvp_expires_at <= v_now THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM prod.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed');

        IF v_attendee_count >= v_event.max_capacity THEN
            RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
        END IF;
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('rsvp', p_rsvp_token_hash, v_rsvp_expires_at)
    RETURNING * INTO v_token;

    UPDATE prod.event_registrations
    SET status = 'accepted'::public.registration_status,
        rsvp_token = v_token.id,
        reviewed_by = p_reviewer_id,
        reviewed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'token', to_jsonb(v_token)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION prod.check_in_event_registration (
  p_registration_id   uuid,
  p_ticket_token_hash text,
  p_checked_in_by     uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_registration prod.event_registrations%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'confirmed'
       OR v_registration.ticket_token IS NULL
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = ''
       OR p_checked_in_by IS NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_ticket_token
    FROM prod.tokens
    WHERE id = v_registration.ticket_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_ticket_token.type <> 'ticket'
       OR v_ticket_token.token_hash <> p_ticket_token_hash
       OR v_ticket_token.expires_at <= v_now
       OR v_ticket_token.used_at IS NOT NULL
       OR v_ticket_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    UPDATE prod.tokens SET used_at = v_now WHERE id = v_ticket_token.id;

    UPDATE prod.event_registrations
    SET checked_in = true,
        checked_in_at = v_now,
        checked_in_by = p_checked_in_by,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$function$;

CREATE OR REPLACE FUNCTION prod.confirm_event_rsvp (
  p_registration_id       uuid,
  p_rsvp_token_hash       text,
  p_management_token_hash text,
  p_ticket_token_hash     text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_rsvp_token prod.tokens%ROWTYPE;
    v_old_management_token prod.tokens%ROWTYPE;
    v_new_management_token prod.tokens%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM prod.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM prod.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_new_management_token;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
    RETURNING * INTO v_ticket_token;

    UPDATE prod.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE prod.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION prod.confirm_event_rsvp (
  p_registration_id         uuid,
  p_rsvp_token_hash         text,
  p_management_token_hash   text,
  p_ticket_token_hash       text,
  p_management_before_hours integer,
  p_ticket_after_hours      integer
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_rsvp_token prod.tokens%ROWTYPE;
    v_old_management_token prod.tokens%ROWTYPE;
    v_new_management_token prod.tokens%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM prod.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM prod.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time - make_interval(hours => p_management_before_hours))
    RETURNING * INTO v_new_management_token;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time + make_interval(hours => p_ticket_after_hours))
    RETURNING * INTO v_ticket_token;

    UPDATE prod.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE prod.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION prod.create_pending_event_registration (
  p_event_id          uuid,
  p_form_data         jsonb,
  p_email             text,
  p_upload_session_id text,
  p_token_hash        text,
  p_token_expires_at  timestamp with time zone
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_event prod.events%ROWTYPE;
    v_token prod.tokens%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
BEGIN
    IF p_email IS NULL
       OR btrim(p_email) = ''
       OR p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_token_expires_at IS NULL
       OR p_token_expires_at <= now() THEN
        RAISE EXCEPTION 'invalid registration verification data' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = p_event_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'event not found' USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('verification', p_token_hash, p_token_expires_at)
    RETURNING * INTO v_token;

    INSERT INTO prod.event_registrations (
        event_id,
        form_data,
        email,
        status,
        verification_token
    )
    VALUES (
        p_event_id,
        p_form_data,
        btrim(p_email),
        'pending_verification'::public.registration_status,
        v_token.id
    )
    RETURNING * INTO v_registration;

    UPDATE prod.registration_files
    SET registration_id = v_registration.id,
        scheduled_deletion_date = v_event.date_time::date + 30
    WHERE upload_session_id = p_upload_session_id
      AND event_id = p_event_id
      AND registration_id IS NULL;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'token', to_jsonb(v_token)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION prod.decline_event_rsvp (
  p_registration_id uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
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
$function$;

CREATE OR REPLACE FUNCTION prod.generate_event_slug (
  event_title text
)
  RETURNS text
  LANGUAGE plpgsql
  AS $function$
DECLARE
  base_slug TEXT;
  final_slug TEXT;
  counter INTEGER := 0;
BEGIN
  base_slug := LOWER(
    TRIM(BOTH '-' FROM
      REGEXP_REPLACE(
        REGEXP_REPLACE(event_title, '[^a-zA-Z0-9]+', '-', 'g'),
        '-+', '-', 'g'
      )
    )
  );
  
  final_slug := base_slug;
  
  WHILE EXISTS (SELECT 1 FROM prod.events WHERE slug = final_slug) LOOP
    counter := counter + 1;
    final_slug := base_slug || '-' || counter;
  END LOOP;
  
  RETURN final_slug;
END;
$function$;

CREATE OR REPLACE FUNCTION prod.get_event_registration_stats (
  p_event_id uuid
)
  RETURNS TABLE (
    total_registrations bigint,
    submitted_count     bigint,
    accepted_count      bigint,
    rejected_count      bigint,
    confirmed_count     bigint,
    checked_in_count    bigint,
    approval_rate       numeric,
    attendance_rate     numeric
  )
  LANGUAGE plpgsql
  AS $function$BEGIN
  RETURN QUERY
  WITH stats AS (
    SELECT
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE event_registrations.status = 'submitted'::registration_status) as submitted,
      COUNT(*) FILTER (WHERE event_registrations.status = 'accepted'::registration_status) as accepted,
      COUNT(*) FILTER (WHERE event_registrations.status = 'rejected'::registration_status) as rejected,
      COUNT(*) FILTER (WHERE event_registrations.status = 'confirmed'::registration_status) as confirmed,
      COUNT(*) FILTER (WHERE event_registrations.status = 'waitlist'::registration_status) as waitlist,
      COUNT(*) FILTER (WHERE checked_in = true) as checked_in
    FROM prod.event_registrations
    WHERE event_registrations.event_id = p_event_id
  )
  SELECT
    total,
    submitted,
    accepted,
    rejected,
    confirmed,
    waitlist,
    checked_in,
    CASE 
      WHEN total > 0 THEN ROUND(((accepted + rejected)::NUMERIC / total * 100), 2)
      ELSE 0 
    END as approval_rate,
    CASE 
      WHEN confirmed > 0 THEN ROUND((checked_in::NUMERIC / confirmed * 100), 2)
      ELSE 0 
    END as attendance_rate
  FROM stats;
END;$function$;

CREATE OR REPLACE FUNCTION prod.revoke_active_registration_tokens (
  p_registration_id uuid,
  p_reason          text,
  p_revoked_at      timestamp with time zone DEFAULT now()
)
  RETURNS void
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
BEGIN
    UPDATE prod.tokens
    SET revoked_at = p_revoked_at,
        revoked_reason = p_reason
    WHERE id IN (
        SELECT token_id
        FROM prod.event_registrations registration
        CROSS JOIN LATERAL unnest(ARRAY[
            registration.verification_token,
            registration.management_token,
            registration.rsvp_token,
            registration.ticket_token
        ]) AS tokens(token_id)
        WHERE registration.id = p_registration_id
    )
      AND used_at IS NULL
      AND revoked_at IS NULL
      AND expires_at > p_revoked_at;
END;
$function$;

CREATE OR REPLACE FUNCTION prod.verify_event_registration (
  p_registration_id         uuid,
  p_token_hash              text,
  p_management_token_hash   text,
  p_ticket_token_hash       text,
  p_management_before_hours integer,
  p_ticket_after_hours      integer
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event prod.events%ROWTYPE;
    v_verification_token prod.tokens%ROWTYPE;
    v_management_token prod.tokens%ROWTYPE;
    v_ticket_token prod.tokens%ROWTYPE;
    v_registration prod.event_registrations%ROWTYPE;
    v_auto_accept boolean;
    v_has_capacity boolean := true;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent concurrent requests from verifying the same registration.
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'pending_verification' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM prod.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent the one-time verification token from being consumed twice.
    SELECT * INTO v_verification_token
    FROM prod.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_verification_token.type <> 'verification'
       OR v_verification_token.token_hash <> p_token_hash
       OR v_verification_token.expires_at <= v_now
       OR v_verification_token.used_at IS NOT NULL
       OR v_verification_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM prod.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed');

        v_has_capacity := v_attendee_count < v_event.max_capacity;
    END IF;

    INSERT INTO prod.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time - make_interval(hours => p_management_before_hours))
    RETURNING * INTO v_management_token;

    IF v_auto_accept AND v_has_capacity THEN
        INSERT INTO prod.tokens (type, token_hash, expires_at)
        VALUES ('ticket', p_ticket_token_hash, v_event.date_time + make_interval(hours => p_ticket_after_hours))
        RETURNING * INTO v_ticket_token;
    END IF;

    UPDATE prod.tokens
    SET used_at = v_now
    WHERE id = v_verification_token.id;

    UPDATE prod.event_registrations
    SET status = CASE
            WHEN NOT v_has_capacity THEN 'waitlist'::public.registration_status
            WHEN v_auto_accept THEN 'confirmed'::public.registration_status
            ELSE 'submitted'::public.registration_status
        END,
        management_token = v_management_token.id,
        ticket_token = CASE WHEN v_auto_accept AND v_has_capacity THEN v_ticket_token.id ELSE NULL END,
        confirmed_at = CASE WHEN v_auto_accept AND v_has_capacity THEN v_now ELSE NULL END,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION prod.withdraw_event_registration (
  p_registration_id uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_registration prod.event_registrations%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM prod.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('submitted', 'waitlist') THEN
        RAISE EXCEPTION 'registration cannot be withdrawn' USING ERRCODE = 'P0001';
    END IF;

    PERFORM prod.revoke_active_registration_tokens(
        p_registration_id,
        'registration_withdrawn',
        v_now
    );

    UPDATE prod.event_registrations
    SET status = 'withdrawn'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$function$;

CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SECURITY DEFINER
  AS $function$DECLARE
    target_schema TEXT;
    role_value TEXT;
    dept_id UUID;
    pref_name TEXT;
BEGIN
    -- Determine target schema from metadata (default to 'test' if not specified)
    target_schema := COALESCE(NEW.raw_user_meta_data->>'schema', 'test');

    -- Extract user metadata
    role_value := NEW.raw_user_meta_data->>'role';
    dept_id := (NEW.raw_user_meta_data->>'department_id')::UUID;
    pref_name := NEW.raw_user_meta_data->>'preferred_name';

    -- Validate that role is provided for a member
    IF role_value IS NULL THEN
        RAISE NOTICE 'Skipping user creation - no role in metadata for user %', NEW.email;
        RETURN NEW;
    END IF;

    -- Insert into appropriate schema's users table
    EXECUTE format('
        INSERT INTO %I.users (user_id, email, role, department_id, preferred_name)
        VALUES ($1, $2, $3, $4, $5)
    ', target_schema)
    USING NEW.id, NEW.email, role_value::user_role, dept_id, pref_name;

    RAISE NOTICE 'Created user record in %.users for %', target_schema, NEW.email;

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't fail the auth signup
        RAISE WARNING 'Error creating user record for %: %', NEW.email, SQLERRM;
        RETURN NEW;
END;$function$;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION test.accept_event_registration (
  p_registration_id uuid,
  p_reviewer_id     uuid,
  p_rsvp_token_hash text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_token test.tokens%ROWTYPE;
    v_rsvp_expires_at timestamptz;
    v_attendee_count integer;
BEGIN
    IF p_rsvp_token_hash IS NULL OR btrim(p_rsvp_token_hash) = '' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'submitted' THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    v_rsvp_expires_at := v_event.date_time - interval '24 hours';
    IF v_rsvp_expires_at <= v_now THEN
        RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
    END IF;

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM test.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed');

        IF v_attendee_count >= v_event.max_capacity THEN
            RAISE EXCEPTION 'registration cannot be accepted' USING ERRCODE = 'P0001';
        END IF;
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('rsvp', p_rsvp_token_hash, v_rsvp_expires_at)
    RETURNING * INTO v_token;

    UPDATE test.event_registrations
    SET status = 'accepted'::public.registration_status,
        rsvp_token = v_token.id,
        reviewed_by = p_reviewer_id,
        reviewed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event),
        'token', to_jsonb(v_token)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION test.check_in_event_registration (
  p_registration_id   uuid,
  p_ticket_token_hash text,
  p_checked_in_by     uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_registration test.event_registrations%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND
       OR v_registration.status::text <> 'confirmed'
       OR v_registration.ticket_token IS NULL
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = ''
       OR p_checked_in_by IS NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_ticket_token
    FROM test.tokens
    WHERE id = v_registration.ticket_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_ticket_token.type <> 'ticket'
       OR v_ticket_token.token_hash <> p_ticket_token_hash
       OR v_ticket_token.expires_at <= v_now
       OR v_ticket_token.used_at IS NOT NULL
       OR v_ticket_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid ticket' USING ERRCODE = 'P0001';
    END IF;

    UPDATE test.tokens SET used_at = v_now WHERE id = v_ticket_token.id;

    UPDATE test.event_registrations
    SET checked_in = true,
        checked_in_at = v_now,
        checked_in_by = p_checked_in_by,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$function$;

CREATE OR REPLACE FUNCTION test.confirm_event_rsvp (
  p_registration_id       uuid,
  p_rsvp_token_hash       text,
  p_management_token_hash text,
  p_ticket_token_hash     text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_rsvp_token test.tokens%ROWTYPE;
    v_old_management_token test.tokens%ROWTYPE;
    v_new_management_token test.tokens%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM test.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM test.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time)
    RETURNING * INTO v_new_management_token;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time)
    RETURNING * INTO v_ticket_token;

    UPDATE test.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE test.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION test.confirm_event_rsvp (
  p_registration_id         uuid,
  p_rsvp_token_hash         text,
  p_management_token_hash   text,
  p_ticket_token_hash       text,
  p_management_before_hours integer,
  p_ticket_after_hours      integer
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_rsvp_token test.tokens%ROWTYPE;
    v_old_management_token test.tokens%ROWTYPE;
    v_new_management_token test.tokens%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
BEGIN
    IF p_rsvp_token_hash IS NULL
       OR btrim(p_rsvp_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'accepted' THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR SHARE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_rsvp_token
    FROM test.tokens
    WHERE id = v_registration.rsvp_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_rsvp_token.type <> 'rsvp'
       OR v_rsvp_token.token_hash <> p_rsvp_token_hash
       OR v_rsvp_token.expires_at <= v_now
       OR v_rsvp_token.used_at IS NOT NULL
       OR v_rsvp_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_old_management_token
    FROM test.tokens
    WHERE id = v_registration.management_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_old_management_token.type <> 'management'
       OR v_old_management_token.expires_at <= v_now
       OR v_old_management_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid RSVP token' USING ERRCODE = 'P0001';
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_rsvp_token.id;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time - make_interval(hours => p_management_before_hours))
    RETURNING * INTO v_new_management_token;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('ticket', p_ticket_token_hash, v_event.date_time + make_interval(hours => p_ticket_after_hours))
    RETURNING * INTO v_ticket_token;

    UPDATE test.tokens
    SET revoked_at = v_now,
        revoked_reason = 'rsvp_confirmed_management_rotated'
    WHERE id = v_old_management_token.id;

    UPDATE test.event_registrations
    SET status = 'confirmed'::public.registration_status,
        management_token = v_new_management_token.id,
        ticket_token = v_ticket_token.id,
        confirmed_at = v_now,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION test.create_pending_event_registration (
  p_event_id          uuid,
  p_form_data         jsonb,
  p_email             text,
  p_upload_session_id text,
  p_token_hash        text,
  p_token_expires_at  timestamp with time zone
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_event test.events%ROWTYPE;
    v_token test.tokens%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
BEGIN
    IF p_email IS NULL
       OR btrim(p_email) = ''
       OR p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_token_expires_at IS NULL
       OR p_token_expires_at <= now() THEN
        RAISE EXCEPTION 'invalid registration verification data' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = p_event_id
    FOR SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'event not found' USING ERRCODE = 'P0002';
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('verification', p_token_hash, p_token_expires_at)
    RETURNING * INTO v_token;

    INSERT INTO test.event_registrations (
        event_id,
        form_data,
        email,
        status,
        verification_token
    )
    VALUES (
        p_event_id,
        p_form_data,
        btrim(p_email),
        'pending_verification'::public.registration_status,
        v_token.id
    )
    RETURNING * INTO v_registration;

    UPDATE test.registration_files
    SET registration_id = v_registration.id,
        scheduled_deletion_date = v_event.date_time::date + 30
    WHERE upload_session_id = p_upload_session_id
      AND event_id = p_event_id
      AND registration_id IS NULL;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'token', to_jsonb(v_token)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION test.decline_event_rsvp (
  p_registration_id uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
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
$function$;

CREATE OR REPLACE FUNCTION test.generate_event_slug (
  event_title text
)
  RETURNS text
  LANGUAGE plpgsql
  AS $function$
DECLARE
  base_slug TEXT;
  final_slug TEXT;
  counter INTEGER := 0;
BEGIN
  base_slug := LOWER(
    TRIM(BOTH '-' FROM
      REGEXP_REPLACE(
        REGEXP_REPLACE(event_title, '[^a-zA-Z0-9]+', '-', 'g'),
        '-+', '-', 'g'
      )
    )
  );
  
  final_slug := base_slug;
  
  WHILE EXISTS (SELECT 1 FROM test.events WHERE slug = final_slug) LOOP
    counter := counter + 1;
    final_slug := base_slug || '-' || counter;
  END LOOP;
  
  RETURN final_slug;
END;
$function$;

CREATE OR REPLACE FUNCTION test.get_event_registration_stats (
  p_event_id uuid
)
  RETURNS TABLE (
    total_registrations bigint,
    submitted_count     bigint,
    accepted_count      bigint,
    rejected_count      bigint,
    confirmed_count     bigint,
    checked_in_count    bigint,
    approval_rate       numeric,
    attendance_rate     numeric
  )
  LANGUAGE plpgsql
  AS $function$BEGIN
  RETURN QUERY
  WITH stats AS (
    SELECT
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE event_registrations.status = 'submitted'::registration_status) as submitted,
      COUNT(*) FILTER (WHERE event_registrations.status = 'accepted'::registration_status) as accepted,
      COUNT(*) FILTER (WHERE event_registrations.status = 'rejected'::registration_status) as rejected,
      COUNT(*) FILTER (WHERE event_registrations.status = 'confirmed'::registration_status) as confirmed,
      COUNT(*) FILTER (WHERE event_registrations.status = 'waitlist'::registration_status) as waitlist,
      COUNT(*) FILTER (WHERE checked_in = true) as checked_in
    FROM test.event_registrations
    WHERE event_registrations.event_id = p_event_id
  )
  SELECT
    total,
    submitted,
    accepted,
    rejected,
    confirmed,
    waitlist,
    checked_in,
    CASE 
      WHEN total > 0 THEN ROUND(((accepted + rejected)::NUMERIC / total * 100), 2)
      ELSE 0 
    END as approval_rate,
    CASE 
      WHEN confirmed > 0 THEN ROUND((checked_in::NUMERIC / confirmed * 100), 2)
      ELSE 0 
    END as attendance_rate
  FROM stats;
END;$function$;

CREATE OR REPLACE FUNCTION test.revoke_active_registration_tokens (
  p_registration_id uuid,
  p_reason          text,
  p_revoked_at      timestamp with time zone DEFAULT now()
)
  RETURNS void
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
BEGIN
    UPDATE test.tokens
    SET revoked_at = p_revoked_at,
        revoked_reason = p_reason
    WHERE id IN (
        SELECT token_id
        FROM test.event_registrations registration
        CROSS JOIN LATERAL unnest(ARRAY[
            registration.verification_token,
            registration.management_token,
            registration.rsvp_token,
            registration.ticket_token
        ]) AS tokens(token_id)
        WHERE registration.id = p_registration_id
    )
      AND used_at IS NULL
      AND revoked_at IS NULL
      AND expires_at > p_revoked_at;
END;
$function$;

CREATE OR REPLACE FUNCTION test.verify_event_registration (
  p_registration_id         uuid,
  p_token_hash              text,
  p_management_token_hash   text,
  p_ticket_token_hash       text,
  p_management_before_hours integer,
  p_ticket_after_hours      integer
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_event test.events%ROWTYPE;
    v_verification_token test.tokens%ROWTYPE;
    v_management_token test.tokens%ROWTYPE;
    v_ticket_token test.tokens%ROWTYPE;
    v_registration test.event_registrations%ROWTYPE;
    v_auto_accept boolean;
    v_has_capacity boolean := true;
    v_attendee_count integer;
BEGIN
    IF p_token_hash IS NULL
       OR btrim(p_token_hash) = ''
       OR p_management_token_hash IS NULL
       OR btrim(p_management_token_hash) = ''
       OR p_ticket_token_hash IS NULL
       OR btrim(p_ticket_token_hash) = '' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent concurrent requests from verifying the same registration.
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text <> 'pending_verification' THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO v_event
    FROM test.events
    WHERE id = v_registration.event_id
    FOR UPDATE;

    IF NOT FOUND OR v_event.date_time <= v_now THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    -- Prevent the one-time verification token from being consumed twice.
    SELECT * INTO v_verification_token
    FROM test.tokens
    WHERE id = v_registration.verification_token
    FOR UPDATE;

    IF NOT FOUND
       OR v_verification_token.type <> 'verification'
       OR v_verification_token.token_hash <> p_token_hash
       OR v_verification_token.expires_at <= v_now
       OR v_verification_token.used_at IS NOT NULL
       OR v_verification_token.revoked_at IS NOT NULL THEN
        RAISE EXCEPTION 'invalid verification token' USING ERRCODE = 'P0001';
    END IF;

    v_auto_accept := COALESCE(
        (v_event.registration_form_schema ->> 'autoAccept')::boolean,
        (v_event.registration_form_schema ->> 'auto_accept')::boolean,
        false
    );

    IF v_event.max_capacity IS NOT NULL THEN
        SELECT count(*) INTO v_attendee_count
        FROM test.event_registrations
        WHERE event_id = v_event.id
          AND status::text IN ('accepted', 'confirmed');

        v_has_capacity := v_attendee_count < v_event.max_capacity;
    END IF;

    INSERT INTO test.tokens (type, token_hash, expires_at)
    VALUES ('management', p_management_token_hash, v_event.date_time - make_interval(hours => p_management_before_hours))
    RETURNING * INTO v_management_token;

    IF v_auto_accept AND v_has_capacity THEN
        INSERT INTO test.tokens (type, token_hash, expires_at)
        VALUES ('ticket', p_ticket_token_hash, v_event.date_time + make_interval(hours => p_ticket_after_hours))
        RETURNING * INTO v_ticket_token;
    END IF;

    UPDATE test.tokens
    SET used_at = v_now
    WHERE id = v_verification_token.id;

    UPDATE test.event_registrations
    SET status = CASE
            WHEN NOT v_has_capacity THEN 'waitlist'::public.registration_status
            WHEN v_auto_accept THEN 'confirmed'::public.registration_status
            ELSE 'submitted'::public.registration_status
        END,
        management_token = v_management_token.id,
        ticket_token = CASE WHEN v_auto_accept AND v_has_capacity THEN v_ticket_token.id ELSE NULL END,
        confirmed_at = CASE WHEN v_auto_accept AND v_has_capacity THEN v_now ELSE NULL END,
        updated_at = v_now
    WHERE id = v_registration.id
    RETURNING * INTO v_registration;

    RETURN jsonb_build_object(
        'registration', to_jsonb(v_registration),
        'event', to_jsonb(v_event)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION test.withdraw_event_registration (
  p_registration_id uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
DECLARE
    v_now timestamptz := now();
    v_registration test.event_registrations%ROWTYPE;
BEGIN
    SELECT * INTO v_registration
    FROM test.event_registrations
    WHERE id = p_registration_id
    FOR UPDATE;

    IF NOT FOUND OR v_registration.status::text NOT IN ('submitted', 'waitlist') THEN
        RAISE EXCEPTION 'registration cannot be withdrawn' USING ERRCODE = 'P0001';
    END IF;

    PERFORM test.revoke_active_registration_tokens(
        p_registration_id,
        'registration_withdrawn',
        v_now
    );

    UPDATE test.event_registrations
    SET status = 'withdrawn'::public.registration_status,
        updated_at = v_now
    WHERE id = p_registration_id
    RETURNING * INTO v_registration;

    RETURN to_jsonb(v_registration);
END;
$function$;

ALTER TABLE "prod"."announcement_reads"
  ADD CONSTRAINT "announcement_reads_announcement_id_fkey" FOREIGN KEY (announcement_id) REFERENCES prod.announcements(id) ON DELETE CASCADE;

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_event_id_fkey" FOREIGN KEY (event_id) REFERENCES prod.events(id) ON DELETE CASCADE;

ALTER TABLE "prod"."registration_files"
  ADD CONSTRAINT "registration_files_event_id_fkey" FOREIGN KEY (event_id) REFERENCES prod.events(id) ON DELETE CASCADE;

ALTER TABLE "prod"."registration_files"
  ADD CONSTRAINT "registration_files_registration_id_fkey" FOREIGN KEY (registration_id) REFERENCES prod.event_registrations(id) ON DELETE CASCADE;

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_management_token_fkey" FOREIGN KEY (management_token) REFERENCES prod.tokens(id);

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_rsvp_token_fkey" FOREIGN KEY (rsvp_token) REFERENCES prod.tokens(id);

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_ticket_token_fkey" FOREIGN KEY (ticket_token) REFERENCES prod.tokens(id);

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_verification_token_fkey" FOREIGN KEY (verification_token) REFERENCES prod.tokens(id);

ALTER TABLE "prod"."users"
  ADD CONSTRAINT "users_department_id_fkey" FOREIGN KEY (department_id) REFERENCES prod.departments(id) ON DELETE SET NULL;

ALTER TABLE "prod"."users"
  ADD CONSTRAINT "users_invited_by_fkey" FOREIGN KEY (invited_by) REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE "prod"."announcement_reads"
  ADD CONSTRAINT "announcement_reads_user_id_fkey" FOREIGN KEY (user_id) REFERENCES prod.users(id) ON DELETE CASCADE;

ALTER TABLE "prod"."announcements"
  ADD CONSTRAINT "announcements_created_by_fkey" FOREIGN KEY (created_by) REFERENCES prod.users(id) ON DELETE SET NULL;

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_checked_in_by_fkey" FOREIGN KEY (checked_in_by) REFERENCES prod.users(id) ON DELETE SET NULL;

ALTER TABLE "prod"."event_registrations"
  ADD CONSTRAINT "event_registrations_reviewed_by_fkey" FOREIGN KEY (reviewed_by) REFERENCES prod.users(id) ON DELETE SET NULL;

ALTER TABLE "prod"."events"
  ADD CONSTRAINT "events_created_by_fkey" FOREIGN KEY (created_by) REFERENCES prod.users(id) ON DELETE SET NULL;

ALTER TABLE "prod"."users"
  ADD CONSTRAINT "users_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE "test"."announcement_reads"
  ADD CONSTRAINT "announcement_reads_announcement_id_fkey" FOREIGN KEY (announcement_id) REFERENCES test.announcements(id) ON DELETE CASCADE;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_event_id_fkey" FOREIGN KEY (event_id) REFERENCES test.events(id) ON DELETE CASCADE;

ALTER TABLE "test"."registration_files"
  ADD CONSTRAINT "registration_files_event_id_fkey" FOREIGN KEY (event_id) REFERENCES test.events(id) ON DELETE CASCADE;

ALTER TABLE "test"."registration_files"
  ADD CONSTRAINT "registration_files_registration_id_fkey" FOREIGN KEY (registration_id) REFERENCES test.event_registrations(id) ON DELETE CASCADE;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_management_token_fkey" FOREIGN KEY (management_token) REFERENCES test.tokens(id) ON DELETE SET NULL;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_rsvp_token_fkey" FOREIGN KEY (rsvp_token) REFERENCES test.tokens(id) ON DELETE SET NULL;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_ticket_token_fkey" FOREIGN KEY (ticket_token) REFERENCES test.tokens(id) ON DELETE SET NULL;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_verification_token_fkey" FOREIGN KEY (verification_token) REFERENCES test.tokens(id) ON DELETE SET NULL;

ALTER TABLE "test"."users"
  ADD CONSTRAINT "users_department_id_fkey" FOREIGN KEY (department_id) REFERENCES test.departments(id) ON DELETE SET NULL;

ALTER TABLE "test"."users"
  ADD CONSTRAINT "users_invited_by_fkey" FOREIGN KEY (invited_by) REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE "test"."announcement_reads"
  ADD CONSTRAINT "announcement_reads_user_id_fkey" FOREIGN KEY (user_id) REFERENCES test.users(id) ON DELETE CASCADE;

ALTER TABLE "test"."announcements"
  ADD CONSTRAINT "announcements_created_by_fkey" FOREIGN KEY (created_by) REFERENCES test.users(id) ON DELETE SET NULL;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_checked_in_by_fkey" FOREIGN KEY (checked_in_by) REFERENCES test.users(id) ON DELETE SET NULL;

ALTER TABLE "test"."event_registrations"
  ADD CONSTRAINT "event_registrations_reviewed_by_fkey" FOREIGN KEY (reviewed_by) REFERENCES test.users(id) ON DELETE SET NULL;

ALTER TABLE "test"."events"
  ADD CONSTRAINT "events_created_by_fkey" FOREIGN KEY (created_by) REFERENCES test.users(id) ON DELETE SET NULL;

ALTER TABLE "test"."users"
  ADD CONSTRAINT "users_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX idx_notification_preferences_prod ON prod.users USING gin (notification_preferences);

CREATE INDEX idx_prod_announcement_reads_announcement_id ON prod.announcement_reads USING btree (announcement_id);

CREATE INDEX idx_prod_announcement_reads_user_id ON prod.announcement_reads USING btree (user_id);

CREATE INDEX idx_prod_announcements_created_at ON prod.announcements USING btree (created_at DESC);

CREATE INDEX idx_prod_announcements_created_by ON prod.announcements USING btree (created_by);

CREATE INDEX idx_prod_announcements_priority ON prod.announcements USING btree (priority);

CREATE INDEX idx_prod_event_registrations_event_id ON prod.event_registrations USING btree (event_id);

CREATE INDEX idx_prod_event_registrations_status ON prod.event_registrations USING btree (status);

CREATE INDEX idx_prod_event_registrations_submitted_at ON prod.event_registrations USING btree (submitted_at);

CREATE INDEX idx_prod_events_category ON prod.events USING btree (category);

CREATE INDEX idx_prod_events_created_by ON prod.events USING btree (created_by);

CREATE INDEX idx_prod_events_date_time ON prod.events USING btree (date_time);

CREATE UNIQUE INDEX idx_prod_events_slug ON prod.events USING btree (slug);

CREATE INDEX idx_prod_events_status ON prod.events USING btree (status);

CREATE INDEX idx_prod_registration_files_orphaned ON prod.registration_files USING btree (uploaded_at)
  WHERE ((registration_id IS NULL) AND (NOT deleted));

CREATE INDEX idx_prod_registration_files_registration_id ON prod.registration_files USING btree (registration_id);

CREATE INDEX idx_prod_registration_files_scheduled_deletion ON prod.registration_files USING btree (scheduled_deletion_date)
  WHERE ((NOT deleted) AND (registration_id IS NOT NULL));

CREATE INDEX idx_prod_registration_files_upload_session ON prod.registration_files USING btree (upload_session_id);

CREATE INDEX idx_prod_users_department ON prod.users USING btree (department_id);

CREATE INDEX idx_prod_users_role ON prod.users USING btree (ROLE);

CREATE INDEX event_registrations_email_idx ON test.event_registrations USING btree (email);

CREATE UNIQUE INDEX event_registrations_management_token_uidx ON test.event_registrations USING btree (management_token)
  WHERE (management_token IS NOT NULL);

CREATE UNIQUE INDEX event_registrations_rsvp_token_uidx ON test.event_registrations USING btree (rsvp_token)
  WHERE (rsvp_token IS NOT NULL);

CREATE UNIQUE INDEX event_registrations_ticket_token_uidx ON test.event_registrations USING btree (ticket_token)
  WHERE (ticket_token IS NOT NULL);

CREATE UNIQUE INDEX event_registrations_verification_token_uidx ON test.event_registrations USING btree (verification_token)
  WHERE (verification_token IS NOT NULL);

CREATE INDEX idx_notification_preferences_test ON test.users USING gin (notification_preferences);

CREATE INDEX idx_test_announcement_reads_announcement_id ON test.announcement_reads USING btree (announcement_id);

CREATE INDEX idx_test_announcement_reads_user_id ON test.announcement_reads USING btree (user_id);

CREATE INDEX idx_test_announcements_created_at ON test.announcements USING btree (created_at DESC);

CREATE INDEX idx_test_announcements_created_by ON test.announcements USING btree (created_by);

CREATE INDEX idx_test_announcements_priority ON test.announcements USING btree (priority);

CREATE INDEX idx_test_event_registrations_event_id ON test.event_registrations USING btree (event_id);

CREATE INDEX idx_test_event_registrations_status ON test.event_registrations USING btree (status);

CREATE INDEX idx_test_event_registrations_submitted_at ON test.event_registrations USING btree (submitted_at);

CREATE INDEX idx_test_events_category ON test.events USING btree (category);

CREATE INDEX idx_test_events_created_by ON test.events USING btree (created_by);

CREATE INDEX idx_test_events_date_time ON test.events USING btree (date_time);

CREATE UNIQUE INDEX idx_test_events_slug ON test.events USING btree (slug);

CREATE INDEX idx_test_events_status ON test.events USING btree (status);

CREATE INDEX idx_test_registration_files_orphaned ON test.registration_files USING btree (uploaded_at)
  WHERE ((registration_id IS NULL) AND (NOT deleted));

CREATE INDEX idx_test_registration_files_registration_id ON test.registration_files USING btree (registration_id);

CREATE INDEX idx_test_registration_files_scheduled_deletion ON test.registration_files USING btree (scheduled_deletion_date)
  WHERE ((NOT deleted) AND (registration_id IS NOT NULL));

CREATE INDEX idx_test_registration_files_upload_session ON test.registration_files USING btree (upload_session_id);

CREATE INDEX idx_test_registration_tokens_expires_at ON test.tokens USING btree (expires_at);

CREATE INDEX idx_test_registration_tokens_hash_type ON test.tokens USING btree (token_hash, TYPE);

CREATE INDEX idx_test_users_department ON test.users USING btree (department_id);

CREATE INDEX idx_test_users_role ON test.users USING btree (ROLE);

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE ON auth.users
  FOR EACH ROW
  WHEN (((old.raw_user_meta_data IS DISTINCT FROM new.raw_user_meta_data) OR ((old.email)::text IS DISTINCT FROM (new.email)::text)))
  EXECUTE FUNCTION public.handle_new_user();

CREATE TRIGGER update_announcements_updated_at
  BEFORE UPDATE ON prod.announcements
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_event_registrations_updated_at
  BEFORE UPDATE ON prod.event_registrations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_events_updated_at
  BEFORE UPDATE ON prod.events
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON prod.users
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_announcements_updated_at
  BEFORE UPDATE ON test.announcements
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_event_registrations_updated_at
  BEFORE UPDATE ON test.event_registrations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_events_updated_at
  BEFORE UPDATE ON test.events
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON test.users
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE POLICY "Co-presidents can view all read receipts" ON "prod"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can mark announcements read" ON "prod"."announcement_reads"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = announcement_reads.user_id)))));

CREATE POLICY "Users can read own read receipts" ON "prod"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = announcement_reads.user_id)))));

CREATE POLICY "announcement_reads_insert_own" ON "prod"."announcement_reads"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((user_id = auth.uid()));

CREATE POLICY "announcement_reads_select_own" ON "prod"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((user_id = auth.uid()));

CREATE POLICY "Co-presidents can create announcements" ON "prod"."announcements"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can read announcements" ON "prod"."announcements"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "announcements_delete_copresidents_or_creator" ON "prod"."announcements"
  FOR DELETE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))));

CREATE POLICY "announcements_insert_copresidents" ON "prod"."announcements"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = ANY (ARRAY['co_president'::public.user_role, 'vp'::public.user_role]))))));

CREATE POLICY "announcements_select_authenticated" ON "prod"."announcements"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "announcements_update_copresidents_or_creator" ON "prod"."announcements"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))))
  WITH CHECK ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))));

CREATE POLICY "Anyone can read departments" ON "prod"."departments"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Co-presidents can manage departments" ON "prod"."departments"
  FOR ALL
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "All users can check in attendees" ON "prod"."event_registrations"
  FOR UPDATE
  TO "authenticated"
  USING (true);

CREATE POLICY "Anyone can submit registrations" ON "prod"."event_registrations"
  FOR INSERT
  TO "anon", "authenticated"
  WITH CHECK (true);

CREATE POLICY "Authenticated users can view all registrations" ON "prod"."event_registrations"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "VPs and Co-Presidents can update status" ON "prod"."event_registrations"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.id = auth.uid()) AND (users.role = ANY (ARRAY['vp'::public.user_role, 'co_president'::public.user_role]))))));

CREATE POLICY "Co-presidents can manage all events" ON "prod"."events"
  FOR ALL
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Co-presidents can read all events" ON "prod"."events"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Creators can update own events" ON "prod"."events"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = events.created_by) AND (events.status <> 'published'::public.event_status)))));

CREATE POLICY "Users can read own events" ON "prod"."events"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = events.created_by)))));

CREATE POLICY "Users can read published events" ON "prod"."events"
  FOR SELECT
  TO "authenticated"
  USING ((status = 'published'::public.event_status));

CREATE POLICY "VPs can create events" ON "prod"."events"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM prod.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'vp'::public.user_role) OR (users.role = 'co_president'::public.user_role))))));

CREATE POLICY "Anyone can upload files" ON "prod"."registration_files"
  FOR INSERT
  TO "anon", "authenticated"
  WITH CHECK (true);

CREATE POLICY "Authenticated users can view files" ON "prod"."registration_files"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Co-presidents can update all profiles" ON "prod"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users users_1
  WHERE ((users_1.user_id = auth.uid()) AND (users_1.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can read all profiles" ON "prod"."users"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Users can update own profile" ON "prod"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = user_id))
  WITH CHECK ((auth.uid() = user_id));

CREATE POLICY "VPs can update team profiles" ON "prod"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM prod.users vp
  WHERE ((vp.user_id = auth.uid()) AND (vp.role = 'vp'::public.user_role) AND (vp.department_id = users.department_id)))));

CREATE POLICY "Co-presidents can view all read receipts" ON "test"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can mark announcements read" ON "test"."announcement_reads"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = announcement_reads.user_id)))));

CREATE POLICY "Users can read own read receipts" ON "test"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = announcement_reads.user_id)))));

CREATE POLICY "announcement_reads_insert_own" ON "test"."announcement_reads"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((user_id IN ( SELECT users.id
   FROM test.users
  WHERE (users.user_id = auth.uid()))));

CREATE POLICY "announcement_reads_select_own" ON "test"."announcement_reads"
  FOR SELECT
  TO "authenticated"
  USING ((user_id IN ( SELECT users.id
   FROM test.users
  WHERE (users.user_id = auth.uid()))));

CREATE POLICY "Co-presidents can create announcements" ON "test"."announcements"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can read announcements" ON "test"."announcements"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "announcements_delete_copresidents_or_creator" ON "test"."announcements"
  FOR DELETE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))));

CREATE POLICY "announcements_insert_copresidents" ON "test"."announcements"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = ANY (ARRAY['co_president'::public.user_role, 'vp'::public.user_role]))))));

CREATE POLICY "announcements_select_authenticated" ON "test"."announcements"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "announcements_update_copresidents_or_creator" ON "test"."announcements"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))))
  WITH CHECK ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'co_president'::public.user_role) OR (announcements.created_by = users.id))))));

CREATE POLICY "Anyone can read departments" ON "test"."departments"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Co-presidents can manage departments" ON "test"."departments"
  FOR ALL
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "All users can check in attendees" ON "test"."event_registrations"
  FOR UPDATE
  TO "authenticated"
  USING (true);

CREATE POLICY "Anyone can submit registrations" ON "test"."event_registrations"
  FOR INSERT
  TO "anon", "authenticated"
  WITH CHECK (true);

CREATE POLICY "Authenticated users can view all registrations" ON "test"."event_registrations"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "VPs and Co-Presidents can update status" ON "test"."event_registrations"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.id = auth.uid()) AND (users.role = ANY (ARRAY['vp'::public.user_role, 'co_president'::public.user_role]))))));

CREATE POLICY "Co-presidents can manage all events" ON "test"."events"
  FOR ALL
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Co-presidents can read all events" ON "test"."events"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.role = 'co_president'::public.user_role)))));

CREATE POLICY "Creators can update own events" ON "test"."events"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = events.created_by) AND (events.status <> 'published'::public.event_status)))));

CREATE POLICY "Users can read own events" ON "test"."events"
  FOR SELECT
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND (users.id = events.created_by)))));

CREATE POLICY "Users can read published events" ON "test"."events"
  FOR SELECT
  TO "authenticated"
  USING ((status = 'published'::public.event_status));

CREATE POLICY "VPs can create events" ON "test"."events"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((EXISTS ( SELECT 1
   FROM test.users
  WHERE ((users.user_id = auth.uid()) AND ((users.role = 'vp'::public.user_role) OR (users.role = 'co_president'::public.user_role))))));

CREATE POLICY "Anyone can upload files" ON "test"."registration_files"
  FOR INSERT
  TO "anon", "authenticated"
  WITH CHECK (true);

CREATE POLICY "Authenticated users can view files" ON "test"."registration_files"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Co-presidents can update all profiles" ON "test"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users users_1
  WHERE ((users_1.user_id = auth.uid()) AND (users_1.role = 'co_president'::public.user_role)))));

CREATE POLICY "Users can read all profiles" ON "test"."users"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "Users can update own profile" ON "test"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((auth.uid() = user_id))
  WITH CHECK ((auth.uid() = user_id));

CREATE POLICY "VPs can update team profiles" ON "test"."users"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM test.users vp
  WHERE ((vp.user_id = auth.uid()) AND (vp.role = 'vp'::public.user_role) AND (vp.department_id = users.department_id)))));

COMMENT ON COLUMN "prod"."events"."album_link" IS 'Google Drive link for event photos/albums';

COMMENT ON COLUMN "prod"."events"."category" IS 'Event category (e.g., "Case Competition", "Workshop", "Networking")';

COMMENT ON COLUMN "prod"."events"."image_position" IS 'Image position for display: "top", "center", "bottom", or pixel offset as text';

COMMENT ON COLUMN "prod"."users"."linkedin_url" IS 'If exec team members want to include their LinkedIn profile';

COMMENT ON COLUMN "test"."events"."album_link" IS 'Google Drive link for event photos/albums';

COMMENT ON COLUMN "test"."events"."category" IS 'Event category (e.g., "Case Competition", "Workshop", "Networking")';

COMMENT ON COLUMN "test"."events"."image_position" IS 'Image position for display: "top", "center", "bottom", or pixel offset as text';

COMMENT ON COLUMN "test"."tokens"."expires_at" IS 'Set when the token is created. Defines the timestamp after which the token is invalid and must be checked during every verification.';

COMMENT ON COLUMN "test"."tokens"."revoked_at" IS 'Set when RSVP is cancelled or the token is manually invalidated.';

COMMENT ON COLUMN "test"."tokens"."token_hash" IS 'SHA-256 hash of the raw token. Raw tokens must never be stored.';

COMMENT ON COLUMN "test"."tokens"."used_at" IS 'Set after consuming a one-time confirmation or ticket token.';

COMMENT ON COLUMN "test"."users"."display_role" IS 'Position Title';

COMMENT ON TABLE "test"."tokens" IS 'General-purpose tokens intended for event registrations, newsletters, etc.';

REVOKE ALL ON FUNCTION "prod"."accept_event_registration"(uuid, uuid, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."accept_event_registration"(uuid, uuid, text) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."check_in_event_registration"(uuid, text, uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."check_in_event_registration"(uuid, text, uuid) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."confirm_event_rsvp"(uuid, text, text, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."confirm_event_rsvp"(uuid, text, text, text) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."confirm_event_rsvp"(uuid, text, text, text, integer, integer) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."confirm_event_rsvp"(uuid, text, text, text, integer, integer) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."create_pending_event_registration"(uuid, jsonb, text, text, text, timestamp WITH time zone) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."create_pending_event_registration"(uuid, jsonb, text, text, text, timestamp WITH time zone) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."decline_event_rsvp"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."decline_event_rsvp"(uuid) TO "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "prod"."generate_event_slug"(text) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "prod"."get_event_registration_stats"(uuid) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."revoke_active_registration_tokens"(uuid, text, timestamp WITH time zone) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."revoke_active_registration_tokens"(uuid, text, timestamp WITH time zone) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."verify_event_registration"(uuid, text, text, text, integer, integer) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."verify_event_registration"(uuid, text, text, text, integer, integer) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "prod"."withdraw_event_registration"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "prod"."withdraw_event_registration"(uuid) TO "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."handle_new_user"() TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."update_updated_at_column"() TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."accept_event_registration"(uuid, uuid, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."accept_event_registration"(uuid, uuid, text) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."check_in_event_registration"(uuid, text, uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."check_in_event_registration"(uuid, text, uuid) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."confirm_event_rsvp"(uuid, text, text, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."confirm_event_rsvp"(uuid, text, text, text) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."confirm_event_rsvp"(uuid, text, text, text, integer, integer) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."confirm_event_rsvp"(uuid, text, text, text, integer, integer) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."create_pending_event_registration"(uuid, jsonb, text, text, text, timestamp WITH time zone) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."create_pending_event_registration"(uuid, jsonb, text, text, text, timestamp WITH time zone) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."decline_event_rsvp"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."decline_event_rsvp"(uuid) TO "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "test"."generate_event_slug"(text) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "test"."get_event_registration_stats"(uuid) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."revoke_active_registration_tokens"(uuid, text, timestamp WITH time zone) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."revoke_active_registration_tokens"(uuid, text, timestamp WITH time zone) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."verify_event_registration"(uuid, text, text, text, integer, integer) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."verify_event_registration"(uuid, text, text, text, integer, integer) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "test"."withdraw_event_registration"(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION "test"."withdraw_event_registration"(uuid) TO "postgres", "service_role";

GRANT USAGE ON SCHEMA "prod" TO "anon", "authenticated";

GRANT CREATE, USAGE ON SCHEMA "prod" TO "postgres";

GRANT USAGE ON SCHEMA "prod" TO "service_role";

GRANT CREATE, USAGE ON SCHEMA "security" TO "postgres";

GRANT USAGE ON SCHEMA "security" TO "service_role";

GRANT USAGE ON SCHEMA "test" TO "anon", "authenticated";

GRANT CREATE, USAGE ON SCHEMA "test" TO "postgres";

GRANT USAGE ON SCHEMA "test" TO "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."announcement_reads" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."announcements" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."departments" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."event_registrations" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."events" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."registration_files" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."tokens" TO "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "prod"."users" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."announcement_reads" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."announcements" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."departments" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."event_registrations" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."events" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."registration_files" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."tokens" TO "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "test"."users" TO "anon", "authenticated", "postgres", "service_role";

GRANT USAGE ON TYPE "public"."announcement_priority" TO "postgres";

GRANT USAGE ON TYPE "public"."application_status" TO "postgres";

GRANT USAGE ON TYPE "public"."email_notification_preference" TO "postgres";

GRANT USAGE ON TYPE "public"."event_status" TO "postgres";

GRANT USAGE ON TYPE "public"."registration_mode" TO "postgres";

GRANT USAGE ON TYPE "public"."registration_status" TO "postgres";

GRANT USAGE ON TYPE "public"."user_role" TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" REVOKE ALL ON FUNCTIONS FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT EXECUTE ON FUNCTIONS TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT EXECUTE ON FUNCTIONS TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT EXECUTE ON FUNCTIONS TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "prod" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT SELECT, UPDATE, USAGE ON SEQUENCES TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" REVOKE ALL ON FUNCTIONS FROM PUBLIC;

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT EXECUTE ON FUNCTIONS TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT EXECUTE ON FUNCTIONS TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT EXECUTE ON FUNCTIONS TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "test" GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLES TO "service_role";


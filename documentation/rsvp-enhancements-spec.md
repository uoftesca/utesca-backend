# Software Specification: RSVP Enhancements & Notification System

**Document Version**: 1.0
**Created**: January 2026
**Status**: Approved for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature Overview](#feature-overview)
3. [Feature 1: 24-Hour RSVP Cutoff](#feature-1-24-hour-rsvp-cutoff)
4. [Feature 2: Display Empty Form Fields](#feature-2-display-empty-form-fields)
5. [Feature 3: Decline Notification Emails](#feature-3-decline-notification-emails)
6. [Feature 4: Notification Preferences System](#feature-4-notification-preferences-system)
7. [Technical Architecture](#technical-architecture)
8. [API Specifications](#api-specifications)
9. [Database Schema Changes](#database-schema-changes)
10. [Error Handling](#error-handling)
11. [Testing Requirements](#testing-requirements)
12. [Deployment Plan](#deployment-plan)
13. [Future Enhancements](#future-enhancements)

---

## Executive Summary

This specification outlines four interconnected enhancements to the UTESCA event registration and RSVP system:

1. **24-Hour RSVP Cutoff**: Prevent RSVP changes (confirm/decline) within 24 hours of event start to give organizers time for final preparations
2. **Display Empty Form Fields**: Show all registration form fields in the admin portal, displaying "--" for optional fields not filled out
3. **Decline Notification Emails**: Automatically notify subscribed users when attendees decline confirmed attendance
4. **Notification Preferences System**: Migrate from single email preference field to granular JSONB-based notification system

### Business Value

- **Reduced No-Shows**: 24-hour cutoff gives organizers accurate final headcounts
- **Improved Visibility**: Portal displays complete registration data including empty fields
- **Proactive Event Management**: Subscribed users notified of capacity changes in real-time
- **User Control**: Granular notification preferences respect user communication preferences and allow any user to opt-in

### Dependencies

**Critical**: Feature 4 (Notification Preferences) **must** be implemented before Feature 3 (Decline Notifications) as Feature 3 relies on the new `notification_preferences` JSONB structure.

---

## Feature Overview

### User Stories

#### US-1: 24-Hour RSVP Cutoff

**As an** event organizer
**I want to** prevent RSVP changes within 24 hours of the event
**So that** I have time to prepare accurate materials and catering

**Acceptance Criteria**:

- Users cannot confirm or decline attendance within 24 hours of event start
- API returns `400 Bad Request` with clear error message
- Frontend displays disabled buttons with explanatory message
- Metadata includes `within_rsvp_cutoff` flag for UI state management

#### US-2: Display Empty Form Fields

**As a** portal administrator
**I want to** see all registration form fields including empty optional ones
**So that** I can quickly scan submissions without missing information

**Acceptance Criteria**:

- All form fields from schema displayed in ApplicationDetailModal
- Empty optional fields show "--" instead of being hidden
- Optional fields labeled with "(optional)" indicator
- No change to database or API (frontend-only fix)

#### US-3: Decline Notification Emails

**As a** portal user interested in event management
**I want to** receive email notifications when attendees decline confirmed attendance
**So that** I can adjust event planning and potentially reach out to waitlist

**Acceptance Criteria**:

- Email sent when user transitions from `confirmed` → `not_attending`
- NO email sent for `accepted` → `not_attending` (never confirmed)
- Only sent to users with `rsvp_changes: true` in notification preferences (role-agnostic)
- Email includes attendee name, email, event details

#### US-4: Notification Preferences System

**As a** portal user
**I want to** control which types of email notifications I receive
**So that** I'm not overwhelmed by irrelevant emails

**Acceptance Criteria**:

- JSONB column supports announcements, RSVP changes, new applications
- Existing preferences migrated without data loss
- API supports updating granular preferences
- Frontend TypeScript types match backend models

---

## Feature 1: 24-Hour RSVP Cutoff

### Functional Requirements

#### FR-1.1: Cutoff Timing

- **Requirement**: Block all RSVP changes (confirm and decline) when current time is within 24 hours of event start
- **Calculation**: `current_time >= (event_datetime - 24 hours)`
- **Timezone**: All comparisons done in UTC to ensure consistency

#### FR-1.2: Error Response

- **HTTP Status**: `400 Bad Request`
- **Error Message**: `"Cannot change RSVP. The cutoff is 24 hours before event"`
- **Applies To**: Both `POST /rsvp/{id}/confirm` and `POST /rsvp/{id}/decline`

#### FR-1.3: Metadata Flag

- **Field**: `within_rsvp_cutoff: boolean`
- **Added To**: `RsvpDetailsByIdResponse` model
- **Purpose**: Allow frontend to show appropriate UI state before API call

#### FR-1.4: Action Flags Update

- **can_confirm**: Only `true` if NOT within cutoff and other conditions met
- **can_decline**: Only `true` if NOT within cutoff and other conditions met

### Non-Functional Requirements

#### NFR-1.1: Performance

- Cutoff check adds negligible latency (< 5ms)
- No database queries required (uses event datetime from existing query)

#### NFR-1.2: Reliability

- Timezone-aware datetime handling prevents edge cases
- Idempotent operations (already implemented) prevent race conditions

### User Experience

#### Frontend Display

When `withinRsvpCutoff: true`:

```typescript
<Alert variant="warning">
  <AlertDescription>
    RSVP changes are no longer available - we are within 24 hours of the event.
    If you need to make changes, please contact us at uoft.esca@gmail.com
  </AlertDescription>
</Alert>
```

- Confirm/Decline buttons disabled
- Clear explanation of why actions are unavailable
- Contact information for manual override

### Implementation Details

#### Backend Changes

**File**: `utesca-backend/src/domains/events/registrations/service.py`

**New Method** (add after line 597):

```python
def _is_within_rsvp_cutoff(self, event_date: datetime) -> bool:
    """
    Check if we are within 24 hours of event start (RSVP cutoff period).

    Once within 24 hours, users cannot confirm or decline their RSVP.

    Args:
        event_date: The event's date_time

    Returns:
        True if within 24 hours of event, False otherwise
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    event_dt = event_date if event_date.tzinfo else event_date.replace(tzinfo=timezone.utc)
    cutoff_time = event_dt - timedelta(hours=24)

    return now >= cutoff_time
```

**Modified Methods**:

- `rsvp_details()`: Add `within_cutoff` check to metadata
- `rsvp_confirm()`: Add cutoff validation before status update
- `rsvp_decline()`: Add cutoff validation before status update

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Event datetime exactly 24 hours away | Cutoff applies (>= comparison) |
| Event datetime timezone-naive | Converted to UTC before comparison |
| Multiple rapid confirm/decline attempts | First request processed, subsequent return appropriate error |
| Event already passed | Existing `_has_event_passed()` check takes precedence |

---

## Feature 2: Display Empty Form Fields

### Functional Requirements

#### FR-2.1: Display All Schema Fields

- **Requirement**: Show all fields defined in registration form schema
- **Behavior**: Iterate through `schema.fields` regardless of whether value exists in `form_data`

#### FR-2.2: Empty Field Placeholder

- **Display Value**: `"—"` (em dash) for null/undefined/empty string
- **Source**: Existing `formatFieldValue()` utility already returns this
- **Optional Label**: Add "(optional)" indicator for non-required fields

#### FR-2.3: No Database Changes

- **Scope**: Frontend-only change
- **Rationale**: Backend already correctly stores only filled fields (reduces JSON size)
- **Frontend Responsibility**: Handle missing keys gracefully

### Non-Functional Requirements

#### NFR-2.1: Backward Compatibility

- No changes to API contracts
- Existing registrations display correctly
- No migration required

### Implementation Details

#### Frontend Changes

**File**: `utesca-portal-frontend/src/components/events/registrations/ApplicationDetailModal.tsx`

**Current Issue** (lines 159-162):

```typescript
// Skip empty optional fields
if (value === undefined || value === null || value === '') {
  return null;
}
```

This causes empty fields to be completely hidden.

**Solution** (lines 155-186):
Remove early return, let `formatFieldValue()` handle display:

```typescript
schema.fields.map((field) => {
  const value = registration.formData[field.id];

  // Don't skip empty fields - show with "--"
  const isFile = isFileObject(value);
  const displayValue = isFile
    ? (value as { fileName: string }).fileName
    : formatFieldValue(value); // Returns '—' for null/undefined

  return (
    <div key={field.id} className="space-y-1">
      <p className="text-sm font-medium text-muted-foreground">
        {field.label}
        {!field.required && <span className="text-xs ml-1">(optional)</span>}
      </p>
      <p className="text-sm">{displayValue}</p>
    </div>
  );
})
```

### User Experience

#### Before

Registration with 3 required + 2 optional fields:

- If user fills all 5 → Shows 5 fields ✓
- If user fills only required → Shows 3 fields ✗ (missing 2 optional)

#### After

- Always shows 5 fields
- Optional empty fields display: `Resume: — (optional)`

---

## Feature 3: Decline Notification Emails

### Functional Requirements

#### FR-3.1: Trigger Condition

- **Event**: User status transitions from `confirmed` → `not_attending`
- **NOT Triggered**: For `accepted` → `not_attending` (user never confirmed)
- **Rationale**: Only confirmed attendees were counted in capacity planning

#### FR-3.2: Recipient Filtering

- **Query Method**: Preference-based, not role-based
- **Filter**: Only users with `notification_preferences.rsvp_changes = true`
- **Rationale**: Any user can opt-in to notifications regardless of role (VPs, Directors, or others interested in event management)

#### FR-3.3: Email Content

Required information:

- Attendee name (or email if name unavailable)
- Attendee email
- Event title
- Event date/time (Toronto timezone)
- Event location
- Previous status (should be "confirmed")

#### FR-3.4: Email Delivery

- **Method**: Resend API via EmailService
- **Execution**: Background task (non-blocking)
- **Error Handling**: Log failures, don't block decline operation
- **Batch Sending**: Individual emails to each recipient (Resend best practice)

### Non-Functional Requirements

#### NFR-3.1: Performance

- Email sending in background task (0ms added to API response)
- Notification preference query typically returns <50 users (negligible database impact)

#### NFR-3.2: Reliability

- Email failures logged but don't affect core functionality
- Idempotent operation (multiple decline calls don't trigger multiple emails)

#### NFR-3.3: Privacy

- Only subscribed users see attendee information
- Email sent to individual recipients (not CC/BCC list)
- User-controlled opt-in respects privacy preferences

### Email Template

#### Subject Line

```
RSVP Decline: {event_title}
```

#### HTML Body Structure

1. **Header**: UTESCA logo, "RSVP Decline Notification" title
2. **Warning Box** (yellow): Attendee information
   - Name, Email, Previous Status
3. **Info Box** (blue): Event details
   - Title, Date/Time, Location
4. **Footer**: Organization contact info

#### Plain Text Fallback

Simple formatted text with same information for email clients that don't support HTML.

### Implementation Details

#### Backend Changes

**File 1**: `utesca-backend/src/core/email/templates.py`

Add `build_rsvp_decline_notification()` function:

- Builds HTML and plain text email for RSVP decline notifications
- Includes attendee information and event details
- Professional template matching existing email design

**File 2**: `utesca-backend/src/core/email/service.py`

Add `send_rsvp_decline_notification()` method:

- Accepts list of recipient emails (subscribed users)
- Sends individual emails to each recipient
- Returns success if at least one email sent
- Logs send counts for monitoring

**File 3**: `utesca-backend/src/domains/events/registrations/service.py`

Add `send_decline_notification_to_subscribed_users()` method:

- Queries all users with RSVP notifications enabled via UserRepository
- Uses `get_users_with_notification_enabled("rsvp_changes")` (role-agnostic)
- Filters by notification preference, not role
- Extracts attendee info from registration form_data
- Calls EmailService with list of subscriber emails
- Catches all exceptions (defensive programming)

**File 4**: `utesca-backend/src/domains/events/registrations/public_api.py`

Modify `decline_rsvp` endpoint:

- Capture `previous_status` before decline operation
- Add background task for subscriber notification if `previous_status == "confirmed"`
- Runs asynchronously after user response sent
- Email sending does not block decline operation

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| No users with rsvp_changes enabled | Log info message, no emails sent |
| Email address missing from form_data | Log warning, skip notification |
| Resend API down | Log error, decline still succeeds |
| User declines from 'accepted' | No notifications sent (working as designed) |
| Same user declines multiple times | Idempotent decline prevents duplicate emails |
| Director opts-in to notifications | Receives emails just like VPs (role-agnostic design) |

---

## Feature 4: Notification Preferences System

### Functional Requirements

#### FR-4.1: JSONB Structure

```json
{
  "announcements": "all" | "urgent_only" | "none",
  "rsvp_changes": true | false,
  "new_application_submitted": true | false
}
```

#### FR-4.2: Notification Types

##### Type 1: Announcements

- **Values**: `"all"`, `"urgent_only"`, `"none"`
- **Purpose**: Club-wide announcements from Co-presidents
- **Future Feature**: Not implemented yet, preserved from old system

##### Type 2: RSVP Changes

- **Values**: `true`, `false`
- **Purpose**: Notifications when attendees decline confirmed attendance
- **Audience**: Any user can opt-in (typically VPs, Co-presidents, event leads)
- **Implemented In**: Feature 3

##### Type 3: New Application Submitted

- **Values**: `true`, `false`
- **Purpose**: Notifications when new event applications submitted
- **Audience**: Any user can opt-in (typically VPs, Co-presidents, department leads)
- **Future Feature**: To be implemented

#### FR-4.3: Database Migration

**Phase 1**: Add JSONB column with data migration

- Add `notification_preferences` JSONB column
- Migrate existing `announcement_email_preference` values:
    - `"all"` → `{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}`
    - `"urgent_only"` → `{"announcements": "urgent_only", "rsvp_changes": false, "new_application_submitted": false}`
    - `"none"` → `{"announcements": "none", "rsvp_changes": false, "new_application_submitted": false}`
- Add NOT NULL constraint
- Add CHECK constraint to ensure required keys exist

**Phase 2**: Remove old column (after verification)

- Drop `announcement_email_preference` column
- Run after 7 days of production verification

#### FR-4.4: Constraint Validation

```sql
CHECK (
  notification_preferences ? 'announcements' AND
  notification_preferences ? 'rsvp_changes' AND
  notification_preferences ? 'new_application_submitted'
)
```

Ensures all three keys always present (prevents partial updates).

### Non-Functional Requirements

#### NFR-4.1: Backward Compatibility

- Old column kept temporarily during transition
- API supports both old and new fields during migration
- Frontend updated to use new structure

#### NFR-4.2: Extensibility

- JSONB allows adding new notification types without migration
- Frontend and backend updated via code changes only
- No schema changes required for new notification types

#### NFR-4.3: Query Performance

```sql
-- Efficient JSONB querying with GIN index
CREATE INDEX idx_notification_preferences
ON users USING GIN (notification_preferences);
```

### Implementation Details

#### Database Migration

**File**: `utesca-backend/database/migrations/add_notification_preferences.sql`

**Critical**: Applies to **BOTH** `test.users` and `prod.users` tables.

**Steps**:

1. Add JSONB column
2. Populate from existing data
3. Add NOT NULL constraint
4. Add CHECK constraint

**Rollback**:

```sql
ALTER TABLE test.users DROP CONSTRAINT notification_preferences_valid;
ALTER TABLE test.users DROP COLUMN notification_preferences;
-- Repeat for prod.users
```

#### Backend Changes

**File 1**: `utesca-backend/src/domains/auth/models.py`

Define new types:

```python
from typing import TypedDict

class NotificationPreferences(TypedDict):
    announcements: Literal["all", "urgent_only", "none"]
    rsvp_changes: bool
    new_application_submitted: bool
```

Update models:

- `UpdateProfileRequest`: Use `notification_preferences` field
- `UserResponse`: Use `notification_preferences` field

**File 2**: `utesca-backend/src/domains/users/repository.py`

Add helper method:

```python
def get_users_with_notification_enabled(
    self,
    notification_type: str
) -> List[UserResponse]:
    """
    Fetch all users who have a specific notification type enabled.
    Role-agnostic - queries by preference, not role.
    """
    ...
```

#### Frontend Changes

**File**: `utesca-portal-frontend/src/types/user.ts`

```typescript
export interface NotificationPreferences {
  announcements: 'all' | 'urgent_only' | 'none';
  rsvpChanges: boolean;
  newApplicationSubmitted: boolean;
}
```

### Migration Strategy

#### Pre-Migration

- [ ] Backup both test.users and prod.users tables
- [ ] Verify backup integrity
- [ ] Test migration script on test schema

#### Migration Execution

- [ ] Run migration on test schema
- [ ] Verify data: `SELECT id, notification_preferences FROM test.users LIMIT 10;`
- [ ] Run migration on prod schema
- [ ] Verify data: `SELECT id, notification_preferences FROM prod.users LIMIT 10;`

#### Post-Migration

- [ ] Deploy backend with new code
- [ ] Deploy frontend with new types
- [ ] Monitor for 7 days
- [ ] Drop old column: `ALTER TABLE users DROP COLUMN announcement_email_preference;`

### Querying Patterns

#### Get Users with RSVP Notifications Enabled

```sql
SELECT * FROM users
WHERE notification_preferences->>'rsvp_changes' = 'true';
```

#### Python/Supabase Query

```python
users = client.schema(schema).table("users") \
    .select("*") \
    .filter("notification_preferences->>rsvp_changes", "eq", "true") \
    .execute()
```

---

## Technical Architecture

### Layered Design

```
┌─────────────────────────────────────┐
│   Public API Layer                  │
│   (public_api.py)                   │
│   - HTTP request/response           │
│   - Background task orchestration   │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Service Layer                     │
│   (service.py)                      │
│   - Business logic                  │
│   - RSVP cutoff validation          │
│   - Leadership notification         │
└────────────┬────────────────────────┘
             │
             ├──────────────┬──────────────┐
             ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Registration │  │    User      │  │    Email     │
│  Repository  │  │  Repository  │  │   Service    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Design Principles Applied

#### Single Responsibility Principle (SRP)

- **Service**: Business logic and orchestration
- **Repository**: Data access only
- **EmailService**: Email delivery only
- **Templates**: Email content generation only

#### Open/Closed Principle (OCP)

- JSONB notification preferences extensible without changing structure
- New email templates added without modifying existing ones

#### Dependency Inversion Principle (DIP)

- Service depends on repository abstractions
- Email service injected, not hardcoded

#### Don't Repeat Yourself (DRY)

- Centralized helper methods (`_is_within_rsvp_cutoff`)
- Reusable email template patterns
- Shared constants for error messages

---

## API Specifications

### Modified Endpoints

#### GET /rsvp/{registration_id}

**Response Model Update**:

```json
{
  "event": { ... },
  "registration": { ... },
  "currentStatus": "confirmed",
  "canConfirm": false,
  "canDecline": false,
  "isFinal": false,
  "eventHasPassed": false,
  "withinRsvpCutoff": true  // NEW FIELD
}
```

#### POST /rsvp/{registration_id}/confirm

**New Error Response** (400):

```json
{
  "detail": "Cannot change RSVP - cutoff is 24 hours before event"
}
```

**When**: Current time within 24 hours of event start

#### POST /rsvp/{registration_id}/decline

**New Error Response** (400):

```json
{
  "detail": "Cannot change RSVP - cutoff is 24 hours before event"
}
```

**When**: Current time within 24 hours of event start

**New Behavior**: Triggers notifications to subscribed users if `previous_status == "confirmed"`

#### PUT /auth/profile

**Request Body Update**:

```json
{
  "notificationPreferences": {
    "announcements": "all",
    "rsvpChanges": true,
    "newApplicationSubmitted": false
  }
}
```

**Response**: Standard `UserResponse` with updated preferences

---

## Database Schema Changes

### Users Table

#### New Column

```sql
notification_preferences JSONB NOT NULL
```

#### Constraints

```sql
-- Ensure all required keys exist
CHECK (
  notification_preferences ? 'announcements' AND
  notification_preferences ? 'rsvp_changes' AND
  notification_preferences ? 'new_application_submitted'
)

-- Optional: Add GIN index for query performance
CREATE INDEX idx_notification_preferences
ON users USING GIN (notification_preferences);
```

#### Migration Logic

```sql
-- Example for test.users (repeat for prod.users)
ALTER TABLE test.users ADD COLUMN notification_preferences JSONB;

UPDATE test.users
SET notification_preferences =
  CASE
    WHEN announcement_email_preference = 'all' THEN
      '{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}'::jsonb
    WHEN announcement_email_preference = 'urgent_only' THEN
      '{"announcements": "urgent_only", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
    WHEN announcement_email_preference = 'none' THEN
      '{"announcements": "none", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
  END;

ALTER TABLE test.users ALTER COLUMN notification_preferences SET NOT NULL;

ALTER TABLE test.users ADD CONSTRAINT notification_preferences_valid
CHECK (
  notification_preferences ? 'announcements' AND
  notification_preferences ? 'rsvp_changes' AND
  notification_preferences ? 'new_application_submitted'
);
```

---

## Error Handling

### HTTP Status Codes

| Code | Scenario | Example |
|------|----------|---------|
| 200 OK | Successful operation | RSVP confirmed |
| 400 Bad Request | Invalid state or timing | Within 24-hour cutoff |
| 404 Not Found | Registration not found | Invalid UUID |
| 500 Internal Server Error | System failure | Database error |

### Error Messages

#### User-Facing Errors

- Clear, actionable messages
- No internal implementation details exposed
- Contact information provided for manual override

#### Internal Error Logging

```python
logger.error(
    f"Failed to send decline notification for registration {registration.id}: {str(e)}",
    exc_info=True
)
```

### Email Failure Handling

**Philosophy**: Email failures should not block core operations

```python
try:
    email_service.send_notification(...)
except Exception as e:
    logger.error(f"Email failed: {e}", exc_info=True)
    # Continue execution - decline still succeeds
```

---

## Testing Requirements

### Unit Tests

#### Feature 1: 24-Hour Cutoff

```python
def test_cutoff_before_24_hours():
    """Test that cutoff returns False when >24 hours before event"""
    service = RegistrationService()
    event_time = datetime.now(timezone.utc) + timedelta(hours=25)
    assert service._is_within_rsvp_cutoff(event_time) == False

def test_cutoff_within_24_hours():
    """Test that cutoff returns True when <24 hours before event"""
    service = RegistrationService()
    event_time = datetime.now(timezone.utc) + timedelta(hours=23)
    assert service._is_within_rsvp_cutoff(event_time) == True
```

#### Feature 3: Decline Notifications

```python
def test_notification_filters_by_preference():
    """Only users with rsvp_changes=true should receive emails"""
    # Mock users with different preferences
    # Verify only those with rsvp_changes=true get emails
    pass

def test_no_notification_for_accepted_decline():
    """Declining from 'accepted' should NOT notify leadership"""
    # Only 'confirmed' -> 'not_attending' triggers notification
    pass
```

#### Feature 4: Notification Migration

```python
def test_migration_from_all_preference():
    """'all' should migrate to all notifications enabled"""
    # Verify migration SQL logic
    pass
```

### Integration Tests

```python
def test_end_to_end_cutoff_enforcement():
    """
    1. Create event 23 hours in future
    2. Verify API returns 400 on confirm/decline
    3. Verify metadata flags are correct
    """
    pass

def test_end_to_end_decline_notification():
    """
    1. User registers and confirms
    2. User declines
    3. Verify leadership receives email
    4. Verify user receives confirmation
    """
    pass
```

### Manual Test Scenarios

#### Scenario 1: 24-Hour Cutoff

1. Create event with `date_time = now + 30 hours`
2. Register and confirm attendance
3. Verify RSVP page shows enabled buttons
4. Simulate time passing to `now + 23 hours`
5. Refresh page
6. Verify buttons disabled, cutoff message shown
7. Try API call → expect 400 error

#### Scenario 2: Decline Notification

1. Setup: 2 users with `rsvp_changes=true` (e.g., 1 VP, 1 Director), 1 VP with `rsvp_changes=false`
2. User confirms attendance
3. User declines
4. Verify 2 subscribed users receive email, 1 does not (regardless of role)
5. Check email content includes correct details

#### Scenario 3: Empty Fields Display

1. Create form with 3 required + 3 optional fields
2. Submit with only required fields filled
3. Open ApplicationDetailModal
4. Verify all 6 fields shown
5. Verify optional fields show "—" with "(optional)" label

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All code reviewed and approved
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Database backup created
- [ ] Migration script tested on test schema

### Deployment Steps

#### Day 1: Feature 4 (Database Migration)

**Morning**:

1. Backup `test.users` and `prod.users` tables
2. Run migration on `test.users`
3. Verify data: `SELECT * FROM test.users LIMIT 10;`
4. Test application with test database

**Afternoon**:
5. Run migration on `prod.users`
6. Verify data: `SELECT * FROM prod.users LIMIT 10;`
7. Deploy backend with new models
8. Deploy frontend with new types
9. Monitor logs for errors

#### Day 2: Feature 1 (RSVP Cutoff)

1. Deploy backend changes (service layer)
2. Deploy frontend changes (RSVP page)
3. Test with events at various time offsets
4. Monitor error rates

#### Day 3: Feature 2 (Empty Fields)

1. Deploy frontend changes (ApplicationDetailModal)
2. Verify in portal with test registrations
3. Get user feedback

#### Day 4: Feature 3 (Decline Notifications)

1. Deploy backend changes (email templates, service methods)
2. Test with test event and user decline
3. Verify emails delivered via Resend dashboard
4. Monitor email send rates

### Post-Deployment Monitoring

- [ ] Check error rates for RSVP endpoints
- [ ] Verify email delivery success rate (>95%)
- [ ] Monitor database query performance
- [ ] Collect user feedback on portal changes

### Rollback Plan

#### If Feature 4 Migration Fails

```sql
ALTER TABLE test.users DROP CONSTRAINT notification_preferences_valid;
ALTER TABLE test.users DROP COLUMN notification_preferences;
ALTER TABLE prod.users DROP CONSTRAINT notification_preferences_valid;
ALTER TABLE prod.users DROP COLUMN notification_preferences;
-- Restore from backup
```

#### If Feature 3 Causes Issues

Comment out subscriber notification in `public_api.py`:

```python
# if event and previous_status == "confirmed":
#     background_tasks.add_task(...)
```

---

## Future Enhancements

### Phase 2 Features

#### 1. Configurable Cutoff Time

Allow event organizers to set custom cutoff (12h, 48h, etc.) per event.

```python
# Event model
cutoff_hours: Optional[int] = 24  # Default to 24, customizable
```

#### 2. Waitlist Auto-Promotion

When confirmed attendee declines, automatically notify waitlisted users.

#### 3. RSVP Reminders

Send email reminders to users who haven't RSVP'd within X days of event.

```json
{
  "rsvp_reminders": true  // New notification preference
}
```

#### 4. SMS Notifications

For urgent changes, send SMS in addition to email.

#### 5. Analytics Dashboard

Track RSVP patterns:

- Decline rate by time before event
- Most common decline timing
- Leadership notification open rates

---

## Appendix

### Related Documentation

- [Event Registration & RSVP Workflow](./event-registration-rsvp-workflow.md)
- [Email Service Documentation](../src/core/email/README.md)
- [Database Schema Documentation](../database/README.md)

### Glossary

- **RSVP**: Répondez s'il vous plaît (please respond) - confirmation of attendance
- **Cutoff**: Time before event when RSVP changes are no longer allowed
- **Subscribed Users**: Users who have opted-in to specific notification types (role-agnostic)
- **JSONB**: PostgreSQL JSON Binary format for efficient JSON storage
- **Background Task**: Asynchronous operation that doesn't block API response

### Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2026 | Rachel (Web VP) | Initial specification |

---

**Document Status**: ✅ Ready for Implementation
**Next Review**: After deployment completion

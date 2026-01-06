# Event Registration & RSVP Workflow

## Overview

This document describes the complete event registration lifecycle in the UTESCA Portal, from initial submission through RSVP confirmation/decline and final check-in at the event.

## Registration Status State Machine

```text
                    ┌─────────────┐
                    │  submitted  │ (Initial application)
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
         ┌──────────┐          ┌──────────┐
         │ accepted │          │ rejected │
         └────┬─────┘          └──────────┘
              │
              ├──────────────────┐
              │                  │
              ▼                  ▼
       ┌───────────┐      ┌───────────────┐
       │ confirmed │      │ not_attending │
       └─────┬─────┘      └───────────────┘
             │
             ▼
      ┌─────────────┐
      │ checked_in  │ (flag, not a status)
      └─────────────┘
```

### Status Definitions

| Status | Description | Can Transition To | Terminal | Public RSVP Access |
|--------|-------------|-------------------|----------|-------------------|
| **submitted** | Initial application submitted by user | accepted, rejected | No | No |
| **accepted** | Application approved, awaiting RSVP confirmation | confirmed, not_attending | No | Yes |
| **rejected** | Application denied by organizer | - | Yes | No |
| **confirmed** | User confirmed attendance via RSVP | not_attending, checked_in | No | Yes |
| **not_attending** | User declined attendance (irreversible) | - | Yes | Yes |

**Terminal Statuses**: Once a registration reaches `rejected` or `not_attending`, it cannot be changed programmatically. Users must contact organizers directly to reverse these decisions.

---

## Complete Workflow

### 1. Registration Submission

**Trigger**: User fills out public event registration form

**Process**:

1. User submits registration form via `POST /public/registrations`
2. Backend validates form data and event capacity
3. System determines approval workflow based on event settings:
   - **Auto-accept**: If enabled, status → `accepted`
   - **Manual review**: If disabled, status → `submitted`

**Database Changes**:

- New record created in `event_registrations` table
- `submitted_at` timestamp recorded
- `form_data` stored as JSONB

**Email Sent**:

- **Auto-accept**: Registration confirmation email with RSVP link
- **Manual review**: "Application Received" email (no RSVP link yet)

---

### 2. Manual Review & Approval (if applicable)

**Trigger**: Co-president or VP reviews pending applications

**Process**:

1. Admin views registration in portal dashboard
2. Admin approves or rejects application via `POST /registrations/{id}/accept` or `POST /registrations/{id}/reject`
3. Status transitions:
   - **Approve**: `submitted` → `accepted`
   - **Reject**: `submitted` → `rejected` (TERMINAL)

**Email Sent**:

- **Approval**: Registration confirmation email with RSVP link
- **Rejection**: No email sent (policy decision)

---

### 3. RSVP Confirmation (New ID-Based System)

**Trigger**: User clicks RSVP link in confirmation email

**RSVP Link Format**: `https://utesca.ca/rsvp/{registration_id}`

#### 3.1 View RSVP Page

**Endpoint**: `GET /rsvp/{registration_id}`

**Access Control**:

- Public endpoint (no authentication required)
- Only returns registrations with status in: `['accepted', 'confirmed', 'not_attending']`
- Returns 404 for `submitted` or `rejected` registrations

**Response Includes**:

```json
{
  "event": {
    "title": "UTESCA Networking Night",
    "dateTime": "2025-02-15T18:00:00Z",
    "location": "SF1101",
    "description": "..."
  },
  "registration": {
    "status": "accepted",
    "submittedAt": "2025-01-20T10:30:00Z",
    "confirmedAt": null
  },
  "currentStatus": "accepted",
  "canConfirm": true,
  "canDecline": true,
  "isFinal": false,
  "eventHasPassed": false
}
```

**UI Display Logic**:

- **Status = accepted**: Show "Confirm Attendance" button + "I am no longer able to attend" decline link
- **Status = confirmed**: Show current status with "Unable to make it?" decline link
- **Status = not_attending**: Show "You are no longer attending this event. This decision is final." (no actions)
- **Event has passed**: Disable all actions, show past event message

---

#### 3.2 Confirm Attendance

**Endpoint**: `POST /rsvp/{registration_id}/confirm`

**Validation**:

1. Registration must exist and be publicly accessible
2. Current status must be `accepted`
3. Event date must not have passed
4. Status cannot be terminal (`not_attending` or `rejected`)

**Process**:

1. Status transitions: `accepted` → `confirmed`
2. `confirmed_at` timestamp recorded
3. Confirmation email sent in background task

**Email Sent**:

- Subject: "You're Confirmed for {event_title}!"
- Body includes:
    - Event details (date, time, location)
    - Current RSVP status: Confirmed
    - RSVP link to change response
    - Warning: "Note that declining attendance is final and cannot be reversed"

**Idempotent**: Calling confirm on already confirmed registration returns success without changes

**Error Cases**:

- `404 Not Found`: Registration not found or not accessible
- `400 Bad Request`: "Cannot confirm attendance - event has already passed"
- `400 Bad Request`: "Registration is not eligible for confirmation" (wrong status)

---

#### 3.3 Decline Attendance (TERMINAL Operation)

**Endpoint**: `POST /rsvp/{registration_id}/decline`

**Validation**:

1. Registration must exist and be publicly accessible
2. Current status must be `accepted` or `confirmed`
3. Event date must not have passed
4. Status cannot already be terminal

**Process**:

1. Status transitions: `accepted` OR `confirmed` → `not_attending` (TERMINAL)
2. `confirmed_at` timestamp recorded (represents decline time)
3. Decline confirmation email sent in background task

**Email Sent**:

- Subject: "RSVP Response Received for {event_title}"
- Body emphasizes:
  - "You are no longer attending {event_title}"
  - "This change is final and cannot be reversed"
  - "If you need to change this, please contact uoft.esca@gmail.com"

**Idempotent**: Calling decline on already declined registration returns success without changes

**Important Notes**:

- **This is a TERMINAL operation** - once declined, user cannot re-confirm through the system
- Users must contact organizers directly to reverse (manual database update required)
- `not_attending` registrations CANNOT be checked in at the event

**Error Cases**:

- `404 Not Found`: Registration not found or not accessible
- `400 Bad Request`: "Cannot decline attendance - event has already passed"
- `400 Bad Request`: "Registration is not eligible for declining"

---

### 4. Event Check-In

**Trigger**: User arrives at event, admin scans QR code or searches by name

**Endpoint**: `POST /attendance/check-in`

**Validation**:

1. Registration must exist
2. Status must be `accepted` OR `confirmed`
3. **CRITICAL**: Status CANNOT be `not_attending`

**Process**:

1. `checked_in` flag set to `true`
2. `checked_in_at` timestamp recorded
3. `checked_in_by` admin user ID recorded

**Error Cases**:

- `400 Bad Request`: "Cannot check in a registration marked as not attending"
- `400 Bad Request`: "Only accepted or confirmed registrations can be checked in"
- `409 Conflict`: "Already checked in or invalid status"

**Note**: `checked_in` is a boolean flag, not a status. Registrations can be `confirmed` + `checked_in = true`.

---

## Email Flow Summary

| Trigger | Email Type | Contains RSVP Link | Recipient Status |
|---------|-----------|-------------------|------------------|
| Auto-accept registration | Registration Confirmation | ✅ Yes | accepted |
| Manual approval | Registration Confirmation | ✅ Yes | accepted |
| Manual review submission | Application Received | ❌ No | submitted |
| User confirms via RSVP | Attendance Confirmed | ✅ Yes | confirmed |
| User declines via RSVP | Attendance Declined | ❌ No | not_attending |

### Email Templates

#### Registration Confirmation Email

```
Subject: Registration Received: {event_title}

Hi {full_name},

Your registration for {event_title} has been received. We're excited to see you there.

Event Details:
Date & Time: {event_datetime}
Location: {event_location}

Confirm Your Attendance:
{base_url}/rsvp/{registration_id}

We look forward to seeing you there!
```

#### Attendance Confirmed Email

```
Subject: You're Confirmed for {event_title}!

Hi {full_name},

Great news! You are confirmed for {event_title}. We look forward to seeing you there!

Event Details:
Date & Time: {event_datetime}
Location: {event_location}

Unable to make it? You can change your RSVP response using the link below. Please note that declining is final.
{base_url}/rsvp/{registration_id}
```

#### Attendance Declined Email

```
Subject: RSVP Response Received for {event_title}

Hi {full_name},

You are no longer attending {event_title}. We have received your RSVP response.

Event: {event_title}
Date & Time: {event_datetime}
Location: {event_location}

Please note: This change is final and cannot be reversed. If you change your mind, please contact us directly at uoft.esca@gmail.com.

We hope to see you at future UTESCA events!
```

---

## Event Date Validation

**Rule**: No RSVP changes (confirm or decline) are allowed after the event date has passed.

**Implementation**:

- `service._has_event_passed(event_date)` helper method
- Compares current UTC time with event datetime (converted to UTC)
- Applied to both confirm and decline operations
- Returns `400 Bad Request` with clear error message

**Frontend Display**:

- RSVP page shows `eventHasPassed: true` flag
- UI disables confirm/decline buttons
- Message: "This event has already occurred. RSVP is no longer available."

---

## Analytics Integration

### Approval Rate

```
(accepted + confirmed + not_attending) / total * 100
```
**Rationale**: Users who declined (`not_attending`) were initially approved, so they count toward approval rate.

### Attendance Rate

```
checked_in / confirmed * 100
```
**Rationale**: Only users who explicitly confirmed attendance (`confirmed` status) should count toward expected attendance. `not_attending` users are excluded from the denominator.

### Portal Dashboard Tabs

1. All Registrations
2. Submitted (pending review)
3. Accepted (awaiting RSVP)
4. Rejected
5. Confirmed (RSVP confirmed)
6. **Not Attending** (declined RSVP)

---

## Security & Access Control

### Public RSVP Access (No Auth Required)

- **Endpoints**: `/rsvp/{registration_id}/*`
- **Access Level**: Public (anyone with the link)
- **Filtered Statuses**: Only `accepted`, `confirmed`, `not_attending` are accessible
- **Security Consideration**: Registration IDs are UUIDs (high entropy, hard to guess)
- **Sharing Method**: Links sent via email to registered email address

### Why ID-Based Instead of Token-Based?

- **Simplicity**: Eliminates need for separate token generation and storage
- **Transparency**: Users can reference their registration ID in communications
- **No Expiration**: Links remain valid indefinitely (user-friendly)
- **Security**: UUIDs provide sufficient entropy (128-bit randomness)

---

## Error Handling

### HTTP Status Codes

| Code | Scenario | Example |
|------|----------|---------|
| `200 OK` | Successful operation | RSVP confirmed successfully |
| `400 Bad Request` | Invalid state transition | Confirming a rejected registration |
| `404 Not Found` | Registration not found or not accessible | Wrong UUID or submitted/rejected status |
| `409 Conflict` | Already checked in | Attempting duplicate check-in |
| `500 Internal Server Error` | Database update failed | Unexpected system error |

### User-Friendly Error Messages

All error responses include clear, actionable messages:
- "Registration not found or not accessible" (don't leak internal status)
- "Cannot confirm attendance - event has already passed"
- "Registration is not eligible for confirmation" (generic for security)
- "Cannot check in a registration marked as not attending" (specific for admins)

---

## Edge Cases & Business Rules

### 1. Idempotent Operations

**Problem**: User clicks "Confirm" button multiple times
**Solution**: Service checks current status and returns success if already confirmed/declined

### 2. Terminal Status Enforcement

**Problem**: User wants to re-confirm after declining
**Solution**: `not_attending` is terminal - UI shows "This decision is final", backend blocks state transitions

### 3. Event Date Passed

**Problem**: User tries to RSVP after event date
**Solution**: Backend validates event datetime, returns 400 error, frontend disables actions

### 4. Check-In Prevention

**Problem**: Admin tries to check in a `not_attending` registration
**Solution**: Explicit validation in `check_in_attendee()` and `bulk_check_in()` with clear error message

### 5. Race Conditions

**Problem**: Two admins approve same registration simultaneously
**Solution**: Database constraints ensure single status update, idempotent design prevents issues

---

## Implementation Architecture

### Layered Design (Following SOLID Principles)

```
┌─────────────────────────────────────┐
│   Public API Layer                  │
│   (public_api.py)                   │
│   - Input validation                │
│   - HTTP request/response handling  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Service Layer                     │
│   (service.py)                      │
│   - Business logic                  │
│   - State validation                │
│   - Email orchestration             │
│   - Event date checking             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Repository Layer                  │
│   (repository.py)                   │
│   - Data access                     │
│   - Database queries                │
│   - Status filtering                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Database (Supabase PostgreSQL)    │
│   - event_registrations table       │
│   - registration_status enum        │
│   - RLS policies                    │
└─────────────────────────────────────┘
```

### Key Design Patterns

1. **Repository Pattern**: Data access abstraction
2. **Service Layer Pattern**: Business logic separation
3. **State Machine Pattern**: Registration status transitions
4. **Background Tasks**: Non-blocking email delivery (FastAPI BackgroundTasks)
5. **Idempotent Operations**: Safe to retry confirm/decline
6. **DRY Principle**: Constants for error messages

---

## Testing Recommendations

### Unit Tests

- [x] `_has_event_passed()` with various timezones
- [x] `rsvp_confirm_by_id()` with all possible statuses
- [x] `rsvp_decline_by_id()` with terminal status validation
- [x] Repository methods with status filtering
- [x] Email template generation

### Integration Tests

- [x] End-to-end RSVP flow: register → accept → confirm
- [x] End-to-end decline flow: register → accept → decline (verify terminal)
- [x] Email delivery for all RSVP actions
- [x] Check-in prevention for `not_attending` status
- [x] Event date validation blocks past events

### Manual Testing Scenarios

1. **Happy Path**: Submit → Auto-accept → Confirm → Check-in
2. **Decline Path**: Submit → Manual accept → Decline (verify final)
3. **Past Event**: Try to confirm/decline after event date passes
4. **Terminal Status**: Try to confirm after declining
5. **Check-In Block**: Verify `not_attending` cannot be checked in

---

## Deployment Checklist

### Database

- [ ] Run `add_not_attending_status_migration.sql`
- [ ] Run `update_analytics_rpc_function.sql`
- [ ] Verify enum values: `SELECT enumlabel FROM pg_enum WHERE enumtypid = 'registration_status'::regtype;`

### Backend

- [ ] Deploy updated API, service, repository layers
- [ ] Verify new endpoints: `/rsvp/{id}`, `/rsvp/{id}/confirm`, `/rsvp/{id}/decline`
- [ ] Verify old token endpoints return 404
- [ ] Test email sending for confirm/decline actions
- [ ] Test check-in prevention for `not_attending` status

### Frontend (Portal)

- [ ] Deploy portal with updated TypeScript types
- [ ] Verify "Not Attending" tab appears on dashboard
- [ ] Verify analytics calculations include `not_attending`
- [ ] Test status badge displays correctly

### Monitoring

- [ ] Monitor error rates for new RSVP endpoints
- [ ] Track email delivery success rates
- [ ] Verify no check-ins occur for `not_attending` registrations
- [ ] Monitor analytics calculation accuracy

---

## Future Enhancements

### Potential Improvements

1. **Waitlist System**: Auto-promote when confirmed users decline
2. **RSVP Reminders**: Scheduled emails for users who haven't RSVP'd
3. **Decline Reasons**: Optional feedback when users decline (analytics)
4. **QR Codes**: Generate unique QR codes for confirmed registrations
5. **Calendar Integration**: .ics file attachment in confirmation emails
6. **SMS Notifications**: Text message reminders for confirmed attendees

---

## Support & Contact

For questions about this workflow or to request changes to a `not_attending` status:

- **Email**: uoft.esca@gmail.com
- **Portal**: Internal admin dashboard for manual status updates

---

**Last Updated**: January 2025
**Document Version**: 1.0
**Related**: See `completed-jira-work-items.md` for implementation details

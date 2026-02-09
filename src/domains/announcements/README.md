# Announcements Domain

The Announcements domain handles sending system-wide announcements to all users via email.

## Features

- **Send Announcements**: Send emails to all users or filtered by email preferences
- **Priority Levels**: Support for normal and urgent priority announcements
- **User Preferences**: Respects user email notification preferences (all, urgent_only, none)
- **Audit Trail**: Records all announcements sent with delivery statistics
- **Admin Only**: All announcement operations require co-president (admin) access

## API Endpoints

### Send Announcement
**POST** `/api/v1/announcements/send`

Sends an announcement email to users based on their preferences.

**Requirements:**
- Admin access (co-president role)

**Request Body:**
```json
{
  "subject": "Important Update",
  "message": "This is the announcement message body.",
  "priority": "normal"
}
```

**Parameters:**
- `subject` (string, required): Email subject line (1-255 characters)
- `message` (string, required): Email message body as plain text
- `priority` (string, optional): "normal" or "urgent" (default: "normal")
  - When set to "urgent", "[URGENT]" is prepended to the subject
- For "urgent", emails send to everyone regardless of preferences
- For "normal", emails only send to users with `announcements` preference enabled

**Response:**
```json
{
  "success": true,
  "message": "Announcement sent to 45 users",
  "stats": {
    "totalRecipients": 50,
    "emailsSent": 45,
    "emailsSkipped": 5,
    "failedEmails": 0
  },
  "announcementId": "550e8400-e29b-41d4-a716-446655440000",
  "createdAt": "2024-01-21T10:30:00Z"
}
```

### Get Announcements
**GET** `/api/v1/announcements/`

Retrieves a paginated list of announcements that have been sent.

**Requirements:**
- Admin access (co-president role)

**Query Parameters:**
- `page` (integer, optional): Page number (1-indexed, default: 1)
- `pageSize` (integer, optional): Number of items per page (default: 50)

**Response:**
```json
{
  "total": 25,
  "announcements": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "subject": "Important Update",
      "message": "This is the announcement message body.",
      "priority": "normal",
      "sentById": "660e8400-e29b-41d4-a716-446655440001",
      "totalRecipients": 50,
      "emailsSent": 45,
      "createdAt": "2024-01-21T10:30:00Z",
      "updatedAt": "2024-01-21T10:30:00Z"
    }
  ],
  "page": 1,
  "pageSize": 50
}
```

## Email Preferences

Users can set their announcement email preference through the profile update endpoint in the auth domain. The preference controls which announcements they receive:

- **"all"**: Receives all announcements (normal and urgent)
- **"urgent_only"**: Receives only announcements marked as urgent
- **"none"**: Never receives announcement emails

Users can set this in `/api/v1/auth/profile` using:
```json
{
  "announcementEmailPreference": "urgent_only"
}
```

## Implementation Details

### Architecture

The announcements domain follows the same pattern as other domains:
- **models.py**: Pydantic request/response schemas
- **repository.py**: Data access layer for database operations
- **service.py**: Business logic and email sending orchestration
- **api.py**: FastAPI router and endpoint definitions

### Email Delivery

The announcement service uses Supabase's Admin Auth API to send emails:

1. Admin sends announcement request with subject, message, and priority
2. Service fetches all users from the database
3. For each user, checks if email should be sent based on priority and preferences
4. Sends emails via Supabase Auth's email service
5. Records announcement in database with delivery statistics
6. Returns summary including sent/skipped/failed counts

### Database Schema

**announcements table:**
```sql
- id: UUID (primary key)
- subject: VARCHAR(255)
- message: TEXT
- priority: ENUM ('normal', 'urgent')
- sent_by_id: UUID (foreign key to users)
- total_recipients: INTEGER
- emails_sent: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

## Usage Example

### Send an urgent announcement:
```bash
curl -X POST http://localhost:8000/api/v1/announcements/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Server Maintenance Tonight",
    "message": "The system will be under maintenance from 10 PM to 2 AM tonight. Please plan accordingly.",
    "priority": "urgent"
  }'
```

### Get announcements history:
```bash
curl http://localhost:8000/api/v1/announcements/?page=1&pageSize=10 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Notes

- All announcement endpoints require admin (co-president) authentication
- Emails are sent asynchronously via Supabase, so they may not be instantly delivered
- The service respects user email preferences for normal priority announcements
- Urgent announcements bypass preferences and send to everyone
- All announcements are logged in the database for audit purposes
- Failed emails are tracked but don't prevent the operation from completing

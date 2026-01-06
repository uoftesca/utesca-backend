# Database Guide

The UTESCA Portal uses **Supabase** (PostgreSQL) containing two schemas:

- **`test` schema**: For local development and testing
- **`prod` schema**: For live production data

## Database Schema Details

### Schema Architecture

```
utesca-portal (Supabase Database)
├── public schema
│   └── Shared enums (user_role, event_status, etc.)
├── test schema
│   ├── departments
│   ├── users
│   ├── events
│   ├── event_registrations
│   ├── announcements
│   ├── announcement_reads
│   ├── application_cycles
│   └── applications
└── prod schema
    ├── departments
    ├── users
    ├── events
    ├── event_registrations
    ├── announcements
    ├── announcement_reads
    ├── application_cycles
    └── applications
```

### Tables Overview (in both test and prod schemas)

| Table | Purpose |
|-------|---------|
| `users` | Executive team member profiles (extends Supabase Auth) |
| `departments` | Club departments (Marketing, Events, etc.) |
| `events` | Published events and drafts |
| `event_registrations` | Student registrations for events |
| `announcements` | Club-wide communications |
| `announcement_reads` | Track who read which announcements |
| `application_cycles` | Recruitment periods |
| `applications` | Position applications |
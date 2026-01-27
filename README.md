# utesca-backend

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### 1. Create a Python Virtual Environment

```bash
cd backend
# Create a new virtual environment
python -m venv venv

# On macOS/Linux, activate the virtual environment:
source venv/bin/activate

# On Windows, activate the virtual environment:
# venv\Scripts\activate
```

### 2. Install Dependencies

Install FastAPI and all required dependencies using the requirements.txt file:

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

You can verify FastAPI is installed correctly by running:

```bash
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
```

### 4. Deactivate Virtual Environment

When you're done working on the project, you can deactivate the virtual environment:

```bash
deactivate
```

## Project Structure

This backend is organized using **Domain-Driven Design (DDD)** principles, where code is structured by business domains rather than technical layers.

```
utesca-backend/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/                      # Core application components
│   │   ├── config.py             # Application settings
│   │   └── security.py           # Authentication & security
│   ├── api/                       # API layer
│   │   └── v1/
│   │       └── router.py         # Main API router
│   ├── domains/                   # Business domains
│   │   ├── events/               # Events domain
│   │   │   ├── schemas.py        # Pydantic schemas
│   │   │   ├── repository.py     # Data access layer
│   │   │   ├── service.py        # Business logic layer
│   │   │   └── api.py            # API endpoints
│   │   ├── users/                # Users domain
│   │   └── projects/             # Projects domain
│   └── utils/                     # Utility functions
├── tests/                         # Test modules
└── requirements.txt               # Python dependencies
```

### Domain Structure

- **`schemas.py`** - Pydantic models for API request/response
- **`repository.py`** - Data access layer (database operations)
- **`service.py`** - Business logic layer
- **`api.py`** - FastAPI endpoints and HTTP handling

## Running the Application

### Development Server

```bash
# Make sure you're in the backend directory and virtual environment is active
cd utesca-backend
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
cd src
python main.py

# Or using FastAPI CLI
fastapi dev main.py
```

### Production Server

```bash
# Using uvicorn directly for production
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Docs**: `http://127.0.0.1:8000/api/v1/docs`
- **Alternative Docs**: `http://127.0.0.1:8000/api/v1/redoc`

## API Structure

All API endpoints are versioned and prefixed with `/api/v1`:

- **Authentication**: `/api/v1/auth/` - Sign in, invitations, profile management
- **Users**: `/api/v1/users/` - User management and team members
- **Departments**: `/api/v1/departments/` - Department management
- **Events**: `/api/v1/events/` - Event creation, management, and analytics
- **Attendance**: `/api/v1/events/attendance/` - Event attendance tracking
- **Event Registrations**: `/api/v1/registrations/` - User event registrations
- **Portal Registrations**: `/api/v1/portal/` - Portal-specific registrations
- **Announcements**: `/api/v1/announcements/` - Send announcements to all users via email

### Announcements Domain

The Announcements domain allows administrators (co-presidents) to send system-wide announcements to all users via email. Key features:

- **Email Notifications**: Send announcements to all users with user preference filtering
- **Priority Levels**: Support for "normal" and "urgent" priority announcements
- **User Preferences**: Respects user email notification preferences (all, urgent_only, none)
- **Delivery Tracking**: Records all announcements with delivery statistics

**Endpoints:**
- `POST /api/v1/announcements/send` - Send an announcement to users
- `GET /api/v1/announcements/` - Get history of sent announcements

**Example Usage:**
```bash
# Send an urgent announcement
curl -X POST http://localhost:8000/api/v1/announcements/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Important Update",
    "message": "This is an important announcement.",
    "priority": "urgent",
    "sendToAll": true
  }'

# Get announcements history
curl http://localhost:8000/api/v1/announcements/?page=1&pageSize=10 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

See [src/domains/announcements/README.md](src/domains/announcements/README.md) for detailed documentation.


## Announcements

Announcement emails are sent through Supabase using the same admin email provider as user invitations.

Endpoints (admin only):
- POST /api/v1/announcements/send
- GET /api/v1/announcements/

Send announcement request body:
- subject: Email subject line
- message: Email message body (plain text)
- priority: normal | urgent (optional, default: normal)
- send_to_all: true | false (optional, default: true). If false, respects announcement_email_preference.

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/announcements/send   -H "Authorization: Bearer <ACCESS_TOKEN>"   -H "Content-Type: application/json"   -d '{"subject":"Meeting Reminder","message":"See you at 6pm.","priority":"normal","send_to_all":true}'
```

## Testing

Run tests using pytest:

```bash
# Run tests
pytest
```

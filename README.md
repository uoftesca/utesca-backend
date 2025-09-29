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
│   │   ├── database.py           # Database configuration
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
├── requirements.txt               # Python dependencies
└── env.example                   # Environment variables template
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

- **Events**: `/api/v1/events/`
- **Users**: `/api/v1/users/`
- **Projects**: `/api/v1/projects/`

## Testing

Run tests using pytest:

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

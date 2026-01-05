"""
UTESCA Portal Backend - FastAPI Application

This is the main entry point for the UTESCA Portal backend API.
It configures FastAPI, CORS, middleware, and database connections.

Environment:
- Uses PostgreSQL schemas (test/prod) for environment separation
- Automatically connects to the correct schema based on ENVIRONMENT variable
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_router
from core.config import get_settings
from core.database import get_schema, get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Get settings instance
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Runs on startup and shutdown to manage resources.
    """
    # Startup
    print("=" * 60)
    print("UTESCA Portal API - Starting")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database Schema: {get_schema()}")
    print("=" * 60)

    # Initialize Supabase client (cached)
    try:
        _ = get_supabase_client()
        print("SUCCESS: Connected to Supabase")
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")
        raise

    yield

    # Shutdown
    print("UTESCA Portal API - Shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="""
    Internal management system for the University of Toronto
    Engineering Student Club Association.
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
)


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API health check.

    Returns basic information about the API and its current configuration.
    """
    return JSONResponse(
        {
            "message": "UTESCA Portal API",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "schema": get_schema(),
            "docs": f"{settings.API_V1_PREFIX}/docs",
            "status": "healthy",
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Used by deployment platforms (Vercel, etc.) to verify the API is running.
    """
    try:
        # Test database connection
        _ = get_supabase_client()

        return JSONResponse(
            {
                "status": "healthy",
                "environment": settings.ENVIRONMENT,
                "database_schema": get_schema(),
                "database_connected": True,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e), "database_connected": False}
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    Logs the error and returns a generic error response to the client.
    """
    print(f"ERROR: Unhandled exception: {exc}")

    # In production, don't expose internal error details
    error_detail = str(exc) if not settings.is_production else "Internal server error"

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": error_detail if not settings.is_production else None},
    )


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info",
    )

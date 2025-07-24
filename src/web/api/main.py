"""
GSC-CLI's FastAPI Application

This is the main application module that sets up the FastAPI app
and includes all routers. The API is now modularized for better
organization and maintainability.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import container
from .routers import analytics, health, performance, queries, sites, sync

# Create FastAPI app
app = FastAPI(
    title="GSC-CLI API",
    description="API for accessing and managing Google Search Console data (Multi-Process Ready).",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add startup event to log process information
@app.on_event("startup")
async def startup_event():
    """Log startup information including process ID"""
    print(f"FastAPI starting in process {os.getpid()}")
    # Ensure database is initialized for this process
    db = container.database()
    if hasattr(db, "get_connection_info"):
        info = db.get_connection_info()
        print(f"Database connection info: {info}")


# Add shutdown event to clean up connections
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown"""
    print(f"FastAPI shutting down in process {os.getpid()}")
    db = container.database()
    if hasattr(db, "close_all_connections"):
        db.close_all_connections()


# Include routers
app.include_router(health.router)
app.include_router(sites.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")
app.include_router(performance.router)
app.include_router(sync.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "GSC-CLI API",
        "version": "0.3.0",
        "description": "Google Search Console data management API",
        "documentation": "/docs",
        "health_check": "/health",
    }

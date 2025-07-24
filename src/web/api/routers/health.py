"""
Health Check Router

API endpoints for health checks and system status.
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from src.services.database import Database

from ..dependencies import get_database

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check(db: Database = Depends(get_database)):
    """Health check endpoint that also shows process information"""
    connection_ok = db.check_connection()

    response = {
        "status": "healthy" if connection_ok else "unhealthy",
        "process_id": os.getpid(),
        "database_connected": connection_ok,
    }

    if hasattr(db, "get_connection_info"):
        response["connection_info"] = db.get_connection_info()

    if not connection_ok:
        raise HTTPException(status_code=503, detail=response)

    return response

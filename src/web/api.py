"""
GSC-CLI's FastAPI Application

This module defines the API endpoints and connects them with the application's
service layer. It acts as the "storefront" for the data, providing a standard
HTTP interface for future AI Agents or Web UIs.
"""

from typing import List

from fastapi import Depends, FastAPI

from src.containers import Container
from src.services.site_service import SiteService

from . import schemas

# Initialize the application container and FastAPI instance
container = Container()
app = FastAPI(
    title="GSC-CLI API",
    description="API for accessing and managing Google Search Console data.",
    version="0.1.0",
)


# Dependency provider functions for FastAPI
def get_site_service() -> SiteService:
    """Get SiteService instance from container"""
    return container.site_service()


@app.get("/api/v1/sites/", response_model=List[schemas.Site], tags=["Sites"])
def list_sites(
    site_service: SiteService = Depends(get_site_service),
):
    """
    Retrieve a list of all configured active sites from the database.
    """
    # The list of dicts returned by site_service.get_all_sites
    # will be automatically converted by Pydantic into a list of Site schemas.
    sites = site_service.get_all_sites(active_only=True)
    return sites

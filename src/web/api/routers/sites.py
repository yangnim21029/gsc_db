"""
Sites Router

API endpoints related to site management.
"""

from typing import List

from fastapi import APIRouter, Depends

from src.services.site_service import SiteService
from src.web import schemas

from ..dependencies import get_site_service

router = APIRouter(
    prefix="/sites",
    tags=["Sites"],
    responses={404: {"description": "Site not found"}},
)


@router.get("/", response_model=List[schemas.Site])
def list_sites(
    site_service: SiteService = Depends(get_site_service),
):
    """
    Retrieve a list of all configured active sites from the database.
    """
    sites = site_service.get_all_sites(active_only=True)
    return sites

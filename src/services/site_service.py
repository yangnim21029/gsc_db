"""
Service layer for managing sites.
This service centralizes all business logic related to site management,
acting as an intermediary between the CLI/API and the database layer.
"""

from typing import Any, Dict, List, Optional

from .database import Database


class SiteService:
    """
    Provides methods for site-related operations.
    This acts as a "Virtual GSC MCP" to manage sites.
    """

    def __init__(self, db: Database):
        """
        Initializes the SiteService.
        Args:
            db: An instance of the Database class.
        """
        self._db = db

    def get_all_sites(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve all sites from the database.
        Args:
            active_only: If True, returns only active sites.

        Returns:
            A list of dictionaries, where each dictionary represents a site.
        """
        return self._db.get_sites(active_only=active_only)

    def get_site_by_id(self, site_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single site by its ID.
        Args:
            site_id: The ID of the site to retrieve.

        Returns:
            A dictionary representing the site, or None if not found.
        """
        return self._db.get_site_by_id(site_id)

    def add_site(
        self, domain: str, name: Optional[str] = None, category: Optional[str] = None
    ) -> Optional[int]:
        """
        Add a new site to the database.

        Args:
            domain: The domain of the site (e.g., "sc-domain:example.com").
            name: The user-friendly name for the site. If not provided, it's derived from the domain.
            category: An optional category for the site.

        Returns:
            The ID of the newly created site, or the ID of the existing site
            if a site with the same domain already exists. Returns None on failure.
        """
        # The name is often derived from the domain, let's create a default
        # if one is not provided.
        if not name:
            name = (
                domain.replace("sc-domain:", "")
                .replace("https://", "")
                .replace("http://", "")
                .rstrip("/")
            )

        return self._db.add_site(domain=domain, name=name, category=category)

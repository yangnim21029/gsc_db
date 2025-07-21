"""
Service layer for managing sites.
This service centralizes all business logic related to site management,
acting as an intermediary between the CLI/API and the database layer.
"""

from typing import Any, Dict, List, Optional

from .database import Database
from .gsc_client import GSCClient


class SiteService:
    """
    Provides methods for site-related operations.
    This acts as a "Virtual GSC MCP" to manage sites.
    """

    def __init__(self, db: Database, gsc_client: Optional[GSCClient] = None):
        """
        Initializes the SiteService.
        Args:
            db: An instance of the Database class.
            gsc_client: An optional GSCClient instance for remote operations.
        """
        self._db = db
        self._gsc_client = gsc_client

    def get_all_sites_with_status(self) -> List[Dict[str, Any]]:
        """
        獲取所有站點的詳細信息，包括本地數據庫中的站點和遠端 GSC 的站點。

        Returns:
            包含站點信息的字典列表，每個字典包含：
            - id: 站點 ID（如果在本地數據庫中）
            - name: 站點名稱
            - domain: 站點域名
            - source: 數據來源（"local" 或 "remote"）
        """
        sites = []

        # 獲取本地數據庫中的站點
        local_sites = self._db.get_sites(active_only=True)
        for site in local_sites:
            sites.append(
                {
                    "id": site["id"],
                    "name": site["name"],
                    "domain": site["domain"],
                    "source": "local",
                }
            )

        # 如果有 GSC 客戶端，也獲取遠端站點
        if self._gsc_client:
            try:
                remote_sites = self._gsc_client.get_sites()
                local_domains = {site["domain"] for site in local_sites}

                for remote_domain in remote_sites:
                    if remote_domain not in local_domains:
                        # 清理域名以生成友好的名稱
                        clean_name = (
                            remote_domain.replace("sc-domain:", "")
                            .replace("https://", "")
                            .replace("http://", "")
                            .rstrip("/")
                        )
                        sites.append(
                            {
                                "id": "N/A",
                                "name": clean_name,
                                "domain": remote_domain,
                                "source": "remote",
                            }
                        )
            except Exception:
                # 如果無法獲取遠端站點，只返回本地站點
                pass

        return sites

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

    def get_site_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a site by its domain.

        Args:
            domain: The domain to search for. Can be in various formats:
                   - "example.com"
                   - "sc-domain:example.com"
                   - "https://example.com"

        Returns:
            A dictionary representing the site, or None if not found.
        """
        # Try exact match first
        site = self._db.get_site_by_domain(domain)
        if site:
            return site

        # If not found, try with sc-domain: prefix
        if not domain.startswith("sc-domain:"):
            site = self._db.get_site_by_domain(f"sc-domain:{domain}")
            if site:
                return site

        # Try without protocol if provided
        if domain.startswith(("https://", "http://")):
            clean_domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
            site = self._db.get_site_by_domain(clean_domain)
            if site:
                return site
            # Also try with sc-domain: prefix
            site = self._db.get_site_by_domain(f"sc-domain:{clean_domain}")
            if site:
                return site

        return None

    def add_site(
        self, domain: str, name: Optional[str] = None, category: Optional[str] = None
    ) -> Optional[int]:
        """
        Add a new site to the database.

        Args:
            domain: The domain of the site (e.g., "sc-domain:example.com").
            name: The user-friendly name for the site. If not provided,
                it's derived from the domain.
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

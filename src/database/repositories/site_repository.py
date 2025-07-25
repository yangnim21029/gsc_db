"""Site repository for managing sites data."""

from typing import Any

from ...models import Site
from ..base import Repository


class SiteRepository(Repository):
    """Repository for site-related database operations."""

    async def get_all(self, active_only: bool = True) -> list[Site]:
        """Get all sites."""
        query = "SELECT * FROM sites"
        if active_only:
            query += " WHERE is_active = 1"

        async with self._lock:
            conn = self._ensure_connection()
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()

        return [self._row_to_site(row) for row in rows]

    async def get_by_id(self, site_id: int) -> Site | None:
        """Get site by ID."""
        async with self._lock:
            conn = self._ensure_connection()
            cursor = await conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
            row = await cursor.fetchone()

        return self._row_to_site(row) if row else None

    async def get_by_hostname(self, hostname: str) -> Site | None:
        """Get site by hostname with smart matching."""
        # Clean hostname
        hostname = hostname.lower().strip()
        hostname = hostname.replace("https://", "").replace("http://", "")
        hostname = hostname.rstrip("/")

        # Try different variations
        variations = [
            hostname,
            f"sc-domain:{hostname}",
            f"https://{hostname}",
            hostname.replace("www.", ""),
            f"www.{hostname}",
        ]

        async with self._lock:
            conn = self._ensure_connection()
            for variant in variations:
                cursor = await conn.execute(
                    "SELECT * FROM sites WHERE domain = ? AND is_active = 1 LIMIT 1", (variant,)
                )
                row = await cursor.fetchone()
                if row:
                    return self._row_to_site(row)

        return None

    async def create(self, domain: str, name: str, category: str | None = None) -> int:
        """Add a new site."""
        async with self._lock:
            conn = self._ensure_connection()
            cursor = await conn.execute(
                """
                INSERT INTO sites (domain, name, category)
                VALUES (?, ?, ?)
                """,
                (domain, name, category),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    @staticmethod
    def _row_to_site(row: Any) -> Site:
        """Convert database row to Site model."""
        return Site(
            id=row[0],
            domain=row[1],
            name=row[2],
            category=row[3],
            is_active=bool(row[4]),
            created_at=row[5],
            updated_at=row[6],
        )

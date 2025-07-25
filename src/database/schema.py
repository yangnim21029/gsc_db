"""Database schema definitions - single source of truth."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class TableSchema:
    """Database table schema definition."""

    name: str
    create_sql: str
    indexes: list[str]


class DatabaseSchema:
    """All database schema definitions in one place."""

    SITES = TableSchema(
        name="sites",
        create_sql="""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        indexes=[],
    )

    PERFORMANCE_DATA = TableSchema(
        name="gsc_performance_data",
        create_sql="""
            CREATE TABLE IF NOT EXISTS gsc_performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                date DATE NOT NULL,
                page TEXT NOT NULL,
                query TEXT NOT NULL,
                device TEXT DEFAULT 'DESKTOP',
                search_type TEXT DEFAULT 'WEB',
                clicks INTEGER NOT NULL,
                impressions INTEGER NOT NULL,
                ctr REAL NOT NULL,
                position REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                UNIQUE(site_id, date, page, query, device, search_type)
            )
        """,
        indexes=[
            "CREATE INDEX IF NOT EXISTS idx_performance_site_date ON gsc_performance_data(site_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_performance_query ON gsc_performance_data(query)",
            "CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_page_clicks ON gsc_performance_data(site_id, page, clicks DESC)",
            "CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_query_clicks ON gsc_performance_data(site_id, query, clicks DESC)",
            "CREATE INDEX IF NOT EXISTS idx_gsc_performance_composite ON gsc_performance_data(site_id, date, page, query, clicks DESC)",
        ],
    )

    HOURLY_RANKINGS = TableSchema(
        name="hourly_rankings",
        create_sql="""
            CREATE TABLE IF NOT EXISTS hourly_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                date DATE NOT NULL,
                hour INTEGER NOT NULL,
                query TEXT NOT NULL,
                page TEXT NOT NULL,
                position REAL NOT NULL,
                clicks INTEGER NOT NULL,
                impressions INTEGER NOT NULL,
                ctr REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                UNIQUE(site_id, date, hour, query, page)
            )
        """,
        indexes=[
            "CREATE INDEX IF NOT EXISTS idx_hourly_site_date ON hourly_rankings(site_id, date, hour)",
        ],
    )

    # Column definitions for easy reference
    PERFORMANCE_COLUMNS: ClassVar[list[str]] = [
        "site_id",
        "date",
        "page",
        "query",
        "device",
        "search_type",
        "clicks",
        "impressions",
        "ctr",
        "position",
    ]

    HOURLY_COLUMNS: ClassVar[list[str]] = [
        "site_id",
        "date",
        "hour",
        "query",
        "page",
        "position",
        "clicks",
        "impressions",
        "ctr",
    ]

    @classmethod
    def get_all_tables(cls) -> list[TableSchema]:
        """Get all table schemas."""
        return [cls.SITES, cls.PERFORMANCE_DATA, cls.HOURLY_RANKINGS]

    @classmethod
    def get_all_create_statements(cls) -> list[str]:
        """Get all CREATE TABLE statements."""
        statements = []
        for table in cls.get_all_tables():
            statements.append(table.create_sql)
            statements.extend(table.indexes)
        return statements

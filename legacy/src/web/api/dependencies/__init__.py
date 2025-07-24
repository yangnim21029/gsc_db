"""
API Dependencies

Common dependencies used across different routers.
"""

from typing import Union

from src.containers import Container
from src.services.analysis_service import AnalysisService
from src.services.data_aggregation_service import DataAggregationService
from src.services.database import Database
from src.services.process_safe_database import ProcessSafeDatabase
from src.services.site_service import SiteService

# Initialize the container
container = Container()


# Dependency provider functions
def get_site_service() -> SiteService:
    """Get SiteService instance from container"""
    return container.site_service()


def get_analysis_service() -> AnalysisService:
    """Get AnalysisService instance from container"""
    return container.analysis_service()


def get_data_aggregation_service() -> DataAggregationService:
    """Get DataAggregationService instance from container"""
    return container.data_aggregation_service()


def get_database() -> Union[Database, ProcessSafeDatabase]:
    """Get Database instance from container"""
    return container.database()


__all__ = [
    "container",
    "get_site_service",
    "get_analysis_service",
    "get_data_aggregation_service",
    "get_database",
]

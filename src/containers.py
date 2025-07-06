"""
Dependency Injection Container

This module defines a dependency injection container using the `dependency-injector`
library. It centralizes the instantiation and wiring of services, making it
easy to manage dependencies and share service instances across the application
(both CLI and API).
"""

from dependency_injector import containers, providers

from .config import settings
from .services.analysis_service import AnalysisService
from .services.database import Database
from .services.gsc_client import GSCClient
from .services.site_service import SiteService


class Container(containers.DeclarativeContainer):
    """
    The main DI container for the application.
    It provides singletons for all major services.
    """

    # Configuration provider
    config = providers.Configuration()
    config.from_dict(settings.model_dump())

    # Services
    db_service = providers.Singleton(
        Database,
        db_path=config.paths.database_path,
    )

    gsc_client = providers.Singleton(GSCClient)

    site_service = providers.Singleton(
        SiteService,
        db=db_service,
    )

    analysis_service = providers.Singleton(
        AnalysisService,
        db=db_service,
    )

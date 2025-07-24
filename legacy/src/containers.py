"""
Dependency Injection Container

This module defines a dependency injection container using the `dependency-injector`
library. It centralizes the instantiation and wiring of services, making it
easy to manage dependencies and share service instances across the application
(both CLI and API).

This container now uses ProcessSafeDatabase by default to support multi-process
deployments while maintaining backward compatibility with single-process applications.
"""

from dependency_injector import containers, providers

from .analysis.hourly_performance_analyzer import HourlyAnalyzer
from .config import settings
from .jobs.bulk_data_synchronizer import BulkDataSynchronizer
from .services.analysis_service import AnalysisService
from .services.data_aggregation_service import DataAggregationService
from .services.gsc_client import GSCClient
from .services.hourly_database import HourlyDatabase
from .services.process_safe_database import ProcessSafeDatabase
from .services.site_service import SiteService


class Container(containers.DeclarativeContainer):
    """應用程式依賴注入容器 - 支援多程序"""

    # --- Configuration Provider ---
    config = providers.Configuration()
    config.from_dict(settings.model_dump())

    # --- Core Services ---
    # 使用 ProcessSafeDatabase 來支援多程序
    # ProcessSafeDatabase 會自動為每個程序創建獨立的連接
    database = providers.Singleton(
        ProcessSafeDatabase,
        database_path=config.paths.database_path,
    )

    gsc_client = providers.Singleton(
        GSCClient,
        db=database,
    )

    site_service = providers.Singleton(
        SiteService,
        db=database,
        gsc_client=gsc_client,
    )

    # 5. 重構 HourlyDatabase 服務，注入 Database 和 GSCClient
    hourly_data_service = providers.Singleton(
        HourlyDatabase,
        db=database,
        gsc_client=gsc_client,
    )

    # --- Analysis & Job Services ---
    analysis_service = providers.Singleton(
        AnalysisService,
        db=database,
    )

    bulk_data_synchronizer = providers.Singleton(
        BulkDataSynchronizer,
        db=database,
        gsc_client=gsc_client,
    )

    hourly_performance_analyzer = providers.Singleton(
        HourlyAnalyzer,
        db=database,
    )

    data_aggregation_service = providers.Singleton(
        DataAggregationService,
        database=database,
    )

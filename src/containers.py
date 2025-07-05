from dependency_injector import containers, providers
from .services.database import Database
from .services.analysis_service import AnalysisService
from .services.gsc_client import GSCClient

class Container(containers.DeclarativeContainer):
    """
    應用程式的依賴注入容器。
    """
    # 配置提供者 (未來可用於讀取設定檔)
    config = providers.Configuration()

    # 服務提供者
    # 使用 Singleton，確保在整個應用程式生命週期中，
    # 每一個服務都只有一個實例。
    db_service = providers.Singleton(Database)
    
    gsc_client = providers.Singleton(GSCClient)
    
    analysis_service = providers.Singleton(
        AnalysisService,
        db=db_service  # 在這裡，我們告訴容器，AnalysisService 依賴於 db_service
    ) 
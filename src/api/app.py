"""Litestar application with high-performance API endpoints."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar, get
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.openapi.spec import Server
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_404_NOT_FOUND

from ..config import get_settings
from ..database.hybrid import HybridDataStore
from ..services.cache import CacheService
from .diagnostics import diagnostics_router
from .performance import performance_router

# from ..services.monitoring import setup_monitoring
from .routes import analytics_router, sites_router, sync_router


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    print("Starting application lifespan...")
    settings = get_settings()

    # Use test database in development mode
    import os
    from pathlib import Path

    db_path = None
    if os.environ.get("GSC_DEV_MODE"):
        test_db_path = Path("data/gsc-data.db")
        test_db_path.parent.mkdir(exist_ok=True)
        db_path = test_db_path
        print(f"Using test database: {db_path}")

    # Initialize database (DuckDB will be enabled based on settings)
    print("Initializing database...")
    db = HybridDataStore(sqlite_path=db_path)
    await db.initialize()
    app.state.db = db
    print("Database initialized successfully")

    # Initialize cache if enabled
    if settings.enable_cache:
        print("Initializing cache...")
        cache = CacheService(settings.redis_url)
        await cache.initialize()
        app.state.cache = cache
        print("Cache initialized successfully")
    else:
        app.state.cache = None
        print("Cache disabled")

    print("Application startup complete")

    yield

    # Shutdown
    print("Shutting down application...")
    await db.close()
    if app.state.cache:
        await app.state.cache.close()
    print("Application shutdown complete")


async def get_db(state: State) -> HybridDataStore:
    """Dependency to get database instance."""
    return state.db  # type: ignore[no-any-return]


async def get_cache(state: State) -> CacheService | None:
    """Dependency to get cache instance."""
    return state.cache  # type: ignore[no-any-return]


def create_app() -> Litestar:
    """
    Create and configure Litestar application.

    Note: While this API supports high concurrency (tested 808 RPS),
    GSC data sync operations must be sequential due to API limitations.
    """
    settings = get_settings()

    # Configure compression
    compression_config = CompressionConfig(
        backend="gzip",
        minimum_size=1000,
        gzip_compress_level=6,
        exclude=["/metrics", "/health"],
    )

    # Configure CORS to fix Swagger fetch errors
    cors_config = CORSConfig(
        allow_origins=["*"],  # Allow all origins for development
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Configure OpenAPI
    openapi_config = OpenAPIConfig(
        title="GSC Database Manager API",
        version="2.0.0",
        description="Modern API for Google Search Console data management and analytics",
        servers=[
            Server(
                url=f"http://{settings.api_host}:{settings.api_port}",
                description="Local server",
            )
        ],
        use_handler_docstrings=True,  # Include handler docstrings in OpenAPI
        path="/schema",  # OpenAPI schema endpoint
        render_plugins=[SwaggerRenderPlugin()],  # Enable Swagger UI
    )

    # Create application
    app = Litestar(
        route_handlers=[
            sites_router,
            analytics_router,
            sync_router,
            performance_router,
            diagnostics_router,
            root,
            health_check,
            docs_redirect,
            handle_inngest_probes,
        ],
        dependencies={
            "db": Provide(get_db),
            "cache": Provide(get_cache),
        },
        compression_config=compression_config,
        cors_config=cors_config,  # Added CORS configuration to fix Swagger fetch errors
        openapi_config=openapi_config,
        lifespan=[lifespan],
        debug=True,  # Enable debug for better error messages
    )

    # Note: Prometheus metrics would be mounted here if needed
    # For now, metrics are handled separately

    return app


@get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint - API information."""
    return {
        "service": "GSC Database Manager API",
        "version": "2.0.0",
        "docs": "/schema/swagger",
        "openapi": "/schema",
    }


@get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "gsc-db-refactor"}


@get("/docs", include_in_schema=False)
async def docs_redirect() -> Redirect:
    """Redirect /docs to Swagger UI."""
    return Redirect(path="/schema/swagger")


@get(
    [
        "/api/inngest",
        "/x/inngest",
        "/.netlify/functions/inngest",
        "/.redwood/functions/inngest",
    ],
    include_in_schema=False,
)
async def handle_inngest_probes() -> Response[None]:
    """Handle automated Inngest service detection probes without logging errors."""
    return Response(None, status_code=HTTP_404_NOT_FOUND)


# Create application instance
app = create_app()

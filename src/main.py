"""Main entry point for running the API server."""

import uvicorn

from .config import get_settings


def main():
    """Run the API server."""
    settings = get_settings()

    uvicorn.run(
        "src.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

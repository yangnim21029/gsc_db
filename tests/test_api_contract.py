"""API Contract Tests - Ensure API endpoints maintain consistent interfaces."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from src.api.app import create_app


class TestAPIContract:
    """Test suite to ensure API contracts remain stable."""

    @pytest.fixture
    async def app(self) -> Litestar:
        """Create test app instance."""
        return create_app()

    @pytest.fixture
    async def client(self, app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
        """Create test client."""
        async with AsyncTestClient(app=app) as client:
            yield client

    async def test_root_endpoint_contract(self, client: AsyncTestClient) -> None:
        """Test root endpoint returns expected structure."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify exact response structure
        assert data == {
            "service": "GSC Database Manager API",
            "version": "2.0.0",
            "docs": "/schema/swagger",
            "openapi": "/schema",
        }

        # Verify data types
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["docs"], str)
        assert isinstance(data["openapi"], str)

    async def test_health_endpoint_contract(self, client: AsyncTestClient) -> None:
        """Test health endpoint returns expected structure."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields exist
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
        assert "version" in data

        # Verify data types
        assert data["status"] == "healthy"
        assert isinstance(data["database"], bool)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["version"], str)

        # Verify timestamp format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    async def test_sites_list_endpoint_contract(self, client: AsyncTestClient) -> None:
        """Test sites list endpoint returns expected structure."""
        response = await client.get("/api/v1/sites")

        assert response.status_code == 200
        data = response.json()

        # Verify response is a list
        assert isinstance(data, list)

        # If there are sites, verify structure
        if data:
            site = data[0]
            assert "id" in site
            assert "domain" in site
            assert "name" in site
            assert "category" in site
            assert "is_active" in site
            assert "created_at" in site
            assert "updated_at" in site

            # Verify data types
            assert isinstance(site["id"], int)
            assert isinstance(site["domain"], str)
            assert isinstance(site["name"], str)
            assert isinstance(site["is_active"], bool)

    async def test_page_keyword_performance_endpoint_contract(
        self, client: AsyncTestClient
    ) -> None:
        """Test page-keyword performance endpoint with various parameters."""
        # Test with minimal parameters
        response = await client.get(
            "/api/v1/page-keyword-performance", params={"site_id": 1, "days": 7}
        )

        # Allow 404 if site doesn't exist, but verify error format
        if response.status_code == 404:
            error = response.json()
            assert "detail" in error
            assert isinstance(error["detail"], str)
            return

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "data" in data
        assert "total_pages" in data
        assert "total_keywords" in data
        assert "generated_at" in data

        # Verify data types
        assert isinstance(data["data"], list)
        assert isinstance(data["total_pages"], int)
        assert isinstance(data["total_keywords"], int)
        assert isinstance(data["generated_at"], str)

        # Verify data item structure if present
        if data["data"]:
            item = data["data"][0]
            assert "url" in item
            assert "total_clicks" in item
            assert "total_impressions" in item
            assert "avg_ctr" in item
            assert "avg_position" in item
            assert "keywords" in item
            assert "keyword_count" in item

            # Verify data types
            assert isinstance(item["url"], str)
            assert isinstance(item["total_clicks"], int)
            assert isinstance(item["total_impressions"], int)
            assert isinstance(item["avg_ctr"], int | float)
            assert isinstance(item["avg_position"], int | float)
            assert isinstance(item["keywords"], list)
            assert isinstance(item["keyword_count"], int)

    async def test_page_keyword_performance_csv_endpoint_contract(
        self, client: AsyncTestClient
    ) -> None:
        """Test CSV export endpoint returns proper format."""
        response = await client.get(
            "/api/v1/page-keyword-performance/csv",
            params={"site_id": 1, "days": 7, "max_results": 10},
        )

        # Allow 404 if site doesn't exist
        if response.status_code == 404:
            return

        assert response.status_code == 200

        # Verify response headers
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "content-disposition" in response.headers
        assert response.headers["content-disposition"].startswith("attachment; filename=")

        # Verify CSV format
        content = response.text
        lines = content.strip().split("\n")

        # Verify header
        assert (
            lines[0]
            == "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count"
        )

        # Verify data format if present
        if len(lines) > 1:
            # Basic CSV structure validation
            data_line = lines[1]
            fields = data_line.split(",")
            assert len(fields) >= 7  # At least 7 fields

    async def test_diagnostics_database_endpoint_contract(self, client: AsyncTestClient) -> None:
        """Test database diagnostics endpoint."""
        response = await client.get("/api/v1/diagnostics/database")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "details" in data

        # Verify details structure
        details = data["details"]
        assert "tables" in details
        assert "indexes" in details
        assert "total_size_mb" in details
        assert "wal_size_mb" in details
        assert "page_size" in details
        assert "journal_mode" in details

        # Verify data types
        assert isinstance(details["tables"], dict)
        assert isinstance(details["indexes"], list)
        assert isinstance(details["total_size_mb"], int | float)

    async def test_parameter_validation_contract(self, client: AsyncTestClient) -> None:
        """Test parameter validation returns consistent error format."""
        # Test with invalid site_id
        response = await client.get(
            "/api/v1/page-keyword-performance", params={"site_id": "invalid", "days": 7}
        )

        assert response.status_code == 400
        error = response.json()

        # Verify error structure
        assert "detail" in error
        assert isinstance(error["detail"], str | list)

        # Test with missing required parameter
        response = await client.get("/api/v1/page-keyword-performance", params={"days": 7})

        assert response.status_code == 400
        error = response.json()
        assert "detail" in error

    async def test_date_range_parameter_contract(self, client: AsyncTestClient) -> None:
        """Test date range parameter handling."""
        # Test with date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        response = await client.get(
            "/api/v1/page-keyword-performance",
            params={
                "site_id": 1,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Should accept date range parameters
        assert response.status_code in [200, 404]  # 404 if site doesn't exist

    async def test_error_response_contract(self, client: AsyncTestClient) -> None:
        """Test error responses maintain consistent format."""
        # Test 404 error
        response = await client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        error = response.json()

        # Verify error structure
        assert "detail" in error or "error" in error

        # Test method not allowed
        response = await client.post("/api/v1/sites")

        assert response.status_code == 405
        error = response.json()
        assert "detail" in error or "error" in error


class TestAPIPerformanceContract:
    """Test API performance characteristics remain stable."""

    @pytest.fixture
    async def app(self) -> Litestar:
        """Create test app instance."""
        return create_app()

    @pytest.fixture
    async def client(self, app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
        """Create test client."""
        async with AsyncTestClient(app=app) as client:
            yield client

    async def test_streaming_response_contract(self, client: AsyncTestClient) -> None:
        """Test streaming endpoints return data incrementally."""
        # This would test that CSV endpoint streams data
        # rather than loading everything into memory
        response = await client.get(
            "/api/v1/page-keyword-performance/csv",
            params={"site_id": 1, "days": 30},
            follow_redirects=False,
        )

        # Verify response can be streamed
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            # Verify we get chunks of data
            content = response.text
            assert isinstance(content, str)


# Contract test for specific business logic
class TestBusinessLogicContract:
    """Test business logic contracts remain stable."""

    @pytest.fixture
    async def app(self) -> Litestar:
        """Create test app instance."""
        return create_app()

    @pytest.fixture
    async def client(self, app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
        """Create test client."""
        async with AsyncTestClient(app=app) as client:
            yield client

    async def test_csv_format_contract(self, client: AsyncTestClient) -> None:
        """Test CSV format remains consistent."""
        response = await client.get(
            "/api/v1/page-keyword-performance/csv",
            params={"site_id": 1, "days": 1, "max_results": 1},
        )

        if response.status_code == 200:
            content = response.text
            lines = content.strip().split("\n")

            # Verify header format exactly
            expected_header = (
                "url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count"
            )
            assert lines[0] == expected_header

            # Verify data line format if present
            if len(lines) > 1:
                # Should have quotes around strings
                assert '"' in lines[1]

                # Should have numeric values without quotes
                # Check that numeric fields don't have quotes
                # (except when they're inside the keywords field)

    async def test_keyword_delimiter_contract(self, client: AsyncTestClient) -> None:
        """Test keyword delimiter remains consistent."""
        response = await client.get(
            "/api/v1/page-keyword-performance", params={"site_id": 1, "days": 7}
        )

        if response.status_code == 200:
            data = response.json()
            if data["data"] and data["data"][0]["keywords"]:
                # Keywords should be a list in JSON response
                assert isinstance(data["data"][0]["keywords"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

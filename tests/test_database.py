"""Tests for hybrid database implementation."""

import asyncio
from datetime import date
from pathlib import Path

import pytest

from src.database.hybrid import HybridDataStore
from src.models import PerformanceData, Site


@pytest.fixture
async def db():
    """Create test database."""
    db_path = Path("./test_data/test.db")
    db_path.parent.mkdir(exist_ok=True)
    
    store = HybridDataStore(db_path)
    await store.initialize()
    
    yield store
    
    await store.close()
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.mark.asyncio
async def test_site_management(db):
    """Test site CRUD operations."""
    # Add site
    site_id = await db.add_site(
        domain="sc-domain:example.com",
        name="Example Site",
        category="Test"
    )
    assert site_id > 0
    
    # Get site
    site = await db.get_site_by_id(site_id)
    assert site is not None
    assert site.domain == "sc-domain:example.com"
    assert site.name == "Example Site"
    
    # List sites
    sites = await db.get_sites()
    assert len(sites) == 1
    assert sites[0].id == site_id


@pytest.mark.asyncio
async def test_performance_data_insert(db):
    """Test performance data insertion."""
    # Add site first
    site_id = await db.add_site("sc-domain:test.com", "Test Site")
    
    # Create test data
    data = [
        PerformanceData(
            site_id=site_id,
            date=date(2024, 1, 1),
            page="https://test.com/page1",
            query="test query",
            device="DESKTOP",
            search_type="WEB",
            clicks=10,
            impressions=100,
            ctr=0.1,
            position=5.5
        )
    ]
    
    # Insert with skip mode
    stats = await db.insert_performance_data(data, mode="skip")
    assert stats["inserted"] == 1
    assert stats["skipped"] == 0
    
    # Try to insert again - should skip
    stats = await db.insert_performance_data(data, mode="skip")
    assert stats["inserted"] == 0
    assert stats["skipped"] == 1
    
    # Insert with overwrite mode
    stats = await db.insert_performance_data(data, mode="overwrite")
    assert stats["updated"] == 1


@pytest.mark.asyncio
async def test_duckdb_analytics(db):
    """Test DuckDB analytics functionality."""
    if not db.enable_duckdb:
        pytest.skip("DuckDB not enabled")
    
    # Add site and data
    site_id = await db.add_site("sc-domain:analytics.com", "Analytics Site")
    
    # Insert test data for multiple days
    data = []
    for day in range(10):
        data.append(PerformanceData(
            site_id=site_id,
            date=date(2024, 1, day + 1),
            page="https://analytics.com/",
            query="analytics test",
            device="DESKTOP",
            search_type="WEB",
            clicks=100 + day * 10,
            impressions=1000 + day * 50,
            ctr=0.1,
            position=3.0 + day * 0.1
        ))
    
    await db.insert_performance_data(data)
    
    # Run trend analysis
    df = await db.analyze_performance_trends(site_id, days=30)
    
    assert not df.is_empty()
    assert len(df) == 10
    assert "clicks_7d_avg" in df.columns
    assert "clicks_wow_change" in df.columns
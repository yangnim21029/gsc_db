#!/usr/bin/env python3
"""
Tests for page keyword performance API endpoints
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.api import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_analysis_service():
    """Mock analysis service with test data"""
    mock_data = [
        {
            "url": "https://example.com/page1",
            "total_clicks": 1000,
            "total_impressions": 5000,
            "avg_ctr": 20.0,
            "avg_position": 3.5,
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "keyword_count": 3,
        },
        {
            "url": "https://example.com/page2",
            "total_clicks": 500,
            "total_impressions": 3000,
            "avg_ctr": 16.67,
            "avg_position": 5.2,
            "keywords": ["keyword4", "keyword5"],
            "keyword_count": 2,
        },
    ]

    mock_service = Mock()
    mock_service.get_page_keyword_performance.return_value = mock_data
    return mock_service


@pytest.fixture
def mock_site_service():
    """Mock site service"""
    mock_service = Mock()
    mock_service.get_site_by_id.return_value = {
        "id": 1,
        "name": "Test Site",
        "url": "https://example.com",
    }
    mock_service.get_site_by_domain.return_value = {
        "id": 1,
        "name": "Test Site",
        "url": "https://example.com",
    }
    return mock_service


def test_page_keyword_performance_with_site_id(client, mock_analysis_service, mock_site_service):
    """Test page keyword performance endpoint with site_id"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post(
                "/api/v1/page-keyword-performance/",
                json={"site_id": 1, "days": 30, "max_results": 100},
            )

    assert response.status_code == 200
    data = response.json()

    assert data["site_id"] == 1
    assert data["time_range"] == "Last 30 days"
    assert data["total_results"] == 2
    assert len(data["data"]) == 2

    # Check first item
    first_item = data["data"][0]
    assert first_item["url"] == "https://example.com/page1"
    assert first_item["total_clicks"] == 1000
    assert first_item["keyword_count"] == 3
    assert len(first_item["keywords"]) == 3


def test_page_keyword_performance_with_hostname(client, mock_analysis_service, mock_site_service):
    """Test page keyword performance endpoint with hostname"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post(
                "/api/v1/page-keyword-performance/",
                json={"hostname": "example.com", "days": 7, "max_results": 50},
            )

    assert response.status_code == 200
    data = response.json()

    assert data["site_id"] == 1
    assert data["time_range"] == "Last 7 days"
    assert data["total_results"] == 2


def test_page_keyword_performance_all_time(client, mock_analysis_service, mock_site_service):
    """Test page keyword performance endpoint with all time data"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post(
                "/api/v1/page-keyword-performance/", json={"site_id": 1, "max_results": 1000}
            )

    assert response.status_code == 200
    data = response.json()

    assert data["time_range"] == "All time"


def test_page_keyword_performance_missing_site(client, mock_analysis_service, mock_site_service):
    """Test error when neither site_id nor hostname is provided"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post("/api/v1/page-keyword-performance/", json={"days": 30})

    assert response.status_code == 400
    assert "Either site_id or hostname must be provided" in response.json()["detail"]


def test_page_keyword_performance_both_site_params(
    client, mock_analysis_service, mock_site_service
):
    """Test error when both site_id and hostname are provided"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post(
                "/api/v1/page-keyword-performance/",
                json={"site_id": 1, "hostname": "example.com", "days": 30},
            )

    assert response.status_code == 400
    assert "Only one of site_id or hostname should be provided" in response.json()["detail"]


def test_page_keyword_performance_invalid_site_id(client, mock_analysis_service, mock_site_service):
    """Test error when site_id doesn't exist"""
    mock_site_service.get_site_by_id.return_value = None

    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.post(
                "/api/v1/page-keyword-performance/", json={"site_id": 999, "days": 30}
            )

    assert response.status_code == 404
    assert "Site with ID 999 not found" in response.json()["detail"]


def test_page_keyword_performance_csv_summary(client, mock_analysis_service, mock_site_service):
    """Test CSV download endpoint with summary format"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.get(
                "/api/v1/page-keyword-performance/csv/",
                params={"site_id": 1, "days": 30, "format": "summary"},
            )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8-sig"
    assert "attachment" in response.headers["content-disposition"]

    # Check CSV content
    content = response.text
    assert "網址" in content
    assert "總點擊數" in content
    assert "關鍵字列表" in content
    assert "https://example.com/page1" in content


def test_page_keyword_performance_csv_detailed(client, mock_analysis_service, mock_site_service):
    """Test CSV download endpoint with detailed format"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.get(
                "/api/v1/page-keyword-performance/csv/",
                params={"site_id": 1, "days": 30, "format": "detailed"},
            )

    assert response.status_code == 200
    assert "_detailed.csv" in response.headers["content-disposition"]

    # Check CSV content
    content = response.text
    assert "網址" in content
    assert "關鍵字" in content
    assert "頁面總點擊數" in content
    # Should have one row per keyword
    assert content.count("keyword1") == 1
    assert content.count("keyword4") == 1


def test_page_keyword_performance_csv_missing_site(
    client, mock_analysis_service, mock_site_service
):
    """Test CSV endpoint error when site parameters are missing"""
    with patch("src.web.api.get_analysis_service", return_value=mock_analysis_service):
        with patch("src.web.api.get_site_service", return_value=mock_site_service):
            response = client.get("/api/v1/page-keyword-performance/csv/", params={"days": 30})

    assert response.status_code == 400
    assert "Either site_id or hostname must be provided" in response.json()["detail"]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依賴注入模塊。
集中管理服務實例的創建，確保單例模式並解耦。
"""

from ..services.database import Database
from ..services.analysis_service import AnalysisService
from ..services.gsc_client import GSCClient

def get_db_service() -> Database:
    """依賴工廠：返回 Database 服務的實例。"""
    return Database()

def get_analysis_service() -> AnalysisService:
    """依賴工廠：返回 AnalysisService 的實例。"""
    db = get_db_service()
    return AnalysisService(db)

def get_gsc_client() -> GSCClient:
    """依賴工廠：返回 GSCClient 服務的實例。"""
    return GSCClient() 
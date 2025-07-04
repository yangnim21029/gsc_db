#!/usr/bin/env python3
"""
GSC CLI - Google Search Console 數據管理工具
主入口點
"""

import sys
from pathlib import Path

# 添加 src 目錄到 Python 路徑
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# 導入並運行 CLI 應用
from src.cli.commands import app

if __name__ == "__main__":
    app() 
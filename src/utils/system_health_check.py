#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系統健康檢查工具
檢查系統運作狀況、依賴組件、配置等
"""

import json
import os
import sys

try:
    from src.services.database import Database
    from src.services.gsc_client import GSCClient
except ImportError as e:
    print(f"❌ 導入模塊失敗: {e}")
    print("請確保所有依賴模塊都存在")
    sys.exit(1)


def check_dependencies():
    """檢查依賴組件"""
    print("📦 檢查依賴組件...")

    required_modules = [
        "google.auth",
        "google.oauth2",
        "googleapiclient",
        "sqlite3",
        "matplotlib",
        "pandas",
        "plotly",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} (缺失)")
            missing_modules.append(module)

    if missing_modules:
        print(f"\n⚠️  發現 {len(missing_modules)} 個缺失的依賴")
        return False
    return True


def check_configuration_files():
    """檢查配置文件"""
    print("\n📁 檢查配置文件...")

    config_files = [
        ("client_secret.json", "必需 - Google OAuth 配置"),
        ("gsc_credentials.json", "可選 - 已保存的認證信息"),
    ]

    all_present = True
    for filename, description in config_files:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    json.load(f)
                print(f"  ✅ {filename} - {description}")
            except json.JSONDecodeError:
                print(f"  ❌ {filename} - JSON 格式錯誤")
                all_present = False
        else:
            if "client_secret" in filename:
                print(f"  ❌ {filename} - {description} (缺失)")
                all_present = False
            else:
                print(f"  ⚠️  {filename} - {description} (尚未認證)")

    return all_present


def check_database_connection():
    """檢查數據庫連接"""
    print("\n🗄️  檢查數據庫連接...")

    try:
        database = Database()
        with database.get_connection() as conn:
            # 檢查主要表格是否存在（使用實際的表格名稱）
            required_tables = [
                "sites",
                "keywords",
                "daily_rankings",
                "page_data",
                "hourly_rankings",
                "sync_tasks",
                "api_usage_stats",
            ]

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            missing_tables = []
            for table in required_tables:
                if table in existing_tables:
                    print(f"  ✅ 表格 {table}")
                else:
                    print(f"  ❌ 表格 {table} (缺失)")
                    missing_tables.append(table)

            # 顯示總表格數量
            print(f"  📊 總表格數: {len(existing_tables)} (包含系統表)")

            if missing_tables:
                print(f"\n⚠️  發現 {len(missing_tables)} 個缺失的核心表格")
                return False

            # 檢查數據庫大小
            cursor = conn.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            )
            db_size = cursor.fetchone()[0]
            print(f"  📊 數據庫大小: {db_size / 1024 / 1024:.2f} MB")

            # 檢查關鍵表格的記錄數
            key_tables = ["sites", "keywords", "daily_rankings", "hourly_rankings"]
            for table in key_tables:
                if table in existing_tables:
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"  📈 {table}: {count:,} 筆記錄")
                    except Exception:
                        pass

            return True

    except Exception as e:
        print(f"  ❌ 數據庫連接失敗: {e}")
        return False


def check_gsc_authentication():
    """檢查 Google Search Console 認證狀態"""
    print("\n🔑 檢查 Google 認證狀態...")

    try:
        gsc_client = GSCClient()

        if gsc_client.is_authenticated():
            print("  ✅ Google 帳號已認證")

            # 檢查憑證有效性
            if hasattr(gsc_client, "credentials") and gsc_client.credentials:
                if gsc_client.credentials.expired:
                    print("  ⚠️  認證已過期，可能需要重新認證")
                else:
                    print("  ✅ 認證有效")

            # 測試 API 連接
            try:
                sites = gsc_client.get_sites()
                print(f"  ✅ API 連接正常，可訪問 {len(sites)} 個站點")
                return True
            except Exception as e:
                print(f"  ❌ API 連接失敗: {e}")
                return False
        else:
            print("  ❌ 尚未完成 Google 認證")
            return False

    except Exception as e:
        print(f"  ❌ 檢查認證狀態失敗: {e}")
        return False


def check_system_resources():
    """檢查系統資源"""
    print("\n💻 檢查系統資源...")

    try:
        # 檢查磁盤空間
        import shutil

        total, used, free = shutil.disk_usage(".")

        print("  💾 磁盤空間:")
        print(f"    總空間: {total / 1024 / 1024 / 1024:.2f} GB")
        print(f"    已使用: {used / 1024 / 1024 / 1024:.2f} GB")
        print(f"    可用空間: {free / 1024 / 1024 / 1024:.2f} GB")

        if free < 1024 * 1024 * 1024:  # 少於 1GB
            print("    ⚠️  可用空間不足")
            return False
        else:
            print("    ✅ 磁盤空間充足")

        # 檢查 Python 版本
        python_version = sys.version
        print(f"  🐍 Python 版本: {python_version.split()[0]}")

        return True

    except Exception as e:
        print(f"  ❌ 檢查系統資源失敗: {e}")
        return False


def main():
    print("🏥 系統健康檢查")
    print("=" * 50)

    checks = [
        ("依賴組件", check_dependencies),
        ("配置文件", check_configuration_files),
        ("數據庫連接", check_database_connection),
        ("Google 認證", check_gsc_authentication),
        ("系統資源", check_system_resources),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 檢查失敗: {e}")
            results.append((name, False))

    # 總結
    print("\n" + "=" * 50)
    print("📋 健康檢查總結")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 正常" if result else "❌ 異常"
        print(f"  {name}: {status}")

    print(f"\n整體狀況: {passed}/{total} 項檢查通過")

    if passed == total:
        print("🎉 系統運作正常！")
    elif passed >= total * 0.8:
        print("⚠️  系統基本正常，但有些小問題需要注意")
    else:
        print("🚨 系統存在嚴重問題，建議立即修復")

    print("\n💡 如果遇到問題，請檢查:")
    print("  1. 是否已安裝所有依賴: pip install -r requirements.txt")
    print("  2. 是否有 client_secret.json 文件")
    print("  3. 是否已完成 Google 認證")
    print("  4. 網絡連接是否正常")


if __name__ == "__main__":
    main()

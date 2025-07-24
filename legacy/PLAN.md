# GSC-CLI 專案開發與重構計劃

本文檔旨在記錄 GSC-CLI 專案的開發歷程、當前狀態以及未來的優化方向，以確保專案的持續健康發展。

## 🎯 總體目標

將 GSC-CLI 打造成一個健壯、高效、易於維護且用戶友好的企業級 Google Search Console 數據管理工具。

---

## ✅ Phase 1: 核心架構重構 (已完成)

第一階段的目標是建立一個清晰、可擴展的現代化軟體架構。

- **[完成]** **統一數據模型**:

  - 引入 `gsc_performance_data` 作為核心數據表。
  - 廢棄並移除了舊的 `daily_rankings` 和 `page_data` 表，消除了數據冗餘。

- **[完成]** **提升數據庫性能**:

  - 在 `database.py` 中使用 `INSERT ... ON CONFLICT` (UPSERT) 語法，極大地提升了數據寫入效率。
  - 啟用 `PRAGMA foreign_keys = ON`，確保了數據庫層面的數據完整性。

- **[完成]** **服務分層與解耦**:

  - 成功將分析邏輯從 `database.py` 抽離到 `AnalysisService`。
  - 將報告生成器 `analytics_report_builder.py` 和交互式可視化工具 `interactive_data_visualizer.py` 重構為完全依賴 `AnalysisService`，移除了對數據庫的直接依賴。

- **[完成]** **簡化數據同步邏輯**:
  - 移除了 `gsc_client.py` 中舊的、複雜的同步方法。
  - 統一使用 `stream_site_data` 作為所有數據獲取的核心入口，該方法高效且內存佔用低。

---

## 🚀 Phase 2: CLI 健壯性與用戶體驗優化 (當前焦點)

第二階段的目標是修復現有 Bug，並將 CLI 工具打磨得更加實用和用戶友好。

- **[進行中]** **修復與優化 `cli/commands.py`**:

  - **問題**: 部分 `analyze` 子命令的方法調用與後端服務不匹配；`sync daily` 命令的實現過於複雜。
  - **解決方案**:
    - [ ] 修正 `analyze report` 和 `analyze compare` 的方法調用，確保其能正確工作。
    - [ ] 將 `sync daily` 的複雜業務邏輯（日期計算、狀態管理、進度條）完全委託給 `jobs/bulk_data_synchronizer.py` 中的 `run_sync` 函數處理，保持 CLI 命令的輕量化。
    - [ ] 為 `analyze compare` 命令的輸出創建一個格式優美的 `rich.Table`，提升可讀性。

- **[待辦]** **增強交互式分析工具**:
  - **問題**: `analyze interactive` 目前功能較為單一。
  - **解決方案**:
    - [ ] 將 `interactive_data_visualizer.py` 的 `run` 方法改造成一個真正的交互式儀表板。
    - [ ] 如果用戶未提供 `--site-id`，則自動列出所有站點供其選擇。
    - [ ] 引導用戶選擇按 `query` 或 `page` 進行分析。
    - [ ] 根據用戶選擇，動態獲取對應的關鍵字/頁面列表，並讓用戶從中選擇一項進行繪圖。
    - [ ] 實現分析循環，允許用戶在完成一次分析後繼續下一次分析或退出。

---

## 🌟 Phase 3: 配置管理與依賴注入 (高級重構)

第三階段的目標是引入更專業的工程實踐，使專案達到生產級別的標準。

- **[待辦]** **重構 `config.py`**:

  - **問題**: 當前配置較為靜態，不利於在不同環境（開發/生產）中部署。
  - **解決方案**:
    - [ ] 引入 `python-dotenv`，支持通過 `.env` 文件加載配置。
    - [ ] 根據 `APP_ENV` 環境變數動態切換數據庫路徑、日誌路徑等。
    - [ ] 確保所有路徑變數都是 `pathlib.Path` 物件，並在應用啟動時自動創建所需目錄。

- **[待辦]** **在 CLI 中全面實施依賴注入**:
  - **問題**: 部分命令仍然可能手動創建服務實例。
  - **解決方案**:
    - [ ] 確保所有 CLI 命令都通過 `typer.Depends` 從 `cli/dependencies.py` 獲取服務實例。
    - [ ] 移除所有在命令函數內部手動創建 `Database()`, `GSCClient()` 的程式碼。

---

## 🧪 Phase 4: 測試覆蓋與持續集成 (未來計劃)

第四階段的目標是建立自動化的質量保障體系，確保專案的長期穩定性。

- **[待辦]** **擴展單元測試**:

  - **目標**: 核心業務邏輯的測試覆蓋率達到 80% 以上。
  - **行動**:
    - [ ] 為 `AnalysisService` 編寫單元測試，特別是針對 `compare_performance_periods` 等複雜查詢。
    - [ ] 為 `jobs/bulk_data_synchronizer.py` 中的 `run_sync` 函數編寫測試，模擬不同的同步場景（如重試、斷點續傳）。

- **[待辦]** **編寫整合測試**:

  - **目標**: 驗證端到端的 CLI 命令是否能正常工作。
  - **行動**:
    - [ ] 使用 `typer.testing.CliRunner` 為核心的 CLI 命令（如 `sync daily`, `analyze report`）編寫整合測試。

- **[待辦]** **建立持續集成 (CI) 流程**:
  - **目標**: 自動化代碼檢查和測試。
  - **行動**:
    - [ ] 創建一個 GitHub Actions 工作流 (`.github/workflows/ci.yml`)。
    - [ ] 在工作流中配置步驟，以在每次 `push` 或 `pull request` 時自動運行 `pytest`。

---

### Phase 5: 依賴健康度檢查與升級 (新)

- [ ] **依賴審查**：定期審查 `requirements.txt`，移除不再需要的套件。
- [ ] **策略性升級**：評估核心依賴（如 `pandas`, `google-api-client`）的新版本，進行分批、測試後的升級，以獲取新功能和安全補丁。
- [ ] **引入 `pip-tools`**：考慮使用 `pip-tools` 管理依賴，通過 `requirements.in` 來維護頂層依賴，自動生成鎖定的 `requirements.txt`。

---

## 歷史紀錄與反思

- **2024-Q2**:
  - 完成了 CLI 的基本框架搭建 (`typer`)。
  - 實現了核心的數據同步與儲存邏輯 (`gsc_client`, `database`)。
  - 引入了 `dependency-injector` 解決了 `typer` 複雜的 DI 問題，實現了服務解耦。
  - 根據 @AI 的建議，完成了配置系統的重構，引入了 `toml` 和 `pydantic`，使配置更健壯、更靈活。

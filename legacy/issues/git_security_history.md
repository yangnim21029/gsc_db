# Git 歷史紀錄安全警報與修復報告

## 1. 問題 (Problem)

在專案開發過程中，包含 Google Cloud Platform (GCP) 敏感憑證的檔案 (`cred/client_secret.json` 和 `cred/credentials.json`) 被意外地提交到了 Git 的歷史紀錄中。

當嘗試將這段歷史推送到遠端倉庫時，被 GitHub 的「推送保護 (Push Protection)」功能自動偵測並攔截，操作失敗。

## 2. 嚴重性 (Severity)

**極高 (Critical)**

一旦這段包含密鑰的歷史紀錄被成功推送到任何可存取的遠端倉庫（無論公開或私有），將導致以下風險：

- **GCP 帳戶權限洩漏**：任何能存取倉庫的人都可以獲得對您 GCP 專案的完整權限。
- **數據外洩**：攻擊者可能存取、修改或刪除您 Google Search Console 的數據。
- **產生非預期費用**：攻擊者可能濫用您的 API 配額，或使用您的帳戶進行其他惡意活動。

## 3. 處理方案 (Solution)

我們採取了以下步驟來徹底解決此問題：

1.  **安裝歷史修改工具**：安裝了 Git 官方推薦的 `git-filter-repo` 工具。
2.  **重寫 Git 歷史**：使用 `git-filter-repo` 掃描並重寫了整個倉庫的歷史紀錄，從每一個 commit 中徹底清除了 `cred/client_secret.json` 和 `cred/credentials.json` 兩個檔案的所有蹤跡。
3.  **強制推送更新**：在確認本地歷史已清理乾淨後，使用 `git push --force` 將這個新的、安全的歷史紀錄強制推送到遠端倉庫，覆蓋了含有敏感資訊的舊歷史。

## 4. 如何預防 (How-to / Prevention)

為了避免未來再次發生類似事件，請遵循以下最佳實踐：

1.  **第一時間使用 `.gitignore`**：

    - 在建立任何密鑰或憑證檔案的**同時**，就將其路徑（例如 `cred/` 或 `*.json`）加入到 `.gitignore` 檔案中。這是最重要的一步。

2.  **Commit 前檢查**：

    - 在執行 `git add .` 和 `git commit` 之前，養成使用 `git status` 檢查檔案狀態的習慣，確保沒有非預期的檔案被加入。

3.  **使用環境變數**：

    - 更安全的做法是，不要將密鑰直接寫在 JSON 檔案裡。可以考慮將密鑰儲存在一個被 `.gitignore` 忽略的 `.env` 檔案中，並透過程式碼讀取環境變數來使用它們。

4.  **啟用倉庫安全功能**：
    - 在 GitHub 倉庫的 `Settings` -> `Code security and analysis` 中，啟用 `Secret Scanning`。這會在密鑰被提交時立即發出警報，提供多一層保護。

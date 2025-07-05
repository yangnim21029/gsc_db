# 如何為 GSC-CLI 貢獻

我們非常歡迎並感謝您考慮為 GSC-CLI 做出貢獻！您的每一份貢獻，無論大小，都對本專案至關重要。

為了確保協作過程順利愉快，請花幾分鐘時間閱讀以下指南。

我們致力於營造一個開放、友善的社群環境。請務必遵守我們的 **[行為準則 (Code of Conduct)](CODE_OF_CONDUCT.md)**。

## ❓ 我該如何開始？

您可以透過多種方式為專案做出貢獻：

- **回報錯誤 (Reporting Bugs)**: 如果您發現了 bug，請先搜尋現有的 [Issues](https://github.com/your-username/gsc-cli/issues)，確認沒有重複的回報。如果沒有，請建立一個新的 issue，並盡可能提供詳細資訊。
- **建議新功能 (Suggesting Enhancements)**: 我們樂於聽到您的新想法！請建立一個新的 issue，詳細描述您希望增加的功能、它能解決什麼問題，以及您設想的使用方式。
- **提交拉取請求 (Pull Requests)**: 如果您準備好直接貢獻程式碼，請參考下面的開發流程。我們歡迎任何形式的改進，從修正錯字到實現完整的新功能。

## 🚀 開發流程

準備好貢獻程式碼了嗎？太棒了！以下是我們的標準開發流程：

1.  **Fork 倉庫**
    點擊頁面右上角的 "Fork" 按鈕，將本倉庫複製到您自己的 GitHub 帳號下。

2.  **Clone 您的 Fork**
    將您 fork 的倉庫 clone 到您的本地電腦。

    ```bash
    git clone https://github.com/YOUR_USERNAME/gsc-cli.git
    cd gsc-cli
    ```

3.  **建立新分支**
    從 `main` 分支建立一個新的功能分支。分支名稱應簡潔明瞭地描述您的工作內容（例如 `feat/add-new-report-type` 或 `fix/auth-flow-bug`）。

    ```bash
    git checkout -b your-branch-name
    ```

4.  **設定開發環境**
    我們使用 `just` 來簡化設定流程。只需執行一個指令即可安裝所有依賴並完成首次認證。

    ```bash
    just bootstrap
    ```

5.  **進行程式碼變更**
    開始編寫您的程式碼！

6.  **運行品質檢查**
    在提交程式碼前，請務必運行所有品質檢查。我們已經設定了 `pre-commit` hook，它會在您每次 `git commit` 時自動運行大部分檢查。

    您也可以隨時手動運行完整的檢查套件：

    ```bash
    just check
    ```

    這會自動格式化程式碼 (`ruff format`)、檢查風格問題 (`ruff check`)、進行類型檢查 (`mypy`) 並運行測試 (`pytest`)。

7.  **提交您的變更**
    我們推薦使用 Conventional Commits 格式來撰寫提交訊息，這有助於自動生成變更日誌。

    - `feat`: 新增功能
    - `fix`: 修復 bug
    - `docs`: 文件變更
    - `style`: 程式碼風格變更（不影響程式碼邏輯）
    - `refactor`: 重構程式碼
    - `test`: 新增或修改測試
    - `chore`: 建構流程、輔助工具的變動

    ```bash
    git add .
    git commit -m "feat: Add support for weekly performance reports"
    ```

8.  **推送至您的 Fork**

    ```bash
    git push origin your-branch-name
    ```

9.  **建立 Pull Request**
    回到您在 GitHub 上的 fork 倉庫頁面，點擊 "Compare & pull request" 按鈕。填寫一個清晰的標題和描述，解釋您的變更內容，並關聯相關的 Issue。

## ✨ Pull Request 指南

- 請確保您的 PR 標題簡潔明瞭，並在描述中提供足夠的上下文。
- 如果您的 PR 解決了某個 issue，請在描述中使用 `Closes #123` 這樣的關鍵字來自動關聯。
- 提交後，CI (持續整合) 流程會自動運行。請確保所有檢查都通過。

---

再次感謝您對 GSC-CLI 的貢獻！我們期待與您一同打造一個更強大的工具。

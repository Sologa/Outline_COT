# OpenAI 官方 Document Skills 中文說明

## 文件目的

這份文件整理 OpenAI 官方 curated skills 裡和文件處理相關的三個 skill：

1. `doc`
2. `slides`
3. `spreadsheet`

本文以目前安裝到本機 `~/.codex/skills/` 的版本為準，並根據實際 `SKILL.md` 與附帶資源整理，不是只看名稱做推測。

## 安裝結果

三個 skills 已安裝於：

- `~/.codex/skills/doc`
- `~/.codex/skills/slides`
- `~/.codex/skills/spreadsheet`

## 整體觀察

這三個 skill 的共同特徵是：

- 都不是單純「檔案格式說明」，而是完整的工作流程規範。
- 都強調先確認輸出品質，再交付。
- 都偏向「可程式化建立與修改」而不是手工 GUI 操作。
- 都強調視覺檢查或 render loop，而不只看文字內容。

它們的分工大致如下：

- `doc`：處理 `.docx`
- `slides`：處理 `.pptx`
- `spreadsheet`：處理 `.xlsx`、`.csv`、`.tsv`

## 1. `doc`

### 定位

`doc` 是官方的 Word 文件 skill，實際上主攻的是 `.docx` 文件的讀取、建立與編修，尤其重視版面、表格、段落階層與視覺保真。

它的 frontmatter 描述很直接：

- 適用於讀、寫、改 `.docx`
- 特別適合格式與版面 fidelity 很重要的任務
- 建議核心工具是 `python-docx`
- 建議搭配 `scripts/render_docx.py` 做視覺檢查

### 它主要做什麼

`doc` 不是只拿來抽文字。它更像是「程式化 Word 文件工程」：

- 讀取或審查 `.docx` 內容
- 建立有專業格式的文件
- 修改既有文件，保留結構與排版
- 在交付前對版面做 render 與人工檢查

### 它要求的工作方式

這個 skill 的核心工作流很清楚：

1. 優先做視覺檢查，而不是只抽文字。
2. 如果環境有 `soffice` 和 `pdftoppm`，就走 `DOCX -> PDF -> PNG` 的 render 路徑。
3. 或者用 skill 附帶的 `scripts/render_docx.py`。
4. 真正編修內容時，優先用 `python-docx` 做結構化修改，例如：
   - heading
   - style
   - table
   - list
5. 每次有實質變更後，都要重新 render 再檢查。
6. 如果無法 render，才退回文字抽取模式，但要明講版面風險。

### 依賴與工具

Python 依賴：

- `python-docx`
- `pdf2image`

系統工具：

- `libreoffice`
- `poppler`

它提供的實用腳本：

- `scripts/render_docx.py`

### 輸出與目錄習慣

這個 skill 對中間檔與最終輸出也有建議：

- 中間檔放 `tmp/docs/`
- 最終輸出放 `output/doc/`

### 品質要求

`doc` 對交付品質要求不低，重點包括：

- 文件要像正式交付件，不是臨時拼湊稿
- 字體、邊界、段落階層、間距要一致
- 表格和圖表不能錯位、裁切、重疊或不可讀
- 引用和參考不能殘留 placeholder 或工具殘碼
- 最終交付前要逐頁檢查

### 適合什麼情境

你可以把它理解成：

- 要產生正式 Word 文件時用
- 要在 `.docx` 裡保留排版與表格時用
- 要做 redlining、結構化編修、版面確認時用

如果只是快速抽純文字，它也能幫上忙，但那不是它最強的用途。

## 2. `slides`

### 定位

`slides` 是官方的 PowerPoint deck skill，主力是建立與修改 `.pptx` 投影片，而且明確偏好使用 `PptxGenJS`。

它不是把 `.pptx` 當成簡單容器，而是把投影片視為一種「可編輯的輸出產品」，所以除了 `.pptx`，還要求保留對應的 authoring `.js`。

### 它主要做什麼

這個 skill 適合：

- 從零建立新投影片 deck
- 根據截圖、PDF、既有 deck 重新製作投影片
- 修改既有 deck 的內容與版面
- 在保持 PowerPoint 可編輯性的前提下加入圖表、公式、視覺元素
- 排查 overflow、元素重疊、字型替換等 layout 問題

### 它的核心設計理念

`slides` 最重要的點是：

- 用 `PptxGenJS` 做 deck authoring
- 不建議用 `python-pptx` 生成投影片，除非只是做 inspection
- 要保留 editable output
- 最終應交付 `.pptx` 和對應 `.js`

這代表它不是「做一個能看就好」的簡報 skill，而是偏向工程化、可重建、可再編修的投影片生產流程。

### 它要求的工作流程

官方 skill 中的 workflow 大致是：

1. 先判斷任務是新建、重建，還是修改。
2. 一開始就定 slide size。
   - 預設用 16:9 的 `LAYOUT_WIDE`
   - 若來源材料不是這個比例，就要先對齊比例
3. 把 skill 內建的 `assets/pptxgenjs_helpers/` 複製到工作目錄，直接 import 使用，不要自己重寫 helper。
4. 用 JavaScript 建 deck，明確設定 theme font、間距與版面。
5. 用附帶腳本 render 成 PNG 做檢查。
6. 對邊界緊、資訊密的 deck，還要跑 overflow 檢查。
7. 最後交付 `.pptx`、authoring `.js`，以及必要的生成資源。

### 它附帶的資源很多

這個 skill 是三者裡最像「小型 toolkit」的一個。它不只一份 `SKILL.md`，還內建不少腳本和 helper。

內建 helpers：

- `assets/pptxgenjs_helpers/`
  - `layout.js`
  - `text.js`
  - `image.js`
  - `latex.js`
  - `code.js`
  - `svg.js`
  - `layout_builders.js`
  - `util.js`
  - `index.js`

內建腳本：

- `scripts/render_slides.py`
- `scripts/slides_test.py`
- `scripts/create_montage.py`
- `scripts/detect_font.py`
- `scripts/ensure_raster_image.py`

參考文件：

- `references/pptxgenjs-helpers.md`

### 它特別強調的規則

`slides` 對投影片生成有明確規範：

- 字體要顯式設定，不要依賴 PowerPoint 預設
- 文字框尺寸要用 helper，例如 `autoFontSize`、`calcTextBox`
- 不要直接塞字元 `•` 做 bullet，要用 bullet options
- 圖片尺寸處理要用 skill 提供的 sizing helper
- 公式建議走 `latexToSvgDataUri()`
- code block 建議走 `codeToRuns()`
- 簡單圖表優先用 PowerPoint 原生 chart，保留可編輯性
- 生成或大改 deck 時，JS 裡要包含 overlap / out-of-bounds 檢查

### 它最適合什麼情境

如果你要的是：

- 工程化產生 `.pptx`
- 可重建、可維護、可編修的簡報
- 有版面驗證與 debug 流程的 deck 開發

那 `slides` 很適合。

如果你只想快速拼一個簡報，不在乎 source code 或 editable authoring，它就顯得比較重。

## 3. `spreadsheet`

### 定位

`spreadsheet` 是官方的試算表 skill，負責 `.xlsx`、`.csv`、`.tsv` 的建立、編修、分析與格式化。

它比一般「表格處理」skill 更強調：

- 公式意識
- 重算與 cached values
- 視覺檢查
- 格式保持

所以它不只是資料分析，也包含 Excel 工程與交付品質。

### 它主要做什麼

這個 skill 覆蓋的範圍很廣：

- 建立新 workbook
- 用公式與格式產生結構化報表
- 分析 tabular data
- 修改既有 workbook，同時避免破壞公式、reference 和 formatting
- 製作 chart、summary table
- 在交付前重算公式與做視覺 render

### 核心工具選型

官方 skill 給出的工具選型非常明確：

- `.xlsx` 編修與格式保留：`openpyxl`
- 分析與 CSV/TSV 流程：`pandas`
- Excel chart：`openpyxl.chart`
- 若環境裡有內部 spreadsheet 重算/render 工具，優先用它做公式重算與 render

它也特別提醒：

- `openpyxl` 不會自己計算公式
- 所以如果需要 cached values，必須借助重算工具

### 它要求的工作流程

大致流程是：

1. 先確認任務目標：create、edit、analyze、visualize。
2. 選對工具：
   - `openpyxl` 做 workbook 結構與格式
   - `pandas` 做資料分析
3. 如果能重算，就先重算公式。
4. 對 derived values 優先用公式，不要硬編結果。
5. 若版面重要，render 後檢查。
6. 輸出穩定命名，清掉中間檔。

### 它特別重視公式品質

這個 skill 最有辨識度的部分是公式規範。它明確要求：

- derived values 用公式，不要硬寫數字
- 避免太複雜、太脆弱的公式
- 小心 absolute / relative reference
- 避免 magic number
- 避免 volatile function，如 `INDIRECT`、`OFFSET`
- 不要用 `FILTER`、`XLOOKUP`、`SORT`、`SEQUENCE` 這類 dynamic array function
- 要防範：
  - `#REF!`
  - `#DIV/0!`
  - `#VALUE!`
  - `#N/A`
  - `#NAME?`
- 小心 circular reference、錯 range、off-by-one

簡單說，它把試算表當成一種「會出 bug 的程式」，不是單純表格。

### 它也很重視格式與視覺交付

若有 `soffice` 和 `pdftoppm`，它建議：

- 先把試算表 render 成 PDF
- 再轉成 PNG 做人工視覺檢查

檢查重點包括：

- 公式結果是否正確
- 版面是否裁切
- 欄寬列高是否合理
- 樣式是否一致
- 文字是否 spill 到相鄰儲存格

### 對既有模板與新表格的態度不同

這個 skill 對「改現有表格」和「做新表格」有不同要求。

改既有表格時：

- 先 render 再看
- 要精確保留原有格式
- 原模板風格優先
- 新填入的 cell 要和既有風格一致

做新表格時：

- 日期、百分比、貨幣格式要合理
- header 要明顯區分
- 不要濫用 border、merged cells、fill colors
- 欄寬列高要可讀
- totals 要容易理解
- 不要讓文字溢出

### 還有 finance / IB 風格規範

`spreadsheet` 不只一般試算表，它甚至內建了財務模型與 investment banking layout 的規範，例如：

- 0 顯示為 `-`
- 負數紅字加括號
- multiples 顯示成 `5.2x`
- header 要標明單位，例如 `Revenue ($mm)`
- source 要寫進 cell comments
- 若無特別樣式指示，輸入、公式、連結、假設要用不同顏色區分
- IB-style 模型要隱藏 gridlines、用橫線區分 totals、section header 用深底白字、子項目要縮排

這代表它其實很適合：

- 分析型 Excel
- 可交付的 business spreadsheet
- 財務模型
- 有固定模板的試算表更新工作

## 三者的差異總結

### `doc`

- 核心對象：`.docx`
- 主要工具：`python-docx`
- 關鍵能力：保留版面與格式、逐頁 render 檢查
- 典型工作：正式 Word 文件建立與編修

### `slides`

- 核心對象：`.pptx`
- 主要工具：`PptxGenJS`
- 關鍵能力：可編輯 deck 生成、版面驗證、helper 與 render 工具鏈
- 典型工作：工程化簡報建立、重建與修改

### `spreadsheet`

- 核心對象：`.xlsx / .csv / .tsv`
- 主要工具：`openpyxl`、`pandas`
- 關鍵能力：公式意識、重算、格式保留、視覺檢查
- 典型工作：分析報表、模板更新、財務模型、結構化 spreadsheet 交付

## 和你本機既有 skill 的關係

你本機原本已有：

- `docx`
- `pptx`
- `xlsx`

這次新增的是官方 curated 的：

- `doc`
- `slides`
- `spreadsheet`

它們大致是同領域，但不是單純改名版。

觀察上：

- `doc` 與既有 `docx` 很接近，但官方版更明確強調 render loop 與 layout fidelity。
- `slides` 與既有 `pptx` 同樣處理簡報，但官方版更偏 `PptxGenJS`、helper 套件與驗證腳本鏈。
- `spreadsheet` 與既有 `xlsx` 同樣處理試算表，但官方版更完整，尤其在公式規範、render、財務格式與 IB-style layout 上更具體。

## 什麼時候選哪一個

如果你未來要讓 agent 處理文件，我會建議這樣理解：

- 要做 Word：優先想到 `doc`
- 要做 PowerPoint：優先想到 `slides`
- 要做 Excel / CSV / 財務模型：優先想到 `spreadsheet`

而你本機原先的 `docx / pptx / xlsx` 可以視為同領域的另一套 skill，必要時再看哪一個規則更貼近你要的工作方式。

## 補充

這三個 skill 的 `SKILL.md` 本身都不算誇張長，但都已經足以構成完整 workflow：

- `doc`：80 行左右
- `slides`：70 行左右
- `spreadsheet`：145 行左右

其中 `slides` 和 `spreadsheet` 的真正價值不只在 `SKILL.md`，還包括它們附帶的 helper、腳本與 examples。

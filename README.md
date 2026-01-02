# yt-CommunityPostReBuilder

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/yt-community-post-rebuilder.svg)](https://pypi.org/project/yt-community-post-rebuilder/)

📺 YouTube 社群貼文存檔工具 - 將 YouTube 頻道的社群貼文完整備份，並產生一個仿 YouTube 風格的離線 HTML 檢視器。

![Preview](docs/preview.png)

## ✨ 功能特點

- 🔐 **會員貼文支援** - 使用瀏覽器設定檔登入，可獲取會員專屬貼文
- 📊 **投票顯示** - 完整顯示投票選項、百分比與總票數
- 📅 **正確排序** - 預先獲取貼文順序，確保公開與會員貼文以正確的時間順序混合排列
- 🖼️ **頻道資訊** - 自動下載頻道頭像、橫幅與完整簡介
- 🌐 **離線瀏覽** - 產生純靜態 HTML，無需架設伺服器即可瀏覽
- 🔍 **搜尋篩選** - 支援文字搜尋、會員/公開/圖片/投票篩選
- 📱 **響應式設計** - 手機與桌面都能良好顯示
- 🌙 **深色主題** - 採用 YouTube 風格的深色介面

## 📋 系統需求

- Python 3.10+
- Chrome 或 Firefox 瀏覽器

## 🚀 安裝

### 方法一：從 PyPI 安裝（推薦）

```bash
pip install yt-community-post-rebuilder
```

### 方法二：從原始碼安裝

```bash
# 複製專案
git clone https://github.com/user/yt-CommunityPostReBuilder.git
cd yt-CommunityPostReBuilder

# 建立虛擬環境（建議）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 安裝
pip install -e .
```

## 📖 使用方式

### 基本用法

```bash
# 存檔公開貼文
yt-community-viewer "https://www.youtube.com/@ChannelName/posts"
```

### 獲取會員貼文

#### 方法一：Firefox 瀏覽器設定檔（推薦）

使用 Firefox 設定檔是最可靠的方式：

**Windows (PowerShell):**

```powershell
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -d firefox -p "C:\Users\你的用戶名\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxx.default-release"
```

**Linux / macOS:**

```bash
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" \
    -d firefox \
    -p ~/.mozilla/firefox/xxxxx.default-release
```

> 💡 **如何找到 Firefox 設定檔路徑？**
> 在 Firefox 網址列輸入 `about:profiles`，找到「根目錄」即可。

#### 方法二：Cookies 檔案（適用於 Chrome）

Chrome 由於安全限制，無法直接使用設定檔登入。建議改用 cookies 檔案：

```bash
# 相對路徑
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -d chrome -c cookies.txt

# 絕對路徑也可以
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -d chrome -c "C:\path\to\cookies.txt"
```

> 💡 **如何取得 Cookies 檔案？**
> 使用瀏覽器擴充套件如 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) 匯出 Netscape 格式的 cookies。
>
> ⚠️ Cookies 可能會過期，建議優先使用 Firefox 設定檔方式。

### 使用 Cookies 檔案（通用）

```bash
# 相對路徑
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -c cookies.txt

# 絕對路徑也可以
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -c "C:\path\to\cookies.txt"
```

> ⚠️ Cookies 可能會過期，建議使用瀏覽器設定檔方式。

### 常用選項

```bash
# 限制貼文數量
yt-community-viewer "URL" -m 50

# 自訂輸出目錄
yt-community-viewer "URL" -o my-archive

# 顯示瀏覽器視窗（除錯用）
yt-community-viewer "URL" --no-headless

# 不獲取會員貼文
yt-community-viewer "URL" --no-members

# 僅從現有存檔重新產生檢視器
yt-community-viewer --generate-only -o my-archive
```

### 完整選項

```
用法: yt-community-viewer [URL] [選項]

位置參數:
  URL                        YouTube 頻道社群貼文網址

選項:
  -o, --output DIR           輸出目錄 (預設: archive-output)
  -m, --max-posts N          最大貼文數量 (預設: 全部)
  -p, --browser-profile PATH 瀏覽器設定檔路徑
  -n, --profile-name NAME    設定檔名稱 (Chrome 多設定檔時使用)
  -c, --cookies FILE         Netscape 格式 cookies 檔案
  -d, --driver TYPE          瀏覽器驅動 (chrome/firefox，預設: chrome)
  --no-headless              顯示瀏覽器視窗
  --no-members               不獲取會員貼文
  --skip-channel-info        跳過頻道資訊
  --generate-only            僅產生檢視器（不重新爬取）
  -h, --help                 顯示說明
```

## 📁 輸出結構

```
archive-output/
├── channel_avatar.jpg       # 頻道頭像
├── channel_banner.jpg       # 頻道橫幅
├── channel_info.json        # 頻道資訊（含完整簡介）
├── post_order.json          # 貼文排序資訊
├── Ugkx.../                  # 各貼文目錄
│   ├── post.json            # 貼文資料
│   └── *.jpg                # 貼文圖片
└── viewer/                   # 靜態網站
    ├── index.html           # 主頁面
    └── assets/              # 靜態資源
```

## 🖥️ 瀏覽存檔

存檔完成後，直接用瀏覽器開啟 `viewer/index.html` 即可瀏覽。

### 檢視器功能

- **篩選按鈕** - 全部 / 公開貼文 / 會員限定 / 含圖片 / 含投票
- **搜尋** - 輸入關鍵字搜尋貼文內容
- **頻道簡介** - 可展開查看完整頻道簡介
- **圖片放大** - 點擊圖片可放大檢視
- **投票顯示** - 完整顯示投票選項與結果
- **原始連結** - 每則貼文都可連回 YouTube 原始貼文

## 📌 關於貼文排序

本工具採用「預先獲取順序」的方式來確保正確排序：

1. 首先使用 Selenium 滾動瀏覽 `/posts` 頁面，記錄所有貼文 ID 的顯示順序
2. 這個順序包含了公開與會員貼文的正確混合順序
3. 存檔完成後依此順序排列貼文

這種方式比解析「3 個月前」這類相對時間更加準確。

## 🔧 程式化使用

```python
from src.main import run_archiver

run_archiver(
    url="https://www.youtube.com/@ChannelName/posts",
    output_dir="my-archive",
    max_posts=100,
    browser_profile="/path/to/profile",
    driver="firefox",
    headless=True,
    include_members=True,
)
```

## ⚠️ 注意事項

1. **會員貼文** - 需要你實際訂閱該頻道的會員才能獲取
2. **投票結果** - 只有在你已投票的情況下才會顯示百分比
3. **瀏覽器設定檔** - 使用設定檔時請確保該瀏覽器已關閉
4. **使用條款** - 請遵守 YouTube 使用條款，僅供個人存檔用途

## 🔄 多次存檔

- 重複執行時，已存在的貼文不會重複下載
- 貼文順序會在每次存檔時更新
- 會員狀態會被保留（即使從公開頁面重新存檔）

## 🐛 常見問題

### InvalidSessionIdException 錯誤

這通常發生在長時間運行時瀏覽器連線中斷。解決方式：
- 使用 `-m` 參數限制每次存檔數量
- 重新執行命令（會跳過已存檔的貼文）

### 無法獲取會員貼文

- 確認你已訂閱該頻道的會員
- 確認瀏覽器已登入正確的帳號
- 使用 `--no-headless` 觀察實際運行狀況

### 橫幅無法下載

- 部分頻道可能沒有設定橫幅
- 確保有提供瀏覽器設定檔（`-p` 參數）或 cookies 檔案（`-c` 參數）
- 工具會自動使用 Selenium 嘗試獲取橫幅圖片

## 🙏 致謝

本專案基於 [yt-community-post-archiver](https://github.com/Pyreko/yt-community-post-archiver) 開發。

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE)

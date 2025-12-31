# YouTube Community Post Viewer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

📺 將 YouTube 頻道的社群貼文存檔，並產生一個類似 YouTube 社群介面的靜態 HTML 檢視器。

![Preview](docs/preview.png)

## ✨ 功能特點

- 🔐 **支援會員貼文**：使用瀏覽器設定檔或 cookies 登入，獲取會員專屬貼文
- 📅 **時間排序**：根據相對時間（如「3 個月前」）估算發文時間並排序
- 🖼️ **頻道資訊**：自動下載頻道頭像和橫幅圖片
- 🌐 **離線瀏覽**：產生純靜態 HTML，無需架設任何服務即可瀏覽
- 🔍 **搜尋篩選**：支援文字搜尋、會員/公開篩選、圖片/投票篩選
- 📱 **響應式設計**：在手機和桌面都能良好顯示
- 🌙 **深色主題**：採用 YouTube 風格的深色介面

## 📋 系統需求

- Python 3.10 或更新版本
- Chrome 或 Firefox 瀏覽器（需支援 headless 模式）

> 💡 **WSL 用戶**：即使沒有 GUI，也可以安裝 Chrome 以 headless 模式運行：
> ```bash
> wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
> echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
> sudo apt update && sudo apt install -y google-chrome-stable
> ```

## 🚀 安裝方式

### 方法一：從原始碼安裝

```bash
# 複製專案
git clone <your-repo-url>
cd YoutubeCommunityPostBuilder

# 建立虛擬環境（建議）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安裝依賴
pip install -e .
```

### 方法二：直接使用 pip

```bash
pip install -e /path/to/YoutubeCommunityPostBuilder
```

## 📖 使用方式

### 基本用法

```bash
# 存檔公開貼文
yt-community-viewer "https://www.youtube.com/@ChannelName/posts"
```

### 獲取會員貼文

要獲取會員限定貼文，你需要提供已登入 YouTube 的瀏覽器設定檔：

```bash
# 使用 Chrome 設定檔
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" \
    -p ~/.config/google-chrome/

# 使用 Firefox 設定檔
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" \
    -p ~/.mozilla/firefox/ \
    -d firefox

# 指定特定設定檔名稱
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" \
    -p ~/.config/chromium/ \
    -n "Profile 1"
```

### 使用 Cookies 檔案

```bash
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" \
    -c /path/to/cookies.txt
```

> 💡 Cookies 檔案需要是 Netscape 格式，可使用瀏覽器擴充功能匯出。

### 其他選項

```bash
# 限制最大貼文數量
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -m 50

# 自訂輸出目錄
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -o my-archive

# 顯示瀏覽器視窗（用於除錯）
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" --no-headless

# 不獲取會員貼文
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" --no-members

# 跳過頻道資訊（頭像/橫幅）
yt-community-viewer "https://www.youtube.com/@ChannelName/posts" --skip-channel-info

# 僅從現有存檔產生檢視器（不重新爬取）
yt-community-viewer --generate-only -o my-archive
```

### 完整選項說明

```
用法: yt-community-viewer [URL] [選項]

位置參數:
  URL                   YouTube 頻道社群貼文網址

選項:
  -o, --output DIR      輸出目錄 (預設: archive-output)
  -m, --max-posts N     最大貼文數量 (預設: 全部)
  -p, --browser-profile PATH  瀏覽器設定檔路徑
  -n, --profile-name NAME     瀏覽器設定檔名稱
  -c, --cookies FILE    Netscape 格式 cookies 檔案
  -d, --driver TYPE     瀏覽器驅動 (chrome/firefox)
  --no-headless         顯示瀏覽器視窗
  --no-members          不獲取會員貼文
  --skip-channel-info   跳過頻道資訊
  --generate-only       僅產生檢視器
  -h, --help            顯示說明
```

## 📁 輸出結構

```
archive-output/
├── channel_avatar.jpg      # 頻道頭像
├── channel_banner.jpg      # 頻道橫幅
├── channel_info.json       # 頻道資訊
├── Ugkx.../                 # 各貼文目錄
│   ├── post.json           # 貼文資料
│   └── *.jpg               # 貼文圖片
└── viewer/                  # 靜態網站
    ├── index.html          # 主頁面（直接開啟此檔案）
    └── assets/             # 靜態資源
        ├── channel_avatar.jpg
        ├── channel_banner.jpg
        ├── posts.json
        └── posts/          # 貼文圖片副本
```

## 🖥️ 瀏覽存檔

存檔完成後，直接用瀏覽器開啟 `archive-output/viewer/index.html` 即可。

不需要架設任何伺服器！

### 功能介紹

- **篩選按鈕**：全部 / 公開貼文 / 會員限定 / 含圖片 / 含投票
- **搜尋**：輸入關鍵字搜尋貼文內容
- **圖片放大**：點擊圖片可放大檢視
- **連結**：每則貼文都有「查看原始貼文」連結

## ⚠️ 關於時間排序

由於 YouTube 社群貼文不提供精確的時間戳，只顯示相對時間（如「3 個月前」），本工具會根據相對時間估算發文日期：

- 估算是基於**執行存檔時**的時間計算
- 同樣顯示「3 個月前」的貼文會被視為同一天
- 若要更精確的排序，建議定期執行存檔

## 🔧 以程式方式使用

```python
from src.main import run_archiver

# 基本使用
run_archiver(
    url="https://www.youtube.com/@ChannelName/posts",
    output_dir="my-archive",
)

# 完整選項
run_archiver(
    url="https://www.youtube.com/@ChannelName/posts",
    output_dir="my-archive",
    max_posts=100,
    browser_profile="~/.config/chromium/",
    profile_name="Default",
    driver="chrome",
    headless=True,
    include_members=True,
    fetch_channel_info=True,
)
```

## 📝 注意事項

1. **會員貼文**需要你實際訂閱該頻道的會員才能獲取
2. **投票結果**只有在你已投票的情況下才會顯示百分比
3. 建議為此工具**建立專用的瀏覽器設定檔**，避免影響日常使用
4. YouTube 可能會更新網頁結構，導致爬取功能暫時失效
5. 請遵守 YouTube 的使用條款，僅供個人存檔用途

## 🙏 致謝

本專案基於 [yt-community-post-archiver](https://github.com/Pyreko/yt-community-post-archiver) 開發。

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE) 檔案

"""
YouTube Community Post Viewer
Main entry point and CLI interface.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .archiver import PostArchiver
from .channel_fetcher import ChannelFetcher
from .data_processor import DataProcessor
from .html_generator import HTMLGenerator


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Archive YouTube community posts and generate a static HTML viewer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例用法:
  # 基本使用 - 存檔公開貼文
  yt-community-viewer "https://www.youtube.com/@ChannelName/posts"

  # 使用瀏覽器設定檔登入以獲取會員貼文
  yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -p ~/.config/chromium/

  # 使用 cookies 檔案
  yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -c cookies.txt

  # 限制最大貼文數量
  yt-community-viewer "https://www.youtube.com/@ChannelName/posts" -m 50

  # 僅從現有存檔產生檢視器（不重新爬取）
  yt-community-viewer --generate-only -o my-archive
        """,
    )
    
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube 頻道社群貼文網址 (例如: https://www.youtube.com/@Channel/posts)",
    )
    
    parser.add_argument(
        "-o", "--output",
        default="archive-output",
        help="輸出目錄 (預設: archive-output)",
    )
    
    parser.add_argument(
        "-m", "--max-posts",
        type=int,
        default=None,
        help="最大貼文數量 (預設: 全部)",
    )
    
    parser.add_argument(
        "-p", "--browser-profile",
        default=None,
        help="瀏覽器設定檔路徑 (用於登入會員貼文)",
    )
    
    parser.add_argument(
        "-n", "--profile-name",
        default=None,
        help="瀏覽器設定檔名稱 (預設使用 default)",
    )
    
    parser.add_argument(
        "-c", "--cookies",
        default=None,
        help="Netscape 格式的 cookies 檔案路徑",
    )
    
    parser.add_argument(
        "-d", "--driver",
        choices=["chrome", "firefox"],
        default="chrome",
        help="使用的瀏覽器驅動 (預設: chrome)",
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="顯示瀏覽器視窗 (用於除錯)",
    )
    
    parser.add_argument(
        "--no-members",
        action="store_true",
        help="不獲取會員貼文",
    )
    
    parser.add_argument(
        "--skip-channel-info",
        action="store_true",
        help="跳過獲取頻道資訊 (頭像/橫幅)",
    )
    
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="僅從現有存檔產生 HTML 檢視器 (不重新爬取)",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.generate_only and not args.url:
        parser.error("請提供 YouTube 頻道社群貼文網址，或使用 --generate-only 從現有存檔產生檢視器")
    
    try:
        run_archiver(
            url=args.url,
            output_dir=args.output,
            max_posts=args.max_posts,
            browser_profile=args.browser_profile,
            profile_name=args.profile_name,
            cookies_file=args.cookies,
            driver=args.driver,
            headless=not args.no_headless,
            include_members=not args.no_members,
            fetch_channel_info=not args.skip_channel_info,
            generate_only=args.generate_only,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        sys.exit(1)


def run_archiver(
    url: Optional[str] = None,
    output_dir: str = "archive-output",
    max_posts: Optional[int] = None,
    browser_profile: Optional[str] = None,
    profile_name: Optional[str] = None,
    cookies_file: Optional[str] = None,
    driver: str = "chrome",
    headless: bool = True,
    include_members: bool = True,
    fetch_channel_info: bool = True,
    generate_only: bool = False,
) -> Path:
    """
    Run the complete archiving and HTML generation process.
    
    Args:
        url: YouTube channel community posts URL
        output_dir: Output directory path
        max_posts: Maximum number of posts to archive
        browser_profile: Browser profile path for login
        profile_name: Browser profile name
        cookies_file: Netscape cookies file path
        driver: Browser driver (chrome or firefox)
        headless: Run browser in headless mode
        include_members: Also archive membership posts
        fetch_channel_info: Fetch channel avatar and banner
        generate_only: Only generate HTML from existing archive
        
    Returns:
        Path to the generated index.html
    """
    output_path = Path(output_dir)
    
    print("=" * 60)
    print("🎬 YouTube 社群貼文存檔工具")
    print("=" * 60)
    
    channel_info = None
    posts = []
    
    if not generate_only:
        # Step 1: Fetch channel info (avatar, banner)
        if fetch_channel_info and url:
            print("\n📸 正在獲取頻道資訊...")
            fetcher = ChannelFetcher(output_dir=output_dir)
            channel_info = fetcher.fetch_channel_info(url)
            
            if channel_info:
                print(f"   頻道名稱: {channel_info.name}")
                print(f"   頻道代號: {channel_info.handle}")
                if channel_info.local_avatar:
                    print(f"   ✅ 已下載頭像")
                if channel_info.local_banner:
                    print(f"   ✅ 已下載橫幅")
            else:
                print("   ⚠️  無法獲取頻道資訊")
        
        # Step 2: Archive posts
        print("\n📥 正在存檔社群貼文...")
        archiver = PostArchiver(
            output_dir=output_dir,
            browser_profile=browser_profile,
            profile_name=profile_name,
            cookies_file=cookies_file,
            driver=driver,
            headless=headless,
        )
        
        # Archive based on authentication availability
        if browser_profile or cookies_file:
            print("   使用已登入的瀏覽器設定檔...")
            posts = archiver.archive_channel(
                channel_url=url,
                include_membership=include_members,
                max_posts=max_posts,
            )
        else:
            print("   未提供登入資訊，僅存檔公開貼文...")
            posts = archiver.archive_channel(
                channel_url=url,
                include_membership=False,
                max_posts=max_posts,
            )
        
        print(f"   已存檔 {len(posts)} 則貼文")
    
    else:
        # Load existing archive
        print("\n📂 從現有存檔載入資料...")
        
        archiver = PostArchiver(output_dir=output_dir)
        posts = archiver.load_archived_posts()
        
        fetcher = ChannelFetcher(output_dir=output_dir)
        channel_info = fetcher.load_channel_info()
        
        print(f"   已載入 {len(posts)} 則貼文")
    
    if not posts:
        print("\n⚠️  沒有找到任何貼文資料")
        return output_path / "viewer" / "index.html"
    
    # Step 3: Process data
    print("\n🔄 正在處理資料...")
    processor = DataProcessor(output_dir=output_dir)
    processed_data = processor.process_all(posts, channel_info)
    
    # Print statistics
    stats = processor.get_statistics(posts)
    print(f"   公開貼文: {stats['public']}")
    print(f"   會員貼文: {stats['members_only']}")
    print(f"   含圖片: {stats['with_images']}")
    print(f"   含投票: {stats['with_polls']}")
    
    # Step 4: Generate HTML viewer
    print("\n🌐 正在產生 HTML 檢視器...")
    generator = HTMLGenerator(output_dir=output_dir)
    index_path = generator.generate(processed_data)
    
    print("\n" + "=" * 60)
    print("✨ 完成！")
    print("=" * 60)
    print(f"\n📁 存檔目錄: {output_path.absolute()}")
    print(f"🌐 檢視器: {index_path.absolute()}")
    print("\n💡 在瀏覽器中開啟 index.html 即可瀏覽存檔內容")
    
    return index_path


if __name__ == "__main__":
    main()

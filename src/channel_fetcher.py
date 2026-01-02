"""
Channel Info Fetcher Module
Fetches channel metadata including avatar and banner images.
"""

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests


@dataclass
class ChannelInfo:
    """Represents YouTube channel information."""
    
    channel_id: str
    name: str
    handle: str
    description: str
    avatar_url: str
    banner_url: str
    local_avatar: str = ""
    local_banner: str = ""
    subscriber_count: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "handle": self.handle,
            "description": self.description,
            "avatar_url": self.avatar_url,
            "banner_url": self.banner_url,
            "local_avatar": self.local_avatar,
            "local_banner": self.local_banner,
            "subscriber_count": self.subscriber_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelInfo":
        """Create from dictionary."""
        return cls(
            channel_id=data.get("channel_id", ""),
            name=data.get("name", ""),
            handle=data.get("handle", ""),
            description=data.get("description", ""),
            avatar_url=data.get("avatar_url", ""),
            banner_url=data.get("banner_url", ""),
            local_avatar=data.get("local_avatar", ""),
            local_banner=data.get("local_banner", ""),
            subscriber_count=data.get("subscriber_count", ""),
        )


class ChannelFetcher:
    """Fetches channel information from YouTube."""
    
    def __init__(
        self, 
        output_dir: str = "archive-output",
        browser_profile: Optional[str] = None,
        driver: str = "chrome",
        headless: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.browser_profile = browser_profile
        self.driver_type = driver
        self.headless = headless
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Don't set Accept-Language to get original channel description
        })
    
    def fetch_channel_info(self, channel_url: str) -> Optional[ChannelInfo]:
        """
        Fetch channel information from a YouTube channel URL.
        
        Args:
            channel_url: URL to the YouTube channel
            
        Returns:
            ChannelInfo object or None if fetching fails
        """
        try:
            # Normalize URL to channel page
            channel_url = self._normalize_channel_url(channel_url)
            
            # Fetch the channel page
            response = self.session.get(channel_url)
            response.raise_for_status()
            html = response.text
            
            # Extract initial data JSON
            channel_info = self._parse_channel_page(html, channel_url)
            
            if channel_info:
                # Fetch full description from /about page
                about_description = self._fetch_about_description(channel_url)
                if about_description:
                    channel_info.description = about_description
                
                # If no banner URL found, try using Selenium
                if not channel_info.banner_url:
                    banner_url = self._fetch_banner_with_selenium(channel_url)
                    if banner_url:
                        channel_info.banner_url = banner_url
                
                # Download images
                self._download_images(channel_info)
                
                # Save channel info
                self._save_channel_info(channel_info)
            
            return channel_info
            
        except Exception as e:
            print(f"Error fetching channel info: {e}")
            return None
    
    def _fetch_about_description(self, channel_url: str) -> Optional[str]:
        """Fetch full channel description from the /about page."""
        try:
            about_url = channel_url + "/about"
            response = self.session.get(about_url)
            response.raise_for_status()
            html = response.text
            
            # Try to find ytInitialData JSON
            match = re.search(r'var ytInitialData = ({.*?});</script>', html, re.DOTALL)
            if not match:
                match = re.search(r'ytInitialData"\s*:\s*({.*?})\s*[,}]</script>', html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                
                # First try: metadata.channelMetadataRenderer.description (most reliable)
                metadata = data.get("metadata", {}).get("channelMetadataRenderer", {})
                if metadata and metadata.get("description"):
                    return metadata["description"]
                
                # Second try: Navigate to the about tab content
                # Path: contents.twoColumnBrowseResultsRenderer.tabs[].tabRenderer.content
                tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
                
                for tab in tabs:
                    tab_renderer = tab.get("tabRenderer", {})
                    if tab_renderer.get("title") == "About" or tab_renderer.get("selected"):
                        content = tab_renderer.get("content", {})
                        
                        # Try sectionListRenderer path
                        section_list = content.get("sectionListRenderer", {}).get("contents", [])
                        for section in section_list:
                            item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                            for item in item_section:
                                # channelAboutFullMetadataRenderer contains the full description
                                about_renderer = item.get("channelAboutFullMetadataRenderer", {})
                                if about_renderer:
                                    desc = about_renderer.get("description", {})
                                    if "simpleText" in desc:
                                        return desc["simpleText"]
                                    elif "runs" in desc:
                                        return "".join(run.get("text", "") for run in desc["runs"])
                    
        except Exception as e:
            print(f"Error fetching about page: {e}")
        
        return None
    
    def _fetch_banner_with_selenium(self, channel_url: str) -> Optional[str]:
        """Fetch banner URL using Selenium for better reliability."""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            
            # Setup driver
            if self.driver_type == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                    options.add_argument("--width=1920")
                    options.add_argument("--height=1080")
                if self.browser_profile:
                    options.add_argument("-profile")
                    options.add_argument(self.browser_profile)
                driver = webdriver.Firefox(options=options)
            else:
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                    options.add_argument("--window-size=1920,1080")
                if self.browser_profile:
                    options.add_argument(f"--user-data-dir={self.browser_profile}")
                driver = webdriver.Chrome(options=options)
            
            banner_url = None
            
            try:
                driver.get(channel_url)
                time.sleep(3)  # Wait for page to load
                
                # Try to find banner image
                # Method 1: Look for yt-image-banner
                try:
                    banner_elements = driver.find_elements(By.CSS_SELECTOR, "yt-image-banner img")
                    for elem in banner_elements:
                        src = elem.get_attribute("src")
                        if src and "yt3.googleusercontent.com" in src:
                            banner_url = src
                            break
                except:
                    pass
                
                # Method 2: Look for banner in style attribute
                if not banner_url:
                    try:
                        banner_container = driver.find_element(By.ID, "page-header-banner")
                        style = banner_container.get_attribute("style")
                        if style:
                            match = re.search(r'url\(["\']?(https://[^"\')\s]+)["\']?\)', style)
                            if match:
                                banner_url = match.group(1)
                    except:
                        pass
                
                # Method 3: Look for any large banner-like image
                if not banner_url:
                    try:
                        imgs = driver.find_elements(By.TAG_NAME, "img")
                        for img in imgs:
                            src = img.get_attribute("src") or ""
                            # Banner URLs typically have specific patterns
                            if "yt3.googleusercontent.com" in src and ("banner" in src.lower() or "=w" in src):
                                width = img.get_attribute("width")
                                if width and int(width) > 800:
                                    banner_url = src
                                    break
                    except:
                        pass
                
                # Method 4: Extract from page source ytInitialData
                if not banner_url:
                    try:
                        page_source = driver.page_source
                        match = re.search(r'"banner":\s*\{"thumbnails":\s*\[(.*?)\]', page_source)
                        if match:
                            thumbnails_str = match.group(1)
                            url_match = re.findall(r'"url":\s*"([^"]+)"', thumbnails_str)
                            if url_match:
                                banner_url = url_match[-1]  # Get highest quality (last one)
                    except:
                        pass
                
                if banner_url:
                    # Upgrade to high quality
                    banner_url = self._get_high_quality_banner(banner_url)
                    print(f"   找到橫幅圖片")
                
            finally:
                driver.quit()
            
            return banner_url
            
        except Exception as e:
            print(f"Warning: Could not fetch banner with Selenium: {e}")
            return None
    
    def _normalize_channel_url(self, url: str) -> str:
        """Normalize URL to the main channel page."""
        url = url.rstrip("/")
        # Remove any path suffix
        for suffix in ["/posts", "/community", "/membership", "/videos", "/about", "/channels", "/playlists"]:
            if url.endswith(suffix):
                url = url[:-len(suffix)]
                break
        return url
    
    def _parse_channel_page(self, html: str, url: str) -> Optional[ChannelInfo]:
        """Parse the channel page HTML to extract info."""
        
        # Try to find ytInitialData JSON
        match = re.search(r'var ytInitialData = ({.*?});</script>', html, re.DOTALL)
        if not match:
            match = re.search(r'ytInitialData"\s*:\s*({.*?})\s*[,}]</script>', html, re.DOTALL)
        
        if match:
            try:
                data = json.loads(match.group(1))
                return self._extract_from_initial_data(data, url)
            except json.JSONDecodeError:
                pass
        
        # Fallback: Try meta tags
        return self._extract_from_meta_tags(html, url)
    
    def _extract_from_initial_data(self, data: dict, url: str) -> Optional[ChannelInfo]:
        """Extract channel info from ytInitialData."""
        try:
            # Navigate to channel metadata
            metadata = None
            header = None
            
            # Try different paths for metadata
            if "metadata" in data:
                metadata = data["metadata"].get("channelMetadataRenderer", {})
            
            # Try to find header
            if "header" in data:
                header = data["header"].get("c4TabbedHeaderRenderer", {})
                if not header:
                    header = data["header"].get("pageHeaderRenderer", {})
            
            # Extract basic info
            channel_id = ""
            name = ""
            handle = ""
            description = ""
            avatar_url = ""
            banner_url = ""
            subscriber_count = ""
            
            if metadata:
                channel_id = metadata.get("externalId", "")
                name = metadata.get("title", "")
                description = metadata.get("description", "")
                avatar_url = metadata.get("avatar", {}).get("thumbnails", [{}])[-1].get("url", "")
            
            if header:
                if not name:
                    name = header.get("title", "")
                if not avatar_url:
                    avatar_thumbnails = header.get("avatar", {}).get("thumbnails", [])
                    if avatar_thumbnails:
                        avatar_url = avatar_thumbnails[-1].get("url", "")
                
                # Banner
                banner_data = header.get("banner", {}).get("thumbnails", [])
                if banner_data:
                    banner_url = banner_data[-1].get("url", "")
                
                # TV banner (often higher quality)
                tv_banner = header.get("tvBanner", {}).get("thumbnails", [])
                if tv_banner:
                    banner_url = tv_banner[-1].get("url", "")
                
                # Subscriber count
                sub_text = header.get("subscriberCountText", {}).get("simpleText", "")
                if sub_text:
                    subscriber_count = sub_text
            
            # Extract handle from URL
            handle_match = re.search(r"@([\w-]+)", url)
            if handle_match:
                handle = "@" + handle_match.group(1)
            
            # Ensure avatar URL is high quality
            if avatar_url:
                avatar_url = self._get_high_quality_avatar(avatar_url)
            
            # Ensure banner URL is high quality
            if banner_url:
                banner_url = self._get_high_quality_banner(banner_url)
            
            return ChannelInfo(
                channel_id=channel_id,
                name=name,
                handle=handle,
                description=description,
                avatar_url=avatar_url,
                banner_url=banner_url,
                subscriber_count=subscriber_count,
            )
            
        except Exception as e:
            print(f"Error extracting from initial data: {e}")
            return None
    
    def _extract_from_meta_tags(self, html: str, url: str) -> Optional[ChannelInfo]:
        """Fallback: Extract basic info from meta tags."""
        name = ""
        description = ""
        avatar_url = ""
        
        # og:title
        match = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        if match:
            name = match.group(1)
        
        # og:description
        match = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if match:
            description = match.group(1)
        
        # og:image (usually the avatar)
        match = re.search(r'<meta property="og:image" content="([^"]*)"', html)
        if match:
            avatar_url = match.group(1)
        
        # Extract handle from URL
        handle = ""
        handle_match = re.search(r"@([\w-]+)", url)
        if handle_match:
            handle = "@" + handle_match.group(1)
        
        if name or avatar_url:
            return ChannelInfo(
                channel_id="",
                name=name,
                handle=handle,
                description=description,
                avatar_url=self._get_high_quality_avatar(avatar_url) if avatar_url else "",
                banner_url="",
            )
        
        return None
    
    def _get_high_quality_avatar(self, url: str) -> str:
        """Convert avatar URL to high quality version."""
        if not url:
            return url
        # YouTube avatar URLs can have size parameters, request large size
        # e.g., =s88-c-k-c0x00ffffff-no-rj -> =s800-c-k-c0x00ffffff-no-rj
        url = re.sub(r"=s\d+-", "=s800-", url)
        return url
    
    def _get_high_quality_banner(self, url: str) -> str:
        """Convert banner URL to high quality version."""
        if not url:
            return url
        # Request high resolution banner
        # e.g., =w1060- -> =w2120-
        url = re.sub(r"=w\d+-", "=w2120-", url)
        return url
    
    def _download_images(self, channel_info: ChannelInfo) -> None:
        """Download avatar and banner images."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download avatar
        if channel_info.avatar_url:
            avatar_path = self.output_dir / "channel_avatar.jpg"
            if self._download_image(channel_info.avatar_url, avatar_path):
                channel_info.local_avatar = "channel_avatar.jpg"
        
        # Download banner
        if channel_info.banner_url:
            banner_path = self.output_dir / "channel_banner.jpg"
            if self._download_image(channel_info.banner_url, banner_path):
                channel_info.local_banner = "channel_banner.jpg"
    
    def _download_image(self, url: str, path: Path) -> bool:
        """Download an image from URL to local path."""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded: {path}")
            return True
            
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def _save_channel_info(self, channel_info: ChannelInfo) -> None:
        """Save channel info to JSON file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        info_path = self.output_dir / "channel_info.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(channel_info.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"Saved channel info: {info_path}")
    
    def load_channel_info(self) -> Optional[ChannelInfo]:
        """Load channel info from saved JSON file."""
        info_path = self.output_dir / "channel_info.json"
        
        if not info_path.exists():
            return None
        
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChannelInfo.from_dict(data)
        except Exception as e:
            print(f"Error loading channel info: {e}")
            return None

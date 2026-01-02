"""
Post Archiver Module
Wrapper around yt-community-post-archiver with additional functionality.
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import parse_relative_date, sanitize_filename


@dataclass
class CommunityPost:
    """Represents a single community post."""
    
    post_id: str
    url: str
    text: str
    images: list[str] = field(default_factory=list)
    local_images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    is_members: bool = False
    relative_date: str = ""
    estimated_date: Optional[datetime] = None
    num_comments: str = "0"
    num_thumbs_up: str = "0"
    poll: Optional[dict] = None
    when_archived: str = ""
    
    @classmethod
    def from_json(cls, data: dict, post_dir: Path) -> "CommunityPost":
        """Create a CommunityPost from JSON data."""
        post_id = data.get("url", "").split("/")[-1] if data.get("url") else ""
        
        # Find local images
        local_images = []
        if post_dir.exists():
            for img_file in post_dir.glob("*.jpg"):
                local_images.append(img_file.name)
            for img_file in post_dir.glob("*.png"):
                local_images.append(img_file.name)
            for img_file in post_dir.glob("*.webp"):
                local_images.append(img_file.name)
        
        # Parse relative date to estimated date
        relative_date = data.get("relative_date", "")
        estimated_date = parse_relative_date(relative_date)
        
        return cls(
            post_id=post_id,
            url=data.get("url", ""),
            text=data.get("text", ""),
            images=data.get("images", []),
            local_images=local_images,
            links=data.get("links", []),
            is_members=data.get("is_members", False),
            relative_date=relative_date,
            estimated_date=estimated_date,
            num_comments=data.get("num_comments", data.get("approximate_num_comments", "0")),
            num_thumbs_up=data.get("num_thumbs_up", "0"),
            poll=data.get("poll"),
            when_archived=data.get("when_archived", ""),
        )


class PostArchiver:
    """Wrapper for yt-community-post-archiver functionality."""
    
    def __init__(
        self,
        output_dir: str = "archive-output",
        browser_profile: Optional[str] = None,
        profile_name: Optional[str] = None,
        cookies_file: Optional[str] = None,
        driver: str = "chrome",
        headless: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.browser_profile = browser_profile
        self.profile_name = profile_name
        self.cookies_file = cookies_file
        self.driver = driver
        self.headless = headless
    
    def _fetch_post_order_from_page(self, channel_url: str, max_posts: Optional[int] = None) -> list[str]:
        """
        Fetch post IDs in order from the channel's posts page using Selenium.
        
        This captures the correct mixed order of public and member posts
        as displayed on YouTube (if logged in as a member).
        
        Returns:
            List of post IDs in display order (newest first)
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            
            # Setup driver
            if self.driver == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                if self.browser_profile:
                    profile_path = self.browser_profile
                    if self.profile_name:
                        profile_path = os.path.join(self.browser_profile, self.profile_name)
                    options.add_argument("-profile")
                    options.add_argument(profile_path)
                driver = webdriver.Firefox(options=options)
            else:
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless")
                if self.browser_profile:
                    options.add_argument(f"--user-data-dir={self.browser_profile}")
                    if self.profile_name:
                        options.add_argument(f"--profile-directory={self.profile_name}")
                driver = webdriver.Chrome(options=options)
            
            post_ids = []
            seen = set()
            
            try:
                # Navigate to posts page
                posts_url = self._ensure_posts_url(channel_url)
                driver.get(posts_url)
                
                # Handle cookies if provided
                if self.cookies_file and os.path.exists(self.cookies_file):
                    time.sleep(2)
                    self._load_cookies_to_driver(driver)
                    driver.refresh()
                
                time.sleep(3)  # Wait for page to load
                
                # Scroll and collect post IDs
                max_same_count = 15
                same_count = 0
                last_count = 0
                
                while True:
                    # Find all post elements
                    posts = driver.find_elements(By.ID, "post")
                    
                    for post in posts:
                        try:
                            # Find the post link to get the URL
                            links = post.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute("href")
                                if href and "/post/" in href:
                                    post_id = href.split("/post/")[-1].split("?")[0]
                                    if post_id and post_id not in seen:
                                        seen.add(post_id)
                                        post_ids.append(post_id)
                                    break
                        except:
                            continue
                    
                    # Check if we've reached max posts
                    if max_posts and len(post_ids) >= max_posts:
                        break
                    
                    # Check if we're still finding new posts
                    if len(post_ids) == last_count:
                        same_count += 1
                        if same_count >= max_same_count:
                            break
                    else:
                        same_count = 0
                        last_count = len(post_ids)
                    
                    # Scroll down
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
                
                print(f"   預先獲取到 {len(post_ids)} 則貼文順序")
                
            finally:
                driver.quit()
            
            return post_ids
            
        except Exception as e:
            print(f"Warning: Could not fetch post order: {e}")
            return []
    
    def _load_cookies_to_driver(self, driver) -> None:
        """Load cookies from file into the Selenium driver."""
        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        cookie = {
                            "domain": parts[0],
                            "name": parts[5],
                            "value": parts[6],
                            "path": parts[2],
                            "secure": parts[3].lower() == "true",
                        }
                        if ".youtube.com" in cookie["domain"]:
                            try:
                                driver.add_cookie(cookie)
                            except:
                                pass
        except Exception as e:
            print(f"Warning: Could not load cookies: {e}")
        
    def archive_channel(
        self,
        channel_url: str,
        include_membership: bool = True,
        max_posts: Optional[int] = None,
    ) -> list[CommunityPost]:
        """
        Archive community posts from a YouTube channel.
        
        Args:
            channel_url: URL to the channel's community/posts page
            include_membership: Whether to also archive membership posts
            max_posts: Maximum number of posts to archive (None for all)
            
        Returns:
            List of archived CommunityPost objects
        """
        # Load existing member post IDs before archiving
        # This preserves member status even if re-archived from /posts page
        existing_member_ids = self._load_member_post_ids()
        
        # Pre-fetch post order from the page (captures correct mixed order)
        print("   正在獲取貼文順序...")
        pre_fetched_order = self._fetch_post_order_from_page(channel_url, max_posts)
        
        # Wait a bit to ensure browser is fully closed before archiver starts
        if pre_fetched_order:
            time.sleep(2)
        
        # Archive regular posts
        regular_url = self._ensure_posts_url(channel_url)
        self._run_archiver(regular_url, max_posts)
        
        # Archive membership posts if requested and authenticated
        if include_membership and (self.browser_profile or self.cookies_file):
            membership_url = self._get_membership_url(channel_url)
            self._run_archiver(membership_url, max_posts)
        
        # Load all archived posts
        posts = self.load_archived_posts()
        
        # Restore member status for posts that were previously marked as members
        self._restore_member_status(posts, existing_member_ids)
        
        # Update post order - use pre-fetched order if available
        self._update_post_order(posts, pre_fetched_order)
        
        return posts
    
    def _load_member_post_ids(self) -> set[str]:
        """Load IDs of posts previously marked as member-only."""
        member_ids = set()
        if not self.output_dir.exists():
            return member_ids
        
        for post_json in self.output_dir.rglob("post.json"):
            try:
                with open(post_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("is_members", False):
                    post_id = data.get("url", "").split("/")[-1]
                    if post_id:
                        member_ids.add(post_id)
            except (json.JSONDecodeError, IOError):
                pass
        
        return member_ids
    
    def _restore_member_status(self, posts: list[CommunityPost], member_ids: set[str]) -> None:
        """Restore member status for posts and update their JSON files."""
        for post in posts:
            if post.post_id in member_ids and not post.is_members:
                # Restore member status
                post.is_members = True
                
                # Update the post.json file
                post_json_path = self.output_dir / post.post_id / "post.json"
                if post_json_path.exists():
                    try:
                        with open(post_json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["is_members"] = True
                        with open(post_json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Warning: Could not update member status for {post.post_id}: {e}")
    
    def _update_post_order(self, posts: list[CommunityPost], pre_fetched_order: list[str] = None) -> None:
        """
        Update the post_order.json file to maintain correct chronological order.
        
        Args:
            posts: List of all archived posts
            pre_fetched_order: List of post IDs in correct display order (if available)
        """
        order_file = self.output_dir / "post_order.json"
        
        # Load existing order
        existing_order = {}
        if order_file.exists():
            try:
                with open(order_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing_order = {item["post_id"]: item["order"] for item in data.get("posts", [])}
            except (json.JSONDecodeError, IOError):
                pass
        
        # If we have pre-fetched order, use it as the primary source
        if pre_fetched_order:
            new_order = {}
            for idx, post_id in enumerate(pre_fetched_order):
                new_order[post_id] = idx
        else:
            # Fall back to when_archived ordering
            # Sort posts by when_archived to get this session's order
            # Earlier when_archived = newer post (was at top of page)
            posts_with_time = []
            for post in posts:
                if post.when_archived:
                    try:
                        archived_dt = datetime.fromisoformat(
                            post.when_archived.replace("+00:00", "").replace("Z", "")
                        )
                        posts_with_time.append((post, archived_dt))
                    except ValueError:
                        pass
            
            # Sort by archive time (ascending = newest posts first)
            posts_with_time.sort(key=lambda x: x[1])
            
            # Assign order numbers (lower = newer)
            new_order = {}
            for idx, (post, _) in enumerate(posts_with_time):
                new_order[post.post_id] = idx
        
        # Merge with existing order - new posts get their new order,
        # existing posts that weren't re-archived keep their old order
        # but shifted to maintain relative positions
        final_order = []
        for post in posts:
            if post.post_id in new_order:
                final_order.append({
                    "post_id": post.post_id,
                    "order": new_order[post.post_id]
                })
            elif post.post_id in existing_order:
                final_order.append({
                    "post_id": post.post_id,
                    "order": existing_order[post.post_id]
                })
        
        # Sort by order and re-assign sequential numbers
        final_order.sort(key=lambda x: x["order"])
        for idx, item in enumerate(final_order):
            item["order"] = idx
        
        # Save to file
        with open(order_file, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "posts": final_order
            }, f, ensure_ascii=False, indent=2)
    
    def _ensure_posts_url(self, url: str) -> str:
        """Ensure the URL points to the posts page."""
        url = url.rstrip("/")
        if not url.endswith("/posts") and not url.endswith("/community"):
            if "/membership" in url:
                return url
            url = url + "/posts"
        return url
    
    def _get_membership_url(self, url: str) -> str:
        """Convert a channel URL to its membership posts URL."""
        url = url.rstrip("/")
        # Remove any existing path suffix
        for suffix in ["/posts", "/community", "/videos", "/about", "/channels"]:
            if url.endswith(suffix):
                url = url[:-len(suffix)]
                break
        return url + "/membership"
    
    def _run_archiver(self, url: str, max_posts: Optional[int] = None, max_retries: int = 2) -> None:
        """Run the yt-community-post-archiver command with retry support."""
        cmd = [
            sys.executable, "-m", "yt_community_post_archiver",
            url,
            "-o", str(self.output_dir),
            "-d", self.driver,
        ]
        
        if max_posts is not None:
            cmd.extend(["-m", str(max_posts)])
        
        if self.browser_profile:
            cmd.extend(["-p", self.browser_profile])
            if self.profile_name:
                cmd.extend(["-n", self.profile_name])
        elif self.cookies_file:
            cmd.extend(["-c", self.cookies_file])
        
        if not self.headless:
            cmd.append("--not-headless")
        
        print(f"Running: {' '.join(cmd)}")
        
        for attempt in range(max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                )
                
                if result.returncode == 0:
                    if result.stdout:
                        print(result.stdout)
                    return
                
                # Check if it's a recoverable error (InvalidSessionIdException)
                if "InvalidSessionIdException" in result.stderr:
                    if attempt < max_retries:
                        print(f"Warning: Browser session lost. Retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(5)  # Wait before retry
                        continue
                    else:
                        print(f"Error: Browser session lost after {max_retries} retries.")
                        print("This may be due to:")
                        print("  - Long running time causing browser timeout")
                        print("  - Browser profile being used by another process")
                        print("  - Insufficient memory")
                        print("Try running with a smaller -m value to archive fewer posts at once.")
                else:
                    print(f"Warning: Archiver returned non-zero exit code: {result.returncode}")
                    print(f"Stderr: {result.stderr}")
                
                if result.stdout:
                    print(result.stdout)
                return
                    
            except subprocess.TimeoutExpired:
                print("Error: Archiver timed out after 1 hour")
                return
            except FileNotFoundError:
                print("Error: yt-community-post-archiver not found. Please install it with:")
                print("  pip install yt-community-post-archiver")
                return
    
    def load_archived_posts(self) -> list[CommunityPost]:
        """Load all archived posts from the output directory."""
        posts = []
        
        if not self.output_dir.exists():
            return posts
        
        # Find all post.json files
        for post_json in self.output_dir.rglob("post.json"):
            try:
                with open(post_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                post = CommunityPost.from_json(data, post_json.parent)
                posts.append(post)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {post_json}: {e}")
        
        return posts
    
    def get_posts_sorted_by_date(self, descending: bool = True) -> list[CommunityPost]:
        """
        Get all posts sorted by estimated date.
        
        Note: Since YouTube doesn't provide exact timestamps, sorting is based on
        relative dates parsed to approximate datetime values.
        """
        posts = self.load_archived_posts()
        
        # Sort by estimated date (posts without dates go to the end)
        def sort_key(post: CommunityPost):
            if post.estimated_date:
                return (0, post.estimated_date)
            return (1, datetime.min)
        
        posts.sort(key=sort_key, reverse=descending)
        return posts

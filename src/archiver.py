"""
Post Archiver Module
Wrapper around yt-community-post-archiver with additional functionality.
"""

import json
import os
import subprocess
import sys
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
        posts = []
        
        # Archive regular posts
        regular_url = self._ensure_posts_url(channel_url)
        self._run_archiver(regular_url, max_posts)
        
        # Archive membership posts if requested and authenticated
        if include_membership and (self.browser_profile or self.cookies_file):
            membership_url = self._get_membership_url(channel_url)
            self._run_archiver(membership_url, max_posts)
        
        # Load all archived posts
        posts = self.load_archived_posts()
        
        return posts
    
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
    
    def _run_archiver(self, url: str, max_posts: Optional[int] = None) -> None:
        """Run the yt-community-post-archiver command."""
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
            cmd.append("--no-headless")
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
            
            if result.returncode != 0:
                print(f"Warning: Archiver returned non-zero exit code: {result.returncode}")
                print(f"Stderr: {result.stderr}")
            
            if result.stdout:
                print(result.stdout)
                
        except subprocess.TimeoutExpired:
            print("Error: Archiver timed out after 1 hour")
        except FileNotFoundError:
            print("Error: yt-community-post-archiver not found. Please install it with:")
            print("  pip install yt-community-post-archiver")
    
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

"""
Data Processor Module
Handles sorting and organizing community posts.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .archiver import CommunityPost
from .channel_fetcher import ChannelInfo


@dataclass
class ProcessedData:
    """Container for all processed archive data."""
    
    channel_info: Optional[ChannelInfo]
    posts: list[CommunityPost]
    member_posts: list[CommunityPost]
    all_posts_sorted: list[CommunityPost]
    archive_date: datetime
    
    @property
    def total_posts(self) -> int:
        return len(self.all_posts_sorted)
    
    @property
    def member_only_count(self) -> int:
        return len(self.member_posts)
    
    @property
    def public_count(self) -> int:
        return len(self.posts)


class DataProcessor:
    """Processes and organizes archived community post data."""
    
    def __init__(self, output_dir: str = "archive-output"):
        self.output_dir = Path(output_dir)
    
    def process_all(
        self,
        posts: list[CommunityPost],
        channel_info: Optional[ChannelInfo] = None,
    ) -> ProcessedData:
        """
        Process all posts and organize them.
        
        Args:
            posts: List of archived community posts
            channel_info: Optional channel information
            
        Returns:
            ProcessedData object with organized posts
        """
        # Separate member and public posts
        member_posts = [p for p in posts if p.is_members]
        public_posts = [p for p in posts if not p.is_members]
        
        # Sort all posts by order
        all_sorted = self._sort_by_order(posts)
        
        return ProcessedData(
            channel_info=channel_info,
            posts=public_posts,
            member_posts=member_posts,
            all_posts_sorted=all_sorted,
            archive_date=datetime.now(),
        )
    
    def _load_post_order(self) -> dict[str, int]:
        """Load post order from post_order.json if it exists."""
        order_file = self.output_dir / "post_order.json"
        if order_file.exists():
            try:
                with open(order_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {item["post_id"]: item["order"] for item in data.get("posts", [])}
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _sort_by_order(
        self,
        posts: list[CommunityPost],
        newest_first: bool = True,
    ) -> list[CommunityPost]:
        """
        Sort posts by their recorded order from post_order.json.
        
        Falls back to when_archived timestamp if order file doesn't exist.
        """
        post_order = self._load_post_order()
        
        if post_order:
            # Use recorded order (lower number = newer post)
            def get_sort_key(post: CommunityPost):
                if post.post_id in post_order:
                    return (0, post_order[post.post_id])
                # Posts not in order file go to the end
                return (1, 0)
            
            return sorted(posts, key=get_sort_key, reverse=not newest_first)
        else:
            # Fall back to when_archived sorting
            return self._sort_by_date(posts, newest_first)
    
    def _sort_by_date(
        self,
        posts: list[CommunityPost],
        newest_first: bool = True,
    ) -> list[CommunityPost]:
        """
        Sort posts by archive order (which reflects the original page order).
        
        Since YouTube displays posts from newest to oldest (top to bottom),
        and the archiver processes them in that order, the `when_archived`
        timestamp reflects the original display order:
        - Earlier `when_archived` = newer post (appeared higher on page)
        - Later `when_archived` = older post (appeared lower on page)
        
        Args:
            posts: List of posts to sort
            newest_first: If True, newest first; if False, oldest first
            
        Returns:
            Sorted list of posts
        """
        def get_sort_key(post: CommunityPost):
            # Primary: use archive timestamp as it reflects page order
            # Earlier archived = newer post (was at top of page)
            if post.when_archived:
                try:
                    # Parse ISO format timestamp
                    archived_dt = datetime.fromisoformat(
                        post.when_archived.replace("+00:00", "").replace("Z", "")
                    )
                    return (0, archived_dt)
                except ValueError:
                    pass
            
            # Secondary: estimated date from relative date (less accurate)
            if post.estimated_date:
                return (1, post.estimated_date)
            
            # Fallback: use a very old date to sort at end
            return (2, datetime.min)
        
        # Earlier when_archived = newer post, so ascending order gives newest first
        # reverse=True means oldest first (larger timestamps first)
        return sorted(posts, key=get_sort_key, reverse=not newest_first)
    
    def filter_by_date_range(
        self,
        posts: list[CommunityPost],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[CommunityPost]:
        """
        Filter posts by date range.
        
        Args:
            posts: List of posts to filter
            start_date: Only include posts on or after this date
            end_date: Only include posts on or before this date
            
        Returns:
            Filtered list of posts
        """
        filtered = []
        
        for post in posts:
            if not post.estimated_date:
                # Include posts without dates
                filtered.append(post)
                continue
            
            if start_date and post.estimated_date < start_date:
                continue
            if end_date and post.estimated_date > end_date:
                continue
            
            filtered.append(post)
        
        return filtered
    
    def filter_members_only(
        self,
        posts: list[CommunityPost],
        include_members: bool = True,
        include_public: bool = True,
    ) -> list[CommunityPost]:
        """
        Filter posts by membership status.
        
        Args:
            posts: List of posts to filter
            include_members: Include member-only posts
            include_public: Include public posts
            
        Returns:
            Filtered list of posts
        """
        filtered = []
        
        for post in posts:
            if post.is_members and include_members:
                filtered.append(post)
            elif not post.is_members and include_public:
                filtered.append(post)
        
        return filtered
    
    def search_posts(
        self,
        posts: list[CommunityPost],
        query: str,
    ) -> list[CommunityPost]:
        """
        Search posts by text content.
        
        Args:
            posts: List of posts to search
            query: Search query (case-insensitive)
            
        Returns:
            List of posts matching the query
        """
        query = query.lower()
        return [p for p in posts if query in p.text.lower()]
    
    def get_posts_with_polls(
        self,
        posts: list[CommunityPost],
    ) -> list[CommunityPost]:
        """Get only posts that contain polls."""
        return [p for p in posts if p.poll is not None]
    
    def get_posts_with_images(
        self,
        posts: list[CommunityPost],
    ) -> list[CommunityPost]:
        """Get only posts that contain images."""
        return [p for p in posts if p.images or p.local_images]
    
    def get_statistics(self, posts: list[CommunityPost]) -> dict:
        """
        Generate statistics about the posts.
        
        Returns:
            Dictionary with various statistics
        """
        total = len(posts)
        members_only = sum(1 for p in posts if p.is_members)
        with_images = sum(1 for p in posts if p.images or p.local_images)
        with_polls = sum(1 for p in posts if p.poll is not None)
        
        # Date range
        dates = [p.estimated_date for p in posts if p.estimated_date]
        oldest = min(dates) if dates else None
        newest = max(dates) if dates else None
        
        return {
            "total_posts": total,
            "members_only": members_only,
            "public": total - members_only,
            "with_images": with_images,
            "with_polls": with_polls,
            "oldest_post": oldest.isoformat() if oldest else None,
            "newest_post": newest.isoformat() if newest else None,
        }

"""
Data Processor Module
Handles sorting and organizing community posts.
"""

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
        
        # Sort all posts by date
        all_sorted = self._sort_by_date(posts)
        
        return ProcessedData(
            channel_info=channel_info,
            posts=public_posts,
            member_posts=member_posts,
            all_posts_sorted=all_sorted,
            archive_date=datetime.now(),
        )
    
    def _sort_by_date(
        self,
        posts: list[CommunityPost],
        descending: bool = True,
    ) -> list[CommunityPost]:
        """
        Sort posts by estimated date.
        
        Since YouTube doesn't provide exact timestamps, we use:
        1. Estimated date from relative date parsing
        2. Archive timestamp as fallback
        3. Original order if neither available
        
        Args:
            posts: List of posts to sort
            descending: If True, newest first; if False, oldest first
            
        Returns:
            Sorted list of posts
        """
        def get_sort_key(post: CommunityPost):
            # Primary: estimated date from relative date
            if post.estimated_date:
                return (0, post.estimated_date)
            
            # Secondary: archive timestamp
            if post.when_archived:
                try:
                    # Parse ISO format timestamp
                    archived_dt = datetime.fromisoformat(
                        post.when_archived.replace("+00:00", "")
                    )
                    return (1, archived_dt)
                except ValueError:
                    pass
            
            # Fallback: use a very old date to sort at end
            return (2, datetime.min)
        
        return sorted(posts, key=get_sort_key, reverse=descending)
    
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

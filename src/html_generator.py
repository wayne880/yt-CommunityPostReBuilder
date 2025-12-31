"""
HTML Generator Module
Generates static HTML pages for viewing archived community posts.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .archiver import CommunityPost
from .channel_fetcher import ChannelInfo
from .data_processor import ProcessedData
from .utils import format_text_with_links


class HTMLGenerator:
    """Generates static HTML pages for the archive viewer."""
    
    def __init__(self, output_dir: str = "archive-output"):
        self.output_dir = Path(output_dir)
        self.template_dir = Path(__file__).parent / "templates"
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        
        # Add custom filters
        self.env.filters["format_text"] = format_text_with_links
        self.env.filters["format_date"] = self._format_date
    
    def _format_date(self, dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if not dt:
            return "Unknown"
        return dt.strftime("%Y-%m-%d %H:%M")
    
    def generate(self, data: ProcessedData) -> Path:
        """
        Generate the complete static HTML site.
        
        Args:
            data: ProcessedData containing all posts and channel info
            
        Returns:
            Path to the generated index.html
        """
        # Create output directory
        html_dir = self.output_dir / "viewer"
        html_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy static assets
        self._copy_static_assets(html_dir)
        
        # Generate index.html
        index_path = self._generate_index(data, html_dir)
        
        # Generate posts data as JSON for client-side filtering
        self._generate_posts_json(data, html_dir)
        
        print(f"\n✅ Generated viewer at: {index_path}")
        print(f"   Open this file in your browser to view the archive.")
        
        return index_path
    
    def _copy_static_assets(self, html_dir: Path) -> None:
        """Copy CSS and JS files to output directory."""
        assets_dir = html_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        # Copy post images to assets folder
        posts_images_dir = assets_dir / "posts"
        posts_images_dir.mkdir(exist_ok=True)
        
        # Copy channel images if they exist
        for img_name in ["channel_avatar.jpg", "channel_banner.jpg"]:
            src = self.output_dir / img_name
            if src.exists():
                shutil.copy2(src, assets_dir / img_name)
        
        # Copy all post images
        for post_dir in self.output_dir.iterdir():
            if post_dir.is_dir() and post_dir.name not in ["viewer", "assets"]:
                dest_dir = posts_images_dir / post_dir.name
                dest_dir.mkdir(exist_ok=True)
                for img in post_dir.glob("*"):
                    if img.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                        shutil.copy2(img, dest_dir / img.name)
    
    def _generate_index(self, data: ProcessedData, html_dir: Path) -> Path:
        """Generate the main index.html file."""
        template = self.env.get_template("index.html")
        
        # Prepare template data
        template_data = {
            "channel": data.channel_info,
            "posts": data.all_posts_sorted,
            "statistics": {
                "total": data.total_posts,
                "public": data.public_count,
                "members": data.member_only_count,
            },
            "archive_date": data.archive_date.strftime("%Y-%m-%d %H:%M"),
            "has_avatar": data.channel_info and data.channel_info.local_avatar,
            "has_banner": data.channel_info and data.channel_info.local_banner,
        }
        
        html_content = template.render(**template_data)
        
        index_path = html_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return index_path
    
    def _generate_posts_json(self, data: ProcessedData, html_dir: Path) -> None:
        """Generate posts data as JSON for client-side functionality."""
        posts_data = []
        
        for post in data.all_posts_sorted:
            posts_data.append({
                "id": post.post_id,
                "url": post.url,
                "text": post.text,
                "images": post.local_images,
                "is_members": post.is_members,
                "relative_date": post.relative_date,
                "estimated_date": post.estimated_date.isoformat() if post.estimated_date else None,
                "num_comments": post.num_comments,
                "num_thumbs_up": post.num_thumbs_up,
                "poll": post.poll,
            })
        
        json_path = html_dir / "assets" / "posts.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(posts_data, f, ensure_ascii=False, indent=2)

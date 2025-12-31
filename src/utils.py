"""
Utility functions for the YouTube Community Post Viewer.
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def parse_relative_date(relative_date: str) -> Optional[datetime]:
    """
    Parse a relative date string (e.g., "3 months ago") to an approximate datetime.
    
    Note: Since YouTube only provides relative dates, the returned datetime is an
    approximation based on the current time when this function is called.
    
    Args:
        relative_date: A string like "3 months ago", "1 year ago", "2 weeks ago"
        
    Returns:
        An approximate datetime, or None if parsing fails
    """
    if not relative_date:
        return None
    
    relative_date = relative_date.lower().strip()
    now = datetime.now()
    
    # Pattern to match relative date strings
    patterns = [
        (r"(\d+)\s*second", "seconds"),
        (r"(\d+)\s*minute", "minutes"),
        (r"(\d+)\s*hour", "hours"),
        (r"(\d+)\s*day", "days"),
        (r"(\d+)\s*week", "weeks"),
        (r"(\d+)\s*month", "months"),
        (r"(\d+)\s*year", "years"),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, relative_date)
        if match:
            value = int(match.group(1))
            
            if unit == "seconds":
                return now - timedelta(seconds=value)
            elif unit == "minutes":
                return now - timedelta(minutes=value)
            elif unit == "hours":
                return now - timedelta(hours=value)
            elif unit == "days":
                return now - timedelta(days=value)
            elif unit == "weeks":
                return now - timedelta(weeks=value)
            elif unit == "months":
                # Approximate: 30 days per month
                return now - timedelta(days=value * 30)
            elif unit == "years":
                # Approximate: 365 days per year
                return now - timedelta(days=value * 365)
    
    # Handle special cases
    if "just now" in relative_date or "moments ago" in relative_date:
        return now
    if "yesterday" in relative_date:
        return now - timedelta(days=1)
    
    return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: The original filename
        
    Returns:
        A sanitized filename safe for most filesystems
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(" .")
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename or "untitled"


def format_number(num_str: str) -> str:
    """
    Format a number string for display (handles K, M suffixes).
    
    Args:
        num_str: A number string like "7.3K" or "1.2M"
        
    Returns:
        The formatted string (passed through, as YouTube's format is already nice)
    """
    return num_str


def extract_channel_handle(url: str) -> Optional[str]:
    """
    Extract the channel handle from a YouTube URL.
    
    Args:
        url: A YouTube channel URL
        
    Returns:
        The channel handle (e.g., "@ChannelName") or None
    """
    # Match @handle format
    match = re.search(r"youtube\.com/(@[\w-]+)", url)
    if match:
        return match.group(1)
    
    # Match /c/channelname format
    match = re.search(r"youtube\.com/c/([\w-]+)", url)
    if match:
        return match.group(1)
    
    # Match /channel/ID format
    match = re.search(r"youtube\.com/channel/([\w-]+)", url)
    if match:
        return match.group(1)
    
    return None


def format_text_with_links(text: str) -> str:
    """
    Convert URLs in text to HTML links.
    
    Args:
        text: Plain text that may contain URLs
        
    Returns:
        HTML-safe text with URLs converted to anchor tags
    """
    import html
    
    # First escape HTML
    text = html.escape(text)
    
    # Convert URLs to links
    url_pattern = r'(https?://[^\s<>"\']+)'
    text = re.sub(
        url_pattern,
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text
    )
    
    # Convert newlines to <br>
    text = text.replace("\n", "<br>")
    
    return text

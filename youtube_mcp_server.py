#!/usr/bin/env python3
"""
YouTube MCP Server

A Model Context Protocol server that provides access to YouTube data via the YouTube Data API v3.
Provides tools for getting video details, playlist information, and playlist items.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("YouTube Data Server")

# YouTube API configuration
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Load API key from credentials file
def load_api_key() -> str:
    """Load YouTube API key from credentials.yml file."""
    script_dir = Path(__file__).parent
    credentials_file = script_dir / "credentials.yml"
    
    try:
        with open(credentials_file, 'r') as f:
            content = f.read()
            # Simple parsing for youtube_api_key: "value"
            for line in content.split('\n'):
                if line.strip().startswith('youtube_api_key:'):
                    # Extract the value between quotes
                    key_part = line.split('youtube_api_key:')[1].strip()
                    if key_part.startswith('"') and key_part.endswith('"'):
                        return key_part[1:-1]  # Remove quotes
                    else:
                        return key_part.strip('\"\'')
        raise ValueError("youtube_api_key not found in credentials.yml")
    except FileNotFoundError:
        raise ValueError("credentials.yml file not found. Please create it with your YouTube API key.")
    except Exception as e:
        raise ValueError(f"Error reading credentials.yml: {str(e)}")

API_KEY = load_api_key()

def get_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    if not url:
        return None
        
    # Handle youtu.be format
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    
    # Handle youtube.com format
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
        query_params = parse_qs(parsed.query)
        return query_params.get("v", [None])[0]
    
    # If it's already just an ID (11 characters, alphanumeric + - and _)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
        
    return None

def get_playlist_id_from_url(url: str) -> Optional[str]:
    """
    Extract playlist ID from YouTube URL formats.
    
    Supports:
    - https://www.youtube.com/playlist?list=PLAYLIST_ID
    - https://youtube.com/playlist?list=PLAYLIST_ID
    """
    if not url:
        return None
        
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
        query_params = parse_qs(parsed.query)
        return query_params.get("list", [None])[0]
    
    # If it's already just an ID
    if re.match(r'^[a-zA-Z0-9_-]+$', url):
        return url
        
    return None

def get_channel_id_from_url(url: str) -> Optional[str]:
    """
    Extract channel ID from YouTube channel URL formats.
    
    Supports:
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/c/channelname
    - https://www.youtube.com/@username
    - https://youtube.com/user/username
    - @username (direct format)
    """
    if not url:
        return None
    
    # Handle direct @username format
    if url.startswith('@'):
        return url[1:]  # Remove the @ symbol
        
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
        path = parsed.path
        
        # Handle /channel/CHANNEL_ID format
        if "/channel/" in path:
            return path.split("/channel/")[1].split("/")[0]
        
        # Handle /c/channelname format (custom URL)
        elif "/c/" in path:
            return path.split("/c/")[1].split("/")[0]
        
        # Handle /@username format
        elif "/@" in path:
            return path.split("/@")[1].split("/")[0]
        
        # Handle /user/username format (legacy)
        elif "/user/" in path:
            return path.split("/user/")[1].split("/")[0]
    
    # If it's already a channel ID (starts with UC and 22 chars after UC)
    if re.match(r'^UC[a-zA-Z0-9_-]{22}$', url):
        return url
    
    # If it's a username or custom name
    if re.match(r'^[a-zA-Z0-9_-]+$', url):
        return url
        
    return None

async def make_youtube_api_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to the YouTube Data API v3."""
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY environment variable is required")
    
    params["key"] = API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                error_data = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
                error_message = error_data.get("error", {}).get("message", "API quota exceeded or invalid key")
                raise ValueError(f"YouTube API error (403): {error_message}")
            elif e.response.status_code == 404:
                raise ValueError("YouTube resource not found (404)")
            else:
                raise ValueError(f"YouTube API error ({e.response.status_code}): {e.response.text}")
        except httpx.RequestError as e:
            raise ValueError(f"Network error connecting to YouTube API: {str(e)}")

@mcp.tool()
async def get_video_details(video_input: str) -> str:
    """
    Get detailed information about a YouTube video.
    
    Args:
        video_input: YouTube video URL or video ID
        
    Returns:
        Formatted string with video details including title, description, statistics, etc.
    """
    # Extract video ID from URL or use as-is if it's already an ID
    video_id = get_video_id_from_url(video_input)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_input}'. Please provide a valid YouTube URL or 11-character video ID."
    
    try:
        # Get video details
        data = await make_youtube_api_request("videos", {
            "part": "snippet,statistics,contentDetails,status",
            "id": video_id
        })
        
        if not data.get("items"):
            return f"Error: Video with ID '{video_id}' not found or is not accessible."
        
        video = data["items"][0]
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        content_details = video.get("contentDetails", {})
        status = video.get("status", {})
        
        # Format duration (convert from ISO 8601 format)
        duration = content_details.get("duration", "Unknown")
        if duration.startswith("PT"):
            # Simple parsing for common formats like PT4M13S
            duration = duration.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s")
        
        # Build formatted response
        result = f"""YouTube Video Details:

Title: {snippet.get('title', 'Unknown')}
Channel: {snippet.get('channelTitle', 'Unknown')}
Published: {snippet.get('publishedAt', 'Unknown')[:10]}
Duration: {duration}

Statistics:
- Views: {int(statistics.get('viewCount', 0)):,}
- Likes: {int(statistics.get('likeCount', 0)):,}
- Comments: {int(statistics.get('commentCount', 0)):,}

Status: {status.get('privacyStatus', 'Unknown').title()}
License: {status.get('license', 'Unknown')}

Description:
{snippet.get('description', 'No description available')[:500]}{'...' if len(snippet.get('description', '')) > 500 else ''}

Video ID: {video_id}
Video URL: https://www.youtube.com/watch?v={video_id}
"""
        
        return result
        
    except Exception as e:
        return f"Error fetching video details: {str(e)}"

@mcp.tool()
async def get_playlist_details(playlist_input: str) -> str:
    """
    Get information about a YouTube playlist.
    
    Args:
        playlist_input: YouTube playlist URL or playlist ID
        
    Returns:
        Formatted string with playlist details including title, description, video count, etc.
    """
    # Extract playlist ID from URL or use as-is if it's already an ID
    playlist_id = get_playlist_id_from_url(playlist_input)
    if not playlist_id:
        return f"Error: Could not extract playlist ID from '{playlist_input}'. Please provide a valid YouTube playlist URL or playlist ID."
    
    try:
        # Get playlist details
        data = await make_youtube_api_request("playlists", {
            "part": "snippet,status,contentDetails",
            "id": playlist_id
        })
        
        if not data.get("items"):
            return f"Error: Playlist with ID '{playlist_id}' not found or is not accessible."
        
        playlist = data["items"][0]
        snippet = playlist.get("snippet", {})
        status = playlist.get("status", {})
        content_details = playlist.get("contentDetails", {})
        
        result = f"""YouTube Playlist Details:

Title: {snippet.get('title', 'Unknown')}
Channel: {snippet.get('channelTitle', 'Unknown')}
Created: {snippet.get('publishedAt', 'Unknown')[:10]}
Video Count: {content_details.get('itemCount', 'Unknown')}

Privacy Status: {status.get('privacyStatus', 'Unknown').title()}

Description:
{snippet.get('description', 'No description available')[:500]}{'...' if len(snippet.get('description', '')) > 500 else ''}

Playlist ID: {playlist_id}
Playlist URL: https://www.youtube.com/playlist?list={playlist_id}
"""
        
        return result
        
    except Exception as e:
        return f"Error fetching playlist details: {str(e)}"

@mcp.tool()
async def get_playlist_items(playlist_input: str, max_results: int = 10) -> str:
    """
    Get videos from a YouTube playlist.
    
    Args:
        playlist_input: YouTube playlist URL or playlist ID
        max_results: Maximum number of videos to return (default: 10, max: 50)
        
    Returns:
        Formatted string with list of videos in the playlist
    """
    # Extract playlist ID from URL or use as-is if it's already an ID
    playlist_id = get_playlist_id_from_url(playlist_input)
    if not playlist_id:
        return f"Error: Could not extract playlist ID from '{playlist_input}'. Please provide a valid YouTube playlist URL or playlist ID."
    
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    try:
        # Get playlist items
        data = await make_youtube_api_request("playlistItems", {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": max_results
        })
        
        if not data.get("items"):
            return f"Error: Playlist with ID '{playlist_id}' not found, is empty, or is not accessible."
        
        items = data["items"]
        total_results = data.get("pageInfo", {}).get("totalResults", len(items))
        
        result = f"""YouTube Playlist Items:

Playlist ID: {playlist_id}
Total Videos: {total_results}
Showing: {len(items)} videos

Videos:
"""
        
        for i, item in enumerate(items, 1):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId", "Unknown")
            
            result += f"""
{i}. {snippet.get('title', 'Unknown Title')}
   Channel: {snippet.get('videoOwnerChannelTitle', snippet.get('channelTitle', 'Unknown'))}
   Published: {snippet.get('publishedAt', 'Unknown')[:10]}
   Video ID: {video_id}
   URL: https://www.youtube.com/watch?v={video_id}
"""
        
        if total_results > len(items):
            result += f"\n... and {total_results - len(items)} more videos"
        
        return result
        
    except Exception as e:
        return f"Error fetching playlist items: {str(e)}"

@mcp.tool()
async def get_channel_details(channel_input: str) -> str:
    """
    Get detailed information about a YouTube channel.
    
    Args:
        channel_input: YouTube channel URL, channel ID, or @username
        
    Returns:
        Formatted string with channel details including name, subscribers, videos, etc.
    """
    # Extract channel ID from URL or use as-is
    channel_id = get_channel_id_from_url(channel_input)
    if not channel_id:
        return f"Error: Could not extract channel ID from '{channel_input}'. Please provide a valid YouTube channel URL, channel ID, or @username."
    
    try:
        # Try to get channel details by ID first
        try:
            data = await make_youtube_api_request("channels", {
                "part": "snippet,statistics,contentDetails,brandingSettings",
                "id": channel_id
            })
        except:
            # If ID fails, try as username (for @username format or custom URLs)
            data = await make_youtube_api_request("channels", {
                "part": "snippet,statistics,contentDetails,brandingSettings", 
                "forUsername": channel_id
            })
        
        if not data.get("items"):
            return f"Error: Channel '{channel_id}' not found or is not accessible."
        
        channel = data["items"][0]
        snippet = channel.get("snippet", {})
        statistics = channel.get("statistics", {})
        branding = channel.get("brandingSettings", {}).get("channel", {})
        
        # Format subscriber count
        subs = int(statistics.get("subscriberCount", 0))
        if subs >= 1000000:
            sub_display = f"{subs/1000000:.1f}M"
        elif subs >= 1000:
            sub_display = f"{subs/1000:.1f}K"
        else:
            sub_display = f"{subs:,}"
        
        # Format view count
        views = int(statistics.get("viewCount", 0))
        if views >= 1000000000:
            view_display = f"{views/1000000000:.1f}B"
        elif views >= 1000000:
            view_display = f"{views/1000000:.1f}M"
        elif views >= 1000:
            view_display = f"{views/1000:.1f}K"
        else:
            view_display = f"{views:,}"
        
        result = f"""YouTube Channel Details:

Name: {snippet.get('title', 'Unknown')}
Handle: @{snippet.get('customUrl', 'N/A')}
Created: {snippet.get('publishedAt', 'Unknown')[:10]}

Statistics:
- Subscribers: {sub_display}
- Total Videos: {int(statistics.get('videoCount', 0)):,}
- Total Views: {view_display}

Description:
{snippet.get('description', 'No description available')[:500]}{'...' if len(snippet.get('description', '')) > 500 else ''}

Channel ID: {channel['id']}
Channel URL: https://www.youtube.com/channel/{channel['id']}
"""
        
        return result
        
    except Exception as e:
        return f"Error fetching channel details: {str(e)}"

@mcp.tool()
async def get_video_categories(region_code: str = "US") -> str:
    """
    Get list of YouTube video categories for a specific region.
    
    Args:
        region_code: Country code (US, GB, CA, etc.) - default: US
        
    Returns:
        Formatted string with available video categories
    """
    try:
        # Get video categories
        data = await make_youtube_api_request("videoCategories", {
            "part": "snippet",
            "regionCode": region_code
        })
        
        if not data.get("items"):
            return f"No video categories found for region: {region_code}"
        
        categories = data["items"]
        
        result = f"""YouTube Video Categories - {region_code}:

Total Categories: {len(categories)}

Categories:
"""
        
        for category in categories:
            snippet = category.get("snippet", {})
            category_id = category.get("id", "Unknown")
            title = snippet.get("title", "Unknown")
            
            # Check if category is assignable (can be used when uploading)
            assignable = snippet.get("assignable", True)
            status = "✅ Assignable" if assignable else "❌ Not assignable"
            
            result += f"""
{category_id}: {title} ({status})"""
        
        result += f"""

Note: Assignable categories can be used when uploading videos.
Non-assignable categories are for YouTube's internal classification.
"""
        
        return result
        
    except Exception as e:
        return f"Error fetching video categories: {str(e)}"

@mcp.tool()
async def get_channel_videos(channel_input: str, max_results: int = 10) -> str:
    """
    Get recent videos from a YouTube channel.
    
    Args:
        channel_input: YouTube channel URL, channel ID, or @username
        max_results: Maximum number of videos to return (default: 10, max: 50)
        
    Returns:
        Formatted string with list of recent videos from the channel
    """
    # Extract channel ID from URL or use as-is
    channel_id = get_channel_id_from_url(channel_input)
    if not channel_id:
        return f"Error: Could not extract channel ID from '{channel_input}'. Please provide a valid YouTube channel URL, channel ID, or @username."
    
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    try:
        # First, get the actual channel ID if we have a username or custom URL
        try:
            # Try to get channel details to resolve the actual channel ID
            channel_data = await make_youtube_api_request("channels", {
                "part": "id,snippet",
                "id": channel_id
            })
            
            if not channel_data.get("items"):
                # Try as username if ID lookup failed
                channel_data = await make_youtube_api_request("channels", {
                    "part": "id,snippet",
                    "forUsername": channel_id
                })
            
            if not channel_data.get("items"):
                return f"Error: Channel '{channel_id}' not found or is not accessible."
            
            actual_channel_id = channel_data["items"][0]["id"]
            channel_title = channel_data["items"][0]["snippet"]["title"]
            
        except Exception:
            return f"Error: Could not resolve channel '{channel_id}'. Please check the channel exists and is accessible."
        
        # Get recent videos from the channel using search
        search_data = await make_youtube_api_request("search", {
            "part": "id,snippet",
            "channelId": actual_channel_id,
            "type": "video",
            "order": "date",
            "maxResults": max_results
        })
        
        if not search_data.get("items"):
            return f"No videos found for channel '{channel_title}' or channel has no public videos."
        
        videos = search_data["items"]
        total_results = search_data.get("pageInfo", {}).get("totalResults", len(videos))
        
        result = f"""Recent Videos from YouTube Channel:

Channel: {channel_title}
Channel ID: {actual_channel_id}
Showing: {len(videos)} of {total_results} videos

Recent Videos:
"""
        
        for i, video in enumerate(videos, 1):
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId", "Unknown")
            
            # Format publish date
            published = snippet.get("publishedAt", "Unknown")
            if published != "Unknown":
                published = published[:10]  # Just the date part
            
            result += f"""
{i}. {snippet.get('title', 'Unknown Title')}
   Published: {published}
   Description: {snippet.get('description', 'No description')[:100]}{'...' if len(snippet.get('description', '')) > 100 else ''}
   Video ID: {video_id}
   URL: https://www.youtube.com/watch?v={video_id}
"""
        
        if total_results > len(videos):
            result += f"\n... and {total_results - len(videos)} more videos available"
        
        result += f"\nChannel URL: https://www.youtube.com/channel/{actual_channel_id}"
        
        return result
        
    except Exception as e:
        return f"Error fetching channel videos: {str(e)}"

@mcp.tool()
async def search_videos(query: str, max_results: int = 10, order: str = "relevance") -> str:
    """
    Search YouTube for videos by keywords.
    
    Args:
        query: Search keywords/terms
        max_results: Maximum number of results to return (default: 10, max: 50)
        order: Sort order - relevance, date, rating, viewCount, title (default: relevance)
        
    Returns:
        Formatted string with search results including video details
    """
    if not query or query.strip() == "":
        return "Error: Search query cannot be empty. Please provide keywords to search for."
    
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    # Validate order parameter
    valid_orders = ["relevance", "date", "rating", "viewCount", "title"]
    if order not in valid_orders:
        order = "relevance"
    
    try:
        # Search for videos
        search_data = await make_youtube_api_request("search", {
            "part": "id,snippet",
            "q": query.strip(),
            "type": "video",
            "order": order,
            "maxResults": max_results,
            "safeSearch": "moderate"  # Filter out inappropriate content
        })
        
        if not search_data.get("items"):
            return f"No videos found for search query: '{query}'. Try different keywords or check spelling."
        
        videos = search_data["items"]
        total_results = search_data.get("pageInfo", {}).get("totalResults", len(videos))
        
        # Get additional video details (views, duration, etc.) for the found videos
        video_ids = [video.get("id", {}).get("videoId") for video in videos if video.get("id", {}).get("videoId")]
        
        video_details = {}
        if video_ids:
            try:
                details_data = await make_youtube_api_request("videos", {
                    "part": "contentDetails,statistics",
                    "id": ",".join(video_ids)
                })
                
                for video in details_data.get("items", []):
                    video_details[video["id"]] = {
                        "duration": video.get("contentDetails", {}).get("duration", "Unknown"),
                        "viewCount": video.get("statistics", {}).get("viewCount", "0"),
                        "likeCount": video.get("statistics", {}).get("likeCount", "0")
                    }
            except:
                # If additional details fail, continue with basic search results
                pass
        
        result = f"""YouTube Video Search Results:

Query: "{query}"
Sort Order: {order.title()}
Showing: {len(videos)} of {total_results:,} results

Videos:
"""
        
        for i, video in enumerate(videos, 1):
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId", "Unknown")
            
            # Format publish date
            published = snippet.get("publishedAt", "Unknown")
            if published != "Unknown":
                published = published[:10]  # Just the date part
            
            # Get additional details if available
            details = video_details.get(video_id, {})
            duration = details.get("duration", "Unknown")
            view_count = int(details.get("viewCount", 0))
            
            # Format duration (convert from ISO 8601 format)
            if duration.startswith("PT"):
                duration = duration.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s")
            
            # Format view count
            if view_count >= 1000000000:
                view_display = f"{view_count/1000000000:.1f}B views"
            elif view_count >= 1000000:
                view_display = f"{view_count/1000000:.1f}M views"
            elif view_count >= 1000:
                view_display = f"{view_count/1000:.1f}K views"
            else:
                view_display = f"{view_count:,} views" if view_count > 0 else "Views: N/A"
            
            result += f"""
{i}. {snippet.get('title', 'Unknown Title')}
   Channel: {snippet.get('channelTitle', 'Unknown')}
   Published: {published}
   Duration: {duration}
   {view_display}
   Description: {snippet.get('description', 'No description')[:150]}{'...' if len(snippet.get('description', '')) > 150 else ''}
   Video ID: {video_id}
   URL: https://www.youtube.com/watch?v={video_id}
"""
        
        if total_results > len(videos):
            result += f"\n... and {total_results - len(videos):,} more results available"
        
        result += f"\n\nSearch Tips:\n- Try different keywords for more results\n- Use order='date' for newest videos\n- Use order='viewCount' for most popular videos"
        
        return result
        
    except Exception as e:
        return f"Error searching videos: {str(e)}"

@mcp.tool()
async def get_trending_videos(region_code: str = "US", max_results: int = 10) -> str:
    """
    Get trending videos from YouTube for a specific region.
    
    Args:
        region_code: Country code (US, GB, CA, etc.) - default: US
        max_results: Maximum number of videos to return (default: 10, max: 50)
        
    Returns:
        Formatted string with trending videos and their details
    """
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    try:
        # Get trending videos (most popular)
        trending_data = await make_youtube_api_request("videos", {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results
        })
        
        if not trending_data.get("items"):
            return f"No trending videos found for region: {region_code}"
        
        videos = trending_data["items"]
        
        result = f"""Trending YouTube Videos - {region_code}:

Showing: {len(videos)} trending videos

Videos:
"""
        
        for i, video in enumerate(videos, 1):
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})
            content_details = video.get("contentDetails", {})
            video_id = video.get("id", "Unknown")
            
            # Format duration (convert from ISO 8601 format)
            duration = content_details.get("duration", "Unknown")
            if duration.startswith("PT"):
                duration = duration.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s")
            
            # Format view count
            view_count = int(statistics.get("viewCount", 0))
            if view_count >= 1000000000:
                view_display = f"{view_count/1000000000:.1f}B views"
            elif view_count >= 1000000:
                view_display = f"{view_count/1000000:.1f}M views"
            elif view_count >= 1000:
                view_display = f"{view_count/1000:.1f}K views"
            else:
                view_display = f"{view_count:,} views"
            
            # Format like count
            like_count = int(statistics.get("likeCount", 0))
            if like_count >= 1000000:
                like_display = f"{like_count/1000000:.1f}M likes"
            elif like_count >= 1000:
                like_display = f"{like_count/1000:.1f}K likes"
            else:
                like_display = f"{like_count:,} likes"
            
            # Format publish date
            published = snippet.get("publishedAt", "Unknown")
            if published != "Unknown":
                published = published[:10]  # Just the date part
            
            result += f"""
{i}. {snippet.get('title', 'Unknown Title')}
   Channel: {snippet.get('channelTitle', 'Unknown')}
   Published: {published}
   Duration: {duration}
   {view_display} | {like_display}
   Description: {snippet.get('description', 'No description')[:150]}{'...' if len(snippet.get('description', '')) > 150 else ''}
   Video ID: {video_id}
   URL: https://www.youtube.com/watch?v={video_id}
"""
        
        result += f"\n\nNote: Trending videos are updated regularly and vary by region."
        
        return result
        
    except Exception as e:
        return f"Error fetching trending videos: {str(e)}"

@mcp.tool()
async def get_video_comments(video_input: str, max_results: int = 10, order: str = "relevance") -> str:
    """
    Get comments from a YouTube video.
    
    Args:
        video_input: YouTube video URL or video ID
        max_results: Maximum number of comments to return (default: 10, max: 50)
        order: Sort order - time, relevance (default: relevance)
        
    Returns:
        Formatted string with video comments
    """
    # Extract video ID from URL or use as-is if it's already an ID
    video_id = get_video_id_from_url(video_input)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_input}'. Please provide a valid YouTube URL or 11-character video ID."
    
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    # Validate order parameter
    valid_orders = ["time", "relevance"]
    if order not in valid_orders:
        order = "relevance"
    
    try:
        # Get video comments
        comments_data = await make_youtube_api_request("commentThreads", {
            "part": "snippet,replies",
            "videoId": video_id,
            "order": order,
            "maxResults": max_results,
            "textFormat": "plainText"  # Get plain text instead of HTML
        })
        
        if not comments_data.get("items"):
            return f"No comments found for video '{video_id}'. Comments may be disabled or the video may not exist."
        
        comments = comments_data["items"]
        total_results = comments_data.get("pageInfo", {}).get("totalResults", len(comments))
        
        # Get basic video info for context
        try:
            video_data = await make_youtube_api_request("videos", {
                "part": "snippet",
                "id": video_id
            })
            video_title = video_data["items"][0]["snippet"]["title"] if video_data.get("items") else "Unknown Video"
        except:
            video_title = "Unknown Video"
        
        result = f"""YouTube Video Comments:

Video: {video_title}
Video ID: {video_id}
Sort Order: {order.title()}
Showing: {len(comments)} of {total_results:,} comments

Comments:
"""
        
        for i, comment_thread in enumerate(comments, 1):
            top_comment = comment_thread.get("snippet", {}).get("topLevelComment", {})
            comment_snippet = top_comment.get("snippet", {})
            
            # Get comment details
            author = comment_snippet.get("authorDisplayName", "Unknown")
            comment_text = comment_snippet.get("textDisplay", "No text")
            like_count = int(comment_snippet.get("likeCount", 0))
            published = comment_snippet.get("publishedAt", "Unknown")
            
            # Format publish date
            if published != "Unknown":
                published = published[:10]  # Just the date part
            
            # Format like count
            if like_count >= 1000:
                like_display = f"{like_count/1000:.1f}K likes"
            else:
                like_display = f"{like_count:,} likes" if like_count > 0 else "No likes"
            
            # Truncate long comments
            if len(comment_text) > 200:
                comment_text = comment_text[:200] + "..."
            
            result += f"""
{i}. {author}
   Posted: {published}
   {like_display}
   Comment: {comment_text}
"""
            
            # Check for replies
            replies = comment_thread.get("replies", {})
            reply_count = replies.get("totalReplyCount", 0)
            if reply_count > 0:
                result += f"\n   📝 {reply_count} repl{'y' if reply_count == 1 else 'ies'}"
            
            result += "\n"
        
        if total_results > len(comments):
            result += f"\n... and {total_results - len(comments):,} more comments available"
        
        result += f"\n\nNote: Comments are sorted by {order}. Some comments may be filtered by YouTube."
        
        return result
        
    except Exception as e:
        # Handle specific API errors
        if "commentsDisabled" in str(e) or "disabled" in str(e).lower():
            return f"Comments are disabled for video '{video_id}'."
        elif "quotaExceeded" in str(e):
            return "Error: YouTube API quota exceeded. Please try again later."
        else:
            return f"Error fetching video comments: {str(e)}"

@mcp.tool()
async def analyze_video_engagement(video_input: str) -> str:
    """
    Analyze video engagement metrics and provide insights.
    
    Args:
        video_input: YouTube video URL or video ID
        
    Returns:
        Formatted string with engagement analysis and insights
    """
    # Extract video ID from URL or use as-is if it's already an ID
    video_id = get_video_id_from_url(video_input)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_input}'. Please provide a valid YouTube URL or 11-character video ID."
    
    try:
        # Get comprehensive video data
        video_data = await make_youtube_api_request("videos", {
            "part": "snippet,statistics,contentDetails",
            "id": video_id
        })
        
        if not video_data.get("items"):
            return f"Error: Video with ID '{video_id}' not found or is not accessible."
        
        video = video_data["items"][0]
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        content_details = video.get("contentDetails", {})
        
        # Extract metrics
        title = snippet.get("title", "Unknown Title")
        channel = snippet.get("channelTitle", "Unknown Channel")
        published = snippet.get("publishedAt", "Unknown")
        
        view_count = int(statistics.get("viewCount", 0))
        like_count = int(statistics.get("likeCount", 0))
        comment_count = int(statistics.get("commentCount", 0))
        
        # Calculate engagement metrics
        if view_count > 0:
            like_rate = (like_count / view_count) * 100
            comment_rate = (comment_count / view_count) * 100
            engagement_rate = like_rate + comment_rate
        else:
            like_rate = comment_rate = engagement_rate = 0
        
        # Calculate video age in days
        video_age_days = "Unknown"
        if published != "Unknown":
            from datetime import datetime
            try:
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                current_date = datetime.now(pub_date.tzinfo)
                video_age_days = (current_date - pub_date).days
            except:
                video_age_days = "Unknown"
        
        # Calculate average views per day
        if isinstance(video_age_days, int) and video_age_days > 0:
            avg_views_per_day = view_count / video_age_days
        else:
            avg_views_per_day = "Unknown"
        
        # Format duration
        duration = content_details.get("duration", "Unknown")
        if duration.startswith("PT"):
            duration = duration.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s")
        
        # Engagement benchmarks (rough industry averages)
        def get_engagement_assessment(rate):
            if rate >= 8.0:
                return "🔥 Exceptional (8%+)"
            elif rate >= 4.0:
                return "⭐ Excellent (4-8%)"
            elif rate >= 2.0:
                return "✅ Good (2-4%)"
            elif rate >= 1.0:
                return "📊 Average (1-2%)"
            else:
                return "📉 Below Average (<1%)"
        
        # Format numbers for display
        def format_number(num):
            if isinstance(num, int):
                if num >= 1000000000:
                    return f"{num/1000000000:.1f}B"
                elif num >= 1000000:
                    return f"{num/1000000:.1f}M"
                elif num >= 1000:
                    return f"{num/1000:.1f}K"
                else:
                    return f"{num:,}"
            return str(num)
        
        result = f"""YouTube Video Engagement Analysis:

Video: {title}
Channel: {channel}
Published: {published[:10] if published != "Unknown" else "Unknown"}
Duration: {duration}

📊 Core Metrics:
- Views: {format_number(view_count)}
- Likes: {format_number(like_count)}
- Comments: {format_number(comment_count)}

🎯 Engagement Rates:
- Like Rate: {like_rate:.2f}% ({like_count:,} likes per 100 views)
- Comment Rate: {comment_rate:.2f}% ({comment_count:,} comments per 100 views)
- Total Engagement Rate: {engagement_rate:.2f}%

📈 Performance Assessment:
- Overall Engagement: {get_engagement_assessment(engagement_rate)}
"""
        
        # Add time-based analysis if available
        if isinstance(video_age_days, int):
            result += f"""
⏰ Time Analysis:
- Video Age: {video_age_days} days
- Average Views/Day: {format_number(int(avg_views_per_day)) if isinstance(avg_views_per_day, (int, float)) else avg_views_per_day}
"""
        
        # Add engagement insights
        result += f"""

🔍 Insights:
"""
        
        if engagement_rate >= 4.0:
            result += "- This video has excellent engagement! The audience is highly responsive.\n"
        elif engagement_rate >= 2.0:
            result += "- Good engagement levels indicate the content resonates with viewers.\n"
        else:
            result += "- Engagement could be improved. Consider more interactive content or better thumbnails.\n"
        
        if like_rate > comment_rate * 5:
            result += "- High like-to-comment ratio suggests easy-to-consume content.\n"
        elif comment_rate > like_rate:
            result += "- High comment rate indicates the content sparks discussion.\n"
        
        if isinstance(video_age_days, int) and video_age_days < 7 and view_count > 10000:
            result += "- Strong early performance - video is gaining momentum quickly.\n"
        
        result += f"""

Video ID: {video_id}
URL: https://www.youtube.com/watch?v={video_id}

Note: Engagement benchmarks are based on general industry averages and may vary by niche."""
        
        return result
        
    except Exception as e:
        return f"Error analyzing video engagement: {str(e)}"

@mcp.tool()
async def get_channel_playlists(channel_input: str, max_results: int = 10) -> str:
    """
    Get playlists from a YouTube channel.
    
    Args:
        channel_input: YouTube channel URL, channel ID, or @username
        max_results: Maximum number of playlists to return (default: 10, max: 50)
        
    Returns:
        Formatted string with channel playlists and their details
    """
    # Extract channel ID from URL or use as-is
    channel_id = get_channel_id_from_url(channel_input)
    if not channel_id:
        return f"Error: Could not extract channel ID from '{channel_input}'. Please provide a valid YouTube channel URL, channel ID, or @username."
    
    # Validate max_results
    max_results = max(1, min(50, max_results))
    
    try:
        # First, resolve the actual channel ID if we have a username or custom URL
        try:
            # Try to get channel details to resolve the actual channel ID
            channel_data = await make_youtube_api_request("channels", {
                "part": "id,snippet",
                "id": channel_id
            })
            
            if not channel_data.get("items"):
                # Try as username if ID lookup failed
                channel_data = await make_youtube_api_request("channels", {
                    "part": "id,snippet",
                    "forUsername": channel_id
                })
            
            if not channel_data.get("items"):
                return f"Error: Channel '{channel_id}' not found or is not accessible."
            
            actual_channel_id = channel_data["items"][0]["id"]
            channel_title = channel_data["items"][0]["snippet"]["title"]
            
        except Exception:
            return f"Error: Could not resolve channel '{channel_id}'. Please check the channel exists and is accessible."
        
        # Get playlists from the channel
        playlists_data = await make_youtube_api_request("playlists", {
            "part": "snippet,contentDetails",
            "channelId": actual_channel_id,
            "maxResults": max_results
        })
        
        if not playlists_data.get("items"):
            return f"No public playlists found for channel '{channel_title}'. The channel may not have created any public playlists yet."
        
        playlists = playlists_data["items"]
        total_results = playlists_data.get("pageInfo", {}).get("totalResults", len(playlists))
        
        result = f"""YouTube Channel Playlists:

Channel: {channel_title}
Channel ID: {actual_channel_id}
Total Playlists: {total_results}
Showing: {len(playlists)} playlists

Playlists:
"""
        
        for i, playlist in enumerate(playlists, 1):
            snippet = playlist.get("snippet", {})
            content_details = playlist.get("contentDetails", {})
            playlist_id = playlist.get("id", "Unknown")
            
            # Get playlist details
            title = snippet.get("title", "Unknown Title")
            description = snippet.get("description", "No description")
            published = snippet.get("publishedAt", "Unknown")
            video_count = content_details.get("itemCount", "Unknown")
            
            # Format publish date
            if published != "Unknown":
                published = published[:10]  # Just the date part
            
            # Truncate long descriptions
            if len(description) > 150:
                description = description[:150] + "..."
            
            result += f"""
{i}. {title}
   Created: {published}
   Videos: {video_count}
   Description: {description}
   Playlist ID: {playlist_id}
   URL: https://www.youtube.com/playlist?list={playlist_id}
"""
        
        if total_results > len(playlists):
            result += f"\n... and {total_results - len(playlists)} more playlists available"
        
        result += f"\n\nChannel URL: https://www.youtube.com/channel/{actual_channel_id}"
        result += f"\n\nNote: Only public playlists are shown. Private playlists are not accessible via the API."
        
        return result
        
    except Exception as e:
        return f"Error fetching channel playlists: {str(e)}"

@mcp.tool()
async def get_video_caption_info(video_input: str, language: str = "en") -> str:
    """
    Get available caption/transcript information from a YouTube video.
    
    Args:
        video_input: YouTube video URL or video ID
        language: Language code for captions (default: en for English)
        
    Returns:
        Formatted string with available caption information
    """
    # Extract video ID from URL or use as-is if it's already an ID
    video_id = get_video_id_from_url(video_input)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_input}'. Please provide a valid YouTube URL or 11-character video ID."
    
    try:
        # Get available captions for the video
        captions_data = await make_youtube_api_request("captions", {
            "part": "snippet",
            "videoId": video_id
        })
        
        if not captions_data.get("items"):
            return f"No captions/transcripts available for video '{video_id}'. The video may not have captions enabled or may not exist."
        
        captions = captions_data["items"]
        
        # Find the requested language or fall back to available options
        target_caption = None
        available_languages = []
        
        for caption in captions:
            snippet = caption.get("snippet", {})
            lang = snippet.get("language", "unknown")
            available_languages.append(lang)
            
            if lang == language:
                target_caption = caption
                break
        
        # If target language not found, try to use the first available
        if not target_caption and captions:
            target_caption = captions[0]
            language = target_caption.get("snippet", {}).get("language", "unknown")
        
        if not target_caption:
            return f"No suitable captions found for video '{video_id}'. Available languages: {', '.join(available_languages)}"
        
        # Get basic video info for context
        try:
            video_data = await make_youtube_api_request("videos", {
                "part": "snippet",
                "id": video_id
            })
            video_title = video_data["items"][0]["snippet"]["title"] if video_data.get("items") else "Unknown Video"
        except:
            video_title = "Unknown Video"
        
        caption_id = target_caption.get("id", "")
        caption_snippet = target_caption.get("snippet", {})
        
        result = f"""YouTube Video Transcripts:

Video: {video_title}
Video ID: {video_id}
Language: {language.upper()}
Caption Type: {caption_snippet.get('trackKind', 'Unknown')}
Auto-Generated: {'Yes' if caption_snippet.get('isAutoSynced') else 'No'}

Available Languages: {', '.join(available_languages)}

Note: This function identifies available transcripts. Due to YouTube API limitations, 
the actual transcript content requires additional API calls that may not be available 
in all regions or for all videos.

To access full transcripts:
1. Use the caption ID: {caption_id}
2. Make a request to the captions download endpoint
3. Parse the returned transcript format (usually SRT or VTT)

Caption ID: {caption_id}
Video URL: https://www.youtube.com/watch?v={video_id}

Tip: Many videos have auto-generated captions in multiple languages.
Manually created captions are typically more accurate than auto-generated ones."""
        
        return result
        
    except Exception as e:
        # Handle specific API errors
        if "quotaExceeded" in str(e):
            return "Error: YouTube API quota exceeded. Please try again later."
        elif "forbidden" in str(e).lower():
            return f"Error: Access to captions for video '{video_id}' is restricted."
        else:
            return f"Error fetching video caption info: {str(e)}"

@mcp.tool()
async def evaluate_video_for_knowledge_base(video_input: str) -> str:
    """
    Analyze video metadata to help decide if video is worth adding to knowledge base.
    
    This function provides a quick evaluation based on video metadata (title, duration, 
    views, captions availability) to help with knowledge base curation decisions.
    Note: This analysis is metadata-only and does not download actual transcript content.
    
    Args:
        video_input: YouTube video URL or video ID
        
    Returns:
        Formatted string with metadata analysis, quality assessment, and recommendation
    """
    # Extract video ID from URL or use as-is if it's already an ID
    video_id = get_video_id_from_url(video_input)
    if not video_id:
        return f"Error: Could not extract video ID from '{video_input}'. Please provide a valid YouTube URL or 11-character video ID."
    
    try:
        # Get video details for context
        video_data = await make_youtube_api_request("videos", {
            "part": "snippet,statistics,contentDetails",
            "id": video_id
        })
        
        if not video_data.get("items"):
            return f"Error: Video with ID '{video_id}' not found or is not accessible."
        
        video = video_data["items"][0]
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        content_details = video.get("contentDetails", {})
        
        video_title = snippet.get("title", "Unknown Title")
        channel_title = snippet.get("channelTitle", "Unknown Channel")
        duration = content_details.get("duration", "Unknown")
        view_count = int(statistics.get("viewCount", 0))
        
        # Initialize recommendation score (will be incremented throughout analysis)
        recommendation_score = 0
        
        # Calculate video age for freshness analysis
        video_age_days = None
        published_date = snippet.get("publishedAt", "Unknown")
        if published_date != "Unknown":
            from datetime import datetime
            try:
                pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                current_date = datetime.now(pub_date.tzinfo)
                video_age_days = (current_date - pub_date).days
            except:
                video_age_days = None
        
        # Format duration
        if duration.startswith("PT"):
            duration = duration.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s")
        
        # Get available captions for quality assessment
        captions_data = await make_youtube_api_request("captions", {
            "part": "snippet",
            "videoId": video_id
        })
        
        has_captions = bool(captions_data.get("items"))
        is_auto_generated = True
        
        if has_captions:
            # Check if captions are manually created (higher quality indicator)
            captions = captions_data["items"]
            for caption in captions:
                caption_snippet = caption.get("snippet", {})
                if not caption_snippet.get("isAutoSynced", True):
                    is_auto_generated = False
                    break
        
        # Initialize analysis variables
        content_type = "Unknown"
        quality_indicators = []
        
        # Analyze title for content type indicators
        title_lower = video_title.lower()
        if any(word in title_lower for word in ["tutorial", "how to", "guide", "learn"]):
            content_type = "Tutorial/Educational"
            recommendation_score += 2
        elif any(word in title_lower for word in ["review", "analysis", "deep dive"]):
            content_type = "Analysis/Review"
            recommendation_score += 2
        elif any(word in title_lower for word in ["introduction", "overview", "basics"]):
            content_type = "Introductory"
            recommendation_score += 1
        elif any(word in title_lower for word in ["news", "update", "announcement"]):
            content_type = "News/Updates"
            recommendation_score += 1
        
        # Calculate freshness bonus based on age
        freshness_bonus = 0
        age_assessment = "Unknown"
        if video_age_days is not None:
            if video_age_days <= 183:  # 0-6 months
                freshness_bonus = 3
                age_assessment = "Very Recent"
            elif video_age_days <= 365:  # 6-12 months
                freshness_bonus = 2
                age_assessment = "Recent"
            elif video_age_days <= 730:  # 1-2 years
                freshness_bonus = 1
                age_assessment = "Moderate Age"
            elif video_age_days <= 1095:  # 2-3 years
                freshness_bonus = 0
                age_assessment = "Older Content"
            else:  # 3+ years
                freshness_bonus = -1
                age_assessment = "Aging Content"
        
        # Tech volatility detection for extra freshness weighting
        high_volatility_topics = ["react", "vue", "angular", "aws", "docker", "kubernetes", "ai", "ml", "machine learning", "next.js", "typescript"]
        is_high_volatility = any(topic in title_lower for topic in high_volatility_topics)
        
        # Apply tech volatility bonus to recent content
        tech_bonus = 0
        if is_high_volatility and freshness_bonus > 0:
            tech_bonus = 2
            freshness_bonus += tech_bonus
        
        # Apply freshness bonus to recommendation score
        recommendation_score += freshness_bonus
        
        # Quality indicators based on metadata
        if view_count > 100000:
            quality_indicators.append("High view count (popular content)")
            recommendation_score += 1
        
        if has_captions and not is_auto_generated:
            quality_indicators.append("Manual captions (higher quality)")
            recommendation_score += 1
        elif has_captions:
            quality_indicators.append("Auto-generated captions available")
        
        # Duration analysis
        if "m" in duration:
            try:
                duration_parts = duration.replace("h", " h ").replace("m", " m ").split()
                minutes = 0
                for i, part in enumerate(duration_parts):
                    if "h" in part:
                        minutes += int(duration_parts[i-1]) * 60
                    elif "m" in part:
                        minutes += int(duration_parts[i-1])
                
                if 10 <= minutes <= 60:
                    quality_indicators.append("Good length for in-depth content (10-60 min)")
                    recommendation_score += 1
                elif minutes > 60:
                    quality_indicators.append("Long-form content (comprehensive)")
                    recommendation_score += 1
                elif minutes >= 5:
                    quality_indicators.append("Moderate length content")
            except:
                pass
        
        # Generate recommendation
        if recommendation_score >= 4:
            recommendation = "🟢 HIGHLY RECOMMENDED - Strong indicators of valuable content"
        elif recommendation_score >= 2:
            recommendation = "🟡 MODERATELY RECOMMENDED - Some positive indicators"
        else:
            recommendation = "🔴 LIMITED RECOMMENDATION - Few quality indicators"
        
        result = f"""Video Knowledge Base Evaluation:

Video: {video_title}
Channel: {channel_title}
Duration: {duration}
Views: {view_count:,}
Content Type: {content_type}
Captions Available: {'Yes' if has_captions else 'No'} {'(Manual)' if has_captions and not is_auto_generated else '(Auto-generated)' if has_captions else ''}

📊 Quality Indicators:
"""
        
        # Add quality indicators
        if quality_indicators:
            for indicator in quality_indicators:
                result += f"• {indicator}\n"
        else:
            result += "• Limited quality indicators detected\n"
        
        # Add freshness analysis section
        if video_age_days is not None:
            result += "\n⏰ Content Freshness Analysis:\n"
            result += f"• Video Age: {video_age_days} days ({age_assessment})\n"
            if is_high_volatility:
                result += "• High-Volatility Tech Topic: Extra freshness priority applied\n"
            if freshness_bonus > 0:
                total_bonus = freshness_bonus
                if tech_bonus > 0:
                    result += f"• Freshness Bonus: +{freshness_bonus} points ({freshness_bonus - tech_bonus} base + {tech_bonus} tech volatility)\n"
                else:
                    result += f"• Freshness Bonus: +{freshness_bonus} points for recent content\n"
            elif freshness_bonus < 0:
                result += f"• Age Penalty: {freshness_bonus} point for older content\n"
        
        result += f"""

🎯 Knowledge Base Recommendation:
{recommendation}

Reasoning:
• Content appears to be {content_type.lower()}
• Video has {view_count:,} views indicating {'strong' if view_count > 100000 else 'moderate'} audience interest
• {'Manual captions suggest higher content quality' if has_captions and not is_auto_generated else 'Auto-generated captions available' if has_captions else 'No captions available'}
• Duration ({duration}) is {'appropriate' if recommendation_score > 2 else 'variable'} for learning content

💡 Decision Support:
{'This video shows strong metadata indicators for knowledge base inclusion. Consider adding it for comprehensive coverage.' if recommendation_score >= 4 else 'Video shows some positive indicators. Review the content to determine if it meets your knowledge base standards.' if recommendation_score >= 2 else 'Limited metadata indicators suggest this may not be optimal for knowledge base inclusion unless it covers a specific niche topic you need.'}

Video URL: https://www.youtube.com/watch?v={video_id}

Note: This evaluation is based on video metadata only. Your YouTube Agent app can provide deeper transcript-based analysis when needed."""
        
        return result
        
    except Exception as e:
        return f"Error evaluating video for knowledge base: {str(e)}"

# Add a resource for server information
@mcp.resource("youtube://server/info")
def get_server_info() -> str:
    """Get information about this YouTube MCP server."""
    return """YouTube MCP Server

This server provides access to YouTube data via the YouTube Data API v3.

Available Tools:
1. get_video_details(video_input) - Get detailed information about a YouTube video
2. get_playlist_details(playlist_input) - Get information about a YouTube playlist  
3. get_playlist_items(playlist_input, max_results) - Get videos from a playlist
4. get_channel_details(channel_input) - Get detailed information about a YouTube channel
5. get_video_categories(region_code) - Get list of YouTube video categories for a region
6. get_channel_videos(channel_input, max_results) - Get recent videos from a YouTube channel
7. search_videos(query, max_results, order) - Search YouTube for videos by keywords
8. get_trending_videos(region_code, max_results) - Get trending videos from YouTube for a specific region
9. get_video_comments(video_input, max_results, order) - Get comments from a YouTube video
10. analyze_video_engagement(video_input) - Analyze video engagement metrics and provide insights
11. get_channel_playlists(channel_input, max_results) - Get playlists from a YouTube channel
12. get_video_caption_info(video_input, language) - Get available caption/transcript information
13. evaluate_video_for_knowledge_base(video_input) - Analyze video metadata to help decide if worth adding to knowledge base

Supported URL formats:
- Videos: https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID
- Playlists: https://www.youtube.com/playlist?list=PLAYLIST_ID
- Channels: https://www.youtube.com/channel/CHANNEL_ID or https://www.youtube.com/@username

You can also use video IDs, playlist IDs, and channel IDs directly.

Environment Requirements:
- YOUTUBE_API_KEY environment variable must be set with a valid YouTube Data API v3 key

API Quota Usage (per call):
- get_video_details: 1 unit
- get_playlist_details: 1 unit  
- get_playlist_items: 1 unit
- get_channel_details: 1 unit
- get_video_categories: 1 unit
- get_channel_videos: 101 units (1 for channel lookup + 100 for search)
- search_videos: 101 units (100 for search + 1 for additional details)
- get_trending_videos: 1 unit
- get_video_comments: 1 unit
- analyze_video_engagement: 1 unit (reuses video details)
- get_channel_playlists: 1 unit
- get_video_caption_info: 50 units (captions API)
- evaluate_video_for_knowledge_base: 51 units (1 for video details + 50 for captions)

Daily Quota Limit: 10,000 units (default)
High-usage functions: search_videos (101), get_channel_videos (101), get_video_caption_info (50), evaluate_video_for_knowledge_base (51)

Note: Monitor your quota usage carefully. Consider caching results for frequently accessed data.
"""

if __name__ == "__main__":
    # For MCP protocol, we can't print to stdout - it must only contain JSON
    # The API key check will happen when tools are called
    mcp.run()

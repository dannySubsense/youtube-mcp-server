# YouTube MCP Server

A comprehensive Model Context Protocol (MCP) server that provides real-time YouTube data access through the YouTube Data API v3. This server enables AI assistants to search, analyze, and retrieve detailed information about YouTube videos, channels, playlists, and more.

## 🚀 Features

### 14 Complete Functions

1. **`get_video_details`** - Get comprehensive video information including title, description, statistics, and metadata
2. **`get_playlist_details`** - Retrieve playlist information and metadata
3. **`get_playlist_items`** - List videos within a playlist with details
4. **`get_channel_details`** - Get channel information including subscriber count, video count, and description
5. **`get_video_categories`** - List available video categories for specific regions
6. **`get_channel_videos`** - Get recent videos from a YouTube channel
7. **`search_videos`** - Search YouTube for videos with customizable parameters
8. **`get_trending_videos`** - Retrieve trending videos for specific regions
9. **`get_video_comments`** - Get comments from videos with sorting options
10. **`analyze_video_engagement`** - Analyze engagement metrics and provide insights
11. **`get_channel_playlists`** - List playlists from a YouTube channel
12. **`get_video_caption_info`** - Get available caption/transcript information
13. **`evaluate_video_for_knowledge_base`** - Intelligent content evaluation with freshness scoring for knowledge base curation
14. **`get_video_transcript`** - Extract actual transcript content from YouTube videos

### Key Capabilities

- ✅ **Real-time data** from YouTube Data API v3
- ✅ **Comprehensive error handling** and API quota management
- ✅ **Multiple URL format support** (youtube.com, youtu.be, @usernames, channel IDs)
- ✅ **Intelligent content evaluation** with technology freshness scoring
- ✅ **Flexible search and filtering** options
- ✅ **Engagement analysis** with industry benchmarks
- ✅ **Regional content support** for trending and categories
- ✅ **MCP protocol compliance** for seamless AI integration

## 📋 Requirements

- Python 3.8+
- YouTube Data API v3 key
- MCP-compatible client (Claude Desktop, Cursor, etc.)

## 🛠️ Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/dannySubsense/youtube-mcp-server.git
cd youtube-mcp-server
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Get YouTube API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3
4. Create credentials (API Key)
5. (Optional) Restrict the API key to YouTube Data API v3 for security

### Step 4: Configure API Key

Create a `credentials.yml` file in the project root:

```yaml
youtube_api_key: "YOUR_YOUTUBE_API_KEY_HERE"
```

**Important:** Never commit your `credentials.yml` file to version control!

### Step 5: Test the Server

```bash
python test_server.py
```

This will run comprehensive tests on all 14 functions to ensure everything is working correctly.

## 🔧 Integration Guides

### Claude Desktop Integration

1. **Install the server** following the setup steps above

2. **Add to Claude Desktop configuration** - Edit your Claude Desktop config file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/path/to/youtube-mcp-server/youtube_mcp_server.py"],
      "env": {
        "YOUTUBE_API_KEY": "your_youtube_api_key_here"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Verify integration** - Ask Claude: "Can you search for Python tutorials on YouTube?"

### Cursor Integration

1. **Install the server** following the setup steps above

2. **Configure in Cursor settings:**

   - Open Cursor Settings
   - Navigate to MCP Servers
   - Add new server with the python command and arguments

3. **Set environment variable** for your API key

4. **Test with Cursor** by asking it to search YouTube content

### Custom Project Integration

For custom applications or other MCP clients:

```python
from youtube_mcp_server import (
    get_video_details,
    search_videos,
    evaluate_video_for_knowledge_base
)

# Example usage
async def example():
    # Search for videos
    results = await search_videos("machine learning", max_results=5)
    print(results)

    # Evaluate video for knowledge base
    evaluation = await evaluate_video_for_knowledge_base("dQw4w9WgXcQ")
    print(evaluation)
```

### Environment Variables Setup

You can also use environment variables instead of the credentials file:

```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

## 📖 Usage Examples

### Basic Video Information

```python
# Get detailed video information
result = await get_video_details("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Also works with video IDs
result = await get_video_details("dQw4w9WgXcQ")
```

### Search and Discovery

```python
# Search for recent Python tutorials
tutorials = await search_videos(
    query="Python tutorial",
    max_results=10,
    order="date"
)

# Get trending videos in the US
trending = await get_trending_videos(region_code="US", max_results=5)
```

### Channel Analysis

```python
# Get channel information
channel_info = await get_channel_details("@3Blue1Brown")

# Get recent videos from a channel
recent_videos = await get_channel_videos("@3Blue1Brown", max_results=5)

# Get all playlists from a channel
playlists = await get_channel_playlists("@3Blue1Brown")
```

### Content Evaluation (Special Feature)

```python
# Evaluate if a video is worth adding to knowledge base
# Includes technology freshness scoring for educational content
evaluation = await evaluate_video_for_knowledge_base("Z6nkEZyS9nA")

# Example output:
# 🟢 HIGHLY RECOMMENDED - Strong indicators of valuable content
# ⏰ Content Freshness: Very Recent (2 days old)
# 🚀 Tech Currency: React 2025 content - framework evolves rapidly
```

### Transcript Extraction (New!)
```python
# Extract full transcript content from a video
transcript = await get_video_transcript("Z6nkEZyS9nA")

# Also works with URLs and different languages
transcript_spanish = await get_video_transcript(
    "https://www.youtube.com/watch?v=Z6nkEZyS9nA", 
    language="es"
)

# Example output:
# 📝 Full Transcript: [Complete video transcript text]
# ⏰ Timestamped Segments: [00:15] Welcome to this tutorial...
# Word Count: ~2,847 words
```

### Engagement Analysis

```python
# Analyze video engagement metrics
engagement = await analyze_video_engagement("dQw4w9WgXcQ")

# Get video comments
comments = await get_video_comments("dQw4w9WgXcQ", max_results=10, order="relevance")
```

## 🎯 Function Reference

| Function                            | Purpose                    | Key Features                                 |
| ----------------------------------- | -------------------------- | -------------------------------------------- |
| `get_video_details`                 | Complete video information | Views, likes, duration, description          |
| `get_playlist_details`              | Playlist metadata          | Title, description, video count              |
| `get_playlist_items`                | Videos in playlist         | Ordered list with metadata                   |
| `get_channel_details`               | Channel information        | Subscribers, total views, description        |
| `get_video_categories`              | Available categories       | Region-specific category list                |
| `get_channel_videos`                | Recent channel videos      | Latest uploads with details                  |
| `search_videos`                     | Video search               | Multiple sort orders, filters                |
| `get_trending_videos`               | Trending content           | Region-specific trending videos              |
| `get_video_comments`                | Video comments             | Sorting, reply counts                        |
| `analyze_video_engagement`          | Engagement metrics         | Industry benchmarks, insights                |
| `get_channel_playlists`             | Channel playlists          | All public playlists                         |
| `get_video_caption_info`            | Caption availability       | Languages, manual vs auto                    |
| `evaluate_video_for_knowledge_base` | Content evaluation         | **Smart freshness scoring for tech content** |
| `get_video_transcript`              | Extract transcript content | **Full text extraction, timestamps, multilingual** |

## 🔥 Special Feature: Intelligent Content Evaluation

The `evaluate_video_for_knowledge_base` function includes advanced content evaluation:

### Technology Freshness Scoring

- **High-volatility topics** (React, AWS, AI/ML): Strong preference for recent content
- **Medium-volatility topics** (Python, general programming): Moderate freshness bonus
- **Stable topics** (algorithms, math): Minimal age penalty

### Quality Indicators

- View count and engagement metrics
- Manual vs auto-generated captions
- Content type detection (tutorial, review, etc.)
- Duration appropriateness
- Technology currency indicators (2024, 2025, "latest", version numbers)

### Smart Recommendations

- 🟢 **HIGHLY RECOMMENDED** - Strong quality + recent tech content
- 🟡 **MODERATELY RECOMMENDED** - Some positive indicators
- 🔴 **LIMITED RECOMMENDATION** - Few quality indicators

## 📊 API Quota Usage

| Function                                  | Quota Cost | Notes            |
| ----------------------------------------- | ---------- | ---------------- |
| Basic functions (get_video_details, etc.) | 1 unit     | Low cost         |
| Search functions                          | 100+ units | High cost        |
| Caption functions                         | 50+ units  | Medium-high cost |
| Evaluation function                       | 51 units   | Medium-high cost |

**Daily limit:** 10,000 units (default)
**Monitor usage** to avoid quota exhaustion.

## 🛡️ Error Handling

The server includes comprehensive error handling for:

- Invalid API keys
- Quota exceeded errors
- Network connectivity issues
- Invalid video/channel IDs
- Regional restrictions
- Disabled comments/captions

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_server.py
```

This tests all 14 functions with real YouTube content and provides detailed output.

## 🚨 Security Notes

- **Never commit** your `credentials.yml` file
- **Restrict your API key** to YouTube Data API v3 only
- **Monitor quota usage** to prevent unexpected costs
- **Use environment variables** in production environments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes with `python test_server.py`
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📝 Development Notes

This project was developed using:

- **Incremental methodology** - One function at a time
- **Test-driven development** - Each function tested before integration
- **User collaboration** - Continuous feedback and approval gates
- **Backup protocols** - Safe development with rollback capabilities

See `documents/testing.md` for detailed development and testing procedures.

## 🐛 Troubleshooting

### Common Issues

**"API key not found" error:**

- Ensure `credentials.yml` exists with correct format
- Check file permissions
- Verify API key is valid and not restricted

**"Quota exceeded" error:**

- Check your Google Cloud Console quota usage
- Consider upgrading quota or optimizing requests
- Use caching for frequently accessed data

**"Video not found" error:**

- Verify the video ID or URL is correct
- Check if video is private or restricted
- Ensure video hasn't been deleted

**MCP connection issues:**

- Verify Python path in configuration
- Check that all dependencies are installed
- Restart your MCP client after configuration changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built using the [Model Context Protocol](https://modelcontextprotocol.io/)
- Powered by [YouTube Data API v3](https://developers.google.com/youtube/v3)
- Developed with [FastMCP](https://github.com/modelcontextprotocol/python-sdk)

---

**Ready to supercharge your AI assistant with YouTube capabilities? Get started today!** 🚀

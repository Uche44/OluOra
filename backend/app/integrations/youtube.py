import httpx
import logging

logger = logging.getLogger(__name__)

async def fetch_channel_details(access_token: str) -> dict:
    """Fetch channel profile info, stats, and uploads playlist ID for the authenticated user."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,contentDetails,statistics",
        "mine": "true"
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch YouTube channel details: {response.status_code} - {response.text}")
                raise Exception("YouTube API request failed while fetching channel details")
            
            data = response.json()
            items = data.get("items", [])
            if not items:
                raise Exception("No YouTube channel found associated with this Google account")
            
            return items[0]
        except Exception as e:
            logger.error(f"Error fetching YouTube channel: {e}")
            raise

async def fetch_latest_videos(access_token: str, uploads_playlist_id: str, max_results: int = 50) -> list[str]:
    """Fetch the latest video IDs from the channel's uploads playlist."""
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": min(max_results, 50)
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch uploads playlist items: {response.status_code} - {response.text}")
                raise Exception("YouTube API request failed while listing uploads playlist")
            
            data = response.json()
            items = data.get("items", [])
            video_ids = [
                item["contentDetails"]["videoId"]
                for item in items
                if "contentDetails" in item and "videoId" in item["contentDetails"]
            ]
            return video_ids
        except Exception as e:
            logger.error(f"Error fetching playlist items: {e}")
            raise

async def fetch_videos_metadata(access_token: str, video_ids: list[str]) -> list[dict]:
    """Fetch metadata and stats (title, viewCount, commentCount) for list of video IDs in chunks of 50."""
    if not video_ids:
        return []
        
    url = "https://www.googleapis.com/youtube/v3/videos"
    headers = {"Authorization": f"Bearer {access_token}"}
    all_video_details = []
    
    # Chunk video IDs into batches of 50 to satisfy YouTube API parameters limits
    chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for chunk in chunks:
            params = {
                "part": "snippet,statistics",
                "id": ",".join(chunk)
            }
            try:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch videos details chunk: {response.status_code} - {response.text}")
                    raise Exception("YouTube API request failed while fetching videos metadata")
                
                data = response.json()
                all_video_details.extend(data.get("items", []))
            except Exception as e:
                logger.error(f"Error fetching videos metadata chunk: {e}")
                raise
                
    return all_video_details

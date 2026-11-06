import httpx
import logging
import html
import re

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

async def fetch_comment_threads(
    access_token: str,
    video_id: str,
    max_results: int = 100,
    page_token: str | None = None,
    etag: str | None = None
) -> dict:
    """
    Fetch a page of comment threads for a specific video from YouTube API.
    Uses part=snippet,replies to retrieve top-level comments and their inline replies.
    Supports If-None-Match revalidation using the etag parameter.
    """
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet,replies",
        "videoId": video_id,
        "maxResults": min(max_results, 100),
        "order": "time"  # Sort comments by time descending (newest first)
    }
    if page_token:
        params["pageToken"] = page_token
        
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    if etag:
        headers["If-None-Match"] = etag
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            
            # Handle ETag match (304 Not Modified)
            if response.status_code == 304:
                logger.info(f"ETag matched for video {video_id} - HTTP 304 Not Modified")
                return {"etag_matched": True}
                
            if response.status_code != 200:
                logger.error(f"Failed to fetch YouTube comment threads: {response.status_code} - {response.text}")
                # Check for commentsDisabled reason
                try:
                    response_json = response.json()
                    error_info = response_json.get("error", {})
                    errors = error_info.get("errors", [])
                    for err in errors:
                        if err.get("reason") == "commentsDisabled":
                            raise Exception("COMMENTS_DISABLED")
                except ValueError:
                    pass
                raise Exception("YouTube API request failed while fetching comment threads")
                
            data = response.json()
            # Capture response etag and store it on a private key
            resp_etag = response.headers.get("etag")
            if resp_etag:
                data["_etag"] = resp_etag
            return data
        except Exception as e:
            if str(e) == "COMMENTS_DISABLED":
                raise
            logger.error(f"Error fetching YouTube comment threads: {e}")
            raise


CAPTIONS_LIST_URL = "https://www.googleapis.com/youtube/v3/captions"
CAPTIONS_DOWNLOAD_URL = "https://www.googleapis.com/youtube/v3/captions/{caption_id}"


def _vtt_to_text(vtt: str) -> str:
    """Flatten a WebVTT caption track into a clean paragraph."""
    lines: list[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT":
            continue
        if "-->" in line:
            continue
        if line.startswith(("NOTE", "STYLE", "REGION", "Kind:", "Language:")):
            continue
        if line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = html.unescape(line).strip()
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return " ".join(lines)


async def fetch_video_transcript(
    access_token: str, video_id: str
) -> tuple[str | None, int]:
    """Fetch the creator-owned video's caption track as plain text.

    Returns ``(text, quota_units)``. A missing caption track, a non-owned video,
    or a permission failure returns ``(None, units)`` rather than raising, so
    script generation can fall back to the video description.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    units = 50  # captions.list

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.get(
                CAPTIONS_LIST_URL,
                params={"part": "snippet", "videoId": video_id},
                headers=headers,
            )
        except Exception as exc:
            logger.warning("YouTube captions.list request failed: %s", exc)
            return None, units

        if response.status_code != 200:
            logger.warning(
                "YouTube captions.list failed: %s - %s",
                response.status_code,
                response.text[:200],
            )
            return None, units

        items = response.json().get("items", [])
        if not items:
            logger.info("No caption tracks found for video %s", video_id)
            return None, units

        def _score(item: dict) -> tuple[bool, bool]:
            snippet = item.get("snippet", {})
            manual = snippet.get("trackKind") != "ASR"
            english = (snippet.get("language") or "").lower().startswith("en")
            return manual, english

        caption = max(items, key=_score)
        caption_id = caption.get("id")
        if not caption_id:
            return None, units

        units += 200  # captions.download
        try:
            download = await client.get(
                CAPTIONS_DOWNLOAD_URL.format(caption_id=caption_id),
                params={"tfmt": "vtt"},
                headers=headers,
            )
        except Exception as exc:
            logger.warning("YouTube captions.download request failed: %s", exc)
            return None, units

        if download.status_code != 200:
            logger.warning(
                "YouTube captions.download failed: %s - %s",
                download.status_code,
                download.text[:200],
            )
            return None, units

        text = _vtt_to_text(download.text)
        return (text or None), units


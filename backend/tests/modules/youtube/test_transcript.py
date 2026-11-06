from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.youtube import _vtt_to_text, fetch_video_transcript


def test_vtt_to_text_strips_timestamps_and_duplicates():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
Hello world

00:00:04.000 --> 00:00:06.000
<v Speaker>Next line</v>
"""
    assert _vtt_to_text(vtt) == "Hello world Next line"


@pytest.mark.asyncio
async def test_fetch_video_transcript_downloads_preferred_track():
    list_response = MagicMock()
    list_response.status_code = 200
    list_response.json.return_value = {
        "items": [
            {"id": "asr-track", "snippet": {"trackKind": "ASR", "language": "en"}},
            {"id": "manual-track", "snippet": {"trackKind": "standard", "language": "en"}},
        ]
    }

    download_response = MagicMock()
    download_response.status_code = 200
    download_response.text = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nReal transcript"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=[list_response, download_response])

    with patch("app.integrations.youtube.httpx.AsyncClient", return_value=mock_client):
        text, units = await fetch_video_transcript("token", "video-id")

    assert text == "Real transcript"
    assert units == 250
    # The manual track should be preferred over ASR.
    assert mock_client.get.call_args_list[1].args[0].endswith("/manual-track")


@pytest.mark.asyncio
async def test_fetch_video_transcript_without_captions_returns_none():
    list_response = MagicMock()
    list_response.status_code = 200
    list_response.json.return_value = {"items": []}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=list_response)

    with patch("app.integrations.youtube.httpx.AsyncClient", return_value=mock_client):
        text, units = await fetch_video_transcript("token", "video-id")

    assert text is None
    assert units == 50

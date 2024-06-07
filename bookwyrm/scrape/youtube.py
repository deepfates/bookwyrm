import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from bookwyrm.models import Document
from .document import create_document

async def fetch_youtube_transcript(video_url) -> Document:

    def extract_video_id(video_url):
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
        return None

    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube video URL")

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        transcript = formatter.format_transcript(transcript_list)
        return create_document(transcript, video_url)
    except Exception as e:
        raise ValueError(f"Failed to retrieve YouTube transcript: {str(e)}")

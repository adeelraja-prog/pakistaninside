import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class YouTubePublisher:
    """Optional YouTube Shorts upload. Requires user-authorised OAuth refresh credentials."""

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self):
        required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "YouTube upload is not authorised. Add GitHub secrets: " + ", ".join(missing)
            )

        credentials = Credentials(
            token=None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            scopes=self.SCOPES,
        )
        self.service = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    def upload_short(self, video_path, title, description, tags=None):
        path = Path(video_path)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Video file missing or empty: {video_path}")

        title = (title or "Adeel Raja News Update").strip()
        if "#Shorts" not in title:
            title = f"{title[:85]} #Shorts"

        body = {
            "snippet": {
                "title": title[:100],
                "description": (description or "Adeel Raja news update") + "\n\n#Shorts #AdeelRaja",
                "tags": (tags or ["AdeelRaja", "PakistanNews", "Shorts"])[:20],
                "categoryId": "25",
                "defaultLanguage": "ur",
            },
            "status": {
                "privacyStatus": os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
                "selfDeclaredMadeForKids": False,
            },
        }
        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(str(path), mimetype="video/mp4", chunksize=-1, resumable=True),
        )
        response = request.execute()
        if not response.get("id"):
            raise RuntimeError(f"YouTube did not confirm video creation: {response}")
        return {"video_id": response["id"], "url": f"https://www.youtube.com/watch?v={response['id']}"}

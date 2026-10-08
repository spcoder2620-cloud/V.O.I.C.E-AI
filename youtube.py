"""
V.O.I.C.E. YOUTUBE LAYER
------------------------
Pulls a video's title and transcript using only the standard library
(no youtube-dl, no API key), matching the rest of this project's
"no external packages" design.

This only reads what a video's public watch page already exposes:
its title and, when present, its caption track. It cannot transcribe
a video with no captions, and YouTube can occasionally block
datacenter IPs with a consent/verification page — in that case
fetch() returns (None, None) or (title, None) and the caller should
say so plainly rather than invent a transcript.
"""

import html
import json
import re
import urllib.parse

from web import Web


YOUTUBE_RE = re.compile(
    r"(https?://(?:www\.|m\.)?youtube\.com/(?:watch\?v=|shorts/|live/)"
    r"[\w-]+(?:[&?][^\s\"'<>]*)?"
    r"|https?://youtu\.be/[\w-]+(?:\?[^\s\"'<>]*)?)",
    re.I
)


class YouTube:
    def __init__(self):
        self.web = Web()

    @staticmethod
    def find_link(text):
        match = YOUTUBE_RE.search(text or "")
        return match.group(1) if match else None

    @staticmethod
    def video_id(url):
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()

        if "youtu.be" in host:
            return parsed.path.strip("/").split("/")[0] or None

        if "/shorts/" in parsed.path or "/live/" in parsed.path:
            return parsed.path.rstrip("/").split("/")[-1] or None

        params = urllib.parse.parse_qs(parsed.query)
        values = params.get("v")
        return values[0] if values else None

    def fetch(self, url):
        """Returns (title, transcript). Either half can be None/empty
        if that part could not be recovered — the caller decides how
        to explain that to the person."""
        video_id = self.video_id(url)

        if not video_id:
            return None, None

        watch_url = "https://www.youtube.com/watch?v=" + video_id
        page = self.web.request(watch_url, timeout=15)

        if not page:
            return None, None

        title = self._title(page)
        captions_url = self._captions_url(page)

        if not captions_url:
            return title, None

        transcript = self._transcript(captions_url)
        return title, transcript

    @staticmethod
    def _title(page):
        match = re.search(
            r'"title":"((?:[^"\\]|\\.)*)"\s*,\s*"lengthSeconds"',
            page
        )

        if match:
            try:
                return json.loads(
                    '"' + match.group(1) + '"'
                ).strip()
            except (ValueError, json.JSONDecodeError):
                return html.unescape(
                    match.group(1)
                ).strip()

        fallback = re.search(
            r"<title>(.*?)</title>",
            page,
            flags=re.S
        )

        if fallback:
            return html.unescape(
                fallback.group(1)
            ).replace(" - YouTube", "").strip()

        return "this video"

    @staticmethod
    def _captions_url(page):
        match = re.search(
            r'"captionTracks":(\[.*?\])',
            page
        )

        if not match:
            return None

        try:
            tracks = json.loads(
                match.group(1)
            )
        except (ValueError, json.JSONDecodeError):
            return None

        if not tracks:
            return None

        english = [
            t for t in tracks
            if t.get("languageCode", "").lower().startswith("en")
        ]

        # Prefer a human-written track over YouTube's auto captions (asr).
        manual = [
            t for t in english
            if t.get("kind") != "asr"
        ]

        chosen = manual or english or tracks
        base_url = chosen[0].get("baseUrl")

        return html.unescape(base_url) if base_url else None

    def _transcript(self, captions_url):
        xml = self.web.request(captions_url, timeout=15)

        if not xml:
            return ""

        pieces = re.findall(
            r"<text[^>]*>(.*?)</text>",
            xml,
            flags=re.S
        )

        lines = []

        for piece in pieces:
            text = html.unescape(piece)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            if text:
                lines.append(text)

        return " ".join(lines)

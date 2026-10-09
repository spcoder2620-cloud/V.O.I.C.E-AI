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
import urllib.error
import urllib.parse
import urllib.request


# YouTube routinely blocks plain scripted requests from datacenter IPs
# (like Render's) with a 403, or detours EU-geolocated requests through
# a cookie-consent page before the real HTML loads. A fuller browser
# header set plus a pre-accepted consent cookie avoids both cases in
# the common case; nothing here works around a captcha challenge.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+1",
}


YOUTUBE_RE = re.compile(
    r"(https?://(?:www\.|m\.)?youtube\.com/(?:watch\?v=|shorts/|live/)"
    r"[\w-]+(?:[&?][^\s\"'<>]*)?"
    r"|https?://youtu\.be/[\w-]+(?:\?[^\s\"'<>]*)?)",
    re.I
)


class YouTube:
    def _get(self, url, timeout=15):
        """Like Web.request, but with real browser headers and with the
        actual failure reason printed (it flows into the UI's research
        panel) instead of being swallowed as a bare empty string."""
        try:
            request = urllib.request.Request(
                url,
                headers=BROWSER_HEADERS
            )

            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:
                return response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

        except urllib.error.HTTPError as exc:
            print(
                "> YouTube fetch failed: HTTP "
                + str(exc.code)
                + " ("
                + ("likely blocked the request" if exc.code in (403, 429) else "unexpected status")
                + ") for "
                + url
            )
            return ""

        except urllib.error.URLError as exc:
            print(
                "> YouTube fetch failed: "
                + str(exc.reason)
                + " for "
                + url
            )
            return ""

        except (TimeoutError, OSError) as exc:
            print(
                "> YouTube fetch failed: "
                + str(exc)
                + " for "
                + url
            )
            return ""

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
        page = self._get(watch_url)

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
        xml = self._get(captions_url)

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

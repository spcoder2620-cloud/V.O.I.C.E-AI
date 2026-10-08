"""
V.O.I.C.E. WEB LAYER
--------------------
Text cleanup helpers and the plain-urllib web client (search + page
fetch). Pulled out of voice.py so other modules (youtube.py) can use
the same HTTP/text plumbing without importing voice.py itself.
"""

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

from smart import SmartEngine


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.0 Safari/605.1.15"
)


class Text:
    STOPWORDS = SmartEngine.STOP

    @staticmethod
    def words(text):
        return re.findall(
            r"[A-Za-z0-9']+",
            text.lower()
        )

    @classmethod
    def keywords(cls, text):
        return Counter(
            word
            for word in cls.words(text)
            if (
                word not in cls.STOPWORDS
                and len(word) >= 3
            )
        )

    @staticmethod
    def sentences(text):
        # Keep newline and punctuation boundaries. This avoids turning an
        # entire webpage into one giant sentence.
        chunks = re.split(
            r"(?:\n+|(?<=[.!?])\s+)",
            text
        )
        return [
            re.sub(
                r"\s+",
                " ",
                chunk
            ).strip()
            for chunk in chunks
            if chunk.strip()
        ]

    @staticmethod
    def clean(text):
        return re.sub(
            r"\s+",
            " ",
            text
        ).strip()


class Web:
    def request(self, url, timeout=12):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:
                return response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError
        ):
            return ""

    def search(self, query, amount=6):
        encoded = urllib.parse.quote_plus(
            query
        )

        url = (
            "https://html.duckduckgo.com/html/?q="
            + encoded
        )

        page = self.request(url)

        if not page:
            return []

        # Capture both result links and result snippets.
        result_pattern = re.compile(
            r'<a[^>]+class="result__a"'
            r'[^>]+href="([^"]+)"'
            r'[^>]*>(.*?)</a>'
            r'(.*?)(?:'
            r'<a[^>]+class="result__url"'
            r'|</div>\s*</div>)',
            flags=re.I | re.S
        )

        results = []
        seen = set()

        for match in result_pattern.finditer(page):
            raw_url = match.group(1)
            raw_title = match.group(2)
            tail = match.group(3)

            title = re.sub(
                r"<[^>]+>",
                "",
                raw_title
            )

            title = Text.clean(
                html.unescape(title)
            )

            url = html.unescape(
                raw_url
            )

            parsed = urllib.parse.urlparse(
                url
            )

            params = urllib.parse.parse_qs(
                parsed.query
            )

            if "uddg" in params:
                url = params["uddg"][0]

            if not url.startswith(
                ("http://", "https://")
            ):
                continue

            if url in seen:
                continue

            seen.add(url)

            snippet_match = re.search(
                r'<a[^>]+class="result__snippet"'
                r'[^>]*>(.*?)</a>|'
                r'<div[^>]+class="result__snippet"'
                r'[^>]*>(.*?)</div>',
                tail,
                flags=re.I | re.S
            )

            snippet = ""

            if snippet_match:
                snippet = (
                    snippet_match.group(1)
                    or snippet_match.group(2)
                    or ""
                )

                snippet = Text.clean(
                    html.unescape(
                        re.sub(
                            r"<[^>]+>",
                            "",
                            snippet
                        )
                    )
                )

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet
            })

            if len(results) >= amount:
                break

        # If DDG changes its HTML around the combined regex, fall back to
        # the simpler link parser so search does not completely fail.
        if not results:
            pattern = (
                r'<a[^>]+class="result__a"'
                r'[^>]+href="([^"]+)"'
                r'[^>]*>(.*?)</a>'
            )

            for raw_url, raw_title in re.findall(
                pattern,
                page,
                flags=re.I | re.S
            ):
                title = Text.clean(
                    html.unescape(
                        re.sub(
                            r"<[^>]+>",
                            "",
                            raw_title
                        )
                    )
                )

                url = html.unescape(
                    raw_url
                )

                parsed = urllib.parse.urlparse(
                    url
                )

                params = urllib.parse.parse_qs(
                    parsed.query
                )

                if "uddg" in params:
                    url = params["uddg"][0]

                if not url.startswith(
                    ("http://", "https://")
                ):
                    continue

                if url in seen:
                    continue

                seen.add(url)

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": ""
                })

                if len(results) >= amount:
                    break

        return results

    def read(self, url):
        page = self.request(url)

        if not page:
            return ""

        for pattern in (
            r"<script.*?</script>",
            r"<style.*?</style>",
            r"<svg.*?</svg>",
            r"<!--.*?-->"
        ):
            page = re.sub(
                pattern,
                " ",
                page,
                flags=re.I | re.S
            )

        # Preserve block boundaries so the brain can recover real sentences.
        page = re.sub(
            r"</?(p|div|br|li|h[1-6]|article|section|main|header|footer|blockquote)[^>]*>",
            "\n",
            page,
            flags=re.I
        )

        page = re.sub(
            r"<[^>]+>",
            " ",
            page
        )

        page = html.unescape(
            page
        )

        return re.sub(
            r"[ \t]+",
            " ",
            page
        ).strip()

    @staticmethod
    def domain(url):
        try:
            domain = urllib.parse.urlparse(
                url
            ).netloc.lower()

            if domain.startswith("www."):
                domain = domain[4:]

            return domain or "unknown"

        except Exception:
            return "unknown"

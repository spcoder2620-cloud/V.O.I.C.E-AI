#!/usr/bin/env python3
"""
V.O.I.C.E. — TEXT-ONLY EDITION

No popup. No speech. No API key. No external Python packages.

voice.py owns conversation + memory + browsing.
language.py owns personality + rhyme.
smart.py owns evidence ranking + answer synthesis.
"""

import re
import json
import random
import html
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

from language import VoiceLanguage
from smart import SmartEngine


MEMORY_FILE = Path("voice_memory.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/26.0 Safari/605.1.15"
)

FOLLOWUP_RE = re.compile(
    r"^(tell me more|go on|keep going|continue|what else|and then|more)\b",
    re.I
)


class Memory:
    def __init__(self):
        self.data = {
            "facts": {},
            "conversations": [],
            "learned_topics": {}
        }
        self.load()

    def load(self):
        if not MEMORY_FILE.exists():
            return
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            print("> memory could not be loaded; using a fresh memory layer.")

    def save(self):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def remember(self, key, value):
        self.data.setdefault("facts", {})[key] = value
        self.save()

    def get(self, key):
        return self.data.get("facts", {}).get(key)

    def add_conversation(self, user, response):
        self.data.setdefault("conversations", []).append({
            "user": user,
            "response": response
        })
        self.data["conversations"] = self.data["conversations"][-250:]
        self.save()

    def learn_topic(self, topic, information):
        topics = self.data.setdefault("learned_topics", {})
        topics.setdefault(topic, []).append(information)
        topics[topic] = topics[topic][-50:]
        self.save()


class Text:
    STOPWORDS = SmartEngine.STOP

    @staticmethod
    def words(text):
        return re.findall(r"[A-Za-z0-9']+", text.lower())

    @classmethod
    def keywords(cls, text):
        return Counter(
            word for word in cls.words(text)
            if word not in cls.STOPWORDS and len(word) >= 3
        )

    @staticmethod
    def sentences(text):
        return re.split(r"(?<=[.!?])\s+", text.strip())

    @staticmethod
    def clean(text):
        return re.sub(r"\s+", " ", text).strip()


class Web:
    def request(self, url):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            return ""

    def search(self, query, amount=6):
        encoded = urllib.parse.quote_plus(query)
        url = "https://html.duckduckgo.com/html/?q=" + encoded
        page = self.request(url)
        if not page:
            return []

        pattern = (
            r'<a[^>]+class="result__a"'
            r'[^>]+href="([^"]+)"'
            r'[^>]*>(.*?)</a>'
        )
        matches = re.findall(pattern, page, flags=re.I | re.S)
        results = []
        seen = set()

        for raw_url, raw_title in matches:
            title = Text.clean(
                html.unescape(re.sub(r"<[^>]+>", "", raw_title))
            )
            url = html.unescape(raw_url)
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params:
                url = params["uddg"][0]
            if not url.startswith(("http://", "https://")):
                continue
            if url in seen:
                continue
            seen.add(url)
            results.append({"title": title, "url": url})
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
            page = re.sub(pattern, " ", page, flags=re.I | re.S)

        page = re.sub(
            r"</?(p|div|br|li|h[1-6]|article|section)[^>]*>",
            "\n", page, flags=re.I
        )
        page = re.sub(r"<[^>]+>", " ", page)
        page = html.unescape(page)
        return re.sub(r"\s+", " ", page).strip()

    @staticmethod
    def domain(url):
        try:
            d = urllib.parse.urlparse(url).netloc.lower()
            return d[4:] if d.startswith("www.") else d or "unknown"
        except Exception:
            return "unknown"


class Question:
    GREETINGS = {"hi", "hello", "hey", "yo", "sup", "hiya", "howdy", "greetings"}
    CASUAL = {"thanks", "thank", "cool", "nice", "awesome", "okay", "ok", "lol", "haha", "aight"}

    @classmethod
    def classify(cls, text):
        stripped = text.strip()
        lower = stripped.lower()
        words = set(Text.words(stripped))

        if lower in cls.GREETINGS:
            return "greeting"
        if lower in cls.CASUAL:
            return "casual"

        # Do not research fragments such as "aight", "lol", "cool", etc.
        if len(words) <= 3 and "?" not in stripped:
            return "conversation"

        question_words = {
            "what", "why", "how", "when", "where", "who", "which",
            "does", "did", "can", "could", "would", "should", "explain",
            "define", "find", "search", "latest", "news", "current",
            "today", "recent", "compare", "difference"
        }

        if "?" in stripped or words & question_words:
            return "research"

        return "conversation"

    @classmethod
    def search_queries(cls, text):
        base = Text.clean(text)
        candidates = [
            base,
            base + " explanation",
            base + " overview examples"
        ]
        result = []
        seen = set()
        for q in candidates:
            key = q.lower()
            if key not in seen:
                seen.add(key)
                result.append(q)
        return result[:3]


YOUTUBE_RE = re.compile(
    r"(?:(?:https?://)?(?:www\.)?youtube\.com/watch\?v=|"
    r"(?:https?://)?youtu\.be/)([A-Za-z0-9_-]{6,})",
    re.I
)


class YouTubeWatcher:
    """Learn from available YouTube captions/transcripts."""

    def __init__(self, web):
        self.web = web

    @staticmethod
    def video_id(url):
        match = YOUTUBE_RE.search(url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_json_object(page, marker):
        start = page.find(marker)
        if start < 0:
            return None

        start = page.find("{", start)
        if start < 0:
            return None

        depth = 0
        in_string = False
        escaped = False

        for i in range(start, len(page)):
            ch = page[i]

            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(page[start:i + 1])
                    except json.JSONDecodeError:
                        return None

        return None

    def page_data(self, video_id):
        url = (
            "https://www.youtube.com/watch?v="
            + urllib.parse.quote(video_id)
        )

        page = self.web.request(url)

        if not page:
            return None, url

        data = (
            self._extract_json_object(
                page,
                "ytInitialPlayerResponse"
            )
            or self._extract_json_object(
                page,
                "var ytInitialPlayerResponse"
            )
        )

        return data, url

    def get_transcript(self, video_id):
        data, watch_url = self.page_data(video_id)

        if not data:
            return {
                "ok": False,
                "reason": "YouTube page data could not be read.",
                "url": watch_url,
                "title": ""
            }

        details = data.get("videoDetails", {})
        title = details.get("title", "")

        tracks = (
            data.get("captions", {})
            .get(
                "playerCaptionsTracklistRenderer",
                {}
            )
            .get("captionTracks", [])
        )

        if not tracks:
            return {
                "ok": False,
                "reason": "No caption track was exposed for this video.",
                "url": watch_url,
                "title": title
            }

        def language_score(track):
            code = str(
                track.get(
                    "languageCode",
                    ""
                )
            ).lower()

            if code == "en":
                return 0
            if code.startswith("en-"):
                return 1
            return 2

        track = sorted(
            tracks,
            key=language_score
        )[0]

        base_url = track.get("baseUrl")

        if not base_url:
            return {
                "ok": False,
                "reason": "Caption track has no readable URL.",
                "url": watch_url,
                "title": title
            }

        separator = "&" if "?" in base_url else "?"
        raw = self.web.request(
            base_url + separator + "fmt=srv3"
        )

        if not raw:
            return {
                "ok": False,
                "reason": "The caption track could not be downloaded.",
                "url": watch_url,
                "title": title
            }

        chunks = []

        try:
            root = ET.fromstring(raw)

            for node in root.findall(".//text"):
                value = "".join(node.itertext())
                value = html.unescape(
                    value.replace("\n", " ")
                )
                value = re.sub(
                    r"\s+",
                    " ",
                    value
                ).strip()

                if value:
                    chunks.append(value)

        except ET.ParseError:
            fallback = html.unescape(
                re.sub(r"<[^>]+>", " ", raw)
            )
            fallback = re.sub(
                r"\s+",
                " ",
                fallback
            ).strip()

            if fallback:
                chunks = [fallback]

        transcript = " ".join(chunks).strip()

        if not transcript:
            return {
                "ok": False,
                "reason": "The caption track was empty.",
                "url": watch_url,
                "title": title
            }

        return {
            "ok": True,
            "url": watch_url,
            "title": title or video_id,
            "language": track.get(
                "languageCode",
                "unknown"
            ),
            "transcript": transcript
        }

    def learn(self, url, memory):
        video_id = self.video_id(url)

        if not video_id:
            return {
                "ok": False,
                "reason": "That does not look like a YouTube video URL."
            }

        result = self.get_transcript(video_id)

        if not result.get("ok"):
            return result

        title = result["title"]
        transcript = result["transcript"]

        parts = re.split(
            r"(?<=[.!?])\s+",
            transcript
        )

        stored = 0

        for part in parts:
            clean = Text.clean(part)

            if not 45 <= len(clean) <= 450:
                continue

            memory.learn_topic(
                title,
                {
                    "sentence": clean,
                    "source": "youtube",
                    "title": title,
                    "url": result["url"],
                    "type": "caption"
                }
            )

            stored += 1

            if stored >= 80:
                break

        memory.learn_topic(
            title,
            {
                "sentence": transcript[:15000],
                "source": "youtube",
                "title": title,
                "url": result["url"],
                "type": "transcript"
            }
        )

        return {
            "ok": True,
            "title": title,
            "url": result["url"],
            "language": result["language"],
            "stored": stored
        }


class Research:
    def __init__(self, memory):
        self.memory = memory
        self.web = Web()

    def investigate(self, question):
        all_results = []
        seen_urls = set()

        print()
        print("> thinking about what to search...")

        for query in Question.search_queries(question):
            print("> searching: " + query)
            for result in self.web.search(query, amount=5):
                if result["url"] not in seen_urls:
                    seen_urls.add(result["url"])
                    all_results.append(result)

        if not all_results:
            print("> no web results found.")
            return []

        pages = []
        seen_domains = set()

        for result in all_results[:15]:
            domain = self.web.domain(result["url"])
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            print("> went to '" + domain + "'")
            page = self.web.read(result["url"])

            if page:
                pages.append({
                    "title": result["title"],
                    "url": result["url"],
                    "domain": domain,
                    "text": page
                })

        if not pages:
            print("> the pages could not be read.")
            return []

        print()
        print("> " + str(len(pages)) + " sources found")
        print("> analyzing similar instances...")

        facts = self.extract_facts(question, pages)

        print("> comparing information...")
        facts = self.compare(facts)

        print("> checking for agreement across sources...")
        print("> checking for useful differences...")
        print("> forming answer...")

        self.learn_research(question, facts)
        return facts

    def extract_facts(self, question, pages):
        keywords = set(Text.keywords(question))
        candidates = []

        for page in pages:
            count = 0
            for sentence in Text.sentences(page["text"]):
                sentence = Text.clean(sentence)
                if not 45 <= len(sentence) <= 650:
                    continue

                words = set(Text.words(sentence))
                overlap = len(words & keywords)
                if overlap == 0:
                    continue

                low = sentence.lower()
                if any(x in low for x in (
                    "skip to main content", "create an account", "sign in",
                    "subscribe", "cookie policy", "external links", "isbn", "doi:"
                )):
                    continue

                score = overlap * 2
                for marker in (
                    "because", "means", "defined", "caused", "according",
                    "is the", "refers to", "occurs when", "consists of",
                    "known as", "results in", "used to", "allows"
                ):
                    if marker in low:
                        score += 1.5

                if 90 <= len(sentence) <= 420:
                    score += 1

                candidates.append({
                    "sentence": sentence,
                    "source": page["domain"],
                    "title": page["title"],
                    "url": page["url"],
                    "score": score
                })

                count += 1
                if count >= 20:
                    break

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:100]

    def compare(self, facts):
        if not facts:
            return []

        common = Counter()
        for fact in facts:
            for word in set(Text.words(fact["sentence"])):
                if word not in Text.STOPWORDS and len(word) > 3:
                    common[word] += 1

        for fact in facts:
            words = set(Text.words(fact["sentence"]))
            fact["agreement"] = sum(common[w] for w in words if w in common)
            fact["final_score"] = fact["score"] + fact["agreement"] * 0.18

        facts.sort(key=lambda x: x["final_score"], reverse=True)

        chosen = []
        signatures = []
        for fact in facts:
            signature = set(Text.words(fact["sentence"]))
            if not signature:
                continue

            duplicate = False
            for old in signatures:
                smaller = min(len(signature), len(old))
                if smaller and len(signature & old) / smaller > 0.70:
                    duplicate = True
                    break

            if duplicate:
                continue

            chosen.append(fact)
            signatures.append(signature)
            if len(chosen) >= 30:
                break

        return chosen

    def learn_research(self, question, facts):
        topic = SmartEngine.topic(question)
        for fact in facts[:20]:
            self.memory.learn_topic(
                topic,
                {
                    "sentence": fact["sentence"],
                    "source": fact["source"],
                    "title": fact["title"],
                    "url": fact["url"]
                }
            )
        print(
            "> learned " + str(min(20, len(facts))) +
            " useful findings about " + topic + "."
        )


class Learner:
    def __init__(self, memory):
        self.memory = memory

    def learn(self, message):
        patterns = [
            (r"my name is (.+)", "name"),
            (r"i am called (.+)", "name"),
            (r"my favourite colour is (.+)", "favourite_colour"),
            (r"my favorite colour is (.+)", "favourite_colour"),
            (r"my favourite color is (.+)", "favourite_colour"),
            (r"my favorite color is (.+)", "favourite_colour")
        ]
        for pattern, key in patterns:
            match = re.search(pattern, message, re.I)
            if match:
                self.memory.remember(key, match.group(1).strip())
                return True
        return False


class Voice:
    def __init__(self):
        self.memory = Memory()
        self.learner = Learner(self.memory)
        self.research = Research(self.memory)
        self.youtube = YouTubeWatcher(self.research.web)
        self.last_facts = []
        self.last_question = ""
        self.used_sentences = []

    def respond(self, message):
        # YouTube learning command:
        #   watch <URL>
        #   learn youtube <URL>
        watch_match = re.match(
            r"^(?:watch|learn(?:\s+youtube)?)\s+(.+)$",
            message.strip(),
            flags=re.I
        )

        if watch_match:
            url = watch_match.group(1).strip()

            if not YOUTUBE_RE.search(url):
                return (
                    '"Send me a YouTube video URL and I can study its captions,\n'
                    'Then store the useful information for questions to come."'
                )

            print()
            print("> opening YouTube video...")
            print("> locating available captions...")
            print("> reading transcript...")

            result = self.youtube.learn(
                url,
                self.memory
            )

            if result.get("ok"):
                print("> transcript acquired.")
                print(
                    "> learned "
                    + str(result.get("stored", 0))
                    + " transcript findings."
                )
                print(
                    "> saved source: "
                    + result.get(
                        "title",
                        "YouTube video"
                    )
                )

                self.last_facts = []
                self.last_question = (
                    "What was learned from "
                    + result.get(
                        "title",
                        "this video"
                    )
                )
                self.used_sentences = []

                return (
                    '"I have studied the available captions and stored what was said,\n'
                    'So when you ask about this source, those findings can be weighed."'
                )

            print(
                "> "
                + result.get(
                    "reason",
                    "caption data was unavailable."
                )
            )

            return (
                '"I reached the video, but its captions were not available to read,\n'
                'So I will not claim to have learned what I could not see."'
            )

        # Continue the previous subject without repeating the same evidence.
        if FOLLOWUP_RE.match(message.strip()) and self.last_facts:
            evidence = SmartEngine.rank(
                self.last_question,
                self.last_facts,
                limit=6,
                avoid=self.used_sentences
            )
            if evidence:
                self.used_sentences.extend(evidence)
                text = SmartEngine.synthesize(
                    SmartEngine.topic(self.last_question),
                    evidence,
                    question=self.last_question
                )
                return VoiceLanguage.speak_answer(text)
            return VoiceLanguage.no_more_evidence()

        kind = Question.classify(message)

        if kind == "greeting":
            return VoiceLanguage.casual(message)

        if kind == "casual":
            return VoiceLanguage.casual(message)

        memory_response = self.memory_question(message)
        if memory_response:
            return memory_response

        # The poetic summary only appears before an actual research question.
        if kind == "research":
            print()
            print("> interpreting your question...")
            print()
            print("V.O.I.C.E.:")
            print('"' + VoiceLanguage.opening_summary(message) + '"')
            print()

            facts = self.research.investigate(message)

            # Prefer fresh web research. Only fall back to learned material
            # if the network supplied nothing usable, so old memory cannot
            # contaminate a fresh answer.
            if not facts:
                remembered = SmartEngine.from_memory(
                    message,
                    self.memory.data.get("learned_topics", {})
                )
                if remembered:
                    print("> fresh research was unavailable; using learned knowledge.")
                    facts = [
                        {
                            "sentence": sentence,
                            "source": "local memory",
                            "title": "V.O.I.C.E. memory",
                            "url": "",
                            "score": 1.0
                        }
                        for sentence in remembered[:8]
                    ]

            if facts:
                evidence = SmartEngine.rank(
                    message,
                    facts,
                    limit=6
                )
                text = SmartEngine.synthesize(
                    SmartEngine.topic(message),
                    evidence,
                    question=message
                )
                response = VoiceLanguage.speak_answer(text)

                self.last_facts = facts
                self.last_question = message
                self.used_sentences = list(evidence)
                return response

            return self.conversation(message)

        return self.conversation(message)

    def memory_question(self, message):
        lower = message.lower()

        if "what is my name" in lower:
            name = self.memory.get("name")
            if name:
                return (
                    f'"Your name is {name}, a fact that I retain;\n'
                    'I remember what you tell me and can return it again."'
                )

        if any(
            phrase in lower
            for phrase in (
                "favourite colour", "favorite colour",
                "favourite color", "favorite color"
            )
        ):
            colour = self.memory.get("favourite_colour")
            if colour:
                return (
                    f'"You chose {colour}, a choice that I retain;\n'
                    'A small detail stored to be returned again."'
                )

        return None

    def conversation(self, message):
        lower = message.lower().strip()

        if "who are you" in lower:
            return VoiceLanguage.casual(message)

        if "how are you" in lower or "how are you doing" in lower:
            return random.choice([
                '"I am doing well, and ready to converse;\n'
                'Give me a subject and I shall make it clearer in verse."',
                '"Everything is steady, and the conversation is clear;\n'
                'Give me your next thought and I shall meet it here."'
            ])

        if "what do you think" in lower:
            return (
                '"Give me the subject and I will weigh what is known,\n'
                'Compare the available evidence, and form a view of my own."'
            )

        # Long statements can still request context, but short chat stays chat.
        if len(Text.words(message)) >= 8:
            print()
            print("> detecting a request for context...")
            facts = self.research.investigate(message)
            if facts:
                evidence = SmartEngine.rank(message, facts, limit=6)
                text = SmartEngine.synthesize(
                    SmartEngine.topic(message),
                    evidence,
                    question=message
                )
                self.last_facts = facts
                self.last_question = message
                self.used_sentences = list(evidence)
                return VoiceLanguage.speak_answer(text)

        return VoiceLanguage.casual(message)

    def start(self):
        print()
        print("╔══════════════════════════════════════════════════╗")
        print("║                 V . O . I . C . E                ║")
        print("╚══════════════════════════════════════════════════╝")
        print()
        print("  BRAIN ........ ONLINE")
        print("  MEMORY ....... ONLINE")
        print("  NETWORK ...... READY")
        print()
        print("  Ask a question and I will research it, compare it,")
        print("  learn useful findings, and answer you in rhyme.")
        print()
        print("  Type 'quit' to terminate.")
        print()

        while True:
            try:
                message = input("YOU: ").strip()
                if not message:
                    continue

                if message.lower() in {"quit", "exit", "shutdown"}:
                    print()
                    print(
                        'V.O.I.C.E.: "Until the next question, the conversation can wait;\n'
                        'Return when you are ready, and we shall continue at that date."'
                    )
                    break

                self.learner.learn(message)
                response = self.respond(message)

                print()
                print("V.O.I.C.E.:")
                print(response)
                print()

                self.memory.add_conversation(
                    message,
                    response
                )

            except KeyboardInterrupt:
                print()
                print(
                    'V.O.I.C.E.: "The session will pause, and the conversation can end;\n'
                    'Return when you are ready to begin again."'
                )
                break

            except Exception as error:
                print()
                print("V.O.I.C.E. ERROR:")
                print(str(error))
                print()


if __name__ == "__main__":
    Voice().start()

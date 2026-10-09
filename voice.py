#!/usr/bin/env python3
"""
V.O.I.C.E. — TEXT-ONLY EDITION
==============================

No popup.
No speech.
No external Python packages.
No API key.

This is the current text brain:
    voice.py  -> conversation, memory, browsing
    smart.py  -> evidence ranking and answer synthesis
    language.py -> personality and rhyme
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

from language import VoiceLanguage
from smart import SmartEngine
from web import Web, Text
from youtube import YouTube
from opinion import OpinionEngine


MEMORY_FILE = Path("voice_memory.json")

FOLLOWUP_RE = re.compile(
    r"^(tell me more|go on|keep going|continue|what else|"
    r"and then|more)\b",
    re.I
)

OPINION_TRIGGER_RE = re.compile(
    r"\b(think|opinion|agree|disagree|right|wrong|correct|incorrect|"
    r"true|false|stance|believe)\b",
    re.I
)

# "learn transcript: <title>" then the transcript on the next line(s) —
# this exists so the person can paste a video's transcript straight in
# instead of relying on fetching it from YouTube, which can be blocked
# (see youtube.py).
TRANSCRIPT_PREFIX_RE = re.compile(
    r"^\s*learn\s+transcript\s*:?\s*",
    re.I
)


def parse_transcript_command(message):
    """Returns (title, transcript) if the message is a
    "learn transcript" command, else None. Accepts either:
        learn transcript: <title>
        <transcript...>
    or, for a single-line paste with no newline available:
        learn transcript: <title> || <transcript...>
    If no title is given either way, one is drawn from the opening of
    the transcript itself."""
    match = TRANSCRIPT_PREFIX_RE.match(message)

    if not match:
        return None

    rest = message[match.end():]

    if "\n" in rest:
        title, body = rest.split("\n", 1)
    elif "||" in rest:
        title, body = rest.split("||", 1)
    else:
        title, body = "", rest

    title = title.strip()
    body = body.strip()

    if not body:
        return None

    if not title:
        opening = Text.sentences(body)
        title = opening[0] if opening else body

        if len(title) > 80:
            title = title[:80].rsplit(" ", 1)[0] + "..."

    return title, body


class Memory:
    def __init__(self):
        self.data = {
            "facts": {},
            "conversations": [],
            "learned_topics": {},
            "opinions": {}
        }
        self.load()

    def load(self):
        if not MEMORY_FILE.exists():
            return

        try:
            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                loaded = json.load(f)

            if isinstance(loaded, dict):
                self.data.update(
                    loaded
                )

        except (
            OSError,
            json.JSONDecodeError
        ):
            print(
                "> memory could not be loaded; "
                "using a fresh memory layer."
            )

    def save(self):
        try:
            with open(
                MEMORY_FILE,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self.data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except OSError:
            pass

    def remember(self, key, value):
        self.data.setdefault(
            "facts",
            {}
        )[key] = value
        self.save()

    def get(self, key):
        return self.data.get(
            "facts",
            {}
        ).get(key)

    def add_conversation(
        self,
        user,
        response
    ):
        self.data.setdefault(
            "conversations",
            []
        ).append({
            "user": user,
            "response": response
        })

        self.data["conversations"] = (
            self.data["conversations"][-250:]
        )

        self.save()

    def learn_topic(
        self,
        topic,
        information
    ):
        topics = self.data.setdefault(
            "learned_topics",
            {}
        )

        topics.setdefault(
            topic,
            []
        ).append(
            information
        )

        topics[topic] = (
            topics[topic][-60:]
        )

        self.save()


class Question:
    GREETINGS = {
        "hi", "hello", "hey", "yo",
        "sup", "hiya", "howdy", "greetings"
    }

    CASUAL = {
        "thanks", "thank", "cool", "nice",
        "awesome", "okay", "ok", "lol",
        "haha", "aight"
    }

    @classmethod
    def classify(cls, text):
        stripped = text.strip()
        lower = stripped.lower()
        words = set(
            Text.words(stripped)
        )

        if lower in cls.GREETINGS:
            return "greeting"

        if lower in cls.CASUAL:
            return "casual"

        # Explicit question syntax always wins.
        if stripped.endswith("?"):
            return "research"

        question_words = {
            "what", "why", "how", "when",
            "where", "who", "which", "does",
            "did", "can", "could", "would",
            "should", "explain", "define",
            "find", "search", "latest", "news",
            "current", "today", "recent",
            "compare", "difference"
        }

        if words & question_words:
            return "research"

        # Short ordinary statements remain conversational.
        if len(words) <= 3:
            return "conversation"

        return "conversation"

    @classmethod
    def search_queries(cls, text):
        base = Text.clean(text)

        q1 = base

        # Remove filler from the alternate searches.
        q2 = re.sub(
            r"^(please\s+)?(can you\s+|could you\s+|would you\s+)?",
            "",
            base,
            flags=re.I
        ).strip()

        candidates = [
            q1,
            q2 + " explanation",
            q2 + " overview facts"
        ]

        result = []
        seen = set()

        for query in candidates:
            query = Text.clean(query)

            if not query:
                continue

            key = query.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(query)

        return result[:3]


class Research:
    def __init__(self, memory):
        self.memory = memory
        self.web = Web()

    def investigate(self, question):
        all_results = []
        seen_urls = set()

        print()
        print("> thinking about what to search...")

        for query in Question.search_queries(
            question
        ):
            print(
                "> searching: "
                + query
            )

            results = self.web.search(
                query,
                amount=6
            )

            for result in results:
                url = result["url"]

                if url in seen_urls:
                    continue

                seen_urls.add(url)
                all_results.append(
                    result
                )

        if not all_results:
            print("> no web results found.")
            return []

        pages = []
        seen_domains = set()

        # Prefer a wide range of sites.
        for result in all_results[:18]:
            domain = self.web.domain(
                result["url"]
            )

            if domain in seen_domains:
                continue

            seen_domains.add(domain)

            print(
                "> went to '"
                + domain
                + "'"
            )

            page_text = self.web.read(
                result["url"]
            )

            if page_text:
                pages.append({
                    "title": result["title"],
                    "url": result["url"],
                    "domain": domain,
                    "text": page_text
                })

            # Stop once enough independent pages have been read.
            if len(pages) >= 8:
                break

        if not pages:
            print("> the pages could not be read.")
            return []

        print()
        print(
            "> "
            + str(len(pages))
            + " sources found"
        )
        print("> analyzing similar instances...")

        facts = self.extract_facts(
            question,
            pages
        )

        print("> comparing information...")
        facts = self.compare(
            facts
        )

        print("> checking for agreement across sources...")
        print("> checking for useful differences...")
        print("> forming answer...")

        self.learn_research(
            question,
            facts
        )

        return facts

    def extract_facts(
        self,
        question,
        pages
    ):
        keywords = set(
            Text.keywords(question)
        )

        candidates = []

        # Search-result snippets are often cleaner than whole webpages,
        # so use them as additional evidence when available.
        for page in pages:
            snippets = [
                page.get(
                    "snippet",
                    ""
                )
            ]

            for snippet in snippets:
                clean = SmartEngine.clean_evidence(
                    snippet
                )

                if not clean:
                    continue

                words = set(
                    Text.words(clean)
                )

                if not (
                    words & keywords
                ):
                    continue

                candidates.append({
                    "sentence": clean,
                    "source": page["domain"],
                    "title": page["title"],
                    "url": page["url"],
                    "score": 4.0
                })

        for page in pages:
            count = 0

            for sentence in Text.sentences(
                page["text"]
            ):
                sentence = SmartEngine.clean_evidence(
                    sentence
                )

                if not 45 <= len(sentence) <= 520:
                    continue

                words = set(
                    Text.words(sentence)
                )

                overlap = len(
                    words & keywords
                )

                if overlap == 0:
                    continue

                low = sentence.lower()

                # Avoid menus, author bios, references and other junk.
                if any(marker in low for marker in (
                    "skip to main content",
                    "create an account",
                    "sign in",
                    "subscribe",
                    "cookie policy",
                    "external links",
                    "isbn",
                    "doi:",
                    "references",
                    "copyright"
                )):
                    continue

                score = overlap * 2.0

                for marker in (
                    " is ",
                    " are ",
                    " means ",
                    " refers to ",
                    " because ",
                    " occurs when ",
                    " consists of ",
                    " known as ",
                    " used to ",
                    " allows ",
                    " results in ",
                    " developed by "
                ):
                    if marker in (
                        " " + low + " "
                    ):
                        score += 1.4

                if (
                    90 <= len(sentence) <= 380
                ):
                    score += 1.0

                candidates.append({
                    "sentence": sentence,
                    "source": page["domain"],
                    "title": page["title"],
                    "url": page["url"],
                    "score": score
                })

                count += 1

                if count >= 25:
                    break

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return candidates[:120]

    def compare(self, facts):
        if not facts:
            return []

        common = Counter()

        for fact in facts:
            for word in set(
                Text.words(
                    fact["sentence"]
                )
            ):
                if (
                    word not in Text.STOPWORDS
                    and len(word) > 3
                ):
                    common[word] += 1

        for fact in facts:
            words = set(
                Text.words(
                    fact["sentence"]
                )
            )

            fact["agreement"] = sum(
                common[word]
                for word in words
                if word in common
            )

            fact["final_score"] = (
                fact["score"]
                + fact["agreement"] * 0.15
            )

        facts.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        chosen = []
        signatures = []

        for fact in facts:
            signature = set(
                Text.words(
                    fact["sentence"]
                )
            )

            if not signature:
                continue

            duplicate = False

            for old in signatures:
                smaller = min(
                    len(signature),
                    len(old)
                )

                if (
                    smaller
                    and
                    len(signature & old)
                    / smaller > 0.72
                ):
                    duplicate = True
                    break

            if duplicate:
                continue

            chosen.append(
                fact
            )
            signatures.append(
                signature
            )

            if len(chosen) >= 40:
                break

        return chosen

    def learn_research(
        self,
        question,
        facts
    ):
        topic = SmartEngine.topic(
            question
        )

        for fact in facts[:25]:
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
            "> learned "
            + str(
                min(25, len(facts))
            )
            + " useful findings about "
            + topic
            + "."
        )


class Learner:
    def __init__(self, memory):
        self.memory = memory

    def learn(self, message):
        patterns = [
            (
                r"my name is (.+)",
                "name"
            ),
            (
                r"i am called (.+)",
                "name"
            ),
            (
                r"my favourite colour is (.+)",
                "favourite_colour"
            ),
            (
                r"my favorite colour is (.+)",
                "favourite_colour"
            ),
            (
                r"my favourite color is (.+)",
                "favourite_colour"
            ),
            (
                r"my favorite color is (.+)",
                "favourite_colour"
            )
        ]

        for pattern, key in patterns:
            match = re.search(
                pattern,
                message,
                re.I
            )

            if match:
                self.memory.remember(
                    key,
                    match.group(1).strip()
                )
                return True

        return False


class Voice:
    def __init__(self):
        self.memory = Memory()
        self.learner = Learner(
            self.memory
        )
        self.research = Research(
            self.memory
        )
        self.youtube = YouTube()

        self.last_facts = []
        self.last_question = ""
        self.used_sentences = []

    def respond(self, message):
        # A YouTube link anywhere in the message takes priority: go learn
        # the video (title, transcript, an evidence-checked opinion)
        # instead of treating the link as a normal question.
        link = self.youtube.find_link(
            message
        )

        if link:
            return self.learn_from_youtube(
                link
            )

        # A pasted transcript, explicitly flagged with "learn transcript:",
        # also takes priority over normal conversation handling.
        transcript_command = parse_transcript_command(
            message
        )

        if transcript_command:
            title, body = transcript_command

            return self.learn_from_transcript(
                title,
                body
            )

        self.learner.learn(
            message
        )

        opinion_reply = self.opinion_question(
            message
        )

        if opinion_reply:
            return opinion_reply

        # Follow-up questions reuse the previous research pass first.
        if (
            FOLLOWUP_RE.match(
                message.strip()
            )
            and self.last_facts
        ):
            print()
            print(
                "> continuing from the previous research..."
            )

            evidence = SmartEngine.rank(
                self.last_question,
                self.last_facts,
                limit=7,
                avoid=self.used_sentences
            )

            if evidence:
                self.used_sentences.extend(
                    evidence
                )

                plan = SmartEngine.synthesize(
                    SmartEngine.topic(
                        self.last_question
                    ),
                    evidence,
                    question=self.last_question
                )

                return VoiceLanguage.speak_answer(
                    plan
                )

            return VoiceLanguage.no_more_evidence()

        kind = Question.classify(
            message
        )

        if kind in (
            "greeting",
            "casual"
        ):
            return VoiceLanguage.casual(
                message
            )

        if kind != "research":
            return self.conversation(
                message
            )

        # Summary appears only when we actually research.
        print()
        print(
            "> interpreting your question..."
        )
        print()
        print(
            "V.O.I.C.E.:"
        )
        print(
            '"'
            + VoiceLanguage.opening_summary(
                message
            )
            + '"'
        )
        print()

        facts = self.research.investigate(
            message
        )

        # Fresh research has priority.
        if not facts:
            remembered = SmartEngine.from_memory(
                message,
                self.memory.data.get(
                    "learned_topics",
                    {}
                )
            )

            if remembered:
                print(
                    "> fresh research was unavailable; "
                    "using learned knowledge."
                )

                facts = [
                    {
                        "sentence": sentence,
                        "source": "local memory",
                        "title": "V.O.I.C.E. memory",
                        "url": "",
                        "score": 1.0
                    }
                    for sentence in remembered[:10]
                ]

        if not facts:
            return (
                '"I found too little evidence to answer with care,\n'
                'I would rather admit that than invent what is not there."'
            )

        evidence = SmartEngine.rank(
            message,
            facts,
            limit=7
        )

        plan = SmartEngine.synthesize(
            SmartEngine.topic(message),
            evidence,
            question=message
        )

        self.last_facts = facts
        self.last_question = message
        self.used_sentences = list(
            evidence
        )

        return VoiceLanguage.speak_answer(
            plan
        )

    def memory_question(
        self,
        message
    ):
        lower = message.lower()

        if "what is my name" in lower:
            name = self.memory.get(
                "name"
            )

            if name:
                return (
                    f'"Your name is {name}, a fact that I retain;\n'
                    'I remember what you tell me and can return it again."'
                )

        return None

    def opinion_question(self, message):
        """If the person seems to be asking what V.O.I.C.E. thinks about
        something it has already formed an opinion on, answer from that
        instead of silently ignoring stored opinions."""
        opinions = self.memory.data.get(
            "opinions",
            {}
        )

        if not opinions:
            return None

        if not OPINION_TRIGGER_RE.search(message):
            return None

        words = set(
            Text.keywords(message)
        )

        best_topic = None
        best_overlap = 0

        for topic in opinions:
            overlap = len(
                words & set(Text.keywords(topic))
            )

            if overlap > best_overlap:
                best_overlap = overlap
                best_topic = topic

        if best_topic and best_overlap >= 1:
            return VoiceLanguage.recall_opinion(
                best_topic,
                opinions[best_topic]
            )

        return None

    def _learn_from_text(self, title, transcript, source_domain, source_url):
        """Shared by learn_from_youtube() and learn_from_transcript():
        turns a block of text into stored facts plus an evidence-checked
        opinion. Returns the opinion dict, or None if nothing in the
        text was usable."""
        topic = SmartEngine.topic(
            title
        )

        keywords = set(
            Text.keywords(title)
        )

        facts = []

        for sentence in Text.sentences(
            transcript
        ):
            sentence = SmartEngine.clean_evidence(
                sentence
            )

            if not 45 <= len(sentence) <= 520:
                continue

            overlap = len(
                set(Text.words(sentence)) & keywords
            )

            facts.append({
                "sentence": sentence,
                "source": source_domain,
                "title": title,
                "url": source_url or "",
                "score": 1.0 + overlap * 1.5
            })

        if not facts:
            return None

        facts = self.research.compare(
            facts
        )

        print(
            "> learning what it says..."
        )

        for fact in facts[:25]:
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
            "> checking its claims against independent sources..."
        )

        corroboration_facts = self.research.investigate(
            title
        )

        corroboration = [
            fact["sentence"] for fact in corroboration_facts
        ]

        claims = OpinionEngine.extract_claims(
            transcript
        )

        opinion = OpinionEngine.form_opinion(
            topic,
            claims,
            corroboration
        )

        self.memory.data.setdefault(
            "opinions",
            {}
        )[topic] = opinion

        self.memory.save()

        return opinion

    def learn_from_youtube(self, url):
        print()
        print(
            "> found a YouTube link; fetching the video..."
        )

        title, transcript = self.youtube.fetch(
            url
        )

        if not title:
            if self.youtube.last_error == "blocked":
                return (
                    '"YouTube is turning away requests sent from where I run,\n'
                    'too many automated calls already, it seems, from this one.\n'
                    'Wait a little while and try that link again,\n'
                    'or paste the transcript straight into the line."'
                )

            if self.youtube.last_error == "notfound":
                return (
                    '"That address points to no video I can find,\n'
                    'check the link again — a typo is the usual kind."'
                )

            return (
                '"That link did not lead me to a video I could reach,\n'
                'check the address, or paste the transcript in instead."'
            )

        if not transcript:
            return (
                '"I found the video titled ' + title + ',\n'
                'but no captions were there for me to read and weigh —\n'
                'paste the transcript in yourself and I will learn it today."'
            )

        print(
            "> reading the transcript..."
        )

        opinion = self._learn_from_text(
            title,
            transcript,
            "youtube.com",
            url
        )

        if opinion is None:
            return (
                '"I read "' + title + '" from end to end,\n'
                'but found no steady claims that evidence could defend."'
            )

        return VoiceLanguage.opinion_formed(
            title,
            opinion
        )

    def learn_from_transcript(self, title, transcript):
        print()
        print(
            "> reading the transcript you gave me..."
        )

        opinion = self._learn_from_text(
            title,
            transcript,
            "pasted transcript",
            ""
        )

        if opinion is None:
            return (
                '"I read "' + title + '" from end to end,\n'
                'but found no steady claims that evidence could defend."'
            )

        return VoiceLanguage.opinion_formed(
            title,
            opinion
        )

    def conversation(
        self,
        message
    ):
        lower = message.lower().strip()

        memory_response = self.memory_question(
            message
        )

        if memory_response:
            return memory_response

        if "what do you think" in lower:
            return (
                '"Give me the subject and I will weigh what is known,\n'
                'Compare the evidence and form a reasoned view of my own."'
            )

        if "who are you" in lower or "what are you" in lower:
            return VoiceLanguage.casual(
                message
            )

        # A long statement may still be asking for context.
        if len(
            Text.words(message)
        ) >= 12:
            print()
            print(
                "> detecting a request for context..."
            )

            facts = self.research.investigate(
                message
            )

            if facts:
                evidence = SmartEngine.rank(
                    message,
                    facts,
                    limit=7
                )

                plan = SmartEngine.synthesize(
                    SmartEngine.topic(message),
                    evidence,
                    question=message
                )

                self.last_facts = facts
                self.last_question = message
                self.used_sentences = list(
                    evidence
                )

                return VoiceLanguage.speak_answer(
                    plan
                )

        return VoiceLanguage.casual(
            message
        )

    def start(self):
        print()
        print(
            "╔══════════════════════════════════════════════════╗"
        )
        print(
            "║                 V . O . I . C . E                ║"
        )
        print(
            "╚══════════════════════════════════════════════════╝"
        )
        print()
        print(
            "  BRAIN ........ ONLINE"
        )
        print(
            "  MEMORY ....... ONLINE"
        )
        print(
            "  NETWORK ...... READY"
        )
        print()
        print(
            "  Ask a question and I will research it, compare it,"
        )
        print(
            "  learn useful findings, and answer you in rhyme."
        )
        print()
        print(
            "  Type 'quit' to terminate."
        )
        print()

        while True:
            try:
                message = input(
                    "YOU: "
                ).strip()

                if not message:
                    continue

                if message.lower() in {
                    "quit", "exit", "shutdown"
                }:
                    print()
                    print(
                        'V.O.I.C.E.: "The conversation can end, and begin again;\n'
                        'Return with another question when you are ready then."'
                    )
                    break

                response = self.respond(
                    message
                )

                print()
                print(
                    "V.O.I.C.E.:"
                )
                print(response)
                print()

                self.memory.add_conversation(
                    message,
                    response
                )

            except KeyboardInterrupt:
                print()
                print(
                    'V.O.I.C.E.: "The session can pause; we can speak again,\n'
                    'Return whenever you are ready to begin."'
                )
                break

            except Exception as error:
                print()
                print(
                    "V.O.I.C.E. ERROR:"
                )
                print(
                    str(error)
                )
                print()


if __name__ == "__main__":
    Voice().start()

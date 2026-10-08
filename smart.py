"""
V.O.I.C.E. SMART LAYER
----------------------
Local research reasoning with no API/model.

The goal is to:
- understand the question type
- clean web text
- rank relevant evidence
- prefer definitions/explanations over navigation
- diversify across sources
- synthesize an answer plan
- reuse local memory when useful

The smart layer produces factual prose.
language.py turns that prose into V.O.I.C.E. rhyme.
"""

import math
import re
from collections import Counter


class SmartEngine:
    STOP = {
        "the","a","an","and","or","of","to","in","on","for",
        "is","are","was","were","be","been","being","with","as",
        "by","that","this","it","its","from","at","which","who",
        "what","when","where","why","how","can","could","would",
        "should","will","shall","do","does","did","has","have","had",
        "not","but","than","then","so","such","also","into","about",
        "over","under","between","through","tell","me","please","my","your",
        "explain","describe","definition","meaning","means"
    }

    JUNK_MARKERS = (
        "skip to main content", "create an account", "sign in",
        "subscribe", "newsletter", "cookie policy", "external links",
        "related entries", "share this", "previous next",
        "table of contents", "edit source", "jump to",
    )

    @classmethod
    def _words(cls, text):
        return [
            w for w in re.findall(r"[a-zA-Z']+", text.lower())
            if w not in cls.STOP and len(w) > 2
        ]

    @staticmethod
    def _cosine(a, b):
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        if not common:
            return 0.0
        dot = sum(a[w] * b[w] for w in common)
        ma = math.sqrt(sum(v * v for v in a.values()))
        mb = math.sqrt(sum(v * v for v in b.values()))
        if not ma or not mb:
            return 0.0
        return dot / (ma * mb)

    @classmethod
    def clean_evidence(cls, sentence):
        s = str(sentence)
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"\[[0-9]+\]", " ", s)
        s = re.sub(r"\{\{.*?\}\}", " ", s)
        s = re.sub(r"</?ref[^>]*>", " ", s, flags=re.I)
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(
            r"\|\s*(last|first|year|title|publisher|location|volume|pages)\s*=.*",
            " ", s, flags=re.I
        )
        s = re.sub(r"\s+", " ", s).strip()
        low = s.lower()

        if any(marker in low for marker in cls.JUNK_MARKERS):
            return ""

        # Search-engine/wiki detritus often carries raw source markup.
        if "x research source" in low or "edit]" in low:
            return ""

        # A sentence dominated by pipes/brackets is almost certainly metadata.
        if s.count("|") >= 2 or s.count("}}") >= 1:
            return ""

        return s.strip(" -:;,.\"'")

    @classmethod
    def question_type(cls, question):
        q = question.lower().strip()

        if re.match(r"^(what is|what are|define|meaning of)\b", q):
            return "definition"
        if re.match(r"^(why|what causes|what caused)\b", q):
            return "cause"
        if re.match(r"^(how does|how do|how is|how are|how can)\b", q):
            return "process"
        if any(x in q for x in (
            "difference between", "compare", "versus", " vs "
        )):
            return "comparison"
        if re.match(r"^(who is|who was|who are)\b", q):
            return "person"
        if re.match(r"^(when did|when was|when is)\b", q):
            return "time"
        if re.match(r"^(where is|where was|where are)\b", q):
            return "place"
        return "general"

    @classmethod
    def topic(cls, question):
        q = question.lower()

        known = [
            ("quantum mechanics", "quantum mechanics"),
            ("quantum physics", "quantum physics"),
            ("black hole", "black holes"),
            ("artificial intelligence", "artificial intelligence"),
            ("machine learning", "machine learning"),
            ("electricity", "electricity"),
            ("mathematics", "mathematics"),
            ("maths", "mathematics"),
            ("math", "mathematics"),
            ("photosynthesis", "photosynthesis"),
            ("gravity", "gravity"),
            ("programming", "programming"),
        ]

        for needle, name in known:
            if needle in q:
                return name

        words = re.findall(r"[a-zA-Z][a-zA-Z'-]+", q)
        useful = [
            w for w in words
            if w.lower() not in cls.STOP
        ]
        return " ".join(useful[:7]) or "this subject"

    @classmethod
    def _centrality(cls, vectors):
        n = len(vectors)
        if not n:
            return []

        sim = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j:
                    sim[i][j] = cls._cosine(vectors[i], vectors[j])

        out_sum = [
            sum(row) or 1.0
            for row in sim
        ]

        scores = [1.0 / n] * n

        for _ in range(10):
            scores = [
                0.15 / n
                + 0.85 * sum(
                    (sim[j][i] / out_sum[j]) * scores[j]
                    for j in range(n)
                    if j != i
                )
                for i in range(n)
            ]

        return scores

    @classmethod
    def rank(cls, question, facts, limit=6, avoid=None):
        q_vector = Counter(
            cls._words(question)
        )

        pool = []

        for fact in facts:
            sentence = cls.clean_evidence(
                fact.get("sentence", "")
            )

            if not 45 <= len(sentence) <= 650:
                continue

            pool.append({
                "sentence": sentence,
                "base": float(
                    fact.get(
                        "final_score",
                        fact.get("score", 0)
                    )
                ),
                "source": fact.get("source", ""),
                "title": fact.get("title", "")
            })

        if not pool:
            return []

        vectors = [
            Counter(cls._words(item["sentence"]))
            for item in pool
        ]

        centrality = cls._centrality(vectors)

        avoid_vectors = [
            Counter(cls._words(text))
            for text in (avoid or [])
        ]

        explanation_markers = (
            " is ", " are ", " means ", " refers to ",
            " because ", " occurs ", " consists of ",
            " used to ", " allows ", " causes ",
            " results in ", " known as ", " defined as ",
            " happens when ", " unlike ", " whereas "
        )

        kind = cls.question_type(question)
        topic = cls.topic(question)

        for item, vec, cen in zip(
            pool, vectors, centrality
        ):
            sentence = item["sentence"]
            low = " " + sentence.lower() + " "

            relevance = cls._cosine(
                vec,
                q_vector
            )

            explanation = sum(
                0.8 for marker in explanation_markers
                if marker in low
            )

            # Topic presence matters more than accidental common words.
            topic_overlap = len(
                set(cls._words(topic))
                & set(cls._words(sentence))
            )

            topic_bonus = topic_overlap * 1.15

            definition_bonus = 0.0
            if kind == "definition":
                if re.search(
                    r"\b" + re.escape(topic) +
                    r"\s+(?:is|are|refers to|means)\b",
                    sentence,
                    flags=re.I
                ):
                    definition_bonus += 5.0

                if sentence.lower().startswith(
                    topic.lower() + " is"
                ):
                    definition_bonus += 3.0

            junk = 0.0

            if any(marker in low for marker in (
                "isbn", "doi:", "publisher", "references"
            )):
                junk += 4.0

            repeat = 2.0 * max(
                (
                    cls._cosine(
                        vec,
                        av
                    )
                    for av in avoid_vectors
                ),
                default=0.0
            )

            item["vector"] = vec
            item["score"] = (
                item["base"] * 0.35
                + relevance * 3.2
                + cen * 2.7
                + explanation
                + topic_bonus
                + definition_bonus
                - junk
                - repeat
            )

        pool.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        selected = []
        used_sources = set()

        # MMR + source diversity.
        while pool and len(selected) < limit:
            best = None
            best_score = float("-inf")

            for item in pool:
                redundancy = max(
                    (
                        cls._cosine(
                            item["vector"],
                            old["vector"]
                        )
                        for old in selected
                    ),
                    default=0.0
                )

                source_bonus = (
                    0.45
                    if (
                        item["source"]
                        and item["source"] not in used_sources
                    )
                    else 0.0
                )

                mmr = (
                    0.80 * item["score"]
                    - 0.20 * redundancy
                    + source_bonus
                )

                if mmr > best_score:
                    best = item
                    best_score = mmr

            selected.append(best)

            if best["source"]:
                used_sources.add(
                    best["source"]
                )

            pool.remove(best)

        return [
            item["sentence"]
            for item in selected
        ]

    @classmethod
    def _definition_clause(cls, topic, evidence):
        """
        Prefer an explicit definition such as:
            Mathematics is the study of...
        over an arbitrary sentence that merely mentions mathematics.
        """
        topic_pattern = re.escape(topic)

        candidates = []

        definition_quality = (
            "study", "understanding", "patterns", "structure",
            "numbers", "quantities", "relationships", "system",
            "process", "field", "branch", "discipline"
        )

        for sentence in evidence:
            s = cls.clean_evidence(sentence)
            if not s:
                continue

            explicit = re.search(
                r"\b" + topic_pattern +
                r"\s+(?:is|are|refers to|means)\s+(.+)",
                s,
                flags=re.I
            )

            if explicit:
                clause = explicit.group(1)

                clause = re.split(
                    r"\b(?:It also|It is also|Today|For example|According to)\b",
                    clause,
                    maxsplit=1,
                    flags=re.I
                )[0]

                clause = clause.strip(" .,:;")

                if 20 <= len(clause) <= 300:
                    quality = sum(
                        2 if term in clause.lower() else 0
                        for term in definition_quality
                    )

                    # Prefer actual definition wording over sentences that
                    # merely happen to start with "topic is".
                    penalty = 0
                    if any(
                        word in clause.lower()
                        for word in (
                            "widely used", "important because",
                            "essential in", "used throughout"
                        )
                    ):
                        penalty += 4

                    candidates.append(
                        (quality - penalty, clause)
                    )

        if candidates:
            candidates.sort(
                key=lambda item: (item[0], -len(item[1])),
                reverse=True
            )
            return candidates[0][1]

        # Fallback: choose a sentence that actually discusses the topic
        # and contains explanatory language.
        topic_words = set(
            cls._words(topic)
        )

        fallback = []

        for sentence in evidence:
            s = cls.clean_evidence(sentence)
            words = set(cls._words(s))

            if not topic_words & words:
                continue

            explanation = sum(
                marker in (" " + s.lower() + " ")
                for marker in (
                    " is ", " are ", " means ",
                    " refers to ", " studies ",
                    " describes "
                )
            )

            fallback.append(
                (-explanation, len(s), s)
            )

        if fallback:
            fallback.sort()
            return fallback[0][2].rstrip(" .")

        return (
            "the subject described by the strongest "
            "available evidence"
        )

    @classmethod
    def synthesize(cls, topic, evidence, question=None):
        if not evidence:
            return ""

        question = question or topic
        kind = cls.question_type(question)

        ranked = cls.rank(
            question,
            [
                {
                    "sentence": sentence,
                    "score": 1.0,
                    "source": "research"
                }
                for sentence in evidence
            ],
            limit=6
        )

        if not ranked:
            return ""

        if kind == "definition":
            lead = (
                f"{topic.capitalize()} is "
                + cls._definition_clause(
                    topic,
                    ranked
                )
            )

            # Add useful breadth: branch/use/application sentences.
            extras = [
                s for s in ranked
                if any(
                    x in s.lower()
                    for x in (
                        "branch", "area", "used in",
                        "application", "science",
                        "engineering", "problem-solving",
                        "patterns", "structures"
                    )
                )
            ]

        elif kind == "cause":
            cause = next(
                (
                    s for s in ranked
                    if any(
                        x in s.lower()
                        for x in (
                            "because", "causes", "caused",
                            "results", "leads to", "due to"
                        )
                    )
                ),
                ranked[0]
            )

            lead = (
                f"The main explanation for {topic} is "
                + cause
            )
            extras = ranked[1:]

        elif kind == "process":
            lead = (
                f"The basic process behind {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        elif kind == "comparison":
            lead = (
                f"The important comparison involving {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        elif kind == "person":
            lead = (
                f"The clearest account of {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        elif kind == "time":
            lead = (
                f"The clearest timeline for {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        elif kind == "place":
            lead = (
                f"The clearest location information for {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        else:
            lead = (
                f"The clearest answer about {topic} is "
                + ranked[0]
            )
            extras = ranked[1:]

        pieces = [lead]

        for sentence in extras[:3]:
            clean = cls.clean_evidence(sentence)

            if not clean:
                continue

            # Avoid adding a detail that is essentially the same sentence.
            if clean.lower() in lead.lower():
                continue

            if len(clean) > 280:
                clean = clean[:277].rsplit(" ", 1)[0] + "..."

            pieces.append(clean)

        return " || ".join(pieces)

    @classmethod
    def answer(cls, question, facts, avoid=None):
        evidence = cls.rank(
            question,
            facts,
            limit=8,
            avoid=avoid
        )
        return cls.synthesize(
            cls.topic(question),
            evidence,
            question=question
        )

    @classmethod
    def from_memory(cls, question, learned_topics):
        if not learned_topics:
            return []

        q_vector = set(
            cls._words(question)
        )

        candidates = []

        for topic, entries in learned_topics.items():
            topic_words = set(
                cls._words(topic)
            )

            overlap = len(
                q_vector & topic_words
            )

            if overlap == 0:
                continue

            for entry in entries:
                if isinstance(entry, dict):
                    sentence = entry.get(
                        "sentence",
                        ""
                    )
                else:
                    sentence = str(entry)

                sentence = cls.clean_evidence(
                    sentence
                )

                if sentence:
                    candidates.append(
                        (overlap, sentence)
                    )

        candidates.sort(
            key=lambda item: (
                item[0],
                len(item[1])
            ),
            reverse=True
        )

        result = []
        seen = set()

        for _, sentence in candidates:
            key = sentence.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(sentence)

            if len(result) >= 12:
                break

        return result

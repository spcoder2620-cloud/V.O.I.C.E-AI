"""
V.O.I.C.E. SMART LAYER

Turns web evidence and local memory into a compact, question-focused answer.
Stdlib only: no model/API is required.
"""

import math
import re
from collections import Counter


class SmartEngine:
    STOP = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
        "is", "are", "was", "were", "be", "been", "being", "with", "as",
        "by", "that", "this", "it", "its", "from", "at", "which", "who",
        "what", "when", "where", "why", "how", "can", "could", "would",
        "should", "will", "shall", "do", "does", "did", "has", "have", "had",
        "not", "but", "than", "then", "so", "such", "also", "into", "about",
        "over", "under", "between", "through", "tell", "me", "please", "my",
        "your"
    }

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

    @staticmethod
    def clean_evidence(sentence):
        s = re.sub(r"<[^>]+>", " ", sentence)
        s = re.sub(r"\[[0-9]+\]", " ", s)
        s = re.sub(r"\{\{.*?\}\}", " ", s)
        s = re.sub(r"</?ref[^>]*>", " ", s, flags=re.I)
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(
            r"\|\s*(last|first|year|title|publisher|location|volume|pages)\s*=.*",
            " ", s, flags=re.I
        )
        s = re.sub(r"\s+", " ", s).strip()

        junk = (
            "skip to main content", "create an account", "sign in",
            "subscribe", "newsletter", "cookie policy", "external links",
            "related entries", "share this", "previous next"
        )
        if any(x in s.lower() for x in junk):
            return ""
        return s.strip(" -:;,.\"")

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
        out_sum = [sum(row) or 1.0 for row in sim]
        scores = [1.0 / n] * n
        for _ in range(12):
            scores = [
                0.15 / n + 0.85 * sum(
                    (sim[j][i] / out_sum[j]) * scores[j]
                    for j in range(n) if j != i
                )
                for i in range(n)
            ]
        return scores

    @classmethod
    def question_type(cls, question):
        q = question.lower().strip()
        if re.match(r"^(what is|what are|define|meaning of)\b", q):
            return "definition"
        if re.match(r"^(why|what causes|what caused)\b", q):
            return "cause"
        if re.match(r"^(how does|how do|how is|how are|how can)\b", q):
            return "process"
        if any(x in q for x in ("difference between", "compare", "versus", " vs ")):
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
            ("photosynthesis", "photosynthesis"),
            ("gravity", "gravity"),
            ("programming", "programming")
        ]
        for needle, name in known:
            if needle in q:
                return name

        words = re.findall(r"[a-zA-Z][a-zA-Z'-]+", q)
        useful = [w for w in words if w.lower() not in cls.STOP]
        return " ".join(useful[:7]) or "this subject"

    @classmethod
    def rank(cls, question, facts, limit=5, avoid=None):
        q_vector = Counter(cls._words(question))
        pool = []

        for fact in facts:
            sentence = cls.clean_evidence(fact.get("sentence", ""))
            if not 45 <= len(sentence) <= 650:
                continue
            pool.append({
                "sentence": sentence,
                "base": float(fact.get("final_score", fact.get("score", 0))),
                "source": fact.get("source", "")
            })

        if not pool:
            return []

        vectors = [Counter(cls._words(x["sentence"])) for x in pool]
        centrality = cls._centrality(vectors)
        avoid_vectors = [Counter(cls._words(a)) for a in (avoid or [])]

        explanation_markers = (
            " is ", " are ", " means ", " refers to ", " because ",
            " occurs ", " consists of ", " used to ", " allows ",
            " causes ", " results in ", " known as ", " defined as ",
            " happens when ", " developed by ", " unlike ", " whereas "
        )

        for p, vec, cen in zip(pool, vectors, centrality):
            relevance = cls._cosine(vec, q_vector)
            low = " " + p["sentence"].lower() + " "
            explanation = sum(0.8 for x in explanation_markers if x in low)
            junk = 2.5 if any(x in low for x in (
                "isbn", "doi:", "publisher", "references", "external links"
            )) else 0.0
            repeat = 2.0 * max(
                (cls._cosine(vec, av) for av in avoid_vectors),
                default=0.0
            )
            p["vector"] = vec
            p["score"] = (
                p["base"] * 0.35 + relevance * 3.2 + cen * 3.2
                + explanation - junk - repeat
            )

        # MMR selection: relevant + different + source diversity.
        pool.sort(key=lambda x: x["score"], reverse=True)
        selected = []
        used_sources = set()

        while pool and len(selected) < limit:
            best = None
            best_score = float("-inf")
            for p in pool:
                redundancy = max(
                    (cls._cosine(p["vector"], s["vector"]) for s in selected),
                    default=0.0
                )
                source_bonus = 0.35 if p["source"] and p["source"] not in used_sources else 0.0
                mmr = 0.78 * p["score"] - 0.22 * redundancy + source_bonus
                if mmr > best_score:
                    best = p
                    best_score = mmr
            selected.append(best)
            if best["source"]:
                used_sources.add(best["source"])
            pool.remove(best)

        return [x["sentence"] for x in selected]

    @classmethod
    def _definition_clause(cls, topic, evidence):
        """Find a clean definition-like clause from the evidence."""
        topic_words = set(cls._words(topic))
        candidates = []

        for sentence in evidence:
            s = cls.clean_evidence(sentence)
            low = s.lower()

            # Look for definition patterns.
            m = re.search(
                r"\b(?:" + re.escape(topic) + r")\s+(?:is|are|refers to|means)\s+(.+)",
                s, flags=re.I
            )
            if m:
                candidates.append(m.group(1).strip(" .,:;"))
                continue

            m = re.search(
                r"(?:is|are|refers to|means)\s+([^.;]{20,280})",
                s, flags=re.I
            )
            if m:
                candidates.append(m.group(1).strip(" .,:;"))
                continue

            if topic_words and len(topic_words & set(cls._words(s))) >= max(1, min(2, len(topic_words))):
                candidates.append(s.rstrip(" ."))

        if candidates:
            clause = candidates[0]
            if len(clause) > 300:
                clause = clause[:297].rsplit(" ", 1)[0] + "..."
            return clause

        return "the subject described by the strongest available evidence"

    @classmethod
    def synthesize(cls, topic, evidence, question=None):
        """Create a concise, answer-shaped set of factual pieces."""
        if not evidence:
            return ""

        question = question or topic
        kind = cls.question_type(question)
        evidence = cls.rank(question, [
            {"sentence": s, "score": 1.0, "source": "research"}
            for s in evidence
        ], limit=5)

        if not evidence:
            return ""

        if kind == "definition":
            lead = f"{topic.capitalize()} is {cls._definition_clause(topic, evidence)}"
        elif kind == "cause":
            causal = next(
                (s for s in evidence if any(x in s.lower() for x in (
                    "because", "causes", "caused", "results", "leads to", "due to"
                ))),
                evidence[0]
            )
            lead = f"The main explanation for {topic} is this: {causal}"
        elif kind == "process":
            lead = f"The basic process behind {topic} is described by the evidence like this: {evidence[0]}"
        elif kind == "comparison":
            lead = f"The important comparison involving {topic} comes down to this: {evidence[0]}"
        elif kind == "person":
            lead = f"The clearest account of {topic} is this: {evidence[0]}"
        elif kind == "time":
            lead = f"The clearest timeline for {topic} begins with this evidence: {evidence[0]}"
        elif kind == "place":
            lead = f"The clearest location information for {topic} is this: {evidence[0]}"
        else:
            lead = f"The clearest answer about {topic} begins here: {evidence[0]}"

        # Add only complementary details; avoid repeating the lead.
        pieces = [lead]
        for sentence in evidence[1:4]:
            if sentence.lower() not in lead.lower():
                pieces.append(sentence)

        # The language layer turns these pieces into rhyme.
        return " || ".join(pieces)

    @classmethod
    def answer(cls, question, facts, avoid=None):
        evidence = cls.rank(question, facts, limit=6, avoid=avoid)
        return cls.synthesize(cls.topic(question), evidence, question=question)

    @classmethod
    def from_memory(cls, question, learned_topics):
        """Retrieve locally learned evidence relevant to the current query."""
        if not learned_topics:
            return []

        q_words = set(cls._words(question))
        candidates = []

        for topic, entries in learned_topics.items():
            topic_words = set(cls._words(topic))
            overlap = len(q_words & topic_words)
            if overlap == 0:
                continue

            for entry in entries:
                if isinstance(entry, dict):
                    sentence = entry.get("sentence", "")
                else:
                    sentence = str(entry)
                sentence = cls.clean_evidence(sentence)
                if sentence:
                    candidates.append((overlap, sentence))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate memory results.
        result = []
        seen = set()
        for _, sentence in candidates:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(sentence)
            if len(result) >= 8:
                break

        return result

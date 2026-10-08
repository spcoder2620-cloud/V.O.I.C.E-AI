"""
V.O.I.C.E. OPINION LAYER
------------------------
Turns a source's claims into a *stated, evidence-weighted* stance —
agree / disagree / uncertain — instead of a random or scripted one.

How it decides:
    1. Pull the assertive (not hedged) sentences out of a source
       (e.g. a video transcript) as candidate "claims".
    2. Compare each claim against independent evidence gathered from
       other web sources on the same topic.
    3. If independent evidence uses agreement language ("confirmed",
       "accurate") and overlaps the claim, that counts as support.
       If it uses contradiction language ("debunked", "false", "no
       evidence"), that counts against it.
    4. The claim with the strongest signal either way becomes the
       opinion; confidence is reported honestly — thin or absent
       corroboration stays "uncertain" / "low confidence" rather than
       pretending to a view the evidence doesn't support.

This is a general evidence-weighing tool, not a fixed ideology: it
works the same way regardless of topic.
"""

import re
from collections import Counter

from smart import SmartEngine


ASSERTIVE_MARKERS = (
    " is ", " are ", " was ", " were ", " proves ", " shows ",
    " means ", " causes ", " always ", " never ", " must ",
    " clearly ", " in fact ", " the truth is ", " actually ",
    " will ", " has ", " have ",
)

AGREEMENT_MARKERS = (
    " confirm", " support", " consistent with", " agrees with",
    " correct", " accurate", " verified", " backed by", " true",
    " proven",
)

CONTRADICTION_MARKERS = (
    " false", " incorrect", " myth", " debunked", " disputed",
    " no evidence", " not true", " contradict", " refute",
    " misleading", " wrong", " unsupported",
)


def _sentences(text):
    chunks = re.split(r"(?:\n+|(?<=[.!?])\s+)", text or "")
    return [
        re.sub(r"\s+", " ", chunk).strip()
        for chunk in chunks
        if chunk.strip()
    ]


class OpinionEngine:
    @classmethod
    def extract_claims(cls, transcript, limit=40):
        """Pull out assertive, declarative sentences a source actually
        commits to, skipping hedged or throwaway lines."""
        claims = []

        for sentence in _sentences(transcript):
            sentence = SmartEngine.clean_evidence(sentence)

            if not 30 <= len(sentence) <= 400:
                continue

            low = " " + sentence.lower() + " "

            if not any(marker in low for marker in ASSERTIVE_MARKERS):
                continue

            claims.append(sentence)

            if len(claims) >= limit:
                break

        return claims

    @classmethod
    def _stance_for_claim(cls, claim, corroboration):
        claim_vector = Counter(SmartEngine._words(claim))

        best_agree = 0.0
        best_disagree = 0.0
        agree_sentence = None
        disagree_sentence = None

        for sentence in corroboration:
            overlap = SmartEngine._cosine(
                claim_vector,
                Counter(SmartEngine._words(sentence))
            )

            if overlap < 0.12:
                continue

            low = " " + sentence.lower() + " "

            if any(marker in low for marker in CONTRADICTION_MARKERS):
                score = overlap + 0.3

                if score > best_disagree:
                    best_disagree = score
                    disagree_sentence = sentence

            elif any(marker in low for marker in AGREEMENT_MARKERS) or overlap > 0.3:
                score = overlap + (
                    0.2 if any(marker in low for marker in AGREEMENT_MARKERS) else 0.0
                )

                if score > best_agree:
                    best_agree = score
                    agree_sentence = sentence

        if best_disagree > best_agree and best_disagree > 0.2:
            return "disagrees", disagree_sentence, best_disagree

        if best_agree > 0.2:
            return "agrees", agree_sentence, best_agree

        return "uncertain", None, 0.0

    @classmethod
    def form_opinion(cls, topic, claims, corroboration):
        """corroboration: sentences gathered from independent sources
        on the same topic (not the source being evaluated)."""
        if not claims:
            return {
                "topic": topic,
                "stance": "uncertain",
                "claim": "",
                "reason": "",
                "confidence": "low",
            }

        results = []

        for claim in claims[:12]:
            stance, reason, score = cls._stance_for_claim(
                claim,
                corroboration
            )
            results.append((score, claim, stance, reason))

        results.sort(key=lambda item: item[0], reverse=True)
        score, claim, stance, reason = results[0]

        if stance == "uncertain" or score < 0.2:
            confidence = "low"
        elif score < 0.45:
            confidence = "medium"
        else:
            confidence = "high"

        return {
            "topic": topic,
            "stance": stance,
            "claim": claim,
            "reason": reason or "",
            "confidence": confidence,
        }

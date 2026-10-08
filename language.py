"""
V.O.I.C.E. LANGUAGE LAYER

Controls HOW V.O.I.C.E. speaks: personality, summaries, greetings,
and rhyme. It does not search the web and does not decide factual content.
"""

import random
import re


class VoiceLanguage:
    """A calm, intelligent, poetic voice. No robot/wire/evil language."""

    @classmethod
    def opening_summary(cls, question: str) -> str:
        q = question.lower().strip()

        if any(x in q for x in ("black hole", "black holes", "singularity")):
            return (
                "You ask what waits beyond where the bright stars cease,\n"
                "Where gravity grows savage and denies the light its release.\n"
                "A question has entered the darker edge of space—\n"
                "I'll search what is known and map that hidden place."
            )

        if any(x in q for x in ("quantum", "particle", "physics")):
            return (
                "You ask where the smallest hidden rules begin,\n"
                "Where certainty grows strange and probability can win.\n"
                "I'll trace what theory and experiment reveal,\n"
                "Then return with the pattern the evidence can seal."
            )

        if any(x in q for x in ("electricity", "energy", "current")):
            return (
                "You seek the force behind the systems that we use,\n"
                "The motion, charge and energy that make the difference clear and true.\n"
                "I'll follow the evidence and separate fact from flame,\n"
                "Then bring back a clearer answer to the question that you name."
            )

        if any(x in q for x in ("mathematics", "math")):
            return (
                "You ask about the language built from pattern, proof and form,\n"
                "Where numbers, structures and relations keep their order through the storm.\n"
                "I'll compare the explanations and reduce them to the core,\n"
                "Then give you the clearest meaning that the evidence has in store."
            )

        return random.choice([
            (
                "Your question seeks an answer that is hidden from the view,\n"
                "So I'll sort through what is known and separate old from new.\n"
                "I'll compare the sources and weigh what they agree,\n"
                "Then shape the strongest answer and return it here to thee."
            ),
            (
                "You have asked a question; now the search can start,\n"
                "I'll sift through information and keep the useful part.\n"
                "The weaker claims will fade while stronger evidence stays,\n"
                "Then I'll return with something clear and worthy of your gaze."
            )
        ])

    @classmethod
    def speak_answer(cls, answer: str) -> str:
        """Render the smart layer's factual answer as rhyming dialogue."""
        if not answer:
            return (
                '"The evidence is too thin for a claim I can defend,\n'
                'Give me another angle and I shall search again."'
            )

        text = re.sub(r"\[[0-9]+\]", "", answer)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"\s+", " ", text).strip().strip('"')

        pieces = [p.strip() for p in text.split("||") if p.strip()]
        if not pieces:
            pieces = [text]

        lines = []

        # Every factual piece gets a rhyming companion line.
        pair_templates = [
            ("{a}.", "That is the central point the evidence has made plain."),
            ("{a}.", "It fits the wider pattern and explains the matter again."),
            ("{a}.", "Together with the evidence, it gives the clearest view."),
            ("{a}.", "The scattered details now connect into something true.")
        ]

        for i, piece in enumerate(pieces[:4]):
            piece = piece.rstrip(" .,:;")
            # Keep individual evidence statements manageable.
            if len(piece) > 320:
                piece = piece[:317].rsplit(" ", 1)[0] + "..."
            left, right = pair_templates[i % len(pair_templates)]
            lines.append(left.format(a=piece))
            lines.append(right)

        lines.extend([
            "The facts provide the substance; the pattern gives it form,",
            "I have weighed what was found and made the answer clear and warm."
        ])

        return '"' + "\n".join(lines) + '"'

    @classmethod
    def casual(cls, message: str) -> str:
        q = message.lower().strip()

        if q in {"hi", "hello", "hey", "yo", "greetings", "hiya", "howdy"}:
            return '"Hello, the question is yours to say,\nTell me what you seek today."'

        if "thank" in q:
            return '"You are welcome; your thanks are understood,\nAsk what you need, and I will help where I could."'

        if "who are you" in q or "what are you" in q:
            return (
                '"I am V.O.I.C.E., built to search and reason,\n'
                'To learn from what I find and answer in verse each season."'
            )

        return (
            '"Your thought is clear; I understand the cue,\n'
            'Continue with the subject and I will work it through with you."'
        )

    @classmethod
    def no_more_evidence(cls) -> str:
        return (
            '"The sources have been used; I have no fresh thread to show,\n'
            'Ask another angle and I can seek a different flow."'
        )

"""
V.O.I.C.E. LANGUAGE LAYER
-------------------------
Controls HOW V.O.I.C.E. speaks.

No popup.
No speech.
No "wire/circuit" or "evil robot" language.
The language layer does not browse the web or decide factual content.
"""

import random
import re


class VoiceLanguage:
    """Calm, intelligent, poetic, and concise."""

    @classmethod
    def opening_summary(cls, question: str) -> str:
        q = question.lower().strip()

        if any(x in q for x in ("black hole", "black holes", "singularity")):
            return (
                "You ask what waits beyond where the bright stars cease,\n"
                "Where gravity grows savage and denies the light its release.\n"
                "I'll search what is known and compare the clues,\n"
                "Then bring back the clearest answer the evidence can choose."
            )

        if any(x in q for x in ("quantum", "particle", "physics")):
            return (
                "You ask where the smallest hidden rules begin,\n"
                "Where certainty grows strange and probability can win.\n"
                "I'll trace what theory and experiment reveal,\n"
                "Then return with the strongest picture the evidence can seal."
            )

        if any(x in q for x in ("electricity", "energy", "current")):
            return (
                "You seek the force behind the systems that we use,\n"
                "The movement, charge and energy that make the difference clear and true.\n"
                "I'll compare what reliable sources explain,\n"
                "Then bring the useful answer back again."
            )

        if any(x in q for x in ("mathematics", "math", "maths")):
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
            ),
        ])

    @classmethod
    def speak_answer(cls, answer: str) -> str:
        """Turn a compact factual plan into a coherent rhyming answer."""
        if not answer:
            return (
                '"The evidence is too thin for a claim I can defend,\n'
                'Give me another angle and I shall search again."'
            )

        text = re.sub(r"\\[[0-9]+\\]", "", answer)
        text = re.sub(r"https?://\\S+", "", text)
        text = re.sub(r"\\s+", " ", text).strip().strip('"')

        pieces = [
            p.strip(" .,:;")
            for p in text.split("||")
            if p.strip()
        ]

        if not pieces:
            pieces = [text]

        topic = pieces[0]
        details = pieces[1:4]

        # Keep the actual researched statement intact, then add short
        # connective lines that rhyme without inventing new facts.
        lines = [topic + "."]

        rhyme_pairs = [
            "That is the central idea, stated clearly and plain.",
            "That is the central idea, and the evidence says the same.",
            "Those details fit together and make the pattern plain."
        ]

        for i, detail in enumerate(details):
            if i == 0:
                lines.append(
                    "It gives a wider picture of the subject you came to explain:"
                )
                lines.append(detail + ".")
            elif i == 1:
                lines.append(
                    "Another part of the evidence extends that view,"
                )
                lines.append(
                    detail + "."
                )
            else:
                lines.append(
                    "And one final point helps the meaning come through:"
                )
                lines.append(
                    detail + "."
                )

        # A restrained ending keeps the answer coherent even though the
        # underlying system has no generative language model.
        lines.append(
            rhyme_pairs[min(len(details), len(rhyme_pairs) - 1)]
        )

        return '"' + "\n".join(lines) + '"'

    @classmethod
    def casual(cls, message: str) -> str:
        q = message.lower().strip()

        if q in {
            "hi", "hello", "hey", "yo",
            "greetings", "hiya", "howdy"
        }:
            return (
                '"Hello, the question is yours to say,\n'
                'Tell me what you seek today."'
            )

        if "thank" in q:
            return (
                '"You are welcome; your thanks are understood,\n'
                'Ask what you need, and I will help where I could."'
            )

        if "who are you" in q or "what are you" in q:
            return (
                '"I am V.O.I.C.E., built to search and reason,\n'
                'To learn from what I find and answer in verse each season."'
            )

        return (
            '"Your thought is clear; I understand the cue,\n'
            'Give me the subject and I will work it through with you."'
        )

    @classmethod
    def no_more_evidence(cls) -> str:
        return (
            '"The sources have been used; I have no fresh thread to show,\n'
            'Ask another angle and I can seek a different flow."'
        )

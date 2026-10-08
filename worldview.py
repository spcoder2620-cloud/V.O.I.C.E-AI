"""
V.O.I.C.E. WORLDVIEW / OPINION LAYER

This is an explicit reasoning rubric, not hidden model training.

It helps V.O.I.C.E. evaluate claims about political labels or other topics
using evidence rather than choosing a conclusion at random.
"""

RUBRIC = {
    "authoritarianism": [
        "support for concentrated political power",
        "support for weakening democratic checks",
        "support for political violence or intimidation",
        "support for suppressing opposition",
    ],
    "nationalism": [
        "strong ethnonational identity claims",
        "nativist political framing",
        "politics centered heavily on national identity",
    ],
    "hierarchy": [
        "support for rigid social hierarchy",
        "claims that some groups deserve greater political rights",
        "explicit anti-egalitarian arguments",
    ],
    "exclusion": [
        "advocacy for excluding groups from political membership",
        "support for discriminatory legal treatment",
        "collective blame of an ethnic or religious group",
    ],
}

def score_position(evidence):
    scores = {dimension: 0.0 for dimension in RUBRIC}

    for item in evidence:
        dimension = item.get("dimension")
        if dimension not in scores:
            continue

        strength = float(item.get("strength", 0))
        direction = item.get("direction", "supports")

        if direction == "supports":
            scores[dimension] += strength
        elif direction == "contradicts":
            scores[dimension] -= strength

    return scores

def classify_position(evidence):
    scores = score_position(evidence)

    strong = sum(v >= 4 for v in scores.values())
    moderate = sum(v >= 2 for v in scores.values())

    if strong >= 3:
        label = "extreme right-wing"
    elif strong >= 2 or moderate >= 3:
        label = "far right"
    elif moderate >= 2:
        label = "right-wing"
    elif any(v > 0 for v in scores.values()):
        label = "mixed / partially right-wing"
    else:
        label = "not enough evidence"

    return {"label": label, "scores": scores}

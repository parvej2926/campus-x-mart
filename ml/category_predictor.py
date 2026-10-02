"""Lightweight category prediction utility for campus marketplace items.

This is a deterministic local model that mimics the intended on-device category
classification workflow without requiring TensorFlow or a heavyweight training
pipeline.
"""

from __future__ import annotations

import re


CATEGORY_KEYWORDS = {
    "Books": ["book", "textbook", "notes", "novel", "study", "exam", "course"],
    "Electronics": ["laptop", "phone", "charger", "keyboard", "mouse", "headphone", "tablet"],
    "Furniture": ["chair", "desk", "table", "bed", "lamp", "shelf", "cabinet"],
    "Bikes": ["bike", "cycle", "helmet", "bicycle", "mountain bike"],
    "Clothes": ["shirt", "jacket", "jeans", "shoe", "dress", "hoodie", "sneakers"],
    "Others": ["misc", "general", "other", "accessory", "tool"],
}

CATEGORY_ORDER = list(CATEGORY_KEYWORDS.keys())


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _matches_keyword(text: str, keyword: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def predict_category(item_name: str) -> str:
    text = _normalize_text(item_name)
    if not text:
        return "Others"

    best_category = "Others"
    best_score = 0

    for category in CATEGORY_ORDER:
        score = sum(1 for keyword in CATEGORY_KEYWORDS[category] if _matches_keyword(text, keyword))
        if score > best_score:
            best_category = category
            best_score = score
        elif score == best_score and category == "Others":
            best_category = "Others"

    return best_category if best_score > 0 else "Others"


if __name__ == "__main__":
    samples = [
        "Used CSE textbook",
        "Gaming laptop with charger",
        "Study desk chair",
        "Second-hand bicycle",
        "Blue hoodie",
        "phonecase for campus",
    ]

    for sample in samples:
        print(f"{sample} -> {predict_category(sample)}")

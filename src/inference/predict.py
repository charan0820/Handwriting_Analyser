import random


def recognize_text(image, model=None) -> tuple[str, float]:
    """Mock implementation — matches locked interface (interfaces.md).
    Returns a fixed-format (text, confidence) pair so evaluation/UI can be
    built against a stable contract before the real model (Day 7) lands.
    """
    mock_texts = ["the quick brown fox", "hello world", "sample handwriting"]
    text = random.choice(mock_texts)
    confidence = round(random.uniform(0.7, 0.99), 4)
    return text, confidence

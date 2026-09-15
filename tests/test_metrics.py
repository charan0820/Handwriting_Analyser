"""Day 1 — tests for evaluation metrics (Member 3)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evaluation.metrics import calculate_cer, calculate_wer


def test_identical_strings():
    assert calculate_cer("hello", "hello") == 0.0
    assert calculate_wer("hello world", "hello world") == 0.0


def test_character_substitution():
    # 1 substitution / 8 reference chars
    assert abs(calculate_cer("computar", "computer") - 0.125) < 1e-9


def test_word_substitution():
    assert abs(calculate_wer("machine learing", "machine learning") - 0.5) < 1e-9


def test_empty_ground_truth():
    assert calculate_cer("", "") == 0.0
    assert calculate_cer("abc", "") == 1.0
    assert calculate_wer("", "") == 0.0
    assert calculate_wer("abc def", "") == 1.0


def test_empty_prediction():
    assert calculate_cer("", "abc") == 1.0
    assert calculate_wer("", "abc def") == 1.0


if __name__ == "__main__":
    test_identical_strings()
    test_character_substitution()
    test_word_substitution()
    test_empty_ground_truth()
    test_empty_prediction()
    print("All tests passed.")

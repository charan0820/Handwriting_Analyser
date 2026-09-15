"""
Day 1 — Evaluation metrics (Member 3)

These are pure functions with no model dependency, so they can be implemented
and tested on Day 1 without waiting on Member 1 (data) or Member 2 (model).
"""


def _levenshtein(seq_a: list, seq_b: list) -> int:
    """Standard edit distance (substitutions + insertions + deletions), O(n*m)."""
    n, m = len(seq_a), len(seq_b)
    if n == 0:
        return m
    if m == 0:
        return n

    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,      # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution
            )
        prev, curr = curr, prev

    return prev[m]


def calculate_cer(predicted: str, ground_truth: str) -> float:
    """Locked interface — see shared/interfaces.md

    CER = edit_distance(chars) / len(ground_truth_chars)
    Returns 0.0 for an empty ground truth with an empty prediction,
    and 1.0 (capped) if ground truth is empty but prediction isn't
    (avoids division by zero while still penalizing hallucinated output).
    """
    if len(ground_truth) == 0:
        return 0.0 if len(predicted) == 0 else 1.0
    dist = _levenshtein(list(predicted), list(ground_truth))
    return dist / len(ground_truth)


def calculate_wer(predicted: str, ground_truth: str) -> float:
    """Locked interface — see shared/interfaces.md

    WER = edit_distance(words) / len(ground_truth_words)
    Same empty-string handling as calculate_cer.
    """
    pred_words = predicted.split()
    gt_words = ground_truth.split()
    if len(gt_words) == 0:
        return 0.0 if len(pred_words) == 0 else 1.0
    dist = _levenshtein(pred_words, gt_words)
    return dist / len(gt_words)


if __name__ == "__main__":
    # Sanity checks against the examples from the project spec (Section 22).
    cases = [
        ("The quick brown fox", "The quick brown fox", 0.0, 0.0),
        ("computar", "computer", 1 / 8, 1.0),
        ("machine learing", "machine learning", None, 1 / 2),
    ]
    for pred, gt, expected_cer, expected_wer in cases:
        cer = calculate_cer(pred, gt)
        wer = calculate_wer(pred, gt)
        print(f"pred={pred!r} gt={gt!r} -> CER={cer:.4f} WER={wer:.4f}")
        if expected_cer is not None:
            assert abs(cer - expected_cer) < 1e-6, f"CER mismatch: {cer} != {expected_cer}"
        if expected_wer is not None:
            assert abs(wer - expected_wer) < 1e-6, f"WER mismatch: {wer} != {expected_wer}"
    print("All sanity checks passed.")

from .metrics import calculate_cer, calculate_wer


def evaluate_batch(predictions: list[str], ground_truths: list[str]) -> dict:
    assert len(predictions) == len(ground_truths)
    cers = [calculate_cer(p, g) for p, g in zip(predictions, ground_truths)]
    wers = [calculate_wer(p, g) for p, g in zip(predictions, ground_truths)]
    n = len(predictions)
    return {
        "cer": sum(cers) / n if n else 0.0,
        "wer": sum(wers) / n if n else 0.0,
        "exact_match": sum(p == g for p, g in zip(predictions, ground_truths)) / n if n else 0.0,
        "n": n,
    }

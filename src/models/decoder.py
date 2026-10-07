def _collapse(indices: list[int], blank=0) -> list[int]:
    """CTC collapse: merge repeats, drop blanks. Pure logic, torch-independent."""
    out = []
    prev = None
    for idx in indices:
        if idx != prev and idx != blank:
            out.append(idx)
        prev = idx
    return out


def decode_predictions(logits, charset: dict) -> list[str]:
    """Locked interface. logits: (T,B,num_classes) torch tensor. Greedy CTC decode."""
    idx_to_char = {i + 1: c for i, c in enumerate(charset["chars"])}  # 0=blank
    pred_indices = logits.argmax(dim=2).permute(1, 0).tolist()  # (B,T)
    texts = []
    for seq in pred_indices:
        collapsed = _collapse(seq, blank=charset.get("blank_index", 0))
        texts.append("".join(idx_to_char.get(i, "") for i in collapsed))
    return texts


if __name__ == "__main__":
    # torch-free smoke test of the core collapse logic
    charset = {"chars": ["h", "e", "l", "o"], "blank_index": 0}
    # "h h _ e e l l _ l o" where _ = blank(0), h=1,e=2,l=3,o=4
    seq = [1, 1, 0, 2, 2, 3, 3, 0, 3, 4]
    result = "".join({1: "h", 2: "e", 3: "l", 4: "o"}.get(i, "") for i in _collapse(seq))
    print("collapsed:", result)
    assert result == "hello", result
    print("OK")

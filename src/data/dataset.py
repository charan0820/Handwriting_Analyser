import os
import random


def load_dataset(data_path: str) -> tuple[list[str], list[str]]:
    """Parses IAM lines.txt format: 'line_id status ... text' (text uses '|' for spaces).
    Expects images at {data_path}/lines/{line_id}.png and annotations at {data_path}/lines.txt
    """
    ann_path = os.path.join(data_path, "lines.txt")
    image_paths, texts = [], []
    with open(ann_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(" ")
            line_id, status = parts[0], parts[1]
            if status == "err":
                continue
            text = parts[-1].replace("|", " ")
            img_path = os.path.join(data_path, "lines", f"{line_id}.png")
            image_paths.append(img_path)
            texts.append(text)
    return image_paths, texts


def writer_disjoint_split(image_paths: list[str], texts: list[str], ratios=(0.8, 0.1, 0.1), seed=42):
    """Groups by writer/form prefix (chars before 2nd '-'), splits groups so no
    writer spans multiple sets. line_id format: a01-000u-00 -> writer group 'a01-000u'."""
    groups = {}
    for path, text in zip(image_paths, texts):
        line_id = os.path.splitext(os.path.basename(path))[0]
        group = "-".join(line_id.split("-")[:2])
        groups.setdefault(group, []).append((path, text))

    keys = list(groups.keys())
    random.Random(seed).shuffle(keys)
    n = len(keys)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    train_keys = keys[:n_train]
    val_keys = keys[n_train:n_train + n_val]
    test_keys = keys[n_train + n_val:]

    def collect(ks):
        paths, txts = [], []
        for k in ks:
            for p, t in groups[k]:
                paths.append(p)
                txts.append(t)
        return paths, txts

    return collect(train_keys), collect(val_keys), collect(test_keys)

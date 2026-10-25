import os
import random
import json
from pathlib import Path


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
    """Legacy form-group split, NOT proof of writer separation.

    Prefer source_dataset_split for downloaded data or verified_writer_split
    with an authoritative sample-to-writer mapping. Retained for compatibility.
    """
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


def source_dataset_split(image_paths, texts):
    """Preserve downloaded source partitions; never pool official test data."""
    groups = {name:([],[]) for name in ('train','validation','test')}
    for path,text in zip(image_paths,texts,strict=True):
        split = Path(path).stem.split('_')[0]
        if split not in groups:
            raise ValueError('Source split unavailable. Supply verified writer metadata for official IAM filenames.')
        groups[split][0].append(path)
        groups[split][1].append(text)
    if any(not values[0] for values in groups.values()):
        raise ValueError('Train, validation and test source partitions are all required.')
    return tuple(groups[name] for name in ('train','validation','test'))


def verified_writer_split(image_paths,texts,writer_ids,ratios=(.8,.1,.1),seed=42):
    groups = {}
    for path,text in zip(image_paths,texts,strict=True):
        sample = Path(path).stem
        if sample not in writer_ids:
            raise ValueError(f'Missing authoritative writer ID for {sample}.')
        groups.setdefault(str(writer_ids[sample]),[]).append((path,text))
    keys=list(groups)
    random.Random(seed).shuffle(keys)
    a,b=int(len(keys)*ratios[0]),int(len(keys)*(ratios[0]+ratios[1]))
    def collect(names):
        entries=[entry for name in names for entry in groups[name]]
        return [p for p,t in entries],[t for p,t in entries]
    return collect(keys[:a]),collect(keys[a:b]),collect(keys[b:])

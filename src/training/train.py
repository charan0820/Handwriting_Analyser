import json
import os

import torch
import yaml
from torch.utils.data import Dataset, DataLoader

from src.data.dataset import load_dataset, writer_disjoint_split
from src.data.preprocessing import preprocess_image
from src.models.crnn import build_crnn
from src.training.losses import ctc_loss
from src.evaluation.metrics import calculate_cer
from src.models.decoder import decode_predictions


def load_charset(path="charset.json"):
    with open(path) as f:
        return json.load(f)


def text_to_indices(text: str, charset: dict) -> list[int]:
    char_to_idx = {c: i + 1 for i, c in enumerate(charset["chars"])}  # 0 reserved for blank
    return [char_to_idx[c] for c in text if c in char_to_idx]


class HandwritingDataset(Dataset):
    def __init__(self, paths, texts, charset):
        self.paths = paths
        self.texts = texts
        self.charset = charset

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        from PIL import Image
        img = Image.open(self.paths[idx])
        arr = preprocess_image(img)  # (H,W,1)
        x = torch.from_numpy(arr).permute(2, 0, 1)  # (1,H,W)
        target = torch.tensor(text_to_indices(self.texts[idx], self.charset), dtype=torch.long)
        return x, target


def collate_fn(batch):
    xs, targets = zip(*batch)
    x = torch.stack(xs)
    target_lengths = torch.tensor([len(t) for t in targets], dtype=torch.long)
    targets_cat = torch.cat(targets)
    return x, targets_cat, target_lengths


def train_model(model, train_loader, val_loader, config: dict, resume_from: str = None) -> dict:
    """Locked interface. Returns history; saves best checkpoint to config['training']['checkpoint_dir']."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=config["training"]["learning_rate"],
                            weight_decay=config["training"]["weight_decay"])

    ckpt_dir = config["training"]["checkpoint_dir"]
    os.makedirs(ckpt_dir, exist_ok=True)
    patience = config["training"]["early_stopping_patience"]

    best_val_cer = float("inf")
    epochs_no_improve = 0
    start_epoch = 0
    history = {"train_loss": [], "val_loss": [], "val_cer": []}

    resume_path = resume_from or config["training"].get("resume_from")
    if resume_path and os.path.exists(resume_path):
        ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        start_epoch = ckpt.get("epoch", -1) + 1
        best_val_cer = ckpt.get("val_cer", float("inf"))
        print(f"[+] Resumed from checkpoint '{resume_path}': starting at epoch {start_epoch} (best val_cer so far: {best_val_cer:.4f})")

    charset = load_charset()

    for epoch in range(start_epoch, config["training"]["epochs"]):
        model.train()
        total_loss = 0.0
        for x, targets, target_lengths in train_loader:
            x, targets, target_lengths = x.to(device), targets.to(device), target_lengths.to(device)
            logits = model(x)  # (T,B,C)
            input_lengths = torch.full((x.size(0),), logits.size(0), dtype=torch.long, device=device)
            loss = ctc_loss(logits, targets, input_lengths, target_lengths)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
        train_loss = total_loss / max(1, len(train_loader))

        val_loss, val_cer = _validate(model, val_loader, charset, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_cer"].append(val_cer)
        print(f"epoch {epoch} train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_cer={val_cer:.4f}")

        if val_cer < best_val_cer:
            best_val_cer = val_cer
            epochs_no_improve = 0
            torch.save({
                "model_state": model.state_dict(),
                "config": config,
                "epoch": epoch,
                "val_cer": val_cer,
            }, os.path.join(ckpt_dir, "best_model.pth"))
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print("early stopping")
                break

    return history


def _validate(model, val_loader, charset, device):
    model.eval()
    total_loss, total_cer, n = 0.0, 0.0, 0
    with torch.no_grad():
        for x, targets, target_lengths in val_loader:
            x, targets, target_lengths = x.to(device), targets.to(device), target_lengths.to(device)
            logits = model(x)
            input_lengths = torch.full((x.size(0),), logits.size(0), dtype=torch.long, device=device)
            loss = ctc_loss(logits, targets, input_lengths, target_lengths)
            total_loss += loss.item()

            preds = decode_predictions(logits, charset)
            gts = []
            offset = 0
            idx_to_char = {i + 1: c for i, c in enumerate(charset["chars"])}
            for tl in target_lengths.tolist():
                idxs = targets[offset:offset + tl].tolist()
                gts.append("".join(idx_to_char[i] for i in idxs))
                offset += tl
            for p, g in zip(preds, gts):
                total_cer += calculate_cer(p, g)
                n += 1
    return total_loss / max(1, len(val_loader)), total_cer / max(1, n)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train CRNN handwriting recognition model.")
    parser.add_argument("--resume", nargs="?", const="models/best_model.pth", default=None,
                        help="Resume training from checkpoint (default: models/best_model.pth)")
    args = parser.parse_args()

    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    charset = load_charset()
    num_classes = len(charset["chars"]) + 1

    paths, texts = load_dataset(config["dataset"]["raw_path"])
    (tr_p, tr_t), (va_p, va_t), _ = writer_disjoint_split(paths, texts, config["dataset"]["split_ratio"])

    train_ds = HandwritingDataset(tr_p, tr_t, charset)
    val_ds = HandwritingDataset(va_p, va_t, charset)
    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"], collate_fn=collate_fn)

    model = build_crnn(num_classes)
    train_model(model, train_loader, val_loader, config, resume_from=args.resume)

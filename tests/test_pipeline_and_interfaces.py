import os
import sys
import tempfile
import numpy as np
import pytest
import torch
from PIL import Image

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.dataset import load_dataset, writer_disjoint_split
from src.data.preprocessing import preprocess_image
from src.data.augmentation import augment_image
from src.segmentation.line_segmentation import find_line_boundaries, segment_text_lines
from src.models.cnn import CNNFeatureExtractor
from src.models.sequence_model import SequenceModel
from src.models.crnn import build_crnn, CRNN
from src.models.decoder import decode_predictions, _collapse
from src.training.losses import ctc_loss
from src.training.train import train_model, collate_fn, load_charset, text_to_indices, HandwritingDataset
from src.inference.predict import recognize_text, load_model
from src.inference.pipeline import process_document, export_txt
from src.evaluation.metrics import calculate_cer, calculate_wer
from src.evaluation.evaluate import evaluate_batch
from src.visualization.visualize import draw_line_regions


def test_locked_interface_signatures():
    """Verify that all 8 locked interfaces defined in interfaces.md exist and are callable."""
    assert callable(load_dataset)
    assert callable(preprocess_image)
    assert callable(segment_text_lines)
    assert callable(build_crnn)
    assert callable(train_model)
    assert callable(recognize_text)
    assert callable(decode_predictions)
    assert callable(calculate_cer)
    assert callable(calculate_wer)


def test_dataset_loading_and_splitting(tmp_path):
    """Test load_dataset with sample IAM lines.txt and writer_disjoint_split."""
    lines_txt = tmp_path / "lines.txt"
    lines_dir = tmp_path / "lines"
    lines_dir.mkdir()

    # Create dummy IAM lines.txt content
    content = (
        "# IAM header comment\n"
        "\n"
        "a01-000u-00 ok 154 408 768 27 51 JJ A|MOVE|to|stop\n"
        "a01-000u-01 err 154 408 768 27 51 JJ should|be|skipped\n"
        "a01-001u-00 ok 154 408 768 27 51 JJ Hello|world\n"
        "b02-000a-00 ok 154 408 768 27 51 JJ Another|writer\n"
    )
    lines_txt.write_text(content, encoding="utf-8")

    # Create matching dummy images
    for name in ["a01-000u-00.png", "a01-001u-00.png", "b02-000a-00.png"]:
        Image.new("L", (100, 30), color=255).save(lines_dir / name)

    image_paths, texts = load_dataset(str(tmp_path))
    assert len(image_paths) == 3
    assert len(texts) == 3
    assert texts[0] == "A MOVE to stop"
    assert texts[1] == "Hello world"
    assert texts[2] == "Another writer"

    # Test writer-disjoint split
    (tr_p, tr_t), (va_p, va_t), (te_p, te_t) = writer_disjoint_split(
        image_paths, texts, ratios=(0.5, 0.25, 0.25), seed=42
    )
    total_samples = len(tr_p) + len(va_p) + len(te_p)
    assert total_samples == 3

    # Ensure no writer group spans across splits
    def get_writers(paths):
        return {"-".join(os.path.basename(p).split("-")[:2]) for p in paths}

    tr_w, va_w, te_w = get_writers(tr_p), get_writers(va_p), get_writers(te_p)
    assert tr_w.isdisjoint(va_w)
    assert tr_w.isdisjoint(te_w)
    assert va_w.isdisjoint(te_w)


def test_preprocessing_various_inputs():
    """Verify preprocessing handles PIL Image, uint8 ndarray, 3D ndarray, and float ndarray."""
    # 1. PIL Image
    pil_img = Image.new("RGB", (300, 50), color=(255, 255, 255))
    res1 = preprocess_image(pil_img)
    assert res1.shape == (64, 256, 1)
    assert res1.dtype == np.float32
    assert 0.0 <= res1.min() <= res1.max() <= 1.0

    # 2. 2D uint8 ndarray
    arr_2d = np.full((50, 300), 255, dtype=np.uint8)
    res2 = preprocess_image(arr_2d)
    assert res2.shape == (64, 256, 1)
    assert res2.dtype == np.float32

    # 3. 3D (H, W, 1) ndarray
    arr_3d = np.full((50, 300, 1), 255, dtype=np.uint8)
    res3 = preprocess_image(arr_3d)
    assert res3.shape == (64, 256, 1)

    # 4. float32 ndarray in [0, 1]
    arr_float = np.full((50, 300), 1.0, dtype=np.float32)
    res4 = preprocess_image(arr_float)
    assert res4.shape == (64, 256, 1)


def test_augmentation():
    """Verify augment_image preserves shape and value range."""
    img = np.random.rand(64, 256, 1).astype(np.float32)
    aug = augment_image(img, seed=123)
    assert aug.shape == (64, 256, 1)
    assert aug.dtype == np.float32
    assert 0.0 <= aug.min() <= aug.max() <= 1.0

    # Test with 2D array
    img_2d = np.random.rand(64, 256).astype(np.float32)
    aug_2d = augment_image(img_2d, seed=123)
    assert aug_2d.shape == (64, 256, 1)


def test_line_segmentation():
    """Verify find_line_boundaries and segment_text_lines correctly crop text lines."""
    doc = np.full((200, 300), 255, dtype=np.uint8)
    # 2 dark lines
    doc[20:40, 10:290] = 0
    doc[80:100, 10:290] = 0

    boundaries = find_line_boundaries(doc)
    assert len(boundaries) == 2
    assert boundaries[0] == (20, 40)
    assert boundaries[1] == (80, 100)

    crops = segment_text_lines(doc)
    assert len(crops) == 2
    assert crops[0].shape == (20, 300)
    assert crops[1].shape == (20, 300)


def test_crnn_model_forward():
    """Verify CRNN forward pass shape (T, B, num_classes)."""
    num_classes = 68
    model = build_crnn(num_classes)
    model.eval()

    # Batch size 1
    x1 = torch.randn(1, 1, 64, 256)
    logits1 = model(x1)
    assert logits1.shape[1] == 1
    assert logits1.shape[2] == num_classes

    # Batch size 4
    x4 = torch.randn(4, 1, 64, 256)
    logits4 = model(x4)
    assert logits4.shape[1] == 4
    assert logits4.shape[2] == num_classes


def test_decoder():
    """Test CTC greedy collapse and decode_predictions."""
    # Test collapse logic directly
    # e.g., [1, 1, 0, 2, 2, 0, 3] -> [1, 2, 3]
    collapsed = _collapse([1, 1, 0, 2, 2, 0, 3], blank=0)
    assert collapsed == [1, 2, 3]

    charset = load_charset()
    # Construct synthetic logits (T=3, B=1, num_classes=68)
    logits = torch.zeros(3, 1, len(charset["chars"]) + 1)
    # Predict 'a' (index in chars), then blank (0), then 'b'
    # Find index of 'a' and 'b'
    idx_a = charset["chars"].index("a") + 1
    idx_b = charset["chars"].index("b") + 1

    logits[0, 0, idx_a] = 10.0
    logits[1, 0, 0] = 10.0  # blank
    logits[2, 0, idx_b] = 10.0

    decoded = decode_predictions(logits, charset)
    assert len(decoded) == 1
    assert decoded[0] == "ab"


def test_recognize_text_interface():
    """Verify recognize_text works with 2 arguments (locked interface) and 3 arguments."""
    num_classes = 68
    model = build_crnn(num_classes)
    model.eval()

    sample_img = np.full((64, 256), 255, dtype=np.uint8)

    # 1. Called with 2 arguments (as documented in interfaces.md)
    text1, conf1 = recognize_text(sample_img, model)
    assert isinstance(text1, str)
    assert isinstance(conf1, float)
    assert 0.0 <= conf1 <= 1.0

    # 2. Called with 3 arguments (passing charset)
    charset = load_charset()
    text2, conf2 = recognize_text(sample_img, model, charset=charset)
    assert isinstance(text2, str)
    assert isinstance(conf2, float)


def test_process_document_pipeline(tmp_path):
    """Verify end-to-end process_document on a simulated document image."""
    model = build_crnn(68)
    model.eval()
    charset = load_charset()

    # Create synthetic multi-line document image
    img = Image.new("L", (300, 150), color=255)
    img_arr = np.array(img)
    img_arr[20:40, 20:280] = 0
    img_arr[70:90, 20:280] = 0
    doc_path = tmp_path / "test_doc.png"
    Image.fromarray(img_arr).save(doc_path)

    result = process_document(str(doc_path), model, charset=charset, ground_truth="hello world")
    assert "full_text" in result
    assert "line_texts" in result
    assert "line_confidences" in result
    assert "annotated_image" in result
    assert "cer" in result
    assert "wer" in result
    assert len(result["line_texts"]) == 2

    # Test export_txt
    out_txt = tmp_path / "output.txt"
    export_txt(result, str(out_txt))
    assert out_txt.exists()


def test_training_one_step_sanity(tmp_path):
    """Verify train_model completes an epoch and saves checkpoint."""
    charset = load_charset()
    num_classes = len(charset["chars"]) + 1
    model = build_crnn(num_classes)

    config = {
        "training": {
            "epochs": 1,
            "batch_size": 2,
            "learning_rate": 0.001,
            "weight_decay": 0.0001,
            "early_stopping_patience": 2,
            "checkpoint_dir": str(tmp_path / "models"),
        }
    }

    # Dummy dataset
    class DummyDS(torch.utils.data.Dataset):
        def __len__(self):
            return 2

        def __getitem__(self, idx):
            x = torch.randn(1, 64, 256)
            target = torch.tensor([1, 2, 3], dtype=torch.long)
            return x, target

    loader = torch.utils.data.DataLoader(DummyDS(), batch_size=2, collate_fn=collate_fn)
    history = train_model(model, loader, loader, config)

    assert "train_loss" in history
    assert "val_loss" in history
    assert "val_cer" in history
    assert len(history["train_loss"]) == 1
    assert os.path.exists(os.path.join(config["training"]["checkpoint_dir"], "best_model.pth"))

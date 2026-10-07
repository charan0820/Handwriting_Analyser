import os
import json
import torch

from src.data.preprocessing import preprocess_image
from src.models.crnn import build_crnn
from src.models.decoder import decode_predictions
from src.postprocessing.text_cleanup import clean_text


def _get_default_charset():
    default_path = os.path.join(os.path.dirname(__file__), "..", "..", "charset.json")
    if not os.path.exists(default_path):
        default_path = "charset.json"
    with open(default_path) as f:
        return json.load(f)


def load_model(checkpoint_path: str, charset_path="charset.json"):
    with open(charset_path) as f:
        charset = json.load(f)
    num_classes = len(charset["chars"]) + 1
    model = build_crnn(num_classes)
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, charset


def recognize_text(image, model, charset=None) -> tuple[str, float]:
    """Locked interface. image: PIL.Image or np.ndarray of a single line crop."""
    if charset is None:
        charset = _get_default_charset()

    arr = preprocess_image(image)
    device = next(model.parameters()).device
    x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)  # (1,1,H,W)
    with torch.no_grad():
        logits = model(x)  # (T,1,C)
        probs = logits.softmax(dim=2)
        confidence = probs.max(dim=2).values.mean().item()  # mean top-class prob across T
        text = decode_predictions(logits, charset)[0]
    return clean_text(text), round(confidence, 4)

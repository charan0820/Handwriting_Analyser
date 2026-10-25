"""Explicit network setup. The application itself only loads local weights."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.recognition import MODEL_ID, MODEL_DIR

if __name__ == '__main__':
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    TrOCRProcessor.from_pretrained(MODEL_ID).save_pretrained(MODEL_DIR)
    VisionEncoderDecoderModel.from_pretrained(MODEL_ID).save_pretrained(MODEL_DIR,safe_serialization=True)
    print(f'Model and processor saved to {MODEL_DIR}. Transcription can now run offline.')

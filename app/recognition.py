"""Lazy, offline-only model adapters. Model downloads live in setup_models.py."""
import importlib.util
import os
from importlib import resources
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from app.store import ROOT

MODEL_ID = 'microsoft/trocr-base-handwritten'
os.environ.setdefault('USE_TF','0')
MODEL_DIR = Path(os.environ.get('HTR_MODEL_DIR', ROOT / 'models' / 'trocr-base-handwritten'))
_segmentation_model = None


def detection_canvas(image: Image.Image):
    """Bound Kraken's *internal* fixed-height resize, including very wide strips.

    Its default model scales to 1800px high with an unconstrained width. A
    longest-edge resize alone cannot bound that width because aspect ratio is
    unchanged. Pad landscape inputs to a square, keeping ink undistorted.
    Returns the canvas, original-to-preview scale and preview content offset.
    """
    scale = min(1.0, 2400 / max(image.size))
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    preview = image.convert('RGB').resize(size)
    if preview.width <= preview.height:
        return preview, scale, (0, 0)
    canvas = Image.new('RGB', (preview.width, preview.width), 'white')
    offset = (0, (canvas.height - preview.height) // 2)
    canvas.paste(preview, offset)
    return canvas, scale, offset


def map_detected_region(line, image, scale, offset):
    """Remove detection-only padding and retain regions that intersect the page."""
    ox, oy = offset
    polygon = np.asarray(line.boundary, dtype=float)
    polygon = (polygon - [ox, oy]) / scale
    if (polygon[:, 0].max() < 0 or polygon[:, 1].max() < 0
            or polygon[:, 0].min() >= image.width or polygon[:, 1].min() >= image.height):
        return None
    polygon[:, 0] = np.clip(polygon[:, 0], 0, image.width - 1)
    polygon[:, 1] = np.clip(polygon[:, 1], 0, image.height - 1)
    if abs(cv2.contourArea(polygon.astype(np.float32))) < 1:
        return None
    baseline = (np.asarray(line.baseline, dtype=float) - [ox, oy]) / scale
    baseline[:, 0] = np.clip(baseline[:, 0], 0, image.width - 1)
    baseline[:, 1] = np.clip(baseline[:, 1], 0, image.height - 1)
    return {'polygon': polygon.tolist(), 'baseline': baseline.tolist()}


def single_line_region(image):
    """Recognize a clearly isolated wide text band without page-layout inference.

    Aspect ratio alone is insufficient: require exactly one substantial band
    after binarization, so wide two-line images still use the learned detector.
    Keep the whole strip as the region, including ascenders and descenders.
    """
    if image.width / image.height < 6:
        return None
    from src.segmentation.line_segmentation import find_line_boundaries
    scale = min(1.0, 2400 / image.width)
    preview = image.convert('L').resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))))
    gray = np.asarray(preview)
    if gray.std() < 5:
        return None
    binary = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
    bands = find_line_boundaries(binary,min_gap=max(2,round(preview.height*.025)),
                                 min_height=max(4,round(preview.height*.08)))
    if len(bands) != 1:
        return None
    ink_y,ink_x = np.where(binary < 128)
    if len(ink_x)==0 or np.ptp(ink_x) < preview.width*.5:
        return None
    return [(0,0),(image.width-1,0),(image.width-1,image.height-1),(0,image.height-1)]


def capabilities():
    import torch
    return {
        'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
        'engines': [
            {'id':'trocr', 'name':'TrOCR Handwritten', 'architecture':'Vision Transformer + Transformer decoder',
             'version':MODEL_ID, 'ready': all((MODEL_DIR / f).exists() for f in ('config.json','preprocessor_config.json','model.safetensors')), 'beam_search':True},
            {'id':'crnn', 'name':'Project CRNN', 'architecture':'CNN + BiLSTM + CTC',
             'version':'baseline-checkpoint', 'ready': (ROOT/'models/best_model.pth').exists(), 'beam_search':False}],
        'detectors': [
            {'id':'kraken', 'name':'Kraken learned lines', 'ready':importlib.util.find_spec('kraken') is not None},
            {'id':'projection', 'name':'Simple straight lines (baseline)', 'ready':True}],
        'offline':True,
    }


def detect_lines(image: Image.Image, detector: str):
    scale = min(1.0, 2400 / max(image.size))
    small = image.resize((max(1,round(image.width*scale)), max(1,round(image.height*scale))))
    polygons = []
    if detector == 'kraken':
        isolated = single_line_region(image)
        if isolated is not None:
            return [isolated]
        small, scale, offset = detection_canvas(image)
        try:
            from kraken import blla
            from kraken.lib import vgsl
        except ImportError as exc:
            raise RuntimeError('Kraken is not installed. Run the WSL2 setup, or explicitly choose the simple baseline detector.') from exc
        global _segmentation_model
        if _segmentation_model is None:
            # Explicit package anchor also supports Python 3.10 (Ubuntu 22.04).
            model_path=resources.files('kraken').joinpath('blla.mlmodel')
            _segmentation_model=vgsl.TorchVGSLModel.load_model(str(model_path))
        segmentation = blla.segment(small, text_direction='horizontal-lr', device='cpu',model=_segmentation_model)
        for line in segmentation.lines:
            boundary = line.boundary
            if boundary and len(boundary) >= 4:
                region = map_detected_region(line, image, scale, offset)
                if region is not None:
                    polygons.append(region)
    else:
        from src.segmentation.line_segmentation import find_line_boundaries
        gray = np.array(small.convert('L'))
        # Adaptive thresholding limits sensitivity to paper shade and lighting.
        binary = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,15)
        for y1,y2 in find_line_boundaries(binary):
            ink = np.where(binary[y1:y2] < 128)[1]
            if len(ink):
                x1,x2 = int(ink.min()), int(ink.max()+1)
                polygons.append([(x1/scale,y1/scale),(x2/scale,y1/scale),(x2/scale,y2/scale),(x1/scale,y2/scale)])
    return polygons


class Recognizer:
    def __init__(self, engine):
        import torch
        self.engine = engine
        self.startup_warnings = []
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if engine == 'trocr':
            if not (MODEL_DIR/'config.json').exists():
                raise RuntimeError('TrOCR weights are missing. Run python scripts/setup_models.py before transcribing, or choose the project CRNN.')
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            self.processor = TrOCRProcessor.from_pretrained(str(MODEL_DIR), local_files_only=True)
            self.model = VisionEncoderDecoderModel.from_pretrained(str(MODEL_DIR), local_files_only=True)
        else:
            from src.inference.predict import load_model
            self.model,self.charset = load_model(str(ROOT/'models/best_model.pth'), str(ROOT/'charset.json'))
        try:
            self.model.to(self.device).eval()
        except torch.cuda.OutOfMemoryError:
            self.device = 'cpu'
            self.model.to('cpu').eval()
            torch.cuda.empty_cache()
            self.startup_warnings.append('GPU memory was unavailable while loading the model; recognition is using CPU.')

    def recognize(self, image, settings):
        import torch
        notes = list(self.startup_warnings)
        try:
            return self._recognize(image,settings,notes)
        except torch.cuda.OutOfMemoryError:
            # Batch size is already one. Release GPU allocations and retry on CPU.
            self.device = 'cpu'
            self.model.to('cpu')
            torch.cuda.empty_cache()
            notes.append('GPU memory was exhausted; this line was recognized on CPU.')
            return self._recognize(image,settings,notes)

    def _recognize(self,image,settings,notes):
        import torch
        with torch.inference_mode():
            if self.engine == 'crnn':
                from src.inference.predict import recognize_text
                text, score = recognize_text(image,self.model,self.charset)
                return text,score,notes
            pixels = self.processor(images=image.convert('RGB'),return_tensors='pt').pixel_values.to(self.device)
            output = self.model.generate(pixels, num_beams=settings.beam_width,
                                         max_new_tokens=settings.max_new_tokens,
                                         return_dict_in_generate=True,output_scores=True)
            text = self.processor.batch_decode(output.sequences,skip_special_tokens=True)[0].strip()
            sequence_scores = getattr(output,'sequences_scores',None)
            if sequence_scores is not None:
                score = float(sequence_scores[0].exp().cpu())
            elif output.scores:
                tokens = output.sequences[0,-len(output.scores):]
                log_scores = torch.stack([step[0].log_softmax(-1)[token]
                                          for step,token in zip(output.scores,tokens)])
                score = float(log_scores.mean().exp().cpu())
            else:
                score = None
            if len(output.scores) >= settings.max_new_tokens:
                notes.append('Output reached its token limit. Split this region or increase the output limit and rerun.')
            return text,score,notes

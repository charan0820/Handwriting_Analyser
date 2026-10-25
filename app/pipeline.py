import time
import uuid
import numpy as np
from PIL import Image
from app.imaging import prepare, crop_line, split_long_line, rectify_line
from app.recognition import Recognizer, detect_lines, MODEL_ID
from app.schemas import Document, Line


class Cancelled(Exception):
    pass


def assemble(lines, mode):
    if mode == 'lines':
        return '\n'.join(line['text'] for line in lines)
    text = ''
    for line in lines:
        separator = '\n\n' if line.get('paragraph_start') else ' '
        text += (separator if text else '') + line['text']
    return text


def infer_paragraphs(lines):
    if not lines:
        return
    boxes = [np.asarray(line.polygon) for line in lines]
    heights = [b[:,1].max()-b[:,1].min() for b in boxes]
    gap = np.median([max(0,boxes[i][:,1].min()-boxes[i-1][:,1].max()) for i in range(1,len(boxes))]) if len(boxes)>1 else 0
    typical = max(1,float(np.median(heights)))
    for i in range(1,len(lines)):
        separation = boxes[i][:,1].min()-boxes[i-1][:,1].max()
        indent = boxes[i][:,0].min()-boxes[i-1][:,0].min()
        lines[i].paragraph_start = bool(separation > max(gap*1.8,typical*.8) or indent > typical*1.5)


def run_document(folder, settings, progress, cancelled, existing=None, selected=None):
    started = time.perf_counter()
    def check():
        if cancelled():
            raise Cancelled()
    check()
    progress(stage='preparing',completed=0,total=0)
    with Image.open(folder/'original.png') as original:
        original_size = original.size
        if existing is None:
            page, transform, notes = prepare(original.convert('RGB'),settings)
            page.save(folder/'page.png')
        else:
            page = Image.open(folder/'page.png').convert('RGB')
            transform,notes = existing['transform'],existing['warnings']
    check()
    if existing:
        document = Document.model_validate(existing)
    else:
        progress(stage='detecting')
        polygons = detect_lines(page,settings.detector)
        lines = [Line(id=uuid.uuid4().hex[:12],**(region if isinstance(region,dict) else {'polygon':region})) for region in polygons]
        infer_paragraphs(lines)
        if not lines:
            notes.append('No text lines detected. Check the crop and contrast, or add a line region manually.')
        if settings.detector == 'projection':
            notes.append('Simple baseline detection is selected; curved, touching, or uneven lines may be missed.')
        document = Document(width=page.width,height=page.height,original_width=original_size[0],
            original_height=original_size[1],transform=transform,settings=settings,lines=lines,warnings=notes)
    targets = [line for line in document.lines if selected is None or line.id in selected]
    progress(stage='recognizing',completed=0,total=len(targets),document=document.model_dump())
    recognizer = Recognizer(settings.engine) if targets else None
    failures = []
    for index,line in enumerate(targets):
        check()
        line.warnings = []
        line.reviewed = False
        try:
            crop = rectify_line(page,line,settings.line_padding)
            if np.ptp(np.asarray(line.polygon)[:,1]) < 16:
                line.warnings.append('Very small text: upload a higher-resolution image if possible.')
            crop.save(folder/f'line-{line.id}.png')
            pieces = split_long_line(crop,max_ratio=8 if settings.engine=='crnn' else 12)
            texts,scores,notes = [],[],[]
            for piece in pieces:
                check()
                text,score,warnings = recognizer.recognize(piece,settings)
                texts.append(text)
                if score is not None:
                    scores.append(score)
                notes.extend(warnings)
            line.raw_text = line.text = ' '.join(texts)
            line.score = float(np.mean(scores)) if scores else None
            line.warnings = list(dict.fromkeys(line.warnings+notes))
            line.reviewed = False
            if len(pieces)>1:
                line.warnings.append('Long line was split into segments. Review word joins.')
            if not line.text:
                line.warnings.append('No text recognized in this region. Adjust the region and rerun.')
        except Cancelled:
            raise
        except Exception as exc:
            failures.append(str(exc))
            line.warnings.append(f'Recognition failed for this line: {exc}')
        document.full_text = assemble([x.model_dump() for x in document.lines],settings.paragraph_mode)
        document.raw_text = '\n'.join(x.raw_text for x in document.lines)
        progress(completed=index+1,document=document.model_dump())
    check()
    if targets and len(failures)==len(targets):
        raise RuntimeError(f'All selected lines failed recognition. {failures[0]}')
    progress(stage='assembling')
    document.model = {'engine':settings.engine,'version':MODEL_ID if settings.engine=='trocr' else 'baseline-checkpoint',
                      'device':recognizer.device if recognizer else 'cpu','score_kind':'uncalibrated model score'}
    document.timings['total_seconds'] = round(time.perf_counter()-started,3)
    return document.model_dump()

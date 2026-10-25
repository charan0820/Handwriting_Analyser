"""Build a labeled demonstration page from real IAM test-line images.

The reference is dataset ground truth, never presented as a model prediction.
IAM data licensing applies; this asset is for the research/student application.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    rows=[line.split() for line in (ROOT/'data/raw/lines.txt').read_text(encoding='utf-8').splitlines()
          if line.startswith('test_')][:6]
    if not rows:
        raise SystemExit('Download IAM lines first: python -m src.data.download_dataset')
    canvas=Image.new('RGB',(1200,720),'white')
    lines=[]
    y=75
    for row in rows:
        image=Image.open(ROOT/'data/raw/lines'/f'{row[0]}.png').convert('RGB')
        image.thumbnail((1040,68))
        canvas.paste(image,(80,y))
        lines.append(row[-1].replace('|',' '))
        y+=92
    public=ROOT/'frontend/public'
    public.mkdir(parents=True,exist_ok=True)
    provenance=PngInfo()
    provenance.add_text('Source','Teklia/IAM-line test partition; six original line crops assembled for a research demonstration.')
    provenance.add_text('Sample IDs',','.join(row[0] for row in rows))
    provenance.add_text('Reference','sample.json contains dataset ground truth, not model predictions.')
    canvas.save(public/'sample.png',pnginfo=provenance)
    (public/'sample.json').write_text(json.dumps({'text':'\n'.join(lines),
        'source':'Teklia/IAM-line test partition; assembled demonstration page',
        'sample_ids':[row[0] for row in rows],'is_model_prediction':False},indent=2),encoding='utf-8')
    print('Saved sample.png and ground-truth sample.json')

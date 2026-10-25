"""Compare actual engines on a user-supplied held-out full-page manifest.

Manifest: [{"image":"relative/page.png","text":"reference text"}].
Never uses downloaded training pages as evidence of held-out performance.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.imaging import validate_image
from app.pipeline import run_document
from app.schemas import Settings
from src.evaluation.metrics import calculate_cer,calculate_wer
from src.evaluation.layout import evaluate_layout

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--detector',choices=['kraken','projection'],default='kraken')
    parser.add_argument('--output',type=Path,default=Path('outputs/reports/benchmark.json'))
    args=parser.parse_args()
    entries=json.loads(args.manifest.read_text(encoding='utf-8'))
    results=[]
    for entry in entries:
        for engine in ('crnn','trocr'):
            import torch
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary)
                validate_image((args.manifest.parent/entry['image']).read_bytes()).save(folder/'original.png')
                doc=run_document(folder,Settings(engine=engine,detector=args.detector),lambda **kw:None,lambda:False)
                result={'image':entry['image'],'engine':engine,
                    'cer':calculate_cer(doc['raw_text'],entry['text']),
                    'wer':calculate_wer(doc['raw_text'],entry['text']),
                    'lines':len(doc['lines']),'seconds':doc['timings']['total_seconds'],
                    'peak_gpu_bytes':torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None,
                    'warnings':doc['warnings'],'line_warnings':[l['warnings'] for l in doc['lines']]}
                if 'regions' in entry:
                    result['layout']=evaluate_layout([line['polygon'] for line in doc['lines']],entry['regions'],
                                                     (doc['width'],doc['height']),doc['transform'])
                results.append(result)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(f'Measured {len(results)} runs; saved {args.output}')

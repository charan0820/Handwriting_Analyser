"""Audit labels and partitions without changing data or model artifacts."""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.dataset import load_dataset, source_dataset_split


def audit(data_path,charset):
    paths,texts=load_dataset(data_path)
    invalid=[]
    missing=[]
    for path,text in zip(paths,texts):
        unknown=sorted(set(text)-set(charset['chars']))
        required=len(text)+sum(a==b for a,b in zip(text,text[1:]))
        if unknown or required>63:
            invalid.append({'sample':Path(path).stem,'unsupported':unknown,'ctc_steps':required})
        if not Path(path).is_file():
            missing.append(path)
    try:
        splits=source_dataset_split(paths,texts)
        partition_counts=dict(zip(('train','validation','test'),[len(p) for p,t in splits]))
    except ValueError as exc:
        partition_counts={'error':str(exc)}
    return {'samples':len(paths),'source_partitions':partition_counts,'writer_disjoint_verified':False,
            'invalid_targets':invalid,'missing_images':missing,'baseline_timesteps':63}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/raw')
    parser.add_argument('--output',default='outputs/reports/dataset-audit.json')
    args=parser.parse_args()
    result=audit(args.data,json.loads(Path('charset.json').read_text()))
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items()},indent=2))

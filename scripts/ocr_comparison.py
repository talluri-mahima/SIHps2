"""Real rendered-page provider rehearsal; coverage/latency, not an accuracy claim."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from app.ocr import LocalOCR
from app.layout import observations

ROOT=Path(__file__).resolve().parents[1]

def main():
    private=ROOT/'.data'/'ocr-comparison'; private.mkdir(parents=True,exist_ok=True)
    rows=[]; engines={}
    for name,number in [('tsm-fire',1),('tsm-occupancy',2)]:
        source=ROOT/'.data'/'public-documents'/f'{name}.pdf'
        with fitz.open(source) as pdf:
            image=pdf[number-1].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        for provider in ['rapidocr','paddleocr']:
            os.environ['AICTE_OCR_PROVIDER']=provider
            started=time.monotonic()
            try:
                lines,method=engines.setdefault(provider,LocalOCR()).recognize(image)
                elapsed=round(time.monotonic()-started,3)
                hints=observations(lines,number)
                (private/f'{name}-{number}-{provider}.json').write_text(json.dumps(dict(lines=lines,hints=hints),indent=2),encoding='utf-8')
                row=dict(document=name,page=number,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                         provider=provider,method=method,status='COMPLETED',elapsed_seconds=elapsed,
                         recognized_regions=len(lines),floor_mentions=sum(x['kind']=='FLOOR_NOTATION_MENTION' for x in hints),
                         expiry_label_mentions=sum(x['kind']=='EXPIRY_LABEL_MENTION' for x in hints),
                         automatic_confirmed_fields=0)
            except Exception as error:
                row=dict(document=name,page=number,provider=provider,status='FAILED',error_type=type(error).__name__,elapsed_seconds=round(time.monotonic()-started,3))
            rows.append(row);print(name,number,provider,row['status'],flush=True)
    for engine in engines.values():engine.close()
    models={p.relative_to(ROOT/'.data/paddle-models').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'.data/paddle-models').rglob('*') if p.is_file() and p.name in {'inference.json','inference.yml','inference.pdiparams','config.json'}}
    (ROOT/'reports/ocr-provider-rehearsal.json').write_text(json.dumps(dict(
        notice='Two development pages only; no independent field labels, CER/WER or real-world accuracy established.',
        real_world_accuracy_established=False,documents=rows,paddle_model_sha256=models),indent=2)+'\n')
    return 1 if any(r['status']=='FAILED' for r in rows) else 0

if __name__=='__main__':sys.exit(main())

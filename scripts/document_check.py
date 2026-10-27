"""Measured development OCR/extraction checks; not an independent accuracy claim."""
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from app.config import ROOT,DATA,validate_environment
from app.seed import pdf_bytes
from app.extract import extract


def image_only(data):
    with fitz.open(stream=data,filetype='pdf') as original,fitz.open() as scan:
        page=scan.new_page(width=595,height=842)
        image=original[0].get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
        page.insert_image(page.rect,stream=image)
        return scan.tobytes()


def run():
    validate_environment()
    dataset=json.loads((ROOT/'fixtures/document-evaluation.json').read_text(encoding='utf-8'))
    folder=DATA/'document-check';folder.mkdir(exist_ok=True)
    results=[]
    for case in dataset['cases']:
        content=pdf_bytes(case['kind'],case['lines'])
        if case['scan']:content=image_only(content)
        path=folder/(case['id']+'.pdf');path.write_bytes(content)
        started=time.monotonic();result=extract(path);elapsed=time.monotonic()-started
        actual={f['key']:f['value'] for f in result['fields']}
        correct=sum(actual.get(k)==v for k,v in case['expected'].items())
        wrong=sum(k in case['expected'] and case['expected'][k]!=v for k,v in actual.items())
        unexpected=sum(k not in case['expected'] for k in actual)
        missing=sum(k not in actual for k in case['expected'])
        results.append({'id':case['id'],'scan':case['scan'],'sha256':hashlib.sha256(content).hexdigest(),'correct_fields':correct,'expected_fields':len(case['expected']),
                        'wrong_fields':wrong,'unexpected_fields':unexpected,'missing_or_abstained':missing,'elapsed_seconds':round(elapsed,3),
                        'actual':actual,'expected':case['expected'],'all_critical_fields_require_confirmation':True,'metrics':result['metrics']})
        print(case['id']+f': {correct}/{len(case["expected"])} expected fields; {wrong} wrong, {missing} missing/abstained')
    summary={key:sum(r[key] for r in results) for key in ['correct_fields','expected_fields','wrong_fields','unexpected_fields','missing_or_abstained']}
    report={'dataset':dataset['dataset'],'split':dataset['split'],'independent_labels':False,'machine':{'platform':platform.system(),'processor':platform.processor(),'python':platform.python_version()},
            'notice':dataset['notice'],'summary':summary,'cases':results,'real_world_accuracy_established':False}
    (ROOT/'reports'/'development-document-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':run()

"""Verify alternative local OCR on a real public PDF without confirming its facts."""
import json
import time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from scripts.paddle_upload_rehearsal import login
ROOT=Path(__file__).resolve().parents[1]

def main():
    cases=json.loads((ROOT/'reports/demo-cases.json').read_text())['cases']
    application=next(c['application_id'] for c in cases if c['type']=='PUBLIC_DOCUMENT_REVIEW')
    with httpx.Client(base_url='http://127.0.0.1:8765',timeout=240) as officer:
        login(officer,'officer');before=officer.get('/v1/applications/'+application).json()
        document=next(d for d in before['documents'] if d['kind']=='FIRE_CERTIFICATE')
        started=time.monotonic();response=officer.post('/v1/documents/'+document['id']+'/ocr-comparisons',json={'page':1});response.raise_for_status()
        result=response.json();after=officer.get('/v1/applications/'+application).json()
        updated=next(d for d in after['documents'] if d['id']==document['id'])
        assert result['method']=='CPU_OCR_PADDLEOCR'
        assert document['fields']==updated['fields']
        assert all(not f['confirmed_by'] for f in updated['fields'])
        name_present=any('THIAGARAJAR SCHOOL OF MANAGEMENT' in ' '.join(line['text'].upper().split()) for line in result['lines'])
        assert name_present,'Expected public institution transcription was not recovered'
        report=dict(status='PASS',document_id=document['id'],source_sha256=document['sha256'],page=1,elapsed_seconds=round(time.monotonic()-started,3),
                    provider=result['method'],expected_name_present=True,accepted_facts_unchanged=True,all_critical_facts_unconfirmed=True,
                    independent_accuracy_established=False,notice='One development page and one visually checked phrase. Not a representative OCR accuracy claim.')
        (ROOT/'reports/public-ocr-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: real public page re-read with PaddleOCR; expected name recovered and accepted facts unchanged.')
if __name__=='__main__':main()

"""Local password login -> scan -> Defender -> PaddleOCR -> authorized preview."""
import json
import secrets
import time
from datetime import datetime,timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]

def login(client,persona):
    lines=(ROOT/'.data/local-access.txt').read_text(encoding='utf-8').splitlines()
    email=persona+'@demo.invalid'; index=lines.index(email)
    response=client.post('/v1/auth/login',json={'email':email,'password':lines[index+1].removeprefix('Password: ')})
    assert response.status_code==200,'Local password sign-in failed'

def main():
    started=time.monotonic()
    with httpx.Client(base_url='http://127.0.0.1:8765',timeout=30) as applicant,httpx.Client(base_url='http://127.0.0.1:8765',timeout=60) as officer:
        login(applicant,'institution');login(officer,'officer')
        response=applicant.post('/v1/applications',json={'name':'Synthetic PaddleOCR scan rehearsal','category':'EOA','evaluation_date':'2026-10-28'})
        response.raise_for_status();application=response.json()['id']
        source=ROOT/'.data/document-check/scan-occupancy.pdf'
        response=applicant.post(f'/v1/applications/{application}/documents',data={'kind':'OCCUPANCY'},
                                files={'file':('synthetic-scan.pdf',source.read_bytes(),'application/pdf')},headers={'Idempotency-Key':secrets.token_hex(16)})
        response.raise_for_status();job=response.json()['job_id'];document=response.json()['document_id']
        deadline=time.monotonic()+330
        while time.monotonic()<deadline:
            state=applicant.get('/v1/jobs/'+job).json()['status']
            if state in {'COMPLETED','FAILED'}:break
            time.sleep(1)
        assert state=='COMPLETED','Scanned upload did not complete'
        response=officer.get('/v1/applications/'+application);response.raise_for_status()
        detail=next(item for item in response.json()['documents'] if item['id']==document)
        expected={'BUILDING':'BLOCK C','COVERED_FLOORS':['G','1'],'VALID_UNTIL':'2027-06-30'}
        actual={f['key']:f['value'] for f in detail['fields']}
        assert actual==expected, 'Scan extraction differed from the synthetic fixture'
        assert all(not f['confirmed_by'] for f in detail['fields']), 'Critical candidates were auto-confirmed'
        assert all('PADDLEOCR' in f['engine'] for f in detail['fields']), 'Unexpected OCR provider'
        preview=officer.get(f'/v1/documents/{document}/pages/1')
        assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        assert any(v['type']=='MALWARE_SCAN' and v['mode']=='WINDOWS_DEFENDER' and v['status']=='NO_THREATS_DETECTED' for v in detail['verification_events'])
        signature=officer.post(f'/v1/documents/{document}/signature-checks');signature.raise_for_status()
        report=dict(status='PASS',at=datetime.now(timezone.utc).isoformat(),application_id=application,
                    document_id=document,elapsed_seconds=round(time.monotonic()-started,3),
                    checks=['Named local password login','Applicant upload','Actual Defender scan','Actual PaddleOCR extraction',
                            'Three exact synthetic expected fields','No automatic critical confirmation','Authorized stored preview','Offline signature check'],
                    fixture='SYNTHETIC_DEVELOPMENT_NOT_HELD_OUT',real_world_accuracy_established=False)
        (ROOT/'reports/paddle-upload-rehearsal.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: local password, upload, Defender, PaddleOCR, source preview and signature workflow.')

if __name__=='__main__':main()

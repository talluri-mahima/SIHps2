"""Prepare explicit public-document and synthetic rectification demo cases locally."""
import json
import secrets
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.seed import DEMO_DOCUMENTS,pdf_bytes
from scripts.paddle_upload_rehearsal import login
ROOT=Path(__file__).resolve().parents[1]

def create(applicant,name,category):
    existing=next((a for a in applicant.get('/v1/applications').json() if a['name']==name),None)
    if existing:return existing['id'],False
    result=applicant.post('/v1/applications',json=dict(name=name,category=category,evaluation_date='2026-10-28'));result.raise_for_status()
    return result.json()['id'],True

def upload(client,application,kind,content):
    result=client.post(f'/v1/applications/{application}/documents',data={'kind':kind},files={'file':(kind.lower()+'.pdf',content,'application/pdf')},headers={'Idempotency-Key':secrets.token_hex(16)});result.raise_for_status()
    deadline=time.monotonic()+320
    while time.monotonic()<deadline:
        state=client.get('/v1/jobs/'+result.json()['job_id']).json()['status']
        if state in {'COMPLETED','FAILED'}:break
        time.sleep(.2)
    if state!='COMPLETED':raise RuntimeError('Document processing failed')
    return result.json()['document_id']

def confirm(officer,application,document):
    data=officer.get(f'/v1/applications/{application}').json()
    for field in next(d for d in data['documents'] if d['id']==document)['fields']:
        if field['confirmed_by']:continue
        response=officer.patch('/v1/fields/'+field['id'],json=dict(raw_value=field['raw'],reason='Automated SYNTHETIC rehearsal only: checked the generated fixture expected value; not a real officer scrutiny.'),headers={'If-Match':str(field['revision'])});response.raise_for_status()

def main():
    report={'notice':'Local demonstration cases. No real application or issuer authentication is implied. Synthetic automatic review actions are explicitly labelled in their audit reasons.','cases':[]}
    with httpx.Client(base_url='http://127.0.0.1:8765',timeout=240) as applicant,httpx.Client(base_url='http://127.0.0.1:8765',timeout=240) as officer:
        login(applicant,'institution');login(officer,'officer')
        public,new=create(applicant,'Public TSM documents — review only, issuer unverified','EOA')
        if new:
            for name,kind in [('tsm-occupancy','OCCUPANCY'),('tsm-fire','FIRE_CERTIFICATE')]:
                upload(applicant,public,kind,(ROOT/'.data/public-documents'/f'{name}.pdf').read_bytes())
        report['cases'].append(dict(application_id=public,name='Public TSM documents — review only, issuer unverified',type='PUBLIC_DOCUMENT_REVIEW',critical_facts='UNCONFIRMED',issuer='NOT_VERIFIED'))
        synthetic,new=create(applicant,'ScopeGuard — completed SYNTHETIC rectification','NEW_INSTITUTION')
        if new:
            for kind,lines in DEMO_DOCUMENTS.items():
                document=upload(applicant,synthetic,kind,pdf_bytes(kind,lines));confirm(officer,synthetic,document)
            base=f'/v1/applications/{synthetic}'
            officer.post(base+'/evaluations').raise_for_status()
            finding=next(f for f in officer.get(base).json()['evaluation']['findings'] if f['reason']=='SCOPE_NOT_ESTABLISHED')
            action='/v1/findings/'+finding['id']+'/actions'
            result=officer.post(action,json=dict(action='REQUEST_CLARIFICATION',reason='SYNTHETIC rehearsal: provide occupancy evidence for BLOCK C including floor 2.'),headers={'If-Match':'1'});result.raise_for_status()
            applicant.post(action,json=dict(action='RESPOND',reason='SYNTHETIC rehearsal: replacement certificate covering floor 2 is being submitted.'),headers={'If-Match':'2'}).raise_for_status()
            replacement=upload(applicant,synthetic,'OCCUPANCY',pdf_bytes('OCCUPANCY',['BUILDING: BLOCK C','COVERED_FLOORS: G, 1, 2','VALID_UNTIL: 2027-06-30']))
            confirm(officer,synthetic,replacement)
            officer.post('/v1/documents/'+replacement+'/source-checks',json=dict(status='VERIFIED',mode='MOCK',note='SYNTHETIC issuer fixture only. This is not an AICTE, municipality or bank response.')).raise_for_status()
            evaluation=officer.post(base+'/evaluations');evaluation.raise_for_status()
            officer.post('/v1/findings/'+finding['id']+'/resolve-after-review',json=dict(evaluation_id=evaluation.json()['id'],supporting_document_ids=[replacement],reason='Automated SYNTHETIC rehearsal: confirmed replacement scope covers G, 1 and 2. Mock source mode retained.'),headers={'If-Match':'3'}).raise_for_status()
            exported=officer.post(base+'/exports');exported.raise_for_status()
            folder=ROOT/'.data/submission';folder.mkdir(exist_ok=True)
            (folder/'synthetic-rectification-report.pdf').write_bytes(officer.get('/v1/exports/'+exported.json()['id']+'/pdf').content)
        report['cases'].append(dict(application_id=synthetic,name='ScopeGuard — completed SYNTHETIC rectification',type='SYNTHETIC_END_TO_END',source_mode='MOCK'))
    (ROOT/'reports/demo-cases.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Prepared public-document review and completed synthetic rectification cases. No real evidence was auto-confirmed.')
if __name__=='__main__':main()

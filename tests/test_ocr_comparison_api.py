import json
import subprocess
from app.main import app
from test_api import upload


def test_ocr_comparison_keeps_original_and_confirmed_facts_unchanged(clients,fresh_app,monkeypatch):
    result,original=upload(clients['institution'],fresh_app)
    officer=clients['officer'];base='/v1/applications/'+fresh_app;document=result['document_id']
    before=officer.get(base).json();fields=before['documents'][0]['fields']
    for field in fields:
        response=officer.patch('/v1/fields/'+field['id'],json={'raw_value':field['raw'],'reason':'Reviewed the original fixture before OCR comparison.'},headers={'If-Match':str(field['revision'])})
        assert response.status_code==200
    before=officer.get(base).json()
    payload={'method':'CPU_OCR_PADDLEOCR','lines':[{'text':'Alternative transcription','bbox':[.1,.1,.8,.2],'score':.95}],'automatic_accepted_fields':0,'notice':'Review required'}
    def run(command,**kwargs):
        assert command[1:3]==['-m','app.ocr_compare'] and kwargs['timeout']==210
        return subprocess.CompletedProcess(command,0,stdout=json.dumps(payload),stderr='')
    monkeypatch.setattr('app.main.subprocess.run',run)
    path='/v1/documents/'+document+'/ocr-comparisons'
    for persona in ['institution','auditor']:
        assert clients[persona].post(path,json={'page':1}).status_code==403
    assert officer.post(path,json={'page':2}).status_code==409
    response=officer.post(path,json={'page':1})
    assert response.status_code==201,response.text
    after=officer.get(base).json()
    assert before['documents'][0]['fields']==after['documents'][0]['fields']
    assert after['revision']>before['revision']
    assert after['documents'][0]['verification_events'][0]['type']=='OCR_COMPARISON'
    assert officer.get('/v1/documents/'+document+'/original').content==original


def test_failed_comparison_never_changes_facts(clients,fresh_app,monkeypatch):
    result,_=upload(clients['institution'],fresh_app);officer=clients['officer'];base='/v1/applications/'+fresh_app
    before=officer.get(base).json()
    def fail(*args,**kwargs):raise subprocess.TimeoutExpired('ocr',210)
    monkeypatch.setattr('app.main.subprocess.run',fail)
    assert officer.post('/v1/documents/'+result['document_id']+'/ocr-comparisons',json={'page':1}).status_code==503
    after=officer.get(base).json()
    assert before['documents'][0]['fields']==after['documents'][0]['fields']

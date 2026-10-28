import json
import secrets
import time
import pymupdf as fitz
from app.seed import pdf_bytes,DEMO_DOCUMENTS


def submit(client,app_id,kind,lines):
    content=pdf_bytes(kind,lines)
    result=client.post(f'/v1/applications/{app_id}/documents',data={'kind':kind},files={'file':('synthetic.pdf',content,'application/pdf')},headers={'Idempotency-Key':secrets.token_hex(16)})
    assert result.status_code==202,result.text
    job=result.json()['job_id'];deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        status=client.get('/v1/jobs/'+job).json()['status']
        if status in {'FAILED','COMPLETED'}:break
        time.sleep(.05)
    assert status=='COMPLETED'
    return result.json()['document_id'],content


def confirm(client,base,doc_id):
    document=next(d for d in client.get(base).json()['documents'] if d['id']==doc_id)
    for field in document['fields']:
        if field['confirmed_by']:continue
        response=client.patch('/v1/fields/'+field['id'],json={'raw_value':field['raw'],'reason':'Checked the exact synthetic source region and value.'},headers={'If-Match':str(field['revision'])})
        assert response.status_code==200,response.text


def test_full_clarification_replacement_resolution_and_pdf_history(clients,fresh_app):
    officer,applicant=clients['officer'],clients['institution'];base='/v1/applications/'+fresh_app
    originals={}
    for kind,lines in DEMO_DOCUMENTS.items():
        doc_id,data=submit(applicant,fresh_app,kind,lines);originals[kind]=(doc_id,data);confirm(officer,base,doc_id)
    assert officer.post(base+'/evaluations').status_code==201
    detail=officer.get(base).json();finding=next(f for f in detail['evaluation']['findings'] if f['reason']=='SCOPE_NOT_ESTABLISHED')
    action='/v1/findings/'+finding['id']+'/actions';resolve='/v1/findings/'+finding['id']+'/resolve-after-review'
    response=officer.post(action,json={'action':'CONFIRM','reason':'Claimed second floor has no matching occupancy scope.'},headers={'If-Match':'1'});assert response.status_code==200
    assert officer.post(action,json={'action':'RESOLVE','reason':'Attempt to close without replacement proof.'},headers={'If-Match':'2'}).status_code==409
    response=officer.post(action,json={'action':'REQUEST_CLARIFICATION','reason':'Please provide current occupancy evidence for BLOCK C covering floor 2.'},headers={'If-Match':'2'});assert response.status_code==200
    response=applicant.post(action,json={'action':'RESPOND','reason':'A corrected synthetic certificate covering floor 2 will be submitted.'},headers={'If-Match':'3'});assert response.status_code==200
    frozen=officer.post(base+'/exports').json()
    replacement,_=submit(applicant,fresh_app,'OCCUPANCY',['BUILDING: BLOCK C','COVERED_FLOORS: G, 1, 2','VALID_UNTIL: 2027-06-30'])
    assert officer.post(base+'/exports').status_code==409
    assert applicant.get('/v1/documents/'+originals['OCCUPANCY'][0]+'/original').content==originals['OCCUPANCY'][1]
    confirm(officer,base,replacement)
    evaluation=officer.post(base+'/evaluations').json()['id']
    body={'evaluation_id':evaluation,'supporting_document_ids':[replacement],'reason':'New current occupancy evidence explicitly covers every claimed floor.'}
    assert clients['institution'].post(resolve,json=body,headers={'If-Match':'4'}).status_code==403
    assert clients['auditor'].post(resolve,json=body,headers={'If-Match':'4'}).status_code==403
    assert officer.post(resolve,json=body,headers={'If-Match':'4'}).status_code==409 # source unavailable
    assert officer.post('/v1/documents/'+replacement+'/source-checks',json={'status':'VERIFIED','mode':'MOCK','note':'Synthetic issuer fixture agrees with the replacement; not a real authority response.'}).status_code==200
    assert officer.post(resolve,json=body,headers={'If-Match':'4'}).status_code==409 # source event makes old evaluation stale
    body['evaluation_id']=officer.post(base+'/evaluations').json()['id']
    wrong=dict(body,supporting_document_ids=[originals['FDR_ADVICE'][0]])
    assert officer.post(resolve,json=wrong,headers={'If-Match':'4'}).status_code==409
    result=officer.post(resolve,json=body,headers={'If-Match':'4'})
    assert result.status_code==200,result.text
    assert result.json()['state']=='RESOLVED'
    assert officer.post(resolve,json=body,headers={'If-Match':'4'}).status_code==412
    assert officer.get('/v1/exports/'+frozen['id']).json()==frozen
    exported=officer.post(base+'/exports').json();history=exported['report']['rectification_history']
    assert len(history)==1 and history[0]['source_modes'][replacement]=='MOCK'
    pdf=officer.get('/v1/exports/'+exported['id']+'/pdf')
    with fitz.open(stream=pdf.content,filetype='pdf') as document:
        text=' '.join(page.get_text() for page in document)
    assert 'Reviewed rectification history' in text and 'MOCK' in text and finding['id'] in text
    assert officer.get(base+'/audit').json()['integrity']

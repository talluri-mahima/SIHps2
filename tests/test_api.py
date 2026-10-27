import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app import models as m
from app.db import Session
from app.seed import pdf_bytes


def upload(c, app_id, lines=None, key=None):
    data=pdf_bytes('OCCUPANCY',lines or ['BUILDING: BLOCK C','COVERED_FLOORS: G, 1'])
    r=c.post(f'/v1/applications/{app_id}/documents',data={'kind':'OCCUPANCY'},files={'file':('certificate.pdf',data,'application/pdf')},headers={'Idempotency-Key':key or secrets.token_hex(12)})
    assert r.status_code==202,r.text
    job=r.json()['job_id']
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        state=c.get('/v1/jobs/'+job).json()['status']
        if state in {'COMPLETED','FAILED'}:break
        time.sleep(.05)
    assert state=='COMPLETED'
    return r.json(),data


def test_unauthenticated_access_denied(server):
    with TestClient(app) as c:
        assert c.get('/v1/applications').status_code==401


def test_officer_only_sees_assigned_application(clients):
    assert all(a['name']!='Separate institution • access test' for a in clients['officer'].get('/v1/applications').json())


def test_cross_tenant_and_unassigned_officer_denied(clients):
    with Session() as db:
        other=db.scalar(select(m.User).where(m.User.email=='other@demo.invalid'))
        target=db.scalar(select(m.Application).where(m.Application.tenant=='institution-b'))
        token=secrets.token_urlsafe(32)
        with Session.begin() as w:
            w.add(m.LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=other.id,expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    for name in ['officer','institution']:
        assert clients[name].get('/v1/applications/'+target.id).status_code==404
    c=TestClient(app);c.cookies.set('aicte_session',token)
    first=clients['institution'].get('/v1/applications').json()[0]['id']
    assert c.get('/v1/applications/'+first).status_code==404
    c.close()


def test_auditor_cannot_mutate(clients,fresh_app):
    c=clients['auditor']
    assert c.post('/v1/applications/'+fresh_app+'/evaluations').status_code==403
    assert c.post('/v1/applications/'+fresh_app+'/exports').status_code==403


def test_applicant_cannot_confirm_or_evaluate(clients,fresh_app):
    c=clients['institution']
    assert c.post('/v1/applications/'+fresh_app+'/evaluations').status_code==403


def test_extra_application_fields_rejected(clients):
    r=clients['institution'].post('/v1/applications',json={'name':'Test school','category':'EOA','evaluation_date':'2026-10-27','tenant':'institution-b'})
    assert r.status_code==422


def test_origin_and_host_boundaries(clients):
    assert clients['officer'].post('/v1/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403
    assert clients['officer'].get('/v1/health',headers={'Host':'evil.example'}).status_code==400


def test_upload_extract_and_box_provenance(clients,fresh_app):
    result,content=upload(clients['institution'],fresh_app)
    d=clients['officer'].get('/v1/applications/'+fresh_app).json()['documents'][0]
    assert d['sha256']==hashlib.sha256(content).hexdigest()
    assert d['status']=='EXTRACTED' and d['pages']==1
    assert len(d['fields'])==2 and all(not f['confirmed_by'] for f in d['fields'])
    assert all(0<=v<=1 for f in d['fields'] for v in f['bbox'])
    assert clients['officer'].get('/v1/documents/'+d['id']+'/pages/1').headers['content-type']=='image/png'
    with TestClient(app) as c:
        assert c.get('/v1/documents/'+d['id']+'/original').status_code==401


def test_idempotency_and_payload_conflict(clients,fresh_app):
    c=clients['institution'];key=secrets.token_hex(12)
    first,content=upload(c,fresh_app,key=key)
    second=c.post('/v1/applications/'+fresh_app+'/documents',data={'kind':'OCCUPANCY'},files={'file':('same.pdf',content,'application/pdf')},headers={'Idempotency-Key':key})
    assert second.status_code==202 and second.json()==first
    changed=pdf_bytes('OCCUPANCY',['BUILDING: OTHER'])
    conflict=c.post('/v1/applications/'+fresh_app+'/documents',data={'kind':'OCCUPANCY'},files={'file':('different.pdf',changed,'application/pdf')},headers={'Idempotency-Key':key})
    assert conflict.status_code==409


@pytest.mark.parametrize('filename,body,status',[('fake.pdf',b'<script>evil</script>',415),('bad.txt',b'%PDF-x',415),('big.pdf',b'%PDF-'+b'x'*(10*1024*1024),413)],ids=['fake-pdf','wrong-extension','oversize-pdf'])
def test_upload_rejects_invalid_content(clients,fresh_app,filename,body,status):
    r=clients['institution'].post('/v1/applications/'+fresh_app+'/documents',data={'kind':'OCCUPANCY'},files={'file':(filename,body,'application/pdf')},headers={'Idempotency-Key':secrets.token_hex(12)})
    assert r.status_code==status


def test_confirmation_is_append_only_and_compare_and_swap(clients,fresh_app):
    upload(clients['institution'],fresh_app)
    d=clients['officer'].get('/v1/applications/'+fresh_app).json()['documents'][0]
    f=d['fields'][0];body={'raw_value':str(f['value']),'reason':'Compared carefully with the original.'}
    path='/v1/fields/'+f['id'];headers={'If-Match':'1'}
    assert clients['institution'].patch(path,json=body,headers=headers).status_code==403
    r=clients['officer'].patch(path,json=body,headers=headers)
    assert r.status_code==200
    assert clients['officer'].patch(path,json=body,headers=headers).status_code==412
    with Session() as db:
        original=db.get(m.Field,f['id']);latest=db.get(m.Field,r.json()['id'])
        assert original.confirmed_by is None and latest.previous_id==original.id


def test_export_confirmed_only_and_replacement_stales(clients,fresh_app):
    officer=clients['officer'];base='/v1/applications/'+fresh_app
    assert officer.post(base+'/exports').status_code==409
    assert officer.post(base+'/evaluations').status_code==201
    detail=officer.get(base).json();findings=detail['evaluation']['findings']
    assert officer.post(base+'/exports').json()['report']['confirmed_findings']==[]
    f=findings[0];path='/v1/findings/'+f['id']+'/actions';body={'action':'CONFIRM','reason':'Reviewed missing evidence against the current inventory.'}
    assert clients['institution'].post(path,json=body,headers={'If-Match':'1'}).status_code==403
    assert officer.post(path,json=body,headers={'If-Match':'1'}).status_code==200
    assert officer.post(path,json=body,headers={'If-Match':'1'}).status_code==412
    result=officer.post(base+'/exports').json()
    assert len(result['report']['confirmed_findings'])==1
    upload(clients['institution'],fresh_app)
    assert officer.get(base).json()['evaluation']['stale']
    assert officer.post(base+'/exports').status_code==409
    assert officer.get('/v1/exports/'+result['id']).json()==result
    assert officer.post(path,json={'action':'RESOLVE','reason':'Replacement uploaded, unverified.'},headers={'If-Match':'3'}).status_code==409


def test_versions_preserved(clients,fresh_app):
    first,content=upload(clients['institution'],fresh_app)
    second,_=upload(clients['institution'],fresh_app,['BUILDING: BLOCK C','COVERED_FLOORS: G, 1, 2'])
    assert second['version']==2
    versions=clients['officer'].get('/v1/documents/'+second['document_id']+'/versions').json()
    assert [v['version'] for v in versions]==[2,1]
    assert clients['institution'].get('/v1/documents/'+first['document_id']+'/original').content==content


def test_source_unavailable_not_verified(clients,fresh_app):
    uploaded,_=upload(clients['institution'],fresh_app)
    path='/v1/documents/'+uploaded['document_id']+'/source-checks'
    r=clients['officer'].post(path,json={'status':'SOURCE_UNAVAILABLE','mode':'MOCK','note':'Mock issuer timed out; no authentication established.'})
    assert r.json()=={'status':'SOURCE_UNAVAILABLE','mode':'MOCK'}
    assert clients['institution'].post(path,json={'status':'VERIFIED','mode':'MANUAL','note':'Applicant tries self attestation.'}).status_code==403


def test_audit_chain_and_manifest_reproducibility(clients,fresh_app):
    c=clients['officer'];base='/v1/applications/'+fresh_app
    a=c.post(base+'/evaluations').json();b=c.post(base+'/evaluations').json()
    assert a['manifest_hash']==b['manifest_hash']
    manifest=c.get('/v1/evaluations/'+a['id']+'/manifest').json()
    from app.rules import digest
    assert digest(manifest['manifest'])==manifest['sha256']
    audit=c.get(base+'/audit').json()
    assert audit['integrity'] and len(audit['events'])>=3


def test_logout_revokes_server_session(clients):
    c=clients['officer'];token=c.cookies.get('aicte_session')
    c.post('/v1/auth/logout');c.cookies.set('aicte_session',token)
    assert c.get('/v1/auth/me').status_code==401


def test_production_profile_fails_closed():
    import os
    from app.config import validate_environment
    old=os.environ['APP_ENV']
    try:
        os.environ['APP_ENV']='production'
        with pytest.raises(RuntimeError):validate_environment()
    finally:os.environ['APP_ENV']=old

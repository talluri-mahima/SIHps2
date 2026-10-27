import hashlib
import json
import secrets
import threading
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PField
from sqlalchemy import select
from . import models as m
from .config import DATA, ROOT, MAX_BYTES, SOFTWARE_VERSION
from .db import Session, initialize
from .rules import CHECKLISTS, KINDS, RULEPACK, RULEPACK_HASH, canonical, digest
from .service import WRITE_LOCK, audit, scoped, document_scope, latest_fields, latest_documents, invalidate, run_job, run_evaluation
from .extract import normalize, ALLOWED

hasher = PasswordHasher()
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    initialize()
    from .seed import seed
    seed()
    with WRITE_LOCK, Session.begin() as db:
        jobs = db.scalars(select(m.Job).where(m.Job.status.in_(['QUEUED', 'PROCESSING', 'RETRY']))).all()
        ids = []
        for j in jobs:
            if j.attempt >= 3:
                j.status = 'FAILED'
                db.get(m.Document, j.document_id).status = 'QUARANTINED'
            else:
                j.status = 'QUEUED'
                ids.append(j.id)
    def drain():
        for job_id in ids:
            run_job(job_id)
    threading.Thread(target=drain, daemon=True).start()
    yield


app = FastAPI(title='AICTE Evidence Workbench', version=SOFTWARE_VERSION, lifespan=lifespan)


@app.middleware('http')
async def boundary(request: Request, call_next):
    host = request.url.hostname
    if host not in {'localhost', '127.0.0.1', '::1', 'testserver'}:
        return JSONResponse({'detail': 'Development server accepts loopback hosts only'}, status_code=400)
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        origin = request.headers.get('origin')
        if origin and (urlparse(origin).hostname != host or urlparse(origin).scheme not in {'http', 'https'} or urlparse(origin).port not in {None, 80, 443, 5173, 8765}):
            return JSONResponse({'detail': 'Origin rejected'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-site mutation rejected'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; frame-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
    return response


def db_session():
    with Session() as db:
        yield db


def current_user(request: Request, db=Depends(db_session)):
    token = request.cookies.get('aicte_session')
    row = db.get(m.LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not row or datetime.fromisoformat(row.expires) < datetime.now(timezone.utc):
        raise HTTPException(401, 'Sign in to continue')
    user = db.get(m.User, row.user_id)
    if not user:
        raise HTTPException(401, 'Sign in to continue')
    return user


def officer(user):
    if user.role != 'OFFICER':
        raise HTTPException(403, 'An assigned scrutiny officer is required')


class StrictModel(BaseModel):
    class Config:
        extra = 'forbid'


class Login(StrictModel):
    email: str = PField(min_length=3, max_length=200)
    password: str = PField(min_length=1, max_length=200)


class NewApplication(StrictModel):
    name: str = PField(min_length=3, max_length=120)
    category: Literal['NEW_INSTITUTION', 'EOA']
    evaluation_date: date


class Correction(StrictModel):
    raw_value: str = PField(min_length=1, max_length=200)
    reason: str = PField(min_length=5, max_length=500)


class Action(StrictModel):
    action: Literal['CONFIRM', 'DISMISS', 'RESOLVE', 'RESPOND', 'VERIFY']
    reason: str = PField(min_length=5, max_length=1000)


class SourceCheck(StrictModel):
    status: Literal['VERIFIED', 'MISMATCH', 'SOURCE_UNAVAILABLE', 'PENDING']
    mode: Literal['MANUAL', 'MOCK']
    note: str = PField(min_length=10, max_length=1000)


@app.get('/v1/health')
def health():
    return {'status': 'ok', 'version': SOFTWARE_VERSION, 'profile': 'development', 'production_ready': False,
            'gates_pending': ['OIDC', 'POSTGRES_RLS', 'MALWARE_SCANNING', 'OS_PARSER_ISOLATION', 'OCR', 'POLICY_APPROVAL', 'SEALED_BENCHMARK']}


@app.get('/v1/dev/personas')
def personas():
    return {'notice': 'Local synthetic development workspace. No government connection.',
            'personas': [{'id': 'officer', 'name': 'Scrutiny officer', 'email': 'officer@demo.invalid'},
                         {'id': 'institution', 'name': 'Institution applicant', 'email': 'institution@demo.invalid'},
                         {'id': 'auditor', 'name': 'Read-only auditor', 'email': 'auditor@demo.invalid'}]}


def issue_session(db, user, response):
    token = secrets.token_urlsafe(48)
    db.add(m.LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                          expires=(datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()))
    response.set_cookie('aicte_session', token, httponly=True, samesite='strict', max_age=28800, path='/')
    return {'id': user.id, 'name': user.name, 'role': user.role, 'tenant': user.tenant}


@app.post('/v1/dev/session/{persona}')
def demo_session(persona: Literal['officer', 'institution', 'auditor'], response: Response, request: Request):
    if request.client and request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
        raise HTTPException(403, 'Local development access only')
    with WRITE_LOCK, Session.begin() as db:
        user = db.scalar(select(m.User).where(m.User.email == f'{persona}@demo.invalid'))
        return issue_session(db, user, response)


@app.post('/v1/auth/login')
def login(body: Login, response: Response, request: Request):
    bucket = (request.client.host if request.client else 'unknown', body.email.lower())
    with LOGIN_LOCK:
        recent = [t for t in LOGIN_ATTEMPTS.get(bucket, []) if t > datetime.now(timezone.utc) - timedelta(minutes=5)]
        if len(recent) >= 8:
            raise HTTPException(429, 'Too many attempts; try later')
        LOGIN_ATTEMPTS[bucket] = recent + [datetime.now(timezone.utc)]
    with WRITE_LOCK, Session.begin() as db:
        user = db.scalar(select(m.User).where(m.User.email == body.email.lower()))
        try:
            if not user or not hasher.verify(user.password_hash, body.password):
                raise HTTPException(401, 'Invalid credentials')
        except VerificationError:
            raise HTTPException(401, 'Invalid credentials')
        return issue_session(db, user, response)


@app.get('/v1/auth/me')
def me(user=Depends(current_user)):
    return {'id': user.id, 'name': user.name, 'role': user.role, 'tenant': user.tenant}


@app.post('/v1/auth/logout')
def logout(request: Request, response: Response):
    token = request.cookies.get('aicte_session')
    with WRITE_LOCK, Session.begin() as db:
        row = db.get(m.LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
        if row:
            db.delete(row)
    response.delete_cookie('aicte_session', path='/')
    return {'signed_out': True}


@app.get('/v1/application-types')
def application_types(user=Depends(current_user)):
    return {'types': CHECKLISTS, 'rulepack': RULEPACK, 'hash': RULEPACK_HASH}


@app.get('/v1/applications')
def applications(user=Depends(current_user), db=Depends(db_session)):
    q = select(m.Application).order_by(m.Application.created_at.desc())
    q = q.where(m.Application.tenant == user.tenant) if user.role == 'SUBMITTER' else q.where(m.Application.id.in_(select(m.Assignment.application_id).where(m.Assignment.user_id == user.id)))
    return [{'id': a.id, 'name': a.name, 'category': a.category, 'academic_year': a.academic_year, 'revision': a.revision, 'synthetic': bool(a.synthetic)} for a in db.scalars(q)]


@app.post('/v1/applications', status_code=201)
def new_application(body: NewApplication, user=Depends(current_user)):
    if user.role != 'SUBMITTER':
        raise HTTPException(403, 'Institution applicants create applications')
    with WRITE_LOCK, Session.begin() as db:
        a = m.Application(tenant=user.tenant, name=body.name.strip(), category=body.category, evaluation_date=body.evaluation_date.isoformat())
        db.add(a)
        db.flush()
        # Explicit development assignment to the known synthetic officer/auditor.
        for u in db.scalars(select(m.User).where(m.User.role.in_(['OFFICER', 'AUDITOR']))):
            if u.email in {'officer@demo.invalid', 'auditor@demo.invalid'}:
                db.add(m.Assignment(user_id=u.id, application_id=a.id))
        audit(db, a, user.id, 'APPLICATION_CREATED', {'category': a.category, 'synthetic': True})
        return {'id': a.id}


@app.get('/v1/applications/{app_id}')
def application_detail(app_id: str, user=Depends(current_user), db=Depends(db_session)):
    a = scoped(db, user, app_id)
    docs = latest_documents(db, app_id)
    ev = db.scalar(select(m.Evaluation).where(m.Evaluation.application_id == app_id).order_by(m.Evaluation.created_at.desc()).limit(1))
    evaluation = None
    if ev:
        evaluation = {'id': ev.id, 'revision': ev.revision, 'manifest_hash': ev.manifest_hash, 'created_at': ev.created_at,
                      'stale': ev.revision != a.revision, **json.loads(ev.result_json)}
        evaluation['findings'] = [{'id': f.id, 'state': f.state, 'version': f.version, **json.loads(f.body_json)} for f in db.scalars(select(m.Finding).where(m.Finding.evaluation_id == ev.id))]
    return {'id': a.id, 'name': a.name, 'category': a.category, 'academic_year': a.academic_year, 'evaluation_date': a.evaluation_date,
            'revision': a.revision, 'synthetic': bool(a.synthetic), 'rulepack': RULEPACK,
            'checklist': [{'kind': k, 'received': any(d.kind == k for d in docs)} for k in CHECKLISTS[a.category]],
            'documents': [{'id': d.id, 'kind': d.kind, 'version': d.version, 'filename': d.filename, 'status': d.status,
                           'sha256': d.sha256, 'pages': d.page_count, 'source_status': d.source_status, 'source_mode': d.source_mode,
                           'fields': list(latest_fields(db, d.id).values())} for d in docs],
            'evaluation': evaluation, 'document_kinds': KINDS}


@app.post('/v1/applications/{app_id}/documents', status_code=202)
async def upload(app_id: str, file: UploadFile = File(...), kind: str = Form(...), idempotency_key: str = Header(..., alias='Idempotency-Key'), user=Depends(current_user)):
    if user.role != 'SUBMITTER':
        raise HTTPException(403, 'Institution applicants submit evidence')
    if kind not in KINDS or not 8 <= len(idempotency_key) <= 128:
        raise HTTPException(422, 'Unknown document type or invalid idempotency key')
    with Session() as db:
        scoped(db, user, app_id)
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, 'Maximum PDF size is 10 MB')
    if not (file.filename or '').lower().endswith('.pdf') or not content.startswith(b'%PDF-'):
        raise HTTPException(415, 'PDF bytes and .pdf filename are required')
    sha = hashlib.sha256(content).hexdigest()
    payload_hash = digest({'sha': sha, 'kind': kind})
    idem = digest([user.id, app_id, 'upload', idempotency_key])
    with WRITE_LOCK, Session.begin() as db:
        a = scoped(db, user, app_id, True)
        old = db.get(m.Idempotency, idem)
        if old:
            if old.payload_hash != payload_hash:
                raise HTTPException(409, 'Idempotency key was already used with different evidence')
            return json.loads(old.response_json)
        versions = db.scalars(select(m.Document).where(m.Document.application_id == app_id, m.Document.kind == kind)).all()
        key = f'{m.uid()}.pdf'
        (DATA / 'objects' / key).write_bytes(content)
        d = m.Document(application_id=app_id, kind=kind, version=max([v.version for v in versions], default=0)+1,
                       filename=(file.filename or 'evidence.pdf').replace('\\', '/').split('/')[-1][:180], object_key=key, sha256=sha, size=len(content))
        db.add(d)
        db.flush()
        j = m.Job(document_id=d.id)
        db.add(j)
        db.flush()
        invalidate(db, a, user.id, {'document_id': d.id, 'kind': kind, 'version': d.version})
        audit(db, a, user.id, 'DOCUMENT_SUBMITTED', {'document_id': d.id, 'sha256': sha, 'scan_mode': 'DEVELOPMENT_NO_MALWARE_PROVIDER'})
        result = {'document_id': d.id, 'job_id': j.id, 'version': d.version}
        db.add(m.Idempotency(key=idem, payload_hash=payload_hash, response_json=canonical(result)))
    threading.Thread(target=run_job, args=(result['job_id'],), daemon=True).start()
    return result


@app.get('/v1/documents/{doc_id}/original')
def original(doc_id: str, user=Depends(current_user), db=Depends(db_session)):
    _, d = document_scope(db, user, doc_id)
    if d.status not in {'EXTRACTED', 'MANUAL_EXTRACTION_REQUIRED', 'OCR_REQUIRED'}:
        raise HTTPException(409, 'Document is not available for viewing')
    return FileResponse(DATA / 'objects' / d.object_key, media_type='application/pdf', filename='evidence.pdf', content_disposition_type='inline')


@app.get('/v1/documents/{doc_id}/pages/{page_no}')
def page_image(doc_id: str, page_no: int, user=Depends(current_user), db=Depends(db_session)):
    _, d = document_scope(db, user, doc_id)
    if d.status != 'EXTRACTED' or not 1 <= page_no <= d.page_count:
        raise HTTPException(404, 'Page unavailable')
    # Small accepted native PDFs only; general rendering isolation remains gated.
    import pymupdf as fitz
    with fitz.open(DATA / 'objects' / d.object_key) as pdf:
        data = pdf[page_no-1].get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).tobytes('png')
    return Response(data, media_type='image/png')


@app.get('/v1/documents/{doc_id}/versions')
def versions(doc_id: str, user=Depends(current_user), db=Depends(db_session)):
    a, d = document_scope(db, user, doc_id)
    return [{'id': v.id, 'version': v.version, 'sha256': v.sha256, 'status': v.status, 'created_at': v.created_at}
            for v in db.scalars(select(m.Document).where(m.Document.application_id == a.id, m.Document.kind == d.kind).order_by(m.Document.version.desc()))]


@app.get('/v1/jobs/{job_id}')
def job_status(job_id: str, user=Depends(current_user), db=Depends(db_session)):
    j = db.get(m.Job, job_id)
    if not j:
        raise HTTPException(404, 'Job not found')
    document_scope(db, user, j.document_id)
    return {'id': j.id, 'status': j.status, 'attempt': j.attempt, 'error': j.error}


@app.patch('/v1/fields/{field_id}')
def correct(field_id: str, body: Correction, if_match: str = Header(..., alias='If-Match'), user=Depends(current_user)):
    officer(user)
    with WRITE_LOCK, Session.begin() as db:
        f = db.get(m.Field, field_id)
        if not f:
            raise HTTPException(404, 'Field not found')
        a, d = document_scope(db, user, f.document_id, True)
        current = latest_fields(db, d.id)[f.key]
        if current['id'] != field_id or if_match != str(f.revision):
            raise HTTPException(412, 'Field has changed; refresh before editing')
        try:
            val = normalize(f.key, body.raw_value)
        except Exception:
            raise HTTPException(422, 'Value does not match the supported field format')
        revision = m.Field(document_id=d.id, key=f.key, raw=f.raw, value_json=canonical(val), page=f.page,
                           bbox_json=f.bbox_json, engine=f.engine, revision=f.revision+1, previous_id=f.id,
                           confirmed_by=user.id, reason=body.reason)
        db.add(revision)
        db.flush()
        invalidate(db, a, user.id, {'field_id': revision.id, 'previous_id': f.id})
        audit(db, a, user.id, 'FIELD_CONFIRMED_OR_CORRECTED', {'field_id': revision.id, 'reason': body.reason})
        return {'id': revision.id, 'revision': revision.revision}


@app.post('/v1/documents/{doc_id}/source-checks')
def source_check(doc_id: str, body: SourceCheck, user=Depends(current_user)):
    officer(user)
    with WRITE_LOCK, Session.begin() as db:
        a, d = document_scope(db, user, doc_id, True)
        d.source_status, d.source_mode, d.source_note = body.status, body.mode, body.note
        invalidate(db, a, user.id, {'source_document': doc_id})
        audit(db, a, user.id, 'SOURCE_ATTESTATION_RECORDED', {'document_id': doc_id, 'mode': body.mode, 'status': body.status, 'note': body.note})
        return {'status': d.source_status, 'mode': d.source_mode}


@app.post('/v1/applications/{app_id}/evaluations', status_code=201)
def evaluate_application(app_id: str, user=Depends(current_user)):
    officer(user)
    with WRITE_LOCK, Session.begin() as db:
        a = scoped(db, user, app_id, True)
        ev = run_evaluation(db, a, user.id)
        return {'id': ev.id, 'manifest_hash': ev.manifest_hash}


@app.get('/v1/evaluations/{evaluation_id}/manifest')
def manifest(evaluation_id: str, user=Depends(current_user), db=Depends(db_session)):
    ev = db.get(m.Evaluation, evaluation_id)
    if not ev:
        raise HTTPException(404, 'Evaluation not found')
    scoped(db, user, ev.application_id)
    return {'manifest': json.loads(ev.manifest_json), 'sha256': ev.manifest_hash, 'result': json.loads(ev.result_json)}


@app.post('/v1/findings/{finding_id}/actions')
def finding_action(finding_id: str, body: Action, if_match: str = Header(..., alias='If-Match'), user=Depends(current_user)):
    with WRITE_LOCK, Session.begin() as db:
        f = db.get(m.Finding, finding_id)
        if not f:
            raise HTTPException(404, 'Finding not found')
        a = scoped(db, user, f.application_id, True)
        if if_match != str(f.version):
            raise HTTPException(412, 'Finding changed; refresh before reviewing')
        ev = db.get(m.Evaluation, f.evaluation_id)
        latest_ev = db.scalar(select(m.Evaluation).where(m.Evaluation.application_id == a.id).order_by(m.Evaluation.created_at.desc()).limit(1))
        if latest_ev.id != ev.id:
            raise HTTPException(409, 'This finding belongs to a historical evaluation')
        if body.action == 'RESPOND':
            if user.role != 'SUBMITTER' or f.state not in {'OPEN', 'VERIFICATION_PENDING', 'RESPONSE_RECEIVED'}:
                raise HTTPException(403, 'Applicant response is not available')
            target = 'RESPONSE_RECEIVED'
        else:
            officer(user)
            if ev.revision != a.revision:
                raise HTTPException(409, 'Evidence changed; run a new evaluation')
            transitions = {'CONFIRM': ({'OPEN', 'RESPONSE_RECEIVED', 'VERIFICATION_PENDING'}, 'REVIEWER_CONFIRMED'),
                           'DISMISS': ({'OPEN', 'RESPONSE_RECEIVED', 'VERIFICATION_PENDING'}, 'DISMISSED'),
                           'VERIFY': ({'RESPONSE_RECEIVED'}, 'VERIFICATION_PENDING'),
                           'RESOLVE': ({'REVIEWER_CONFIRMED'}, 'RESOLVED')}
            allowed, target = transitions[body.action]
            if f.state not in allowed:
                raise HTTPException(409, 'Invalid finding transition')
        f.state, f.version, f.updated_at = target, f.version+1, m.now()
        audit(db, a, user.id, 'FINDING_' + target, {'finding_id': f.id, 'reason': body.reason})
        return {'state': f.state, 'version': f.version}


@app.post('/v1/applications/{app_id}/exports', status_code=201)
def export(app_id: str, user=Depends(current_user)):
    officer(user)
    with WRITE_LOCK, Session.begin() as db:
        a = scoped(db, user, app_id, True)
        ev = db.scalar(select(m.Evaluation).where(m.Evaluation.application_id == app_id).order_by(m.Evaluation.created_at.desc()).limit(1))
        if not ev or ev.revision != a.revision:
            raise HTTPException(409, 'Run an evaluation against current evidence first')
        findings = db.scalars(select(m.Finding).where(m.Finding.evaluation_id == ev.id, m.Finding.state == 'REVIEWER_CONFIRMED')).all()
        body = {'application_id': a.id, 'name': a.name, 'synthetic': True, 'report_type': 'DEMONSTRATION_REVIEW_NOT_OFFICIAL_DEFICIENCY',
                'policy_status': 'DRAFT_NOT_APPROVED', 'evaluation_id': ev.id, 'manifest_hash': ev.manifest_hash,
                'exported_by': user.id, 'created_at': m.now(), 'confirmed_findings': [{'id': f.id, **json.loads(f.body_json)} for f in findings]}
        row = m.Export(application_id=a.id, body_json=canonical(body), sha256=digest(body))
        db.add(row)
        db.flush()
        audit(db, a, user.id, 'DEMONSTRATION_REPORT_EXPORTED', {'export_id': row.id, 'sha256': row.sha256, 'confirmed_count': len(findings)})
        return {'id': row.id, 'sha256': row.sha256, 'report': body}


@app.get('/v1/exports/{export_id}')
def read_export(export_id: str, user=Depends(current_user), db=Depends(db_session)):
    row = db.get(m.Export, export_id)
    if not row:
        raise HTTPException(404, 'Export not found')
    scoped(db, user, row.application_id)
    return {'id': row.id, 'sha256': row.sha256, 'report': json.loads(row.body_json)}


@app.get('/v1/applications/{app_id}/audit')
def audit_log(app_id: str, user=Depends(current_user), db=Depends(db_session)):
    scoped(db, user, app_id)
    events = db.scalars(select(m.Audit).where(m.Audit.application_id == app_id).order_by(m.Audit.id)).all()
    previous, intact = '', True
    results = []
    for e in events:
        payload = {'application_id': e.application_id, 'actor': e.actor, 'action': e.action,
                   'detail': json.loads(e.detail_json), 'created_at': e.created_at, 'prev_hash': e.prev_hash}
        intact = intact and e.prev_hash == previous and e.event_hash == digest(payload)
        previous = e.event_hash
        results.append({'id': e.id, 'action': e.action, 'actor': e.actor, 'at': e.created_at, 'detail': payload['detail'], 'hash': e.event_hash})
    return {'integrity': intact, 'events': results, 'notice': 'Application hash chain; not tamper-proof against privileged database administrators.'}


if (ROOT / 'web' / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'web' / 'dist', html=True), name='web')

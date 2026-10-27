import hashlib
import json
import subprocess
import sys
import threading
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from . import models as m
from .config import DATA, ROOT, SOFTWARE_VERSION
from .db import Session
from .rules import canonical, digest, evaluate, RULEPACK_HASH

# One development API process. DB row locking is also used for PostgreSQL.
WRITE_LOCK = threading.RLock()


def audit(db, app, actor, action, detail):
    db.flush()
    previous = db.scalar(select(m.Audit).where(m.Audit.application_id == app.id).order_by(m.Audit.id.desc()).limit(1))
    payload = {'application_id': app.id, 'actor': actor, 'action': action, 'detail': detail, 'created_at': m.now(), 'prev_hash': previous.event_hash if previous else ''}
    row = m.Audit(application_id=app.id, actor=actor, action=action, detail_json=canonical(detail),
                  created_at=payload['created_at'], prev_hash=payload['prev_hash'], event_hash=digest(payload))
    db.add(row)
    db.flush()


def scoped(db, user, app_id, write=False):
    query = select(m.Application).where(m.Application.id == app_id)
    if write:
        query = query.with_for_update()
    app = db.scalar(query)
    allowed = app and ((user.role == 'SUBMITTER' and user.tenant == app.tenant) or
                       (user.role in {'OFFICER', 'AUDITOR'} and db.scalar(select(m.Assignment).where(m.Assignment.application_id == app_id, m.Assignment.user_id == user.id))))
    if not allowed:
        raise HTTPException(404, 'Application not found')
    if write and user.role == 'AUDITOR':
        raise HTTPException(403, 'Read-only role')
    return app


def document_scope(db, user, doc_id, write=False):
    doc = db.get(m.Document, doc_id)
    if not doc:
        raise HTTPException(404, 'Document not found')
    return scoped(db, user, doc.application_id, write), doc


def field_dict(f):
    return {'id': f.id, 'document_id': f.document_id, 'key': f.key, 'raw': f.raw, 'value': json.loads(f.value_json),
            'page': f.page, 'bbox': json.loads(f.bbox_json), 'engine': f.engine, 'revision': f.revision,
            'confirmed_by': f.confirmed_by, 'previous_id': f.previous_id}


def latest_fields(db, doc_id):
    fields = db.scalars(select(m.Field).where(m.Field.document_id == doc_id).order_by(m.Field.revision, m.Field.created_at)).all()
    return {f.key: field_dict(f) for f in fields}


def latest_documents(db, app_id):
    docs = db.scalars(select(m.Document).where(m.Document.application_id == app_id).order_by(m.Document.version)).all()
    return list({d.kind: d for d in docs}.values())


def invalidate(db, app, actor, detail):
    app.revision += 1
    for f in db.scalars(select(m.Finding).where(m.Finding.application_id == app.id, m.Finding.state == 'REVIEWER_CONFIRMED')):
        f.state = 'VERIFICATION_PENDING'
        f.version += 1
    audit(db, app, actor, 'EVIDENCE_REVISION_CHANGED', detail)


def run_job(job_id):
    with WRITE_LOCK, Session.begin() as db:
        job = db.get(m.Job, job_id)
        if not job or job.status not in {'QUEUED', 'RETRY'} or job.attempt >= 3:
            return
        job.status = 'PROCESSING'
        job.attempt += 1
        doc = db.get(m.Document, job.document_id)
        doc.status = 'PROCESSING'
        key = doc.object_key
    try:
        completed = subprocess.run([sys.executable, '-m', 'app.extract', str(DATA / 'objects' / key)],
                                   cwd=str(ROOT), capture_output=True, text=True, timeout=30, check=True)
        result = json.loads(completed.stdout)
        with WRITE_LOCK, Session.begin() as db:
            job = db.get(m.Job, job_id)
            doc = db.get(m.Document, job.document_id)
            for f in result['fields']:
                db.add(m.Field(document_id=doc.id, key=f['key'], raw=f['raw'], value_json=canonical(f['value']),
                               page=f['page'], bbox_json=canonical(f['bbox']), engine=f['engine']))
            doc.page_count = result['pages']
            doc.status = result['status']
            job.status = 'COMPLETED'
            app = db.get(m.Application, doc.application_id)
            invalidate(db, app, 'worker', {'document_id': doc.id, 'status': doc.status})
            audit(db, app, 'worker', 'EXTRACTION_COMPLETED', {'document_id': doc.id, 'fields': len(result['fields'])})
    except Exception:
        with WRITE_LOCK, Session.begin() as db:
            job = db.get(m.Job, job_id)
            job.status = 'FAILED'
            job.error = 'PARSER_FAILED_OR_BUDGET_EXCEEDED'
            doc = db.get(m.Document, job.document_id)
            doc.status = 'QUARANTINED'
            audit(db, db.get(m.Application, doc.application_id), 'worker', 'EXTRACTION_FAILED', {'document_id': doc.id, 'error': job.error})


def run_evaluation(db, app, actor):
    docs = latest_documents(db, app.id)
    snapshots = [{'id': d.id, 'kind': d.kind, 'sha256': d.sha256, 'version': d.version,
                  'status': d.status, 'source_status': d.source_status, 'source_mode': d.source_mode,
                  'source_note': d.source_note, 'fields': latest_fields(db, d.id)} for d in docs]
    manifest = {'application_id': app.id, 'context_revision': app.revision, 'category': app.category,
                'academic_year': app.academic_year, 'evaluation_date': app.evaluation_date,
                'documents': snapshots, 'rulepack_hash': RULEPACK_HASH, 'software': SOFTWARE_VERSION}
    result = evaluate(app.category, app.evaluation_date, snapshots)
    ev = m.Evaluation(application_id=app.id, revision=app.revision, manifest_json=canonical(manifest),
                      manifest_hash=digest(manifest), result_json=canonical(result))
    db.add(ev)
    db.flush()
    for f in result['findings']:
        db.add(m.Finding(application_id=app.id, evaluation_id=ev.id, body_json=canonical(f)))
    audit(db, app, actor, 'EVALUATION_COMPLETED', {'evaluation_id': ev.id, 'manifest_hash': ev.manifest_hash})
    return ev

"""Synthetic evidence goes through the same native extraction job as uploads."""
import hashlib
import secrets
from argon2 import PasswordHasher
from sqlalchemy import select
import pymupdf as fitz
from . import models as m
from .config import DATA
from .db import Session
from .service import WRITE_LOCK, audit

DEMO_DOCUMENTS = {
    'ROOM_SCHEDULE': ['BUILDING: BLOCK C', 'CLAIMED_FLOORS: G, 1, 2'],
    'OCCUPANCY': ['BUILDING: BLOCK C', 'COVERED_FLOORS: G, 1', 'VALID_UNTIL: 2027-06-30'],
    'FIRE_CERTIFICATE': ['BUILDING: BLOCK C', 'COVERED_FLOORS: G, 1, 2', 'VALID_UNTIL: 2027-06-30'],
    'DPR': ['FDR_NUMBER: 007781', 'HOLDER: EXAMPLE EDUCATIONAL TRUST', 'BANK: SYNTHETIC BANK', 'UNRESTRICTED_CLAIM_INR: 20,000,000'],
    'FDR_ADVICE': ['FDR_NUMBER: 007781', 'HOLDER: EXAMPLE EDUCATIONAL TRUST', 'BANK: SYNTHETIC BANK', 'PRINCIPAL_INR: 20,000,000', 'LIEN_INR: 18,000,000'],
}


def pdf_bytes(kind, lines):
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(0, 0, 595, 75), color=None, fill=(0.06, 0.18, 0.19))
        page.insert_text((36, 42), 'SYNTHETIC DEMONSTRATION', fontsize=17, color=(1, 1, 1))
        page.insert_text((36, 112), kind.replace('_', ' '), fontsize=18)
        page.insert_text((36, 145), 'Not issued by AICTE, a bank or any public authority.', fontsize=10, color=(0.4, 0.4, 0.4))
        for index, line in enumerate(lines):
            page.insert_text((36, 205 + index * 34), line, fontsize=11)
        page.insert_text((36, 760), 'Purpose: local testing of documentary consistency. No real institutional data.', fontsize=9)
        return doc.tobytes()


def seed():
    with WRITE_LOCK, Session.begin() as db:
        if db.scalar(select(m.User).limit(1)):
            return
        hasher = PasswordHasher()
        users = []
        for persona, role, tenant, name in [('officer', 'OFFICER', 'authority-demo', 'Meera Rao'),
                                            ('institution', 'SUBMITTER', 'institution-a', 'Example Educational Trust'),
                                            ('auditor', 'AUDITOR', 'authority-demo', 'Independent auditor'),
                                            ('other', 'SUBMITTER', 'institution-b', 'Other synthetic institution')]:
            u = m.User(email=f'{persona}@demo.invalid', role=role, tenant=tenant, name=name,
                       password_hash=hasher.hash(secrets.token_urlsafe(32)))
            db.add(u)
            users.append(u)
        a = m.Application(tenant='institution-a', name='Example Institute of Technology', category='NEW_INSTITUTION', evaluation_date='2026-10-27')
        b = m.Application(tenant='institution-b', name='Separate institution • access test', category='EOA', evaluation_date='2026-10-27')
        db.add_all([a, b])
        db.flush()
        for u in users:
            if u.role in {'OFFICER', 'AUDITOR'}:
                db.add(m.Assignment(user_id=u.id, application_id=a.id))
        for target in [a, b]:
            audit(db, target, 'seed', 'SYNTHETIC_APPLICATION_CREATED', {'synthetic': True, 'policy_status': 'DRAFT'})
        for kind, lines in DEMO_DOCUMENTS.items():
            data = pdf_bytes(kind, lines)
            key = f'{m.uid()}.pdf'
            (DATA / 'objects' / key).write_bytes(data)
            d = m.Document(application_id=a.id, kind=kind, filename=f'{kind.lower()}.pdf', version=1,
                           object_key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))
            db.add(d)
            db.flush()
            db.add(m.Job(document_id=d.id))
            audit(db, a, 'seed', 'SYNTHETIC_DOCUMENT_QUEUED', {'document_id': d.id, 'sha256': d.sha256})

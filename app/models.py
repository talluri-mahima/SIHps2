import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    tenant: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[str] = mapped_column(String)


class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    tenant: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    academic_year: Mapped[str] = mapped_column(String, default='2026-27')
    evaluation_date: Mapped[str] = mapped_column(String)
    synthetic: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Assignment(Base):
    __tablename__ = 'assignments'
    __table_args__ = (UniqueConstraint('user_id', 'application_id'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))


class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = (UniqueConstraint('application_id', 'kind', 'version'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))
    kind: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String)
    object_key: Mapped[str] = mapped_column(String, unique=True)
    sha256: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default='QUEUED')
    source_status: Mapped[str] = mapped_column(String, default='NOT_CHECKED')
    source_mode: Mapped[str] = mapped_column(String, default='NONE')
    source_note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String, default=now)


class Field(Base):
    __tablename__ = 'fields'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    key: Mapped[str] = mapped_column(String)
    raw: Mapped[str] = mapped_column(Text)
    value_json: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer)
    bbox_json: Mapped[str] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    previous_id: Mapped[str | None] = mapped_column(ForeignKey('fields.id'), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String, default=now)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), unique=True)
    status: Mapped[str] = mapped_column(String, default='QUEUED')
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(String, default='')


class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))
    revision: Mapped[int] = mapped_column(Integer)
    manifest_json: Mapped[str] = mapped_column(Text)
    manifest_hash: Mapped[str] = mapped_column(String)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Finding(Base):
    __tablename__ = 'findings'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))
    evaluation_id: Mapped[str] = mapped_column(ForeignKey('evaluations.id'))
    body_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String, default='OPEN')
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    detail_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    prev_hash: Mapped[str] = mapped_column(String)
    event_hash: Mapped[str] = mapped_column(String)


class Export(Base):
    __tablename__ = 'exports'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'))
    body_json: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Idempotency(Base):
    __tablename__ = 'idempotency'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String)
    response_json: Mapped[str] = mapped_column(Text)


@event.listens_for(Audit, 'before_update')
@event.listens_for(Audit, 'before_delete')
def immutable_audit(*_):
    raise ValueError('Audit events are append-only')

"""Adopt the existing foundation schema without changing existing evidence."""
from alembic import op
from app.models import Base
revision='0001'
down_revision=None

FOUNDATION={'users','sessions','applications','assignments','documents','fields','jobs','evaluations','findings','audit','exports','idempotency'}

def upgrade():
    # Existing milestone 0.1 tables are adopted with checkfirst; no data is overwritten.
    Base.metadata.create_all(op.get_bind(),tables=[t for t in Base.metadata.sorted_tables if t.name in FOUNDATION],checkfirst=True)

def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore a verified backup instead.')

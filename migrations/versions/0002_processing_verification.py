"""Immutable processing artifacts and verification evidence."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'

def upgrade():
    op.create_table('page_artifacts',sa.Column('id',sa.String(),primary_key=True),sa.Column('document_id',sa.String(),sa.ForeignKey('documents.id'),nullable=False),sa.Column('page',sa.Integer(),nullable=False),sa.Column('image_key',sa.String(),nullable=False),sa.Column('text_json',sa.Text(),nullable=False),sa.Column('method',sa.String(),nullable=False),sa.UniqueConstraint('document_id','page'))
    op.create_table('processing_results',sa.Column('id',sa.String(),primary_key=True),sa.Column('document_id',sa.String(),sa.ForeignKey('documents.id'),nullable=False),sa.Column('payload_json',sa.Text(),nullable=False),sa.Column('created_at',sa.String(),nullable=False))
    op.create_table('verification_events',sa.Column('id',sa.String(),primary_key=True),sa.Column('document_id',sa.String(),sa.ForeignKey('documents.id'),nullable=False),sa.Column('check_type',sa.String(),nullable=False),sa.Column('mode',sa.String(),nullable=False),sa.Column('status',sa.String(),nullable=False),sa.Column('payload_json',sa.Text(),nullable=False),sa.Column('actor',sa.String(),nullable=False),sa.Column('created_at',sa.String(),nullable=False))

def downgrade():
    raise RuntimeError('Verification/evidence history cannot be dropped by downgrade.')

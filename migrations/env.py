from alembic import context
from sqlalchemy import create_engine
from app.models import Base
from app.config import DATABASE_URL

def run():
    connectable=context.config.attributes.get('connection')
    if connectable is not None:
        context.configure(connection=connectable,target_metadata=Base.metadata)
        with context.begin_transaction():context.run_migrations()
    else:
        engine=create_engine(DATABASE_URL)
        with engine.connect() as connection:
            context.configure(connection=connection,target_metadata=Base.metadata)
            with context.begin_transaction():context.run_migrations()

run()

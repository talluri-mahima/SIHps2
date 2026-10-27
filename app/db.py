from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL, validate_environment
from .models import Base

validate_environment()
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 30} if DATABASE_URL.startswith('sqlite') else {})
Session = sessionmaker(engine, expire_on_commit=False)

if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_config(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')


def initialize():
    # Development schema bootstrap only. Production migrations are a blocked gate.
    Base.metadata.create_all(engine)

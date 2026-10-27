"""Restore a verified snapshot and read its records and immutable objects."""
import hashlib
import importlib.util
import json
import sqlite3
import zipfile
from pathlib import Path
from contextlib import closing


def test_backup_can_be_restored_and_releases_windows_handles(tmp_path,monkeypatch):
    script=Path(__file__).resolve().parents[1]/'scripts/backup.py'
    spec=importlib.util.spec_from_file_location('local_backup_test',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for folder in ['objects','derived','processing']:(tmp_path/folder).mkdir()
    database=tmp_path/'platform.db'
    with closing(sqlite3.connect(database)) as connection:
        connection.execute('CREATE TABLE example (id INTEGER PRIMARY KEY, value TEXT)')
        connection.execute('INSERT INTO example VALUES (1,?)',('preserved',))
        connection.commit()
    content=b'immutable original'
    (tmp_path/'objects'/'original.pdf').write_bytes(content)
    monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setattr(module,'DATABASE_URL','sqlite:///'+str(database))
    archive_path=module.backup()
    with zipfile.ZipFile(archive_path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['objects/original.pdf']==hashlib.sha256(content).hexdigest()
        restored=tmp_path/'restored.db';restored.write_bytes(archive.read('platform.db'))
    with closing(sqlite3.connect(restored)) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert connection.execute('SELECT value FROM example').fetchone()[0]=='preserved'
    assert list((tmp_path/'processing').iterdir())==[]

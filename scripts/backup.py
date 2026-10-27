"""Consistent local SQLite database backup and private evidence archive."""
import json
import sqlite3
import sys
import tempfile
import zipfile
import hashlib
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import DATA,DATABASE_URL

def backup():
    if not DATABASE_URL.startswith('sqlite:///'):raise RuntimeError('Use the database provider backup workflow for non-SQLite stores.')
    database=Path(DATABASE_URL.removeprefix('sqlite:///'))
    if not database.is_file():raise RuntimeError('No local database found.')
    output=DATA/'backups';output.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=output/f'evidence-backup-{stamp}.zip'
    # Originals are immutable. Stop new submissions for an exact cross-store snapshot.
    with tempfile.TemporaryDirectory(dir=DATA/'processing') as temp:
        snapshot=Path(temp)/'platform.db'
        with closing(sqlite3.connect(database)) as source,closing(sqlite3.connect(snapshot)) as dest:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity check failed')
        manifest={}
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot,'platform.db')
            manifest['platform.db']=hashlib.sha256(snapshot.read_bytes()).hexdigest()
            for directory in ['objects','derived']:
                for item in sorted((DATA/directory).rglob('*')):
                    if item.is_file():
                        relative=item.relative_to(DATA).as_posix()
                        archive.write(item,relative)
                        manifest[relative]=hashlib.sha256(item.read_bytes()).hexdigest()
            archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        with zipfile.ZipFile(target) as archive:
            for name,sha in manifest.items():
                if hashlib.sha256(archive.read(name)).hexdigest()!=sha:raise RuntimeError('Archive verification failed')
    print(f'Verified private backup: {target}')
    return target

if __name__=='__main__':backup()

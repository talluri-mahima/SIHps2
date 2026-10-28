"""Whitelist source/build/evidence reports; exclude credentials, runtime DB and PDFs."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    destination=ROOT/'.data/submission';destination.mkdir(parents=True,exist_ok=True)
    target=destination/'SIH26261-prototype-0.3.zip'
    files=[]
    for directory in ['app','migrations','rulepacks','scripts','docs','fixtures','web/src','web/dist','.github']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ['README.md','SECURITY.md','.env.example','.gitignore','alembic.ini','requirements.in','requirements.lock','requirements-paddle.in','requirements-paddle.lock','web/package.json','web/package-lock.json','web/tsconfig.json','web/vite.config.ts','web/index.html']:
        if (ROOT/name).is_file():files.append(ROOT/name)
    files.extend(p for p in (ROOT/'reports').glob('*.json') if p.name!='submission-package.json')
    files.extend(p for p in (ROOT/'reports/screenshots').rglob('*.png') if p.is_file())
    # Tests are necessary to reproduce the delivery gate.
    files.extend(p for p in (ROOT/'tests').rglob('*.py') if '__pycache__' not in p.parts)
    entries={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}
    forbidden=[name for name in entries if name.startswith(('.data/','.venv/','.venv-paddle/','sources/')) or name=='.env' or 'local-access' in name]
    if forbidden:raise RuntimeError('Private runtime file selected')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest=dict(version='0.3.0',created_at=datetime.now(timezone.utc).isoformat(),git_head=commit,
                  notice='Local prototype; independent accuracy and external issuer integrations remain unvalidated. Source files are individually hashed even if HEAD predates packaging.',sha256=entries)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in entries:archive.write(ROOT/name,name)
        archive.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as archive:
        for name,sha in entries.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=sha:raise RuntimeError('Package verification failed')
    output=dict(path='.data/submission/'+target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(entries),git_head=commit,private_runtime_files_included=False)
    (ROOT/'reports/submission-package.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Verified submission package:',target)
if __name__=='__main__':main()

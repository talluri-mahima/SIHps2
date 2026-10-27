"""Executable milestone gate; never upgrades a development test into release approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gate',choices=['foundation','production'],default='foundation')
    args=parser.parse_args()
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    if args.gate=='production':
        report={'gate':'production','status':'BLOCKED','reasons':['OIDC','PostgreSQL RLS deployment verification','Mandatory malware provider and OS-level parser/network isolation','Policy-approved rule packs','Independent held-out accuracy benchmark','Production recovery/privacy/security acceptance']}
        (reports/'production-gate.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('BLOCKED: production requirements remain. See docs/DELIVERY_STATUS.md.')
        return 1
    commands=[('backend_tests',[sys.executable,'-m','pytest','tests','-q','--junitxml=reports/foundation-tests.xml'],ROOT),
              ('web_build',['npm.cmd' if os.name=='nt' else 'npm','run','build'],ROOT/'web')]
    results=[]
    for name,command,cwd in commands:
        result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=180)
        results.append({'name':name,'status':'PASS' if result.returncode==0 else 'FAIL','exit_code':result.returncode})
        print(name+': '+results[-1]['status'])
        if result.returncode:print((result.stdout+result.stderr)[-5000:])
    files={}
    for directory in ['app','tests','rulepacks','web/src','scripts','fixtures','migrations']:
        for p in sorted((ROOT/directory).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                files[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ['requirements.lock','requirements-paddle.lock','web/package-lock.json','alembic.ini']:
        path=ROOT/name
        if path.is_file():files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    counts={}
    if (reports/'foundation-tests.xml').exists():
        suites=ET.parse(reports/'foundation-tests.xml').getroot()
        counts={key:sum(int(s.get(key,0)) for s in suites.iter('testsuite')) for key in ['tests','failures','errors','skipped']}
    report={'gate':'foundation','status':'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
            'at':datetime.now(timezone.utc).isoformat(),'checks':results,'test_counts':counts,'source_sha256':files,
            'source_fingerprint':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),
            'production_ready':False,'accuracy_benchmark_run':False,'notice':'Foundation behavior checks only; planned product release gates remain open.'}
    (reports/'foundation-gate.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Foundation '+report['status']+'; production release not approved.')
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':sys.exit(main())

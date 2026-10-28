"""Reproducible, provisional selected-field evaluation. Never a validated accuracy claim."""
import hashlib
import json
import os
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.extract import extract
ROOT=Path(__file__).resolve().parents[1]

def main():
    labels=json.loads((ROOT/'fixtures/real-document-labels.json').read_text())
    freeze=json.loads((ROOT/'reports/extractor-freeze.json').read_text())
    frozen=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in freeze['files'].items())
    manifest={d['id']:d for d in json.loads((ROOT/'reports/public-document-sources.json').read_text())['documents']}
    cases=[]
    for case in labels['cases']:
        path=ROOT/manifest[case['id']]['local_file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest[case['id']]['sha256']:raise RuntimeError('Source changed; labels need revision')
        started=time.monotonic(); result=extract(path,use_ocr=False); elapsed=round(time.monotonic()-started,3)
        actual={f['key']:f for f in result['fields']}; measurements=[]
        for key,expected in case['expected'].items():
            field=actual.get(key)
            match=bool(field and field['value']==expected['value'])
            citation=bool(field and field['page']==expected['page'] and field['bbox'][0]<expected['region'][2] and field['bbox'][2]>expected['region'][0] and field['bbox'][1]<expected['region'][3] and field['bbox'][3]>expected['region'][1])
            measurements.append(dict(key=key,status='CORRECT' if match else 'WRONG' if field else 'MISSED_OR_ABSTAINED',citation_region_matches=citation,actual=field['value'] if field else None,expected=expected['value']))
        cases.append(dict(id=case['id'],split=case['split'],sha256=manifest[case['id']]['sha256'],elapsed_seconds=elapsed,
                          expected_fields=len(measurements),correct=sum(x['status']=='CORRECT' for x in measurements),wrong=sum(x['status']=='WRONG' for x in measurements),
                          missed=sum(x['status']=='MISSED_OR_ABSTAINED' for x in measurements),citation_regions_matched=sum(x['citation_region_matches'] for x in measurements),
                          unsafe_candidates=[key for key in case['must_abstain'] if key in actual],unscored_candidate_keys=[key for key in actual if key not in case['expected'] and key not in case['must_abstain']],measurements=measurements))
        print(case['id'],cases[-1]['correct'],'/',len(measurements),'correct;',cases[-1]['wrong'],'wrong;',cases[-1]['missed'],'missed',flush=True)
    report=dict(at=datetime.now(timezone.utc).isoformat(),dataset=labels['dataset'],label_status=labels['label_status'],independent_labels=False,
                real_world_accuracy_established=False,extractor_matches_pre_holdout_freeze=frozen,notice=labels['notice'],
                summary={key:sum(c[key] for c in cases) for key in ['expected_fields','correct','wrong','missed','citation_regions_matched']},cases=cases)
    (ROOT/'reports/real-document-check.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0
if __name__=='__main__':sys.exit(main())

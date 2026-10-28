"""Acquire a small, explicit public evaluation corpus; never train or upload it."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('tsm-occupancy', 'OCCUPANCY', 'https://tsm.ac.in/documents/1771588638822-Occupancy-Certificate.pdf', 'https://tsm.ac.in/mandatory-disclosure'),
    ('tsm-fire', 'FIRE', 'https://tsm.ac.in/documents/1771588643417-fire-service-licence-2023-2024.pdf', 'https://tsm.ac.in/mandatory-disclosure'),
    ('mes-disclosure', 'MIXED_DISCLOSURE', 'https://old.mesce.ac.in/pdf/mand.pdf', 'https://old.mesce.ac.in/pdf/mand.pdf'),
    ('bit-sindri-eoa-2026', 'EOA', 'https://www.bitsindri.ac.in/wp-content/uploads/2026/04/Extension-of-Approval-EOA-Report-2026-27.pdf', 'https://www.bitsindri.ac.in/wp-content/uploads/2026/04/Extension-of-Approval-EOA-Report-2026-27.pdf'),
    ('mitrc-fire-linked-receipt','FIRE_LINK_NEGATIVE_CONTROL','https://mitrc.ac.in/wp-content/uploads/2024/04/Fire-and-Safety-Certificate.pdf','https://mitrc.ac.in/pages/fire-safety-certificate'),
    ('bcrec-eoa-holdout','EOA_INSTITUTION_HOLDOUT','https://bcrecapc.ac.in/public/pdf/2026-27.PDF','https://bcrecapc.ac.in/public/pdf/2026-27.PDF'),
]

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--new-only',action='store_true');args=parser.parse_args()
    manifest=ROOT/'reports/public-document-sources.json'
    previous={r['id']:r for r in json.loads(manifest.read_text())['documents']} if manifest.exists() else {}
    destination = ROOT / '.data' / 'public-documents'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for name, kind, url, listing in SOURCES:
        existing=destination/f'{name}.pdf'
        if args.new_only and existing.is_file() and name in previous and hashlib.sha256(existing.read_bytes()).hexdigest()==previous[name].get('sha256'):
            records.append(previous[name]);print(name,'PRESERVED');continue
        record = dict(id=name, document_type=kind, url=url, listing_url=listing,
                      retrieved_at=datetime.now(timezone.utc).isoformat(),
                      authenticity='INSTITUTION_PUBLISHED_NOT_ISSUER_VERIFIED',
                      license='NOT_ESTABLISHED', training_permission='NOT_ESTABLISHED',
                      use='LOCAL_LAYOUT_EVALUATION_ONLY', ground_truth='NOT_YET_INDEPENDENTLY_LABELLED')
        try:
            with urlopen(Request(url, headers={'User-Agent': 'SIH26261-public-layout-evaluation/0.2'}), timeout=45) as response:
                if response.geturl().split(':')[0] != 'https':
                    raise ValueError('HTTPS downgrade')
                data = response.read(25 * 1024 * 1024 + 1)
                record['resolved_url'] = response.geturl()
            if len(data) > 25 * 1024 * 1024 or not data.startswith(b'%PDF-'):
                raise ValueError('Not a bounded PDF')
            (destination / f'{name}.pdf').write_bytes(data)
            record.update(status='DOWNLOADED', bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), local_file=f'.data/public-documents/{name}.pdf')
        except Exception as error:
            record.update(status='DOWNLOAD_FAILED', error_type=type(error).__name__)
        records.append(record)
        print(name, record['status'])
    report = dict(purpose='Public real-layout evaluation, not model training or an accuracy benchmark', documents=records)
    (ROOT / 'reports' / 'public-document-sources.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()

"""Measure coverage on public layouts without publishing their extracted contents."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from app.extract import extract

ROOT = Path(__file__).resolve().parents[1]

def main():
    manifest = json.loads((ROOT/'reports/public-document-sources.json').read_text())
    results = []
    for source in manifest['documents']:
        if source['status'] != 'DOWNLOADED':
            continue
        path = ROOT/source['local_file']
        with fitz.open(path) as pdf:
            pages = len(pdf)
            native_pages = sum(bool(page.get_text().strip()) for page in pdf)
            pdf[0].get_pixmap(matrix=fitz.Matrix(1,1)).save(path.with_suffix('.png'))
        try:
            result = extract(path)
            row = dict(id=source['id'], sha256=source['sha256'], pages=pages,
                       native_text_pages=native_pages, status=result['status'],
                       candidate_keys=[f['key'] for f in result['fields']],
                       layout_observation_counts={kind:sum(h['kind']==kind for h in result.get('layout_observations',[])) for kind in sorted({h['kind'] for h in result.get('layout_observations',[])})},
                       page_classifications=result.get('page_classifications',[]),
                       metrics=result['metrics'], independently_labelled=False,
                       accuracy='NOT_MEASURED', issuer_authentication='NOT_PERFORMED')
        except Exception as error:
            row = dict(id=source['id'], pages=pages, status='REJECTED_OR_FAILED', error_type=type(error).__name__)
        results.append(row)
        print(source['id'], row['status'], row.get('candidate_keys', []))
    (ROOT/'reports/public-layout-coverage.json').write_text(json.dumps(dict(
        notice='Coverage inspection only. No real-world accuracy claim. Public PDFs remain local and ignored.',
        documents=results), indent=2)+'\n')

if __name__ == '__main__':
    main()

"""Bounded native-PDF extraction for explicit labelled demonstration facts.

Not a general AI extractor. Unknown layouts/scans abstain. Executed in a child
process with a parent-enforced timeout; OS network sandbox is a later gate.
"""
import json
import re
import sys
import time
from pathlib import Path
from datetime import date
from decimal import Decimal, InvalidOperation
from contextlib import ExitStack
import pymupdf as fitz
from .candidates import labelled_candidate, classify
from .ocr import LocalOCR
from .layout import associated_lines, observations

ALLOWED = {'BUILDING', 'CLAIMED_FLOORS', 'COVERED_FLOORS', 'FDR_NUMBER', 'HOLDER', 'BANK',
           'PRINCIPAL_INR', 'LIEN_INR', 'UNRESTRICTED_CLAIM_INR', 'VALID_UNTIL'}


def normalize(key, raw):
    if key.endswith('_INR'):
        # Exact rupees only in milestone 1. Unsupported fractions abstain.
        val = Decimal(raw.replace(',', '').strip())
        if not val.is_finite() or val < 0 or val != val.to_integral_value() or val > 10**14:
            raise ValueError('Unsupported currency value')
        return int(val)
    if key.endswith('FLOORS'):
        floors = [v.strip().upper() for v in raw.split(',')]
        if not floors or len(set(floors)) != len(floors) or any(not re.fullmatch(r'G|B[1-3]|[1-9][0-9]?', f) for f in floors):
            raise ValueError('Ambiguous floor list')
        return floors
    if key == 'VALID_UNTIL':
        return date.fromisoformat(raw).isoformat()
    if key == 'FDR_NUMBER':
        if not re.fullmatch(r'[A-Za-z0-9 -]{1,64}', raw):
            raise ValueError('Ambiguous identifier')
        return raw.replace(' ', '').replace('-', '').upper()
    if not raw or len(raw) > 160:
        raise ValueError('Unsupported text')
    return ' '.join(raw.upper().split())


def extract(path, output_dir=None, use_ocr=None):
    started = time.monotonic()
    if use_ocr is None:
        import os
        use_ocr = os.getenv('AICTE_OCR_ENABLED', 'true').lower() == 'true'
    import os
    force_ocr = os.getenv('AICTE_OCR_FORCE', 'false').lower() == 'true'
    output = Path(output_dir) if output_dir else None
    if output:
        output.mkdir(parents=True, exist_ok=True)
    with ExitStack() as cleanup, fitz.open(path) as doc:
        if doc.is_encrypted or not 0 < len(doc) <= 30:
            raise ValueError('UNSUPPORTED_PDF')
        if doc.embfile_count() or doc.xref_length() > 10000:
            raise ValueError('PDF_COMPLEXITY_OR_ATTACHMENT_LIMIT')
        for xref in range(1, doc.xref_length()):
            for key in ('JS', 'JavaScript', 'OpenAction', 'AA', 'RichMediaContent', 'EF'):
                if doc.xref_get_key(xref, key)[0] != 'null':
                    raise ValueError('ACTIVE_PDF_CONTENT')
        fields = []
        readable_pages = 0
        page_results, all_lines, low_confidence = [], [], 0
        layout_hints, page_classifications = [], []
        ocr_engine = None
        for page_no, page in enumerate(doc, 1):
            if page.rect.width > 4000 or page.rect.height > 4000:
                raise ValueError('PAGE_DIMENSION_LIMIT')
            text = page.get_text()
            if len(text) > 200000:
                raise ValueError('TEXT_LIMIT')
            lines = []
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    x0,y0,x1,y1=line['bbox']
                    lines.append({'text': ''.join(s['text'] for s in line['spans']),
                                  'bbox': [x0/page.rect.width,y0/page.rect.height,x1/page.rect.width,y1/page.rect.height],
                                  'score': None})
            method = 'NATIVE_PDF'
            # Limit rendered pixels even when OCR needs higher resolution.
            scale = min(2.0, (12000000 / (page.rect.width * page.rect.height)) ** .5)
            needs_ocr = use_ocr and (force_ocr or len(text.strip()) < 25)
            image = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False) if output or needs_ocr else None
            if needs_ocr:
                if ocr_engine is None:
                    ocr_engine = LocalOCR()
                    cleanup.callback(ocr_engine.close)
                lines, method = ocr_engine.recognize(image)
                # Merge horizontally adjacent OCR regions on the same text row.
                rows=[]
                for item in sorted(lines,key=lambda l:(l['bbox'][1],l['bbox'][0])):
                    center=(item['bbox'][1]+item['bbox'][3])/2
                    row=next((r for r in rows if abs(r['center']-center)<max(.006,(item['bbox'][3]-item['bbox'][1])*.5)),None)
                    if row is None:
                        rows.append({'center':center,'items':[item]})
                    else:
                        row['items'].append(item)
                lines=[]
                for row in rows:
                    items=sorted(row['items'],key=lambda l:l['bbox'][0])
                    lines.append({'text':' '.join(i['text'] for i in items),
                                  'bbox':[min(i['bbox'][0] for i in items),min(i['bbox'][1] for i in items),max(i['bbox'][2] for i in items),max(i['bbox'][3] for i in items)],
                                  'score':min(i['score'] for i in items)})
            readable_pages += bool(lines)
            if output:
                image.save(str(output / f'{page_no}.png'))
            page_results.append({'page':page_no,'method':method,'lines':lines,'image':f'{page_no}.png' if output else None})
            layout_hints.extend(observations(lines, page_no))
            page_classifications.extend(dict(item, page=page_no) for item in classify([line['text'] for line in lines]))
            for line in [*lines, *associated_lines(lines)]:
                all_lines.append(line['text'])
                if line['score'] is not None and line['score'] < .65:
                    low_confidence+=1
                    continue
                try:
                    candidate=labelled_candidate(line['text'])
                    if not candidate:
                        continue
                    key,raw,normalized_raw=candidate
                    value=normalize(key,normalized_raw)
                except (ValueError,InvalidOperation):
                    continue
                quality='LOW_RECOGNITION' if line['score'] is not None and line['score']<.90 else 'UNCONFIRMED_CANDIDATE'
                fields.append({'key':key,'raw':raw,'value':value,'page':page_no,'bbox':line['bbox'],
                               'engine':f'{method}:{quality}:{line.get("association","EXPLICIT_LABEL")}:pymupdf-{fitz.VersionBind}:candidates-v3',
                               'recognition_score':line['score']})
        # Duplicate critical keys remain ambiguous instead of taking the last value.
        counts = {f['key']: sum(x['key'] == f['key'] for x in fields) for f in fields}
        fields = [f for f in fields if counts[f['key']] == 1]
        return {'pages': len(doc), 'fields': fields, 'page_artifacts': page_results,
                'classification_candidates':classify(all_lines),
                'page_classifications':page_classifications, 'layout_observations':layout_hints,
                'metrics':{'elapsed_seconds':round(time.monotonic()-started,3),'ocr_pages':sum(p['method'].startswith('CPU_OCR_') for p in page_results),
                           'ocr_provider':os.getenv('AICTE_OCR_PROVIDER','rapidocr'), 'forced_ocr':force_ocr,
                           'low_recognition_lines_omitted':low_confidence,'candidate_fields':len(fields),
                           'low_recognition_candidates':sum('LOW_RECOGNITION' in f['engine'] for f in fields),
                           'automatic_accepted_critical_fields':0,'duplicate_keys_omitted':[k for k,n in counts.items() if n>1]},
                'status': 'OCR_REQUIRED' if readable_pages < len(doc) else 'EXTRACTED' if fields else 'MANUAL_EXTRACTION_REQUIRED'}


if __name__ == '__main__':
    try:
        print(json.dumps(extract(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)))
    except Exception:
        print(json.dumps({'error': 'UNSUPPORTED_OR_MALFORMED_PDF'}))
        sys.exit(1)

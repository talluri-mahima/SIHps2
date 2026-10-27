"""Bounded native-PDF extraction for explicit labelled demonstration facts.

Not a general AI extractor. Unknown layouts/scans abstain. Executed in a child
process with a parent-enforced timeout; OS network sandbox is a later gate.
"""
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
import pymupdf as fitz

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


def extract(path):
    with fitz.open(path) as doc:
        if doc.is_encrypted or not 0 < len(doc) <= 30:
            raise ValueError('UNSUPPORTED_PDF')
        if doc.embfile_count() or doc.xref_length() > 10000:
            raise ValueError('PDF_COMPLEXITY_OR_ATTACHMENT_LIMIT')
        for xref in range(1, doc.xref_length()):
            for key in ('JS', 'JavaScript', 'OpenAction', 'AA', 'RichMediaContent', 'EF'):
                if doc.xref_get_key(xref, key)[0] != 'null':
                    raise ValueError('ACTIVE_PDF_CONTENT')
        fields = []
        text_pages = 0
        for page_no, page in enumerate(doc, 1):
            if page.rect.width > 4000 or page.rect.height > 4000:
                raise ValueError('PAGE_DIMENSION_LIMIT')
            text = page.get_text()
            if len(text) > 200000:
                raise ValueError('TEXT_LIMIT')
            text_pages += bool(text.strip())
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    raw_line = ''.join(s['text'] for s in line['spans'])
                    match = re.fullmatch(r'([A-Z_]+):\s*(.{1,200})', raw_line.strip())
                    if not match or match[1] not in ALLOWED:
                        continue
                    key, raw = match[1], match[2]
                    try:
                        value = normalize(key, raw)
                    except (ValueError, InvalidOperation):
                        continue
                    x0, y0, x1, y1 = line['bbox']
                    fields.append({'key': key, 'raw': raw, 'value': value, 'page': page_no,
                                   'bbox': [x0/page.rect.width, y0/page.rect.height, x1/page.rect.width, y1/page.rect.height],
                                   'engine': f'pymupdf:{fitz.VersionBind}:labelled-native-v1'})
        # Duplicate critical keys remain ambiguous instead of taking the last value.
        counts = {f['key']: sum(x['key'] == f['key'] for x in fields) for f in fields}
        fields = [f for f in fields if counts[f['key']] == 1]
        return {'pages': len(doc), 'fields': fields,
                'status': 'OCR_REQUIRED' if text_pages < len(doc) else 'EXTRACTED' if fields else 'MANUAL_EXTRACTION_REQUIRED'}


if __name__ == '__main__':
    try:
        print(json.dumps(extract(sys.argv[1])))
    except Exception:
        print(json.dumps({'error': 'UNSUPPORTED_OR_MALFORMED_PDF'}))
        sys.exit(1)

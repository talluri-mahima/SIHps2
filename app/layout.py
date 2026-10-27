"""Conservative layout hints. Mentions are never proof of certificate coverage."""
import re
from .candidates import LABELS, canonical_label


def union_bbox(items):
    return [min(x['bbox'][0] for x in items), min(x['bbox'][1] for x in items),
            max(x['bbox'][2] for x in items), max(x['bbox'][3] for x in items)]


def associated_lines(lines):
    """Join exact known labels to a unique nearby value; ambiguous rows abstain."""
    result = []
    for label in lines:
        if canonical_label(label['text'].strip().rstrip(':=')) not in LABELS:
            continue
        box = label['bbox']; center = (box[1]+box[3])/2
        candidates = [item for item in lines if item is not label
                      and item['bbox'][0] >= box[2]-.002
                      and 0 <= item['bbox'][0]-box[2] < .12
                      and abs((item['bbox'][1]+item['bbox'][3])/2-center) < .008
                      and canonical_label(item['text'].strip().rstrip(':=')) not in LABELS]
        if len(candidates) != 1:
            continue
        value = candidates[0]
        scores = [v['score'] for v in [label, value] if v['score'] is not None]
        result.append(dict(text=label['text'].strip().rstrip(':=')+': '+value['text'],
                           bbox=union_bbox([label, value]), score=min(scores) if scores else None,
                           association='UNIQUE_SAME_ROW_LABEL_VALUE'))
    return result


def observations(lines, page):
    hints = []
    for index, line in enumerate(lines):
        match = re.search(r'(?<![A-Za-z0-9])G\s*\+\s*([1-9][0-9]?)(?![0-9])', line['text'], re.I)
        if match:
            count = int(match[1])
            hints.append(dict(kind='FLOOR_NOTATION_MENTION', page=page, line_index=index,
                              bbox=line['bbox'], raw=match[0], suggested_value=['G', *[str(i) for i in range(1,count+1)]],
                              status='REVIEW_REQUIRED', meaning='Mention only; building identity, certificate type and covered scope must be established by an officer.'))
        if re.search(r'valid\s*(?:upto|up to|until)|expiry', line['text'], re.I):
            hints.append(dict(kind='EXPIRY_LABEL_MENTION', page=page, line_index=index,
                              bbox=line['bbox'], raw=line['text'], status='REVIEW_REQUIRED',
                              meaning='Inspect the original date. Adjacent or handwritten numeric dates are not inferred.'))
    return hints

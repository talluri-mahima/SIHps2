"""Source-grounded English document patterns, not authenticity or approval decisions."""
import re
from .candidates import candidate_value


def understand(lines,page):
    text=' '.join(x['text'] for x in lines)
    receipt=bool(re.search(r'ONLINE\s+PAYMENT\s+RECEIPT',text,re.I))
    eoa=bool(re.search(r'Extension\s+of\s+Approval',text,re.I))
    fire=bool(re.search(r'fire.{0,30}(?:licen[cs]e|safety certificate)',text,re.I)) and not receipt
    annotations=[]; candidates=[]
    if receipt:
        annotations.append(dict(page=page,kind='PAYMENT_RECEIPT',status='NOT_CERTIFICATE_EVIDENCE',
                                reason='Payment confirms a transaction, not approval, occupancy or fire-certificate coverage.'))
    def add(key,raw,line,basis):
        try:normalized=candidate_value(key,raw)
        except ValueError:return
        candidates.append(dict(key=key,raw=raw,normalized=normalized,page=page,bbox=line['bbox'],
                               score=line['score'],basis=basis))
    for line in lines:
        value=line['text'].strip()
        if receipt:continue
        # Institution names are metadata; never silently used as a building identifier.
        if fire:
            match=re.fullmatch(r'(.{5,150}?)\s*\(\s*G\s*\+\s*([1-9])\s*\)',value,re.I)
            if match:
                add('INSTITUTION_NAME',match[1],line,'FIRE_SUBJECT_WITH_FLOOR_NOTATION')
                # Floor mention stays a hint: it does not establish building linkage.
        match=re.search(r'\b(?:the\s+)?(Main Building|Block\s+[A-Z0-9-]{1,12})\s*\(\s*G\s*\+\s*([1-9])\s*\)',value,re.I)
        if match:
            add('BUILDING',match[1],line,'EXPLICIT_BUILDING_NARRATIVE')
            # Explicit building notation is reviewable scope, never auto-confirmed.
            add('COVERED_FLOORS',', '.join(['G',*[str(i) for i in range(1,int(match[2])+1)]]),line,'EXPLICIT_BUILDING_FLOOR_NOTATION')
        if eoa:
            match=re.search(r'\bAPPROVAL\s+PROCESS\s+(20\d{2}-\d{2})',value,re.I)
            if match:add('ACADEMIC_YEAR',match[1],line,'EOA_APPROVAL_PROCESS_YEAR')
            match=re.search(r'Date\s+of\s+Approval\s*:\s*(\d{1,2}[- ]+[A-Za-z]{3,9}[- ]+20\d{2})',value,re.I)
            if match:add('ISSUED_ON',match[1],line,'EXPLICIT_EOA_APPROVAL_DATE')
            match=re.search(r'F\.\s*No\.\s*([^\s]+/20\d{2}/EOA)',value,re.I)
            if match:add('APPROVAL_REFERENCE',match[1],line,'EXPLICIT_EOA_REFERENCE')
        # Limit authority detection to a standalone heading, not an address/body mention.
        if re.fullmatch(r'All India Council for Technical Education',value,re.I):
            add('ISSUING_AUTHORITY',value,line,'STANDALONE_AUTHORITY_HEADING')
        elif re.fullmatch(r'TAMIL\s*NADU\s+FIRE\s*(?:&|AND)?\s*RESCUE\s+SERVICES?',value,re.I):
            add('ISSUING_AUTHORITY',value,line,'STANDALONE_AUTHORITY_HEADING')
    return candidates,annotations

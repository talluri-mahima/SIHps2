"""Pure, deterministic evidence checks. No regulatory decision or LLM judgment."""
import hashlib
import json
from datetime import date
from .config import ROOT


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


RULEPACK = json.loads((ROOT / 'rulepacks' / 'demo-2026-27.json').read_text(encoding='utf-8'))
RULEPACK_HASH = digest(RULEPACK)
CHECKLISTS = {
    'NEW_INSTITUTION': ['ROOM_SCHEDULE', 'OCCUPANCY', 'FIRE_CERTIFICATE', 'DPR', 'FDR_ADVICE'],
    'EOA': ['PRIOR_EOA', 'ROOM_SCHEDULE', 'OCCUPANCY', 'FIRE_CERTIFICATE'],
}
KINDS = sorted(set(sum(CHECKLISTS.values(), [])) | {'LIEN_EVIDENCE', 'APPLICATION_DECLARATION', 'BUILDING_PLAN'})


def evaluate(category, evaluation_date, documents):
    findings, coverage = [], []
    by_kind = {d['kind']: d for d in documents}

    def emit(rule, title, explanation, evidence=(), reason='EVIDENCE_GAP', module='Documents'):
        specification=next(r for r in RULEPACK['rules'] if r['id']==rule)
        findings.append({'rule_id': rule, 'rule_version': RULEPACK['version'], 'title': title,
                         'explanation': explanation, 'reason': reason, 'module': module,
                         'severity': 'REVIEW_NEEDED', 'certainty': 'UNRESOLVED',
                         'verification_status': 'NOT_ESTABLISHED', 'evidence': list(evidence),
                         'required_action': 'Review the linked evidence and request specific clarification where needed.',
                         'check_basis':specification['basis'],'source_context':RULEPACK.get('source_context')})

    def accepted(kind, key):
        d = by_kind.get(kind)
        f = d and d['fields'].get(key)
        if not f or not f['confirmed_by']:
            return None
        if kind in {'OCCUPANCY','FIRE_CERTIFICATE','BUILDING_PLAN'} and any(
            p.get('page')==f['page'] and p.get('status')=='NOT_CERTIFICATE_EVIDENCE'
            for p in d.get('document_annotations',[])):
            return None
        return f

    def refs(*fields):
        return [{'field_id': f['id'], 'document_id': f['document_id'], 'page': f['page'], 'bbox': f['bbox']} for f in fields if f]

    for kind in CHECKLISTS[category]:
        if kind not in by_kind:
            emit('DOC-COMPLETE-001', f'Missing {kind.replace("_", " ").lower()}',
                 'Expected evidence for this demonstration workflow has not been submitted. This checklist is not an approved APH pack.',
                 reason='MISSING_DOCUMENT')
            findings[-1]['expected_document_kind']=kind

    for d in documents:
        if d['kind'] in {'OCCUPANCY','FIRE_CERTIFICATE','BUILDING_PLAN'} and any(
            p.get('status')=='NOT_CERTIFICATE_EVIDENCE' for p in d.get('document_annotations',[])):
            emit('DOC-TYPE-001','Submitted certificate includes payment-receipt evidence',
                 'Identified payment-receipt pages cannot establish building or fire-certificate coverage. Inspect the complete bundle and obtain the actual applicable certificate.',
                 reason='PAYMENT_RECEIPT_NOT_AUTHORIZATION')
            findings[-1]['expected_document_kind']=d['kind']

    rooms = accepted('ROOM_SCHEDULE', 'CLAIMED_FLOORS')
    occ = accepted('OCCUPANCY', 'COVERED_FLOORS')
    rb, ob = accepted('ROOM_SCHEDULE', 'BUILDING'), accepted('OCCUPANCY', 'BUILDING')
    fire = accepted('FIRE_CERTIFICATE', 'COVERED_FLOORS')
    fb = accepted('FIRE_CERTIFICATE', 'BUILDING')
    building_matches = rb and ob and rb['value'] == ob['value']
    if rooms and isinstance(rooms['value'], list):
        for floor in rooms['value']:
            supported = bool(building_matches and occ and floor in occ['value'])
            fire_supported = bool(rb and fb and rb['value'] == fb['value'] and fire and floor in fire['value'])
            coverage.append({'building': rb['value'] if rb else 'Unconfirmed', 'floor': floor,
                             'occupancy': 'SUPPORTED' if supported else 'UNKNOWN',
                             'fire': 'SUPPORTED' if fire_supported else 'UNKNOWN',
                             'evidence': refs(rooms, occ, rb, ob, fire, fb)})
        uncovered = [r['floor'] for r in coverage if r['occupancy'] != 'SUPPORTED']
        if uncovered:
            emit('INFRA-SCOPE-001', 'Occupancy coverage is not established',
                 f'Claimed floor(s) {", ".join(uncovered)} are not established by the accepted occupancy scope and building identity. This does not establish that rooms are absent.',
                 refs(rooms, occ, rb, ob), 'SCOPE_NOT_ESTABLISHED', 'ScopeGuard')
        if any(r['fire'] != 'SUPPORTED' for r in coverage):
            emit('INFRA-SCOPE-001', 'Fire evidence coverage needs review',
                 'Accepted fire evidence does not establish coverage for every claimed floor. Occupancy evidence does not substitute for fire evidence.',
                 refs(rooms, fire, rb, fb), 'FIRE_SCOPE_NOT_ESTABLISHED', 'ScopeGuard')
    elif 'ROOM_SCHEDULE' in by_kind:
        emit('INFRA-SCOPE-001', 'Confirm the room-schedule facts',
             'Claimed floors are missing, unreadable or not reviewer-confirmed. No coverage pass is produced.',
             reason='UNCONFIRMED_CRITICAL_FIELD', module='ScopeGuard')

    if 'DPR' in by_kind or 'FDR_ADVICE' in by_kind:
        did, fid = accepted('DPR', 'FDR_NUMBER'), accepted('FDR_ADVICE', 'FDR_NUMBER')
        claim, principal, lien = accepted('DPR', 'UNRESTRICTED_CLAIM_INR'), accepted('FDR_ADVICE', 'PRINCIPAL_INR'), accepted('FDR_ADVICE', 'LIEN_INR')
        holder_d, holder_f = accepted('DPR', 'HOLDER'), accepted('FDR_ADVICE', 'HOLDER')
        bank_d, bank_f = accepted('DPR', 'BANK'), accepted('FDR_ADVICE', 'BANK')
        fs = refs(did, fid, claim, principal, lien, holder_d, holder_f, bank_d, bank_f)
        if not all([did, fid, claim, principal, lien, holder_d, holder_f, bank_d, bank_f]):
            emit('FIN-LIEN-001', 'Financial evidence is not ready for reconciliation',
                 'Confirm instrument number, holder, bank, principal, lien and claimed unrestricted funding. Missing facts cannot establish available funds.',
                 fs, 'UNCONFIRMED_CRITICAL_FIELD', 'Hestia')
        elif did['value'] != fid['value'] or holder_d['value'] != holder_f['value'] or bank_d['value'] != bank_f['value']:
            emit('FIN-LIEN-001', 'Financial instrument identity is unresolved',
                 'Exact instrument number, holder and bank do not agree. No fuzzy financial join or availability calculation was performed.',
                 fs, 'INSTRUMENT_IDENTITY_MISMATCH', 'Hestia')
        elif claim['value'] > 0 and lien['value'] > 0:
            emit('FIN-LIEN-001', 'Unrestricted funding claim requires bank confirmation',
                 f'DPR treats FDR {did["value"]} as INR {claim["value"]:,} unrestricted funding. The advice records INR {lien["value"]:,} under lien against INR {principal["value"]:,} principal. Current unrestricted residual is UNKNOWN; principal minus lien is not certified availability.',
                 fs, 'LIEN_VS_UNRESTRICTED_CLAIM', 'Hestia')
        elif claim['value'] > principal['value']:
            emit('FIN-LIEN-001', 'Claim exceeds the recorded principal',
                 'The matched DPR funding claim exceeds the submitted principal. This is a documentary inconsistency, not proof of fraud.',
                 fs, 'CLAIM_EXCEEDS_PRINCIPAL', 'Hestia')

    for d in documents:
        exp = d['fields'].get('VALID_UNTIL')
        if exp and exp['confirmed_by'] and date.fromisoformat(exp['value']) < date.fromisoformat(evaluation_date):
            emit('DOC-EXPIRY-001', f'{d["kind"].replace("_", " ").title()} has an earlier expiry date',
                 f'Explicit validity ends {exp["value"]}, before evaluation date {evaluation_date}. Review applicable date semantics before any deficiency confirmation.',
                 refs(exp), 'DOCUMENT_EXPIRED')
    return {'findings': findings, 'coverage': coverage, 'rulepack': RULEPACK,
            'rulepack_hash': RULEPACK_HASH, 'approval_decision': None}

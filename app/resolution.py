"""A disappearing finding alone does not prove rectification."""
from datetime import date


def check_resolution(old,result,documents,supporting_ids,old_kinds,evaluation_date):
    selected=[d for d in documents if d['id'] in supporting_ids]
    if len(selected)!=len(supporting_ids):return 'Current supporting document not found'
    rule=old['rule_id']
    if any(f['rule_id']==rule and f['module']==old['module'] for f in result['findings']):
        return 'The current evaluation still has an unresolved check for this rule and module'
    kinds={d['kind'] for d in selected}
    if rule=='INFRA-SCOPE-001':
        expected={'SCOPE_NOT_ESTABLISHED':'OCCUPANCY','FIRE_SCOPE_NOT_ESTABLISHED':'FIRE_CERTIFICATE'}.get(old['reason'],'ROOM_SCHEDULE')
        if expected not in kinds:return 'Select the certificate or schedule that addresses this specific scope gap'
        if not result.get('coverage') or any(r['occupancy']!='SUPPORTED' or r['fire']!='SUPPORTED' for r in result['coverage']):
            return 'Every claimed floor needs explicit occupancy and fire support before scope resolution'
    elif rule=='DOC-COMPLETE-001':
        expected=old.get('expected_document_kind')
        if not expected:
            expected=next((d['kind'] for d in documents if old['title']=='Missing '+d['kind'].replace('_',' ').lower()),None)
        if expected not in kinds:return 'Select the specific document that was missing'
    elif rule=='DOC-EXPIRY-001':
        if not kinds.intersection(old_kinds):return 'Select a replacement of the expired document type'
        for d in selected:
            if d['kind'] not in old_kinds:continue
            expiry=d['fields'].get('VALID_UNTIL')
            if not expiry or not expiry.get('confirmed_by') or date.fromisoformat(expiry['value'])<date.fromisoformat(evaluation_date):
                return 'A confirmed current validity date is required; removing the date cannot resolve expiry'
    elif rule=='FIN-LIEN-001':
        if not kinds.intersection({'DPR','FDR_ADVICE','LIEN_EVIDENCE'}):return 'Select relevant financial evidence'
    elif rule=='DOC-TYPE-001':
        related=old_kinds|{old.get('expected_document_kind')}
        if not kinds.intersection(related):return 'Select the applicable replacement certificate'
        if any(p.get('status')=='NOT_CERTIFICATE_EVIDENCE' for d in selected for p in d.get('document_annotations',[])):return 'Inspect the replacement certificate purpose before resolving'
    else:return 'This rule has no supported rectification procedure'
    return None

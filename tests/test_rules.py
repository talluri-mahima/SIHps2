import pytest
from app.rules import evaluate, digest
from app.extract import normalize


def doc(kind, **values):
    return {'kind': kind, 'fields': {key: {'id': kind+key, 'document_id': kind, 'key': key, 'value': val,
            'page': 1, 'bbox': [.1,.1,.7,.2], 'confirmed_by': 'reviewer'} for key,val in values.items()}}


def infra(floors=('G','1'), claimed=('G','1','2')):
    return [doc('ROOM_SCHEDULE', BUILDING='BLOCK C', CLAIMED_FLOORS=list(claimed)),
            doc('OCCUPANCY', BUILDING='BLOCK C', COVERED_FLOORS=list(floors)),
            doc('FIRE_CERTIFICATE', BUILDING='BLOCK C', COVERED_FLOORS=list(claimed))]


def finance():
    return [doc('DPR', FDR_NUMBER='007781', HOLDER='TRUST', BANK='BANK', UNRESTRICTED_CLAIM_INR=20000000),
            doc('FDR_ADVICE', FDR_NUMBER='007781', HOLDER='TRUST', BANK='BANK', PRINCIPAL_INR=20000000, LIEN_INR=18000000)]


def reasons(result):
    return {f['reason'] for f in result['findings']}


def test_scope_outside_certificate_is_unknown_not_absence():
    r = evaluate('NEW_INSTITUTION','2026-10-27',infra())
    assert [x['occupancy'] for x in r['coverage']] == ['SUPPORTED','SUPPORTED','UNKNOWN']
    assert 'SCOPE_NOT_ESTABLISHED' in reasons(r)
    assert 'rooms are absent' in next(f['explanation'] for f in r['findings'] if f['reason']=='SCOPE_NOT_ESTABLISHED')
    assert r['approval_decision'] is None


def test_full_scope_has_no_scope_finding():
    assert 'SCOPE_NOT_ESTABLISHED' not in reasons(evaluate('NEW_INSTITUTION','2026-10-27',infra(('G','1','2'))))


def test_unknown_building_cannot_pass():
    d=infra(('G','1','2'))
    d[1]['fields']['BUILDING']['confirmed_by']=None
    assert all(r['occupancy']=='UNKNOWN' for r in evaluate('EOA','2026-10-27',d)['coverage'])


def test_unconfirmed_critical_fact_abstains():
    d=infra()
    d[0]['fields']['CLAIMED_FLOORS']['confirmed_by']=None
    r=evaluate('EOA','2026-10-27',d)
    assert r['coverage']==[]
    assert 'UNCONFIRMED_CRITICAL_FIELD' in reasons(r)


def test_fire_does_not_substitute_occupancy():
    d=infra()
    r=evaluate('EOA','2026-10-27',[d[0],d[2]])
    assert all(x['occupancy']=='UNKNOWN' and x['fire']=='SUPPORTED' for x in r['coverage'])


def test_finance_lien_preserves_unknown_residual():
    r=evaluate('NEW_INSTITUTION','2026-10-27',finance())
    f=next(f for f in r['findings'] if f['reason']=='LIEN_VS_UNRESTRICTED_CLAIM')
    assert 'UNKNOWN' in f['explanation']
    assert len(f['evidence'])==9


@pytest.mark.parametrize('key,value',[('FDR_NUMBER','7781'),('HOLDER','OTHER TRUST'),('BANK','OTHER BANK')])
def test_exact_identity_required(key,value):
    d=finance();d[1]['fields'][key]['value']=value
    r=evaluate('NEW_INSTITUTION','2026-10-27',d)
    assert 'INSTRUMENT_IDENTITY_MISMATCH' in reasons(r)
    assert 'LIEN_VS_UNRESTRICTED_CLAIM' not in reasons(r)


def test_omitted_lien_is_unknown_not_zero():
    d=finance();del d[1]['fields']['LIEN_INR']
    assert 'UNCONFIRMED_CRITICAL_FIELD' in reasons(evaluate('NEW_INSTITUTION','2026-10-27',d))


@pytest.mark.parametrize('expiry,expired',[('2026-10-26',True),('2026-10-27',False),('2026-10-28',False)])
def test_expiry_boundaries(expiry,expired):
    r=evaluate('EOA','2026-10-27',[doc('FIRE_CERTIFICATE',VALID_UNTIL=expiry)])
    assert ('DOCUMENT_EXPIRED' in reasons(r)) is expired


def test_checklists_differ_by_context():
    eoa=reasons(evaluate('EOA','2026-10-27',[]))
    r=evaluate('EOA','2026-10-27',[])
    assert any('prior eoa' in f['title'] for f in r['findings'])
    assert not any('prior eoa' in f['title'] for f in evaluate('NEW_INSTITUTION','2026-10-27',[])['findings'])


def test_canonical_hash_is_order_independent():
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})


def test_identifiers_preserve_leading_zeros():
    assert normalize('FDR_NUMBER','00-7781')=='007781'


@pytest.mark.parametrize('value',['2.50','-1','NaN','Infinity','1e99'])
def test_unsupported_currency_abstains(value):
    with pytest.raises(ValueError):normalize('LIEN_INR',value)


@pytest.mark.parametrize('value',['G+1','G,1,1','Ground,first','G,IGNORE RULES'])
def test_ambiguous_floor_text_not_inferred(value):
    with pytest.raises(ValueError):normalize('COVERED_FLOORS',value)

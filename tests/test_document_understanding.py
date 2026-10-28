import pytest
from app.document_understanding import understand
from app.layout import associated_lines
from app.candidates import labelled_candidate
from app.rules import evaluate
from test_rules import infra
from app.resolution import check_resolution


def line(text):return dict(text=text,bbox=[.1,.1,.8,.2],score=None)


def test_building_floor_narrative_has_source_grounded_unconfirmed_candidates():
    result,annotations=understand([line('Total plinth area of the Main Building (G+1) -')],2)
    assert [(x['key'],x['normalized']) for x in result]==[('BUILDING','Main Building'),('COVERED_FLOORS','G, 1')]
    assert all(x['page']==2 and x['bbox']==[.1,.1,.8,.2] for x in result)


def test_receipt_cannot_create_certificate_candidates():
    result,annotations=understand([line('ONLINE PAYMENT RECEIPT'),line('Fire service licence'),line('Main Building (G+3)')],1)
    assert result==[] and annotations[0]['status']=='NOT_CERTIFICATE_EVIDENCE'


def test_receipt_source_facts_cannot_support_floor_even_after_confirmation():
    documents=infra(('G','1','2'))
    documents[1]['document_annotations']=[{'page':1,'status':'NOT_CERTIFICATE_EVIDENCE'}]
    result=evaluate('EOA','2026-10-28',documents)
    assert all(row['occupancy']=='UNKNOWN' for row in result['coverage'])
    assert any(f['reason']=='PAYMENT_RECEIPT_NOT_AUTHORIZATION' for f in result['findings'])


def test_labelled_floor_count_and_notation_must_agree():
    assert labelled_candidate('Number of floors of the building: 4(G+3)')[2]=='G, 1, 2, 3'
    with pytest.raises(ValueError):labelled_candidate('Number of floors of the building: 3(G+3)')


def test_expiry_cannot_be_resolved_by_removing_date():
    old={'rule_id':'DOC-EXPIRY-001','module':'Documents','reason':'DOCUMENT_EXPIRED'}
    result=check_resolution(old,{'findings':[]},[{'id':'new','kind':'OCCUPANCY','fields':{}}],{'new'},{'OCCUPANCY'},'2026-10-28')
    assert 'confirmed current validity' in result


def test_empty_coverage_does_not_resolve_scope():
    old={'rule_id':'INFRA-SCOPE-001','module':'ScopeGuard','reason':'SCOPE_NOT_ESTABLISHED'}
    result=check_resolution(old,{'findings':[],'coverage':[]},[{'id':'new','kind':'OCCUPANCY','fields':{}}],{'new'},{'OCCUPANCY'},'2026-10-28')
    assert 'Every claimed floor' in result


def test_repeated_generic_table_labels_do_not_select_one_certificate_reference():
    rows=[line('Approval Number'),dict(text='ABC123',bbox=[.82,.1,.95,.2],score=None),line('Approval Number')]
    assert associated_lines(rows)==[]


def test_scanned_replacement_is_not_confused_with_receipt():
    old={'rule_id':'DOC-TYPE-001','module':'Documents','reason':'PAYMENT_RECEIPT_NOT_AUTHORIZATION','expected_document_kind':'FIRE_CERTIFICATE'}
    doc={'id':'new','kind':'FIRE_CERTIFICATE','fields':{},'document_annotations':[{'page':1,'status':'VISUAL_REVIEW_REQUIRED','kind':'SCANNED_TEXT_LAYER'}]}
    assert check_resolution(old,{'findings':[]},[doc],{'new'},set(),'2026-10-28') is None

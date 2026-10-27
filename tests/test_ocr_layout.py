import pytest
from app.ocr import paddle_lines, LocalOCR
from app.layout import associated_lines, observations
from app.candidates import labelled_candidate, classify


def line(text, box):
    return dict(text=text,bbox=box,score=None)


def test_paddle_result_normalizes_source_coordinates():
    result=paddle_lines(dict(rec_texts=['Ground floor'],rec_scores=[.91],rec_polys=[[[10,20],[90,20],[90,40],[10,40]]]),100,200)
    assert result==[dict(text='Ground floor',score=.91,bbox=[.1,.1,.9,.2])]


@pytest.mark.parametrize('payload',[
    dict(rec_texts=['x'],rec_scores=[],rec_polys=[]),
    dict(rec_texts=['x'],rec_scores=[float('nan')],rec_polys=[[[0,0],[1,0],[1,1],[0,1]]]),
    dict(rec_texts=['x'],rec_scores=[.9],rec_polys=[[[0,0],[0,0],[0,0],[0,0]]]),
])
def test_malformed_paddle_output_is_rejected(payload):
    with pytest.raises(ValueError):paddle_lines(payload,100,100)


def test_unknown_provider_never_silently_substitutes(monkeypatch):
    monkeypatch.setenv('AICTE_OCR_PROVIDER','cloud-unknown')
    with pytest.raises(ValueError,match='UNKNOWN_OCR_PROVIDER'):LocalOCR()


def test_unique_same_row_label_value_retains_both_source_regions():
    rows=[line('Covered floors', [.1,.1,.3,.12]),line('Ground, First',[.32,.1,.5,.12])]
    joined=associated_lines(rows)
    assert joined[0]['bbox']==[.1,.1,.5,.12]
    assert labelled_candidate(joined[0]['text'])==('COVERED_FLOORS','Ground, First','G, 1')


def test_multiple_neighboring_cells_and_unrelated_rows_abstain():
    rows=[line('Covered floors',[.1,.1,.3,.12]),line('G, 1',[.31,.1,.35,.12]),line('G, 2',[.36,.1,.4,.12])]
    assert associated_lines(rows)==[]
    assert associated_lines([rows[0],line('G, 1',[.31,.3,.5,.32])])==[]


def test_floor_mention_does_not_become_coverage_fact():
    source=line('Main building (G+3)',[.1,.2,.8,.23])
    hints=observations([source],2)
    assert hints[0]['suggested_value']==['G','1','2','3']
    assert hints[0]['status']=='REVIEW_REQUIRED'
    assert hints[0]['page']==2
    assert labelled_candidate(source['text']) is None


def test_handwritten_date_label_has_no_guessed_date():
    hints=observations([line('Valid upto',[.1,.2,.2,.23])],1)
    assert hints[0]['kind']=='EXPIRY_LABEL_MENTION'
    assert 'suggested_value' not in hints[0]


def test_fire_licence_heading_recognized_as_unconfirmed_type():
    assert classify(['FORM OF FIRE & RESCUE SERVICE LICENCE'])[0]['kind']=='FIRE_CERTIFICATE'


def test_explicit_force_ocr_uses_selected_provider_and_keeps_provenance(tmp_path,monkeypatch):
    from app.extract import extract
    from app.seed import pdf_bytes
    path=tmp_path/'weak-text-layer.pdf'
    path.write_bytes(pdf_bytes('OCCUPANCY',['This native text layer has enough characters to bypass automatic OCR.']))
    monkeypatch.setenv('AICTE_OCR_FORCE','true')
    monkeypatch.setenv('AICTE_OCR_PROVIDER','paddleocr')
    monkeypatch.setattr(LocalOCR,'recognize',lambda self,image:([
        dict(text='Covered floors: G, 1',bbox=[.1,.1,.8,.2],score=.95)
    ],'CPU_OCR_PADDLEOCR'))
    result=extract(path,use_ocr=True)
    assert result['metrics']['ocr_pages']==1
    assert result['metrics']['forced_ocr'] is True
    assert result['fields'][0]['value']==['G','1']
    assert 'PADDLEOCR:UNCONFIRMED_CANDIDATE' in result['fields'][0]['engine']
    assert result['metrics']['automatic_accepted_critical_fields']==0


def test_uninstalled_paddle_fails_without_silent_fallback(tmp_path,monkeypatch):
    monkeypatch.setenv('AICTE_OCR_PROVIDER','paddleocr')
    monkeypatch.setenv('AICTE_PADDLE_PYTHON',str(tmp_path/'missing-python'))
    with pytest.raises(ValueError,match='PADDLE_WORKER_NOT_INSTALLED'):
        LocalOCR().recognize(None)

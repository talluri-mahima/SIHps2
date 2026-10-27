import io
import json
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest
import pymupdf as fitz
from sqlalchemy import select,text
from app.candidates import labelled_candidate,candidate_value
from app.extract import extract
from app.verify import signatures
from app.qr import reference_status
from app.db import Session,initialize
from app import models as m
from app.seed import pdf_bytes


def test_varied_labels_and_indian_amounts():
    assert labelled_candidate('Principal amount: Rs. 2.00 crore')==('PRINCIPAL_INR','Rs. 2.00 crore','20000000.00')
    assert labelled_candidate('FDR No.: 00-7781')[0]=='FDR_NUMBER'
    assert labelled_candidate('Occupancy scope: Ground floor and First floor')[2]=='G, 1'
    with pytest.raises(ValueError):candidate_value('VALID_UNTIL','02/03/2026')


def test_native_alternative_layout_produces_source_candidates(tmp_path):
    file=tmp_path/'different.pdf'
    file.write_bytes(pdf_bytes('FDR_ADVICE',['FDR No.: 00-7781','Principal amount: INR 2 crore','Lien amount: Rs. 1.80 crore']))
    result=extract(file,use_ocr=False)
    values={f['key']:f['value'] for f in result['fields']}
    assert values=={'FDR_NUMBER':'007781','PRINCIPAL_INR':20000000,'LIEN_INR':18000000}
    assert result['metrics']['ocr_pages']==0


def test_real_cpu_ocr_from_image_only_pdf(tmp_path):
    native=pdf_bytes('OCCUPANCY',['Building: BLOCK C','Floors covered: G, 1','Valid until: 2027-06-30'])
    with fitz.open(stream=native,filetype='pdf') as original:
        image=original[0].get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
    file=tmp_path/'scanned.pdf'
    with fitz.open() as scan:
        page=scan.new_page(width=595,height=842);page.insert_image(page.rect,stream=image);scan.save(file)
    with fitz.open(file) as scan:assert scan[0].get_text().strip()==''
    result=extract(file,tmp_path/'pages')
    values={f['key']:f['value'] for f in result['fields']}
    assert result['metrics']['ocr_pages']==1
    assert values['BUILDING']=='BLOCK C' and values['COVERED_FLOORS']==['G','1']
    assert values['VALID_UNTIL']=='2027-06-30'
    assert (tmp_path/'pages'/'1.png').is_file()
    assert all('CPU_OCR' in f['engine'] for f in result['fields'])


def test_unsigned_does_not_mean_forged(tmp_path):
    file=tmp_path/'unsigned.pdf';file.write_bytes(pdf_bytes('PRIOR_EOA',[]))
    result=signatures(file)
    assert result['status']=='NO_SIGNATURE_PRESENT' and result['network_fetching'] is False
    assert 'forgery' in result['notice']


def test_real_signature_integrity_and_explicit_trust(tmp_path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic test signer')])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(datetime.now(timezone.utc)-timedelta(days=1)).not_valid_after(datetime.now(timezone.utc)+timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=True,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=None,decipher_only=None),critical=True).sign(key,hashes.SHA256()))
    keyfile=tmp_path/'test-key.pem';certfile=tmp_path/'test-cert.pem'
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    signer=signers.SimpleSigner.load(str(keyfile),str(certfile))
    source=io.BytesIO(pdf_bytes('SIGNED_SYNTHETIC_DOCUMENT',[]));output=io.BytesIO()
    signers.sign_pdf(IncrementalPdfFileWriter(source),signature_meta=signers.PdfSignatureMetadata(field_name='TestSignature'),signer=signer,output=output)
    file=tmp_path/'signed.pdf';file.write_bytes(output.getvalue())
    untrusted=signatures(file)
    assert untrusted['signatures'][0]['integrity'] and untrusted['signatures'][0]['cryptographic_validity']
    assert not untrusted['signatures'][0]['trusted_chain']
    trusted=signatures(file,str(certfile))
    assert trusted['signatures'][0]['trusted_chain']
    assert trusted['signatures'][0]['revocation']=='NOT_ESTABLISHED_OFFLINE'


@pytest.mark.parametrize('url',['http://example.org','https://127.0.0.1/a','https://169.254.169.254/latest','file:///etc/passwd','https://localhost/a','javascript:alert(1)'])
def test_qr_references_cannot_become_network_requests(url):
    assert reference_status(url).startswith('BLOCKED')


def test_public_qr_still_requires_authorized_adapter():
    assert reference_status('https://example.org/certificate/123')=='NOT_FETCHED_AUTHORIZED_ADAPTER_REQUIRED'


def test_migrations_preserve_existing_records(clients,fresh_app):
    initialize()
    with Session() as db:
        assert db.get(m.Application,fresh_app)
        assert db.scalar(text('SELECT version_num FROM alembic_version'))=='0002'


def test_integrations_dont_claim_government_connection(clients):
    r=clients['officer'].get('/v1/integrations')
    assert r.status_code==200
    assert r.json()['production_ready'] is False
    services={s['name']:s for s in r.json()['services']}
    assert services['Persistent database']['state']=='CONNECTED'
    assert services['Scanned-document OCR']['state']=='AVAILABLE'
    assert services['AICTE institutional records']['state']=='NOT_CONNECTED'


def test_pdf_report_contains_only_confirmed_snapshot(clients,fresh_app):
    c=clients['officer'];base='/v1/applications/'+fresh_app
    c.post(base+'/evaluations')
    f=c.get(base).json()['evaluation']['findings'][0]
    assert c.post('/v1/findings/'+f['id']+'/actions',json={'action':'CONFIRM','reason':'Reviewed current missing evidence.'},headers={'If-Match':'1'}).status_code==200
    exported=c.post(base+'/exports').json()
    response=c.get('/v1/exports/'+exported['id']+'/pdf')
    assert response.status_code==200 and response.headers['content-type']=='application/pdf'
    with fitz.open(stream=response.content,filetype='pdf') as pdf:
        text_content=' '.join(p.get_text() for p in pdf)
        assert 'SYNTHETIC DEMONSTRATION REVIEW REPORT' in text_content
        assert 'Confirmed observations: 1' in text_content
        assert f['title'] in text_content
    assert response.headers['x-report-content-sha256']==exported['sha256']


def test_demo_login_can_be_disabled(clients,monkeypatch):
    monkeypatch.setenv('AICTE_DEMO_LOGIN','false')
    assert clients['officer'].post('/v1/dev/session/officer').status_code==404
    assert clients['officer'].get('/v1/auth/config').json()['demo_login_enabled'] is False

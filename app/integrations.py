"""Readiness is configuration and local checks, never a fabricated live connection."""
import importlib.util
import os
from pathlib import Path
from sqlalchemy import text
from .config import DATA, SOFTWARE_VERSION, ROOT


def readiness(db):
    from sqlalchemy import select
    from .models import VerificationEvent
    database_ok=db.scalar(text('SELECT 1'))==1
    modules={name:importlib.util.find_spec(name) is not None for name in ['rapidocr_onnxruntime','pyhanko','alembic']}
    disk_ok=(DATA/'objects').is_dir() and (DATA/'derived').is_dir()
    scan_result=db.scalar(select(VerificationEvent).where(VerificationEvent.check_type=='MALWARE_SCAN',VerificationEvent.mode=='WINDOWS_DEFENDER').order_by(VerificationEvent.created_at.desc()).limit(1))
    scanner=os.getenv('AICTE_MALWARE_SCANNER','none').lower()
    provider=os.getenv('AICTE_OCR_PROVIDER','rapidocr').lower()
    paddle_python=Path(os.getenv('AICTE_PADDLE_PYTHON',str(ROOT/'.venv-paddle'/'Scripts'/'python.exe')))
    paddle_ready=paddle_python.is_file() and all((DATA/'paddle-models'/folder/'inference.json').is_file() for folder in ['detection','recognition'])
    ocr_available=(paddle_ready if provider=='paddleocr' else modules['rapidocr_onnxruntime'] if provider=='rapidocr' else False) and os.getenv('AICTE_OCR_ENABLED','true').lower()=='true'
    return {'version':SOFTWARE_VERSION,'profile':'LOCAL_PROTOTYPE','production_ready':False,
            'services':[
                {'name':'Application API','state':'CONNECTED','mode':'LOCAL','detail':'Authenticated application and evidence endpoints'},
                {'name':'Persistent database','state':'CONNECTED' if database_ok else 'FAILED','mode':db.bind.dialect.name.upper(),'detail':'Database round-trip tested; schema managed by Alembic'},
                {'name':'Private evidence storage','state':'CONNECTED' if disk_ok else 'FAILED','mode':'LOCAL_FILESYSTEM','detail':'Application-authorized access; private originals and derived pages'},
                {'name':'Native PDF extraction','state':'AVAILABLE','mode':'ON_DEVICE','detail':'PDF text, word locations and bounded derived-page rendering'},
                {'name':'Scanned-document OCR','state':'AVAILABLE' if ocr_available else 'UNAVAILABLE','mode':'CPU_ON_DEVICE','detail':provider+' selected; local dependencies/model presence checked, document accuracy must be evaluated separately'},
                {'name':'PDF signature validation','state':'AVAILABLE' if modules['pyhanko'] else 'UNAVAILABLE','mode':'LOCAL_CRYPTOGRAPHIC','detail':'Offline integrity/trust checks; revocation remains unresolved without approved evidence'},
                {'name':'User login','state':'AVAILABLE','mode':'LOCAL_PASSWORD_AND_SESSION','detail':'Argon2 passwords and revocable server sessions; OIDC is not connected'},
                {'name':'AICTE institutional records','state':'NOT_CONNECTED','mode':'AUTHORIZATION_REQUIRED','detail':'No authorized portal API credentials or data-sharing contract'},
                {'name':'Issuer / bank / DigiLocker','state':'NOT_CONNECTED','mode':'MANUAL_REVIEW','detail':'No authorized source adapter connected; manual and mock observations remain labelled'},
                {'name':'Cloud AI / OCR','state':'NOT_CONFIGURED','mode':'OPTIONAL','detail':'Not needed for local OCR; no document is sent to a cloud model'},
                {'name':'Malware scanning','state':'CONNECTED' if scanner=='defender' and scan_result and scan_result.status=='NO_THREATS_DETECTED' else 'CONFIGURED' if scanner!='none' else 'NOT_CONNECTED','mode':'WINDOWS_DEFENDER' if scanner=='defender' else 'STRUCTURAL_CHECKS_ONLY','detail':'Configured scanner runs before parsing; inconclusive/detection quarantines the document. Latest provider result: '+(scan_result.status if scan_result else 'none')},
                {'name':'Policy rule pack','state':'DRAFT','mode':'REVIEW_REQUIRED','detail':'Source-backed consistency checks are not an approved regulatory decision engine'}]}

"""Local cryptographic signature validation. No document-directed network access."""
import json
import logging
import os
import sys


def signatures(path, trust_file=None):
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
    from pyhanko.keys import load_cert_from_pemder
    roots=[load_cert_from_pemder(trust_file)] if trust_file else []
    vc=ValidationContext(trust_roots=roots,allow_fetching=False,revocation_mode='soft-fail')
    records=[]
    with open(path,'rb') as stream:
        reader=PdfFileReader(stream,strict=True)
        for sig in reader.embedded_signatures:
            try:
                status=validate_pdf_signature(sig,signer_validation_context=vc)
                records.append({'field':sig.field_name,'integrity':bool(status.intact),'cryptographic_validity':bool(status.valid),
                                'trusted_chain':bool(status.trusted),'coverage':str(status.coverage),
                                'modification_level':str(status.modification_level),'docmdp_ok':status.docmdp_ok,
                                'revocation':'NOT_ESTABLISHED_OFFLINE',
                                'signer_subject':status.signing_cert.subject.human_friendly,
                                'certificate_not_before':status.signing_cert.not_valid_before.isoformat(),
                                'certificate_not_after':status.signing_cert.not_valid_after.isoformat(),
                                'trusted_timestamp':bool(status.timestamp_validity and status.timestamp_validity.trusted)})
            except Exception:
                records.append({'field':sig.field_name,'integrity':None,'cryptographic_validity':None,'trusted_chain':False,'revocation':'NOT_ESTABLISHED_OFFLINE','error':'SIGNATURE_VALIDATION_INCONCLUSIVE'})
    return {'status':'SIGNATURES_CHECKED' if records else 'NO_SIGNATURE_PRESENT','mode':'LOCAL_CRYPTOGRAPHIC',
            'trust_roots_configured':bool(roots),'network_fetching':False,'signatures':records,
            'notice':'Integrity, trust and revocation are separate. No signature is not proof of forgery; document scope and issuer authority require separate review.'}


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    try:
        print(json.dumps(signatures(sys.argv[1],os.getenv('AICTE_SIGNATURE_TRUST_PEM'))))
    except Exception:
        print(json.dumps({'status':'VALIDATION_INCONCLUSIVE','mode':'LOCAL_CRYPTOGRAPHIC','error':'UNSUPPORTED_SIGNATURE_OR_DOCUMENT','network_fetching':False}))
        sys.exit(1)

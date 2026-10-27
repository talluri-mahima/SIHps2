"""Decode QR data locally; never visit document-supplied URLs."""
import ipaddress
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

def reference_status(value):
    parsed=urlparse(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        return 'BLOCKED_UNSAFE_OR_NON_HTTPS_REFERENCE'
    host=parsed.hostname.lower().rstrip('.')
    if host in {'localhost'} or host.endswith(('.local','.localhost','.internal')):
        return 'BLOCKED_PRIVATE_REFERENCE'
    try:
        if not ipaddress.ip_address(host).is_global:return 'BLOCKED_PRIVATE_REFERENCE'
    except ValueError:
        pass
    return 'NOT_FETCHED_AUTHORIZED_ADAPTER_REQUIRED'


def decode(directory):
    import cv2
    detector=cv2.QRCodeDetector()
    references=[]
    paths=sorted(Path(directory).glob('*.png'))[:5]
    for file in paths:
        image=cv2.imread(str(file))
        if image is None:continue
        ok,values,_,_=detector.detectAndDecodeMulti(image)
        if not ok:
            single,_,_=detector.detectAndDecode(image)
            values=[single] if single else []
        for value in values:
            if value and len(value)<=2048:
                references.append({'text':value,'status':reference_status(value),'page':int(file.stem)})
    return {'status':'REFERENCES_DECODED' if references else 'NO_QR_REFERENCE_DECODED','mode':'LOCAL_DECODE_ONLY',
            'pages_checked':len(paths),'decoded_references':references,'network_requests':0,
            'notice':'QR content is untrusted data. No URL was visited and no issuer authenticity was established.'}

if __name__=='__main__':
    try:print(json.dumps(decode(sys.argv[1])))
    except Exception:
        print(json.dumps({'status':'DECODE_INCONCLUSIVE','mode':'LOCAL_DECODE_ONLY','network_requests':0}))
        sys.exit(1)

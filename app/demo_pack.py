"""Synthetic demonstration fixtures, including actual image-only scan PDFs."""
import io
import zipfile
from .seed import DEMO_DOCUMENTS,pdf_bytes
import pymupdf as fitz

def scanned_pdf(data):
    with fitz.open(stream=data,filetype='pdf') as source,fitz.open() as output:
        image=source[0].get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
        page=output.new_page(width=595,height=842)
        page.insert_image(page.rect,stream=image)
        return output.tobytes()

def demo_files():
    files={kind.lower()+'.pdf':pdf_bytes(kind,lines) for kind,lines in DEMO_DOCUMENTS.items()}
    files['occupancy-corrected-scan.pdf']=scanned_pdf(pdf_bytes('OCCUPANCY',['Building: BLOCK C','Floors covered: G, 1, 2','Valid until: 2027-06-30']))
    files['README.txt']=b'SYNTHETIC DEMONSTRATION ONLY\nUpload room_schedule.pdf as ROOM_SCHEDULE, occupancy.pdf as OCCUPANCY, fire_certificate.pdf as FIRE_CERTIFICATE, dpr.pdf as DPR and fdr_advice.pdf as FDR_ADVICE.\nAfter reviewing initial findings, submit occupancy-corrected-scan.pdf as a replacement OCCUPANCY record. This is an image-only PDF and uses real CPU OCR.\nAll values are fictional. No record was issued by AICTE or a real bank. Source verification is not implied.\n'
    return files

def zip_bytes():
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in demo_files().items():archive.writestr(name,data)
    return output.getvalue()

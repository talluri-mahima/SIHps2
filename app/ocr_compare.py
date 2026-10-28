"""Read a stored page image with the selected local OCR; do not change accepted facts."""
import json
import sys
import pymupdf as fitz
from .ocr import LocalOCR

if __name__=='__main__':
    engine=LocalOCR()
    try:
        image=fitz.Pixmap(sys.argv[1])
        if image.width*image.height>12_000_000:raise ValueError('IMAGE_PIXEL_LIMIT')
        lines,method=engine.recognize(image)
        print(json.dumps(dict(method=method,lines=lines,automatic_accepted_fields=0,notice='Alternative OCR transcription only. Compare with the original and confirm corrections explicitly.')))
    finally:engine.close()

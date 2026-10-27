"""Explicit local OCR providers. No silent provider substitution or remote API."""
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def paddle_lines(payload, width, height):
    """Normalize PaddleOCR 3.x output and reject malformed coordinates/scores."""
    import math
    lines = []
    texts, scores, polygons = payload['rec_texts'], payload['rec_scores'], payload['rec_polys']
    if not len(texts) == len(scores) == len(polygons) or len(texts) > 10000:
        raise ValueError('OCR_RESULT_LIMIT_OR_SHAPE')
    for text, score, polygon in zip(texts, scores, polygons):
        if len(polygon) != 4 or not isinstance(text, str) or len(text) > 20000:
            raise ValueError('INVALID_OCR_RESULT')
        xs = [float(p[0]) for p in polygon]; ys = [float(p[1]) for p in polygon]
        score = float(score)
        if not all(math.isfinite(v) for v in [*xs, *ys, score]) or not 0 <= score <= 1:
            raise ValueError('INVALID_OCR_RESULT')
        bbox = [max(0, min(xs)/width), max(0, min(ys)/height), min(1, max(xs)/width), min(1, max(ys)/height)]
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError('INVALID_OCR_BOUNDS')
        lines.append(dict(text=text, bbox=bbox, score=score))
    return lines


class LocalOCR:
    def __init__(self):
        self.provider = os.getenv('AICTE_OCR_PROVIDER', 'rapidocr').lower()
        self.engine = None
        self.worker = None
        self.reader = None
        if self.provider not in {'rapidocr', 'paddleocr'}:
            raise ValueError('UNKNOWN_OCR_PROVIDER')

    def recognize(self, image):
        if self.provider == 'paddleocr':
            root = Path(__file__).resolve().parents[1]
            python = Path(os.getenv('AICTE_PADDLE_PYTHON', str(root/'.venv-paddle'/'Scripts'/'python.exe')))
            if not python.is_file():
                raise ValueError('PADDLE_WORKER_NOT_INSTALLED')
            with tempfile.TemporaryDirectory(prefix='aicte-ocr-') as tmp:
                path = Path(tmp)/'page.png'; result = Path(tmp)/'result.json'
                image.save(str(path))
                if self.worker is None:
                    self.worker = subprocess.Popen([str(python),str(root/'scripts/paddle_worker.py'),'--serve'],
                                                   stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                                   text=True,encoding='utf-8')
                    self.reader = ThreadPoolExecutor(max_workers=1)
                try:
                    self.worker.stdin.write(json.dumps({'input':str(path),'output':str(result)})+'\n')
                    self.worker.stdin.flush()
                    response=self.reader.submit(self.worker.stdout.readline).result(timeout=180)
                    if json.loads(response).get('status')!='COMPLETED':
                        raise ValueError('PADDLE_WORKER_FAILED')
                except Exception:
                    self.close()
                    raise
                if not result.is_file() or result.stat().st_size > 10_000_000:
                    raise ValueError('PADDLE_WORKER_FAILED')
                return paddle_lines(json.loads(result.read_text(encoding='utf-8')), image.width, image.height), 'CPU_OCR_PADDLEOCR'
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
        if self.engine is None:
            self.engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
        pixels = np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)
        results, _ = self.engine(pixels)
        payload = dict(rec_texts=[], rec_scores=[], rec_polys=[])
        for polygon, text, score in results or []:
            payload['rec_texts'].append(text); payload['rec_scores'].append(float(score)); payload['rec_polys'].append(polygon)
        return paddle_lines(payload, image.width, image.height), 'CPU_OCR_RAPIDOCR'

    def close(self):
        if self.worker is not None:
            try:
                self.worker.stdin.close()
                self.worker.wait(timeout=3)
            except (OSError,subprocess.TimeoutExpired):
                self.worker.kill()
            finally:
                self.worker.stdout.close()
                self.worker=None
        if self.reader is not None:
            self.reader.shutdown(wait=False,cancel_futures=True)
            self.reader=None

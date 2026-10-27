"""Isolated CPU worker. Provision models explicitly; requests use local files only."""
import json
import os
import sys
import contextlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
os.environ.setdefault('OMP_NUM_THREADS', '1')

def main():
    from paddleocr import PaddleOCR
    provision = '--provision' in sys.argv
    models = ROOT/'.data'/'paddle-models'
    # oneDNN/PIR raises NotImplementedError on this tested Windows runtime.
    options = dict(device='cpu', cpu_threads=2, enable_mkldnn=False,
                   use_doc_orientation_classify=False, use_doc_unwarping=False,
                   use_textline_orientation=False,
                   text_detection_model_name='PP-OCRv5_mobile_det',
                   text_recognition_model_name='en_PP-OCRv5_mobile_rec')
    if not provision:
        for option, folder in [('text_detection_model_dir','detection'), ('text_recognition_model_dir','recognition')]:
            directory = models/folder
            if not (directory/'inference.json').is_file():
                raise RuntimeError('PADDLE_MODELS_NOT_PROVISIONED')
            options[option] = str(directory)
    with contextlib.redirect_stdout(sys.stderr):
        pipeline = PaddleOCR(**options)
    if provision:
        # Copy downloaded model directories into the application's ignored store.
        import shutil
        cache = Path.home()/'.paddlex'/'official_models'
        for name, folder in [('PP-OCRv5_mobile_det','detection'),('en_PP-OCRv5_mobile_rec','recognition')]:
            shutil.copytree(cache/name, models/folder, dirs_exist_ok=True)
        print('Local OCR model files provisioned; no application document uploaded.')
        return
    if '--serve' in sys.argv:
        for request in sys.stdin:
            item=json.loads(request)
            with contextlib.redirect_stdout(sys.stderr):
                payload=predict(pipeline,item['input'])
            Path(item['output']).write_text(json.dumps(payload),encoding='utf-8')
            print(json.dumps({'status':'COMPLETED'}),flush=True)
        return
    payload=predict(pipeline,sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(payload), encoding='utf-8')


def predict(pipeline,path):
    results = list(pipeline.predict(input=path))
    if len(results) != 1:
        raise ValueError('EXPECTED_ONE_PAGE')
    result = results[0].json
    if isinstance(result, str):
        result = json.loads(result)
    result = result.get('res', result)
    return {key:result[key] for key in ('rec_texts','rec_scores','rec_polys')}

if __name__ == '__main__':
    main()

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
except ImportError:
    pass
DATA = Path(os.getenv('AICTE_DATA_DIR', str(ROOT / '.data'))).resolve()
DATABASE_URL = os.getenv('AICTE_DATABASE_URL', f'sqlite:///{DATA / "platform.db"}')
MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 30
SOFTWARE_VERSION = '0.2.0'


def validate_environment():
    # Fail closed: this milestone has no production identity or malware provider.
    if os.getenv('APP_ENV', 'development') != 'development':
        raise RuntimeError('Production release blocked: OIDC, malware isolation, RLS and policy gates are not implemented.')
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'objects').mkdir(exist_ok=True)
    (DATA / 'derived').mkdir(exist_ok=True)
    (DATA / 'processing').mkdir(exist_ok=True)

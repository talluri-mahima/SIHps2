"""Set named local demo-account passwords without printing or committing them."""
import getpass
import secrets
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from argon2 import PasswordHasher
from sqlalchemy import select,delete
from app.db import Session,initialize
from app.seed import seed
from app.models import User,LoginSession

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate',action='store_true',help='Generate random passwords into an ignored private local file')
    args=parser.parse_args()
    initialize();seed()
    hasher=PasswordHasher()
    generated=[]
    for persona in ['officer','institution','auditor']:
        email=f'{persona}@demo.invalid'
        password=secrets.token_urlsafe(18) if args.generate else getpass.getpass(f'Choose password for {email} (12+ characters): ')
        if len(password)<12:raise SystemExit('Password too short; no password was changed for this account.')
        if not args.generate and password!=getpass.getpass('Confirm password: '):raise SystemExit('Passwords did not match.')
        with Session.begin() as db:
            user=db.scalar(select(User).where(User.email==email))
            user.password_hash=hasher.hash(password)
            db.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
        print('Password configured for '+email)
        if args.generate:generated.append(email+'\nPassword: '+password+'\n')
    if generated:
        from app.config import DATA
        location=DATA/'local-access.txt'
        location.write_text('PRIVATE LOCAL DEMONSTRATION ACCOUNTS — DO NOT SHARE OR COMMIT\n\n'+'\n'.join(generated),encoding='utf-8')
        print('Credentials saved privately in .data/local-access.txt; passwords are not printed.')
    print('Set AICTE_DEMO_LOGIN=false in your local .env and restart to require password sign-in.')

if __name__=='__main__':main()

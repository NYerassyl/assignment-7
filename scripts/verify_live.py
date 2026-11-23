"""Run persistence and actual Swagger UI acceptance on an isolated PostgreSQL DB."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from uuid import uuid4
import httpx
from sqlalchemy.engine import make_url

root=Path(__file__).resolve().parents[1]
url=make_url(os.environ['DATABASE_URL'])
assert url.host in (None,'localhost','127.0.0.1') and url.database.endswith('_test')
env={**os.environ, 'JWT_SECRET': secrets.token_urlsafe(48)}
origin='http://127.0.0.1:8017'
child=None

def start():
    global child
    child=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1','--port','8017'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(60):
        if child.poll() is not None: raise RuntimeError('Server failed to start')
        try:
            if httpx.get(origin+'/api/health',timeout=1).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('Server readiness timeout')

def stop():
    if child and child.poll() is None:
        child.terminate();child.wait(timeout=10)

try:
    start()
    name='persist'+uuid4().hex.translate(str.maketrans('0123456789','abcdefghij'))[:10]
    r=httpx.post(origin+'/api/auth/register',json={'email':name+'@example.com','nickname':name,'password':'PersistencePassword123!'})
    assert r.status_code==201,r.text
    data=r.json();headers={'Authorization':'Bearer '+data['token']}
    uid=data['user']['id']
    assert httpx.patch(origin+'/api/users/'+uid,json={'bio':'Survives restart'},headers=headers).status_code==200
    stop();start()
    r=httpx.get(origin+'/api/users/me',headers=headers)
    assert r.status_code==200 and r.json()['bio']=='Survives restart'
    assert httpx.delete(origin+'/api/users/'+uid,headers=headers).status_code==204
    print('PASS: database and JWT session persist across two server processes',flush=True)
    subprocess.run([sys.executable,'scripts/verify_swagger.py'],cwd=root,env=env,check=True,timeout=180)
finally:
    stop()

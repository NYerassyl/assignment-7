import os
import time
from concurrent.futures import ThreadPoolExecutor
import jwt
from sqlalchemy import text
from database import engine
from auth_security import verify_password, hash_token


def test_register_login_storage_and_docs(client, register):
    data, headers = register()
    uid = data['user']['id']
    assert len(data['token'].split('.')) == 3
    assert client.get('/api/users/me', headers=headers).json()['id'] == uid
    with engine().connect() as db:
        password = db.scalar(text('SELECT "passwordHash" FROM "User" WHERE id=:id'), {'id':uid})
        digest = db.scalar(text('SELECT "tokenHash" FROM "AuthSession" WHERE "userId"=:id'), {'id':uid})
    assert password != 'StrongPassword123!' and verify_password('StrongPassword123!', password)
    assert digest == hash_token(data['token'])
    login = client.post('/api/auth/login', json={'email':'ALICE@example.com','password':'StrongPassword123!'})
    assert login.status_code == 200 and login.json()['token'] != data['token']
    for path in ['/docs','/openapi.json','/api/health']:
        assert client.get(path).status_code == 200


def test_duplicate_validation_and_invalid_login(client, register):
    register()
    for email, nickname in [('alice@example.com','other'),('other@example.com','alice')]:
        assert client.post('/api/auth/register', json={'email':email,'nickname':nickname,'password':'StrongPassword123!'}).status_code == 409
    assert client.post('/api/auth/register', json={'email':'invalid','nickname':'a','password':'short'}).status_code == 422
    assert client.post('/api/auth/login', json={'email':'alice@example.com','password':'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'email':'missing@example.com','password':'wrong'}).status_code == 401


def test_missing_forged_expired_and_revoked_tokens(client, register):
    data, headers = register()
    assert client.get('/api/users/me').status_code == 401
    claims = jwt.decode(data['token'], os.environ['JWT_SECRET'], algorithms=['HS256'], audience='worldofcodes-api', issuer='worldofcodes-auth')
    for changes in [{'exp':int(time.time())-1},{'iss':'wrong'},{'aud':'wrong'},{'sub':'missing'}]:
        token = jwt.encode({**claims, **changes}, os.environ['JWT_SECRET'], algorithm='HS256')
        assert client.get('/api/users/me',headers={'Authorization':'Bearer '+token}).status_code == 401
    assert client.get('/api/users/me',headers={'Authorization':'Bearer a.b.c'}).status_code == 401
    assert client.post('/api/auth/logout',headers=headers).status_code == 204
    assert client.get('/api/users/me',headers=headers).status_code == 401
    assert client.post('/api/auth/logout',headers=headers).status_code == 401


def test_owner_update_delete_and_public_privacy(client, register):
    alice, a = register()
    bob, b = register('bobby')
    url = '/api/users/'+alice['user']['id']
    public = client.get(url).json()
    assert not {'email','passwordHash','coins','token'} & public.keys()
    assert client.patch(url,json={'bio':'changed'},headers=b).status_code == 403
    assert client.delete(url,headers=b).status_code == 403
    assert client.patch(url,json={'bio':'Learning Python','displayName':'Alice'},headers=a).status_code == 200
    assert client.get('/api/users/me',headers=a).json()['bio'] == 'Learning Python'
    assert client.patch(url,json={'xp':1000},headers=a).status_code == 422
    assert client.patch(url,json={},headers=a).status_code == 422
    assert client.delete(url,headers=a).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get('/api/users/me',headers=a).status_code == 401
    assert client.get('/api/users/me',headers=b).status_code == 200


def test_concurrent_logout(client, register):
    _, headers = register()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post('/api/auth/logout',headers=headers).status_code, range(2)))
    assert sorted(results) == [204,401]


def test_concurrent_registration(client):
    payload = {'email':'race@example.com','nickname':'racer','password':'StrongPassword123!'}
    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(pool.map(lambda _: client.post('/api/auth/register',json=payload).status_code, range(3)))
    assert sorted(statuses) == [201,409,409]


def test_missing_secret_does_not_create_user(client, monkeypatch):
    monkeypatch.delenv('JWT_SECRET')
    response = client.post('/api/auth/register',json={'email':'none@example.com','nickname':'none','password':'StrongPassword123!'})
    assert response.status_code == 503
    with engine().connect() as db:
        assert db.scalar(text('SELECT count(*) FROM "User"')) == 0

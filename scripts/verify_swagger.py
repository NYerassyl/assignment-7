"""Execute every operation through Swagger's Try it out / Execute buttons.
Run against an isolated running test server; creates unique temporary accounts.
"""
import json
import os
import re
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

origin = os.environ.get('TEST_ORIGIN', 'http://127.0.0.1:8017')
assert origin.startswith('http://127.0.0.1:'), 'Local test servers only'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(origin+'/docs')
    page.locator('.swagger-ui .opblock').first.wait_for(timeout=60000)

    def execute(method, path, status=200, data=None, params=None):
        block = page.locator('.opblock').filter(has=page.locator('[data-path="'+path+'"]')).filter(has=page.locator('.opblock-summary-method').filter(has_text=re.compile('^'+method+'$')))
        if 'is-open' not in block.get_attribute('class'):
            block.locator('.opblock-summary').click()
        if not block.get_by_role('button',name='Execute',exact=True).count():
            block.get_by_role('button',name='Try it out',exact=True).click()
        if data is not None:
            block.locator('textarea').fill(json.dumps(data))
        url = path
        for name,value in (params or {}).items():
            block.locator('tr[data-param-name="'+name+'"] input').fill(value)
            url = url.replace('{'+name+'}',value)
        with page.expect_response(lambda r: r.url.split('?')[0] == origin+url and r.request.method == method) as response:
            block.get_by_role('button',name='Execute',exact=True).click()
        result = response.value
        assert result.status == status, (path,result.status,result.text())
        print(method,path,status,flush=True)
        return result.json() if status != 204 else None

    def authorize(token):
        page.locator('.auth-wrapper button.authorize').click()
        modal=page.locator('.dialog-ux')
        logout=modal.locator('button').filter(has_text=re.compile(r'^\s*Logout\s*$'))
        if logout.count(): logout.click()
        modal.locator('input').fill(token)
        modal.locator('button.authorize').click()
        modal.locator('button.btn-done').click()

    execute('GET','/api/health')
    execute('GET','/api/users/me',401)
    suffix = uuid4().hex.translate(str.maketrans('0123456789','abcdefghij'))[:14]
    payload={'email':suffix+'@example.com','nickname':'user'+suffix,'password':'SwaggerPassword123!'}
    account=execute('POST','/api/auth/register',201,payload)
    execute('POST','/api/auth/register',409,payload)
    execute('POST','/api/auth/register',422,{**payload,'password':'short'})
    execute('POST','/api/auth/login',401,{'email':payload['email'],'password':'wrong'})
    logged=execute('POST','/api/auth/login',200,{'email':payload['email'],'password':payload['password']})
    authorize(logged['token'])
    execute('GET','/api/users/me')
    execute('GET','/api/users/{user_id}',params={'user_id':account['user']['id']})
    execute('PATCH','/api/users/{user_id}',data={'bio':'Verified in Swagger'},params={'user_id':account['user']['id']})
    other_payload={**payload,'nickname':'other'+suffix,'email':'other'+payload['email']}
    other=execute('POST','/api/auth/register',201,other_payload)
    execute('PATCH','/api/users/{user_id}',403,{'bio':'Not allowed'},{'user_id':other['user']['id']})
    execute('DELETE','/api/users/{user_id}',403,params={'user_id':other['user']['id']})
    execute('POST','/api/auth/logout',204)
    execute('GET','/api/users/me',401)
    authorize(account['token'])
    execute('DELETE','/api/users/{user_id}',204,params={'user_id':account['user']['id']})
    execute('GET','/api/users/{user_id}',404,params={'user_id':account['user']['id']})
    authorize(other['token'])
    execute('DELETE','/api/users/{user_id}',204,params={'user_id':other['user']['id']})
    browser.close()

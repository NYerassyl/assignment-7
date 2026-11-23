from fastapi import APIRouter, Response
import auth_service
import profile_service
from canonical_schemas import Register, Login, ProfilePatch
from site_auth import SiteSession, PlayerId, LogoutSession

router = APIRouter(prefix='/api')


@router.get('/health', tags=['health'])
def health():
    return {'status': 'ok'}


@router.post('/auth/register', tags=['auth'], status_code=201)
def register(payload: Register, session: SiteSession):
    return auth_service.register(session, payload)


@router.post('/auth/login', tags=['auth'])
def login(payload: Login, session: SiteSession):
    return auth_service.login(session, payload)


@router.post('/auth/logout', tags=['auth'], status_code=204)
def logout(session: SiteSession, identity: LogoutSession):
    auth_service.logout(session, identity)
    return Response(status_code=204)


@router.get('/users/me', tags=['profiles'])
def me(session: SiteSession, actor: PlayerId):
    return auth_service.current_profile(session, actor)


@router.get('/users/{user_id}', tags=['profiles'])
def public_profile(user_id: str, session: SiteSession):
    return profile_service.public_profile(session, user_id)


@router.patch('/users/{user_id}', tags=['profiles'])
def update_profile(user_id: str, payload: ProfilePatch, session: SiteSession, actor: PlayerId):
    return profile_service.update_profile(session, actor, user_id, payload)


@router.delete('/users/{user_id}', tags=['profiles'], status_code=204)
def delete_profile(user_id: str, session: SiteSession, identity: LogoutSession):
    # Exclusive session lock also avoids upgrading a shared lock during CASCADE.
    profile_service.delete_profile(session, identity.user_id, user_id)
    return Response(status_code=204)

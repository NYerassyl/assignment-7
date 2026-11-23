"""Resource ownership is checked on the server, never trusted from a request body."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from canonical_models import Player
from canonical_schemas import ProfilePatch
from auth_service import private_user
from errors import DomainError


def public_profile(session: Session, user_id: str) -> dict:
    user = session.get(Player, user_id)
    if user is None:
        raise DomainError(404, 'USER_NOT_FOUND', 'Player not found.')
    return {'id': user.id, 'nickname': user.nickname,
            'displayName': user.displayName or user.nickname, 'bio': user.bio}


def owned_user(session: Session, actor_id: str, user_id: str) -> Player:
    if actor_id != user_id:
        raise DomainError(403, 'FORBIDDEN', 'You can only change your own profile.')
    user = session.get(Player, user_id)
    if user is None:
        raise DomainError(404, 'USER_NOT_FOUND', 'Player not found.')
    return user


def update_profile(session: Session, actor_id: str, user_id: str, payload: ProfilePatch) -> dict:
    user = owned_user(session, actor_id, user_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    user.updatedAt = datetime.now(timezone.utc).replace(tzinfo=None)
    session.flush()
    return private_user(user)


def delete_profile(session: Session, actor_id: str, user_id: str) -> None:
    user = owned_user(session, actor_id, user_id)
    session.delete(user)
    session.flush()

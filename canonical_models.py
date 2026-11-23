"""Account subset extracted from WorldOfCodes; migrations are Alembic-owned here."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Player(Base):
    """User model. Player preserves the source project's Python class name."""
    __tablename__ = 'User'
    __table_args__ = (CheckConstraint('xp >= 0 AND coins >= 0', name='user_rewards_nonnegative'),)
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(24))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    passwordHash: Mapped[str] = mapped_column(String(255))
    normalizedNickname: Mapped[str] = mapped_column(String(24), unique=True)
    nicknameChanges: Mapped[int] = mapped_column(default=0, server_default='0')
    renamedAt: Mapped[datetime | None] = mapped_column(DateTime)
    updatedAt: Mapped[datetime] = mapped_column(DateTime)
    displayName: Mapped[str | None] = mapped_column(String(40))
    bio: Mapped[str] = mapped_column(Text, default='', server_default='')
    avatarUrl: Mapped[str | None] = mapped_column(String(2048))
    xp: Mapped[int] = mapped_column(default=0, server_default='0')
    coins: Mapped[int] = mapped_column(default=0, server_default='0')
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    sessions: Mapped[list['AuthSession']] = relationship(back_populates='user', passive_deletes=True)


class AuthSession(Base):
    __tablename__ = 'AuthSession'
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    userId: Mapped[str] = mapped_column(ForeignKey('User.id', ondelete='CASCADE'), index=True)
    tokenHash: Mapped[str] = mapped_column(String(64), unique=True)
    expiresAt: Mapped[datetime] = mapped_column(DateTime)
    revokedAt: Mapped[datetime | None] = mapped_column(DateTime)
    createdAt: Mapped[datetime] = mapped_column(DateTime)
    user: Mapped[Player] = relationship(back_populates='sessions')

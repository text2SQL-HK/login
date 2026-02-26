import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence, Union

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Session, ChatLog
from schemas import UserCreate, UserUpdate, ChatLogCreate

# ---------------------------------------------------------------------------
# 비밀번호 해싱 설정 (bcrypt)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ===========================================================================
# 사용자 (User) CRUD
# ===========================================================================

async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """회원가입: 새 사용자를 생성합니다."""
    user = User(
        user_id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        username=data.username,
        phone_number=data.phone_number,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """이메일로 사용자를 조회합니다."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """user_id로 사용자를 조회합니다."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """이메일/비밀번호를 검증하고 사용자를 반환합니다. (3회 실패 시 차단)"""
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    
    # 3회 이상 실패 시 차단 여부 확인
    if user.failed_login_attempts >= 3:
        raise HTTPException(status_code=403, detail="로그인 시도 횟수(3회)를 초과하여 계정이 잠겼습니다. 관리자에게 문의하세요.")

    if not verify_password(password, user.password_hash):
        # 실패 횟수 증가
        user.failed_login_attempts += 1
        await db.flush()
        
        remaining = 3 - user.failed_login_attempts
        if remaining > 0:
            raise HTTPException(status_code=401, detail=f"비밀번호가 올바르지 않습니다. (남은 횟수: {remaining}회)")
        else:
            raise HTTPException(status_code=403, detail="로그인 시도 횟수(3회)를 초과하여 계정이 잠겼습니다.")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="비활성화된 계정입니다.")

    # 성공 시 실패 횟수 초기화
    user.failed_login_attempts = 0
    await db.flush()
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    """사용자 정보를 수정합니다."""
    if data.username is not None:
        user.username = data.username
    if data.phone_number is not None:
        user.phone_number = data.phone_number
    await db.flush()
    await db.refresh(user)
    return user


# ===========================================================================
# 세션 (Session) CRUD
# ===========================================================================

async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    expire_hours: int = 24,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """새 세션을 생성하고 토큰을 반환합니다."""
    token = secrets.token_urlsafe(64)
    now = datetime.now(timezone.utc)
    session = Session(
        session_token=token,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now,
        expires_at=now + timedelta(hours=expire_hours),
    )
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, token: str) -> Optional[Session]:
    """유효한 세션을 조회합니다 (만료 검사 포함)."""
    result = await db.execute(
        select(Session).where(
            Session.session_token == token,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def delete_session(db: AsyncSession, token: str) -> None:
    """특정 세션을 삭제합니다 (로그아웃)."""
    await db.execute(delete(Session).where(Session.session_token == token))
    await db.flush()


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """만료된 세션을 일괄 삭제합니다."""
    result = await db.execute(
        delete(Session).where(Session.expires_at <= datetime.now(timezone.utc))
    )
    await db.flush()
    return result.rowcount  # type: ignore


# ===========================================================================
# 채팅 로그 (ChatLog) CRUD
# ===========================================================================

async def create_chat_log(db: AsyncSession, user_id: uuid.UUID, data: ChatLogCreate) -> ChatLog:
    """채팅 메시지를 저장합니다."""
    log = ChatLog(
        user_id=user_id,
        content=data.content,
        message_type=data.message_type,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_chat_logs(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[ChatLog]:
    """채팅 로그를 페이지네이션하여 조회합니다 (최신순)."""
    result = await db.execute(
        select(ChatLog)
        .order_by(ChatLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()

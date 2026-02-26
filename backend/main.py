import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, Base, get_db
from models import User
import crud
import schemas

load_dotenv()

SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))
COOKIE_NAME = "session_token"
LOGIN_UI_PREFIX = "/login"
LOGIN_CHAT_PAGE = f"{LOGIN_UI_PREFIX}/chat"
LOGIN_MYPAGE_PAGE = f"{LOGIN_UI_PREFIX}/mypage"
LOGIN_STATIC_PREFIX = f"{LOGIN_UI_PREFIX}/static"


# ---------------------------------------------------------------------------
# Lifespan: 앱 시작 시 테이블 자동 생성
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Login & Chat System", lifespan=lifespan)


# ---------------------------------------------------------------------------
# 정적 파일 서빙 (프론트엔드)
# ---------------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount(LOGIN_STATIC_PREFIX, StaticFiles(directory=FRONTEND_DIR), name="static")


# ---------------------------------------------------------------------------
# 의존성: 현재 로그인 사용자 가져오기
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """쿠키에서 세션 토큰을 꺼내 DB와 대조하여 사용자를 반환합니다."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    session = await crud.get_session(db, token)
    if session is None:
        raise HTTPException(status_code=401, detail="세션이 만료되었거나 유효하지 않습니다.")

    user = await crud.get_user_by_id(db, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="비활성화된 계정입니다.")

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """로그인 여부를 선택적으로 확인합니다 (비로그인 시 None)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = await crud.get_session(db, token)
    if session is None:
        return None
    return await crud.get_user_by_id(db, session.user_id)


# ===========================================================================
# 페이지 라우팅 (HTML 서빙)
# ===========================================================================
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url=LOGIN_UI_PREFIX, status_code=307)


@app.get(LOGIN_UI_PREFIX, include_in_schema=False)
async def login_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get(LOGIN_CHAT_PAGE, include_in_schema=False)
async def chat_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get(LOGIN_MYPAGE_PAGE, include_in_schema=False)
async def mypage_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "mypage.html"))


# ===========================================================================
# 인증 API (/api/auth)
# ===========================================================================
@app.post("/api/auth/register", response_model=schemas.UserOut)
async def register(data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """회원가입"""
    existing = await crud.get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")
    user = await crud.create_user(db, data)
    return user


@app.post("/api/auth/login", response_model=schemas.UserOut)
async def login(
    data: schemas.UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """로그인: 세션 생성 & 쿠키 발급"""
    user = await crud.authenticate_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    # 클라이언트 정보 수집
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session = await crud.create_session(
        db,
        user_id=user.user_id,
        expire_hours=SESSION_EXPIRE_HOURS,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Set-Cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=session.session_token,
        max_age=SESSION_EXPIRE_HOURS * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return user


@app.post("/api/auth/logout", response_model=schemas.MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """로그아웃: 세션 삭제 & 쿠키 파기"""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await crud.delete_session(db, token)

    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "로그아웃되었습니다."}


@app.get("/api/auth/me", response_model=schemas.UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 로그인된 사용자 정보"""
    return current_user


# ===========================================================================
# 사용자 API (/api/users)
# ===========================================================================
@app.put("/api/users/me", response_model=schemas.UserOut)
async def update_me(
    data: schemas.UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """사용자 정보 수정"""
    updated = await crud.update_user(db, current_user, data)
    return updated


# ===========================================================================
# 채팅 API (/api/login/chat)
# ===========================================================================
@app.post("/api/login/chat", response_model=schemas.ChatLogOut)
async def post_chat(
    data: schemas.ChatLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """채팅 메시지 저장"""
    log = await crud.create_chat_log(db, current_user.user_id, data)
    return schemas.ChatLogOut(
        id=log.id,
        user_id=log.user_id,
        username=current_user.username,
        content=log.content,
        message_type=log.message_type,
        created_at=log.created_at,
    )


@app.get("/api/login/chat", response_model=list[schemas.ChatLogOut])
async def get_chat(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """채팅 로그 조회 (페이지네이션)"""
    logs = await crud.get_chat_logs(db, limit=limit, offset=offset)
    result = []
    for log in logs:
        # 각 로그의 작성자 이름을 포함
        user = await crud.get_user_by_id(db, log.user_id)
        result.append(schemas.ChatLogOut(
            id=log.id,
            user_id=log.user_id,
            username=user.username if user else "Unknown",
            content=log.content,
            message_type=log.message_type,
            created_at=log.created_at,
        ))
    return result

import uuid
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# 사용자 (User) 관련 스키마
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    """회원가입 요청"""
    email: str = Field(..., max_length=255, examples=["user@example.com"])
    password: str = Field(..., min_length=6, max_length=128)
    username: str = Field(..., min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    """로그인 요청"""
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """사용자 정보 수정 요청"""
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)


class UserOut(BaseModel):
    """사용자 정보 응답 (비밀번호 제외)"""
    user_id: uuid.UUID
    email: str
    username: str
    phone_number: Optional[str] = None
    access_level: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 채팅 로그 (ChatLog) 관련 스키마
# ---------------------------------------------------------------------------
class ChatLogCreate(BaseModel):
    """채팅 메시지 저장 요청"""
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="TEXT", max_length=10)


class ChatLogOut(BaseModel):
    """채팅 로그 응답"""
    id: int
    user_id: uuid.UUID
    username: str = ""
    content: str
    message_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 공통 응답 스키마
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    """단순 메시지 응답"""
    message: str

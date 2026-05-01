from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from src.models import AttendanceStatus, Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)
    role: Role
    institution_id: int | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class MonitoringTokenRequest(BaseModel):
    key: str


class BatchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    institution_id: int


class InviteCreateResponse(BaseModel):
    invite_token: str
    expires_at: datetime


class JoinBatchRequest(BaseModel):
    token: str


class SessionCreateRequest(BaseModel):
    batch_id: int
    title: str = Field(min_length=1, max_length=200)
    date: date
    start_time: time
    end_time: time


class AttendanceMarkRequest(BaseModel):
    session_id: int
    status: AttendanceStatus


class AttendanceRow(BaseModel):
    student_id: int
    status: AttendanceStatus
    marked_at: datetime


class SessionAttendanceResponse(BaseModel):
    session_id: int
    records: list[AttendanceRow]


class SummaryCounts(BaseModel):
    present: int
    absent: int
    late: int
    total: int


class MonitoringAttendanceRow(BaseModel):
    session_id: int
    batch_id: int
    student_id: int
    status: AttendanceStatus
    marked_at: datetime


class MonitoringAttendanceResponse(BaseModel):
    items: list[MonitoringAttendanceRow]


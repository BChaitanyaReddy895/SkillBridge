from datetime import datetime, timedelta
from secrets import token_urlsafe
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.db import Base, engine, get_db
from src.deps import get_current_user, get_monitoring_claims, require_roles
from src.models import (
    Attendance,
    AttendanceStatus,
    Batch,
    BatchInvite,
    BatchStudent,
    BatchTrainer,
    Institution,
    Role,
    Session as TrainingSession,
    User,
)
from src.schemas import (
    AttendanceMarkRequest,
    BatchCreateRequest,
    InviteCreateResponse,
    JoinBatchRequest,
    LoginRequest,
    MonitoringAttendanceResponse,
    MonitoringAttendanceRow,
    MonitoringTokenRequest,
    SessionAttendanceResponse,
    SessionCreateRequest,
    SignupRequest,
    SummaryCounts,
    TokenResponse,
)
from src.security import create_access_token, create_monitoring_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.post("/auth/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if payload.institution_id is not None:
        inst = db.get(Institution, payload.institution_id)
        if inst is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    user = User(
        name=payload.name,
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        institution_id=payload.institution_id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email already exists")
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user_id=user.id, role=user.role.value))


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    stmt = select(User).where(User.email == str(payload.email).lower())
    user = db.scalar(stmt)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user_id=user.id, role=user.role.value))


@app.post("/auth/monitoring-token", response_model=TokenResponse)
def monitoring_token(
    body: MonitoringTokenRequest,
    user: User = Depends(require_roles(Role.monitoring_officer)),
) -> TokenResponse:
    if body.key != settings.monitoring_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return TokenResponse(access_token=create_monitoring_token(user_id=user.id, role=user.role.value))


@app.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role.value}


def _utcnow() -> datetime:
    # Keep UTC but naive for cross-database compatibility (SQLite/MySQL/Postgres).
    return datetime.utcnow()


def _summary_counts(db: Session, *, batch_id: int | None = None, institution_id: int | None = None) -> SummaryCounts:
    q = (
        select(Attendance.status, func.count(Attendance.id))
        .join(TrainingSession, TrainingSession.id == Attendance.session_id)
        .join(Batch, Batch.id == TrainingSession.batch_id)
    )
    if batch_id is not None:
        q = q.where(Batch.id == batch_id)
    if institution_id is not None:
        q = q.where(Batch.institution_id == institution_id)

    q = q.group_by(Attendance.status)
    rows = db.execute(q).all()
    counts = {AttendanceStatus.present: 0, AttendanceStatus.absent: 0, AttendanceStatus.late: 0}
    total = 0
    for status_value, cnt in rows:
        counts[status_value] = int(cnt)
        total += int(cnt)

    return SummaryCounts(
        present=counts[AttendanceStatus.present],
        absent=counts[AttendanceStatus.absent],
        late=counts[AttendanceStatus.late],
        total=total,
    )


@app.post("/batches")
def create_batch(
    body: BatchCreateRequest,
    user: User = Depends(require_roles(Role.trainer, Role.institution)),
    db: Session = Depends(get_db),
) -> dict:
    inst = db.get(Institution, body.institution_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    if user.role == Role.trainer:
        if user.institution_id != body.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer institution mismatch")
    if user.role == Role.institution:
        if user.institution_id != body.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Institution mismatch")

    batch = Batch(name=body.name, institution_id=body.institution_id)
    db.add(batch)
    db.flush()

    if user.role == Role.trainer:
        db.add(BatchTrainer(batch_id=batch.id, trainer_id=user.id))

    db.commit()
    db.refresh(batch)
    return {"id": batch.id, "name": batch.name, "institution_id": batch.institution_id}


@app.post("/batches/{batch_id}/invite", response_model=InviteCreateResponse)
def create_invite(
    batch_id: int,
    user: User = Depends(require_roles(Role.trainer)),
    db: Session = Depends(get_db),
) -> InviteCreateResponse:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    is_assigned = db.get(BatchTrainer, {"batch_id": batch_id, "trainer_id": user.id}) is not None
    if not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer not assigned to batch")

    token = token_urlsafe(32)[:64]
    expires_at = _utcnow() + timedelta(hours=48)
    inv = BatchInvite(batch_id=batch_id, token=token, created_by=user.id, expires_at=expires_at, used=False)
    db.add(inv)
    db.commit()
    return InviteCreateResponse(invite_token=token, expires_at=expires_at)


@app.post("/batches/join")
def join_batch(
    body: JoinBatchRequest,
    user: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(BatchInvite).where(BatchInvite.token == body.token)
    inv = db.scalar(stmt)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if inv.used:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invite already used")
    if inv.expires_at <= _utcnow():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invite expired")

    if db.get(BatchStudent, {"batch_id": inv.batch_id, "student_id": user.id}) is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Already joined")

    db.add(BatchStudent(batch_id=inv.batch_id, student_id=user.id))
    inv.used = True
    db.commit()
    return {"batch_id": inv.batch_id, "student_id": user.id}


@app.post("/sessions")
def create_session(
    body: SessionCreateRequest,
    user: User = Depends(require_roles(Role.trainer)),
    db: Session = Depends(get_db),
) -> dict:
    batch = db.get(Batch, body.batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    is_assigned = db.get(BatchTrainer, {"batch_id": body.batch_id, "trainer_id": user.id}) is not None
    if not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer not assigned to batch")

    if body.start_time >= body.end_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must be before end_time")

    sess = TrainingSession(
        batch_id=body.batch_id,
        trainer_id=user.id,
        title=body.title,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return {"id": sess.id, "batch_id": sess.batch_id, "trainer_id": sess.trainer_id, "title": sess.title}


@app.post("/attendance/mark")
def mark_attendance(
    body: AttendanceMarkRequest,
    user: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
) -> dict:
    sess = db.get(TrainingSession, body.session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    is_enrolled = db.get(BatchStudent, {"batch_id": sess.batch_id, "student_id": user.id}) is not None
    if not is_enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student not enrolled in batch")

    now = _utcnow()
    if sess.date != now.date() or not (sess.start_time <= now.time() <= sess.end_time):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session is not active")

    stmt = select(Attendance).where(Attendance.session_id == sess.id, Attendance.student_id == user.id)
    rec = db.scalar(stmt)
    if rec is None:
        rec = Attendance(session_id=sess.id, student_id=user.id, status=body.status)
        db.add(rec)
    else:
        rec.status = body.status
        rec.marked_at = now

    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "session_id": rec.session_id, "student_id": rec.student_id, "status": rec.status.value}


@app.get("/sessions/{session_id}/attendance", response_model=SessionAttendanceResponse)
def session_attendance(
    session_id: int,
    user: User = Depends(require_roles(Role.trainer)),
    db: Session = Depends(get_db),
) -> SessionAttendanceResponse:
    sess = db.get(TrainingSession, session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    is_assigned = db.get(BatchTrainer, {"batch_id": sess.batch_id, "trainer_id": user.id}) is not None
    if not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer not assigned to batch")

    stmt = select(Attendance).where(Attendance.session_id == session_id).order_by(Attendance.marked_at.asc())
    recs = db.scalars(stmt).all()
    return SessionAttendanceResponse(
        session_id=session_id,
        records=[{"student_id": r.student_id, "status": r.status, "marked_at": r.marked_at} for r in recs],
    )


@app.get("/batches/{batch_id}/summary", response_model=SummaryCounts)
def batch_summary(
    batch_id: int,
    user: User = Depends(require_roles(Role.institution)),
    db: Session = Depends(get_db),
) -> SummaryCounts:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    if user.institution_id != batch.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Institution mismatch")
    return _summary_counts(db, batch_id=batch_id)


@app.get("/institutions/{institution_id}/summary", response_model=SummaryCounts)
def institution_summary(
    institution_id: int,
    user: User = Depends(require_roles(Role.programme_manager)),
    db: Session = Depends(get_db),
) -> SummaryCounts:
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    return _summary_counts(db, institution_id=institution_id)


@app.get("/programme/summary", response_model=SummaryCounts)
def programme_summary(
    user: User = Depends(require_roles(Role.programme_manager)),
    db: Session = Depends(get_db),
) -> SummaryCounts:
    return _summary_counts(db)


@app.get("/monitoring/attendance", response_model=MonitoringAttendanceResponse)
def monitoring_attendance(
    _claims: dict = Depends(get_monitoring_claims),
    db: Session = Depends(get_db),
) -> MonitoringAttendanceResponse:
    stmt = (
        select(Attendance, TrainingSession.batch_id)
        .join(TrainingSession, TrainingSession.id == Attendance.session_id)
        .order_by(Attendance.marked_at.desc())
        .limit(100)
    )
    rows = db.execute(stmt).all()
    items: list[MonitoringAttendanceRow] = []
    for att, batch_id in rows:
        items.append(
            MonitoringAttendanceRow(
                session_id=att.session_id,
                batch_id=batch_id,
                student_id=att.student_id,
                status=att.status,
                marked_at=att.marked_at,
            )
        )
    return MonitoringAttendanceResponse(items=items)


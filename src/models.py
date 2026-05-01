import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


class Role(str, enum.Enum):
    student = "student"
    trainer = "trainer"
    institution = "institution"
    programme_manager = "programme_manager"
    monitoring_officer = "monitoring_officer"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="institution")
    batches: Mapped[list["Batch"]] = relationship(back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    institution: Mapped[Institution | None] = relationship(back_populates="users")

    trainer_batches: Mapped[list["BatchTrainer"]] = relationship(back_populates="trainer")
    student_batches: Mapped[list["BatchStudent"]] = relationship(back_populates="student")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    institution: Mapped[Institution] = relationship(back_populates="batches")
    trainers: Mapped[list["BatchTrainer"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    students: Mapped[list["BatchStudent"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    invites: Mapped[list["BatchInvite"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class BatchTrainer(Base):
    __tablename__ = "batch_trainers"
    __table_args__ = (UniqueConstraint("batch_id", "trainer_id", name="uq_batch_trainer"),)

    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    trainer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    batch: Mapped[Batch] = relationship(back_populates="trainers")
    trainer: Mapped[User] = relationship(back_populates="trainer_batches")


class BatchStudent(Base):
    __tablename__ = "batch_students"
    __table_args__ = (UniqueConstraint("batch_id", "student_id", name="uq_batch_student"),)

    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    batch: Mapped[Batch] = relationship(back_populates="students")
    student: Mapped[User] = relationship(back_populates="student_batches")


class BatchInvite(Base):
    __tablename__ = "batch_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    batch: Mapped[Batch] = relationship(back_populates="invites")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False, index=True)
    trainer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    batch: Mapped[Batch] = relationship(back_populates="sessions")
    attendance_records: Mapped[list["Attendance"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_attendance_once"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="attendance_records")


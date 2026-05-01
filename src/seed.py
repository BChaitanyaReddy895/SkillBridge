from datetime import date, time, timedelta

from src.db import Base, SessionLocal, engine
from src.models import (
    Attendance,
    AttendanceStatus,
    Batch,
    BatchStudent,
    BatchTrainer,
    Institution,
    Role,
    Session,
    User,
)
from src.security import hash_password


DEFAULT_PASSWORD = "Pass@123"


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_seed_data() -> None:
    db = SessionLocal()
    try:
        # Institutions (2)
        inst_a = Institution(name="North Skills Institute")
        inst_b = Institution(name="South Skills Academy")
        db.add_all([inst_a, inst_b])
        db.flush()

        # Institution users (2)
        institution_users = [
            User(
                name="Nisha Institution",
                email="institution.north@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.institution,
                institution_id=inst_a.id,
            ),
            User(
                name="Suraj Institution",
                email="institution.south@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.institution,
                institution_id=inst_b.id,
            ),
        ]

        # Programme manager + monitoring officer
        programme_manager = User(
            name="Priya Programme Manager",
            email="pm@skillbridge.test",
            hashed_password=hash_password(DEFAULT_PASSWORD),
            role=Role.programme_manager,
            institution_id=None,
        )
        monitoring_officer = User(
            name="Ravi Monitoring Officer",
            email="monitor@skillbridge.test",
            hashed_password=hash_password(DEFAULT_PASSWORD),
            role=Role.monitoring_officer,
            institution_id=None,
        )

        db.add_all(institution_users + [programme_manager, monitoring_officer])
        db.flush()

        # Trainers (4)
        trainers = [
            User(
                name="Trainer A1",
                email="trainer1@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.trainer,
                institution_id=inst_a.id,
            ),
            User(
                name="Trainer A2",
                email="trainer2@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.trainer,
                institution_id=inst_a.id,
            ),
            User(
                name="Trainer B1",
                email="trainer3@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.trainer,
                institution_id=inst_b.id,
            ),
            User(
                name="Trainer B2",
                email="trainer4@skillbridge.test",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role=Role.trainer,
                institution_id=inst_b.id,
            ),
        ]
        db.add_all(trainers)
        db.flush()

        # Students (15)
        students = []
        for i in range(1, 16):
            institution_id = inst_a.id if i <= 8 else inst_b.id
            students.append(
                User(
                    name=f"Student {i}",
                    email=f"student{i}@skillbridge.test",
                    hashed_password=hash_password(DEFAULT_PASSWORD),
                    role=Role.student,
                    institution_id=institution_id,
                )
            )
        db.add_all(students)
        db.flush()

        # Batches (3)
        batch_1 = Batch(name="Batch Alpha", institution_id=inst_a.id)
        batch_2 = Batch(name="Batch Beta", institution_id=inst_a.id)
        batch_3 = Batch(name="Batch Gamma", institution_id=inst_b.id)
        db.add_all([batch_1, batch_2, batch_3])
        db.flush()

        # Batch-Trainer mapping
        db.add_all(
            [
                BatchTrainer(batch_id=batch_1.id, trainer_id=trainers[0].id),
                BatchTrainer(batch_id=batch_1.id, trainer_id=trainers[1].id),
                BatchTrainer(batch_id=batch_2.id, trainer_id=trainers[1].id),
                BatchTrainer(batch_id=batch_3.id, trainer_id=trainers[2].id),
                BatchTrainer(batch_id=batch_3.id, trainer_id=trainers[3].id),
            ]
        )

        # Batch-Student mapping
        batch_1_students = students[:6]
        batch_2_students = students[6:10]
        batch_3_students = students[10:]
        for student in batch_1_students:
            db.add(BatchStudent(batch_id=batch_1.id, student_id=student.id))
        for student in batch_2_students:
            db.add(BatchStudent(batch_id=batch_2.id, student_id=student.id))
        for student in batch_3_students:
            db.add(BatchStudent(batch_id=batch_3.id, student_id=student.id))

        db.flush()

        # Sessions (8)
        today = date.today()
        sessions = [
            Session(
                batch_id=batch_1.id,
                trainer_id=trainers[0].id,
                title="Python Basics",
                date=today,
                start_time=time(0, 0),
                end_time=time(23, 59),
            ),
            Session(
                batch_id=batch_1.id,
                trainer_id=trainers[1].id,
                title="APIs 101",
                date=today - timedelta(days=1),
                start_time=time(10, 0),
                end_time=time(11, 30),
            ),
            Session(
                batch_id=batch_2.id,
                trainer_id=trainers[1].id,
                title="Databases Intro",
                date=today - timedelta(days=2),
                start_time=time(9, 30),
                end_time=time(11, 0),
            ),
            Session(
                batch_id=batch_2.id,
                trainer_id=trainers[1].id,
                title="SQL Practice",
                date=today - timedelta(days=3),
                start_time=time(14, 0),
                end_time=time(15, 30),
            ),
            Session(
                batch_id=batch_3.id,
                trainer_id=trainers[2].id,
                title="Git Essentials",
                date=today - timedelta(days=1),
                start_time=time(13, 0),
                end_time=time(14, 30),
            ),
            Session(
                batch_id=batch_3.id,
                trainer_id=trainers[3].id,
                title="Debugging Skills",
                date=today - timedelta(days=2),
                start_time=time(10, 30),
                end_time=time(12, 0),
            ),
            Session(
                batch_id=batch_1.id,
                trainer_id=trainers[0].id,
                title="Testing Fundamentals",
                date=today - timedelta(days=4),
                start_time=time(11, 0),
                end_time=time(12, 30),
            ),
            Session(
                batch_id=batch_3.id,
                trainer_id=trainers[2].id,
                title="Deployment Basics",
                date=today - timedelta(days=5),
                start_time=time(15, 0),
                end_time=time(16, 30),
            ),
        ]
        db.add_all(sessions)
        db.flush()

        # Attendance records for meaningful summaries
        def add_attendance_for_group(session_obj: Session, student_group: list[User]) -> None:
            pattern = [
                AttendanceStatus.present,
                AttendanceStatus.present,
                AttendanceStatus.late,
                AttendanceStatus.absent,
            ]
            for idx, stu in enumerate(student_group):
                db.add(
                    Attendance(
                        session_id=session_obj.id,
                        student_id=stu.id,
                        status=pattern[idx % len(pattern)],
                    )
                )

        # Only past/current sessions get attendance
        add_attendance_for_group(sessions[0], batch_1_students)
        add_attendance_for_group(sessions[1], batch_1_students)
        add_attendance_for_group(sessions[2], batch_2_students)
        add_attendance_for_group(sessions[3], batch_2_students)
        add_attendance_for_group(sessions[4], batch_3_students)
        add_attendance_for_group(sessions[5], batch_3_students)
        add_attendance_for_group(sessions[6], batch_1_students)
        add_attendance_for_group(sessions[7], batch_3_students)

        db.commit()
    finally:
        db.close()


def main() -> None:
    reset_db()
    create_seed_data()
    print("Seed complete.")
    print(f"Default password for all seeded users: {DEFAULT_PASSWORD}")
    print("Example roles:")
    print("- student1@skillbridge.test")
    print("- trainer1@skillbridge.test")
    print("- institution.north@skillbridge.test")
    print("- pm@skillbridge.test")
    print("- monitor@skillbridge.test")


if __name__ == "__main__":
    main()


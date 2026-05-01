from datetime import date, time

from src.models import Batch, BatchStudent, BatchTrainer, Institution, Role, Session, User
from src.security import hash_password


def _signup(client, *, name: str, email: str, password: str, role: str, institution_id=None):
    payload = {"name": name, "email": email, "password": password, "role": role}
    if institution_id is not None:
        payload["institution_id"] = institution_id
    return client.post("/auth/signup", json=payload)


def _login(client, *, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_student_signup_and_login_returns_jwt(client):
    signup_res = _signup(
        client,
        name="Student One",
        email="student.one@test.dev",
        password="Pass@123",
        role=Role.student.value,
    )
    assert signup_res.status_code == 200
    assert signup_res.json()["access_token"]

    login_res = _login(client, email="student.one@test.dev", password="Pass@123")
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20


def test_trainer_creates_session_with_required_fields(client, db_session):
    inst = Institution(name="Inst A")
    db_session.add(inst)
    db_session.flush()

    trainer = User(
        name="Trainer One",
        email="trainer.one@test.dev",
        hashed_password=hash_password("Pass@123"),
        role=Role.trainer,
        institution_id=inst.id,
    )
    db_session.add(trainer)
    db_session.flush()

    batch = Batch(name="Batch A", institution_id=inst.id)
    db_session.add(batch)
    db_session.flush()

    db_session.add(BatchTrainer(batch_id=batch.id, trainer_id=trainer.id))
    db_session.commit()

    login_res = _login(client, email="trainer.one@test.dev", password="Pass@123")
    token = login_res.json()["access_token"]

    res = client.post(
        "/sessions",
        json={
            "batch_id": batch.id,
            "title": "FastAPI Intro",
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "FastAPI Intro"


def test_student_successfully_marks_own_attendance(client, db_session):
    inst = Institution(name="Inst B")
    db_session.add(inst)
    db_session.flush()

    trainer = User(
        name="Trainer Two",
        email="trainer.two@test.dev",
        hashed_password=hash_password("Pass@123"),
        role=Role.trainer,
        institution_id=inst.id,
    )
    student = User(
        name="Student Two",
        email="student.two@test.dev",
        hashed_password=hash_password("Pass@123"),
        role=Role.student,
        institution_id=inst.id,
    )
    db_session.add_all([trainer, student])
    db_session.flush()

    batch = Batch(name="Batch B", institution_id=inst.id)
    db_session.add(batch)
    db_session.flush()

    db_session.add(BatchTrainer(batch_id=batch.id, trainer_id=trainer.id))
    db_session.add(BatchStudent(batch_id=batch.id, student_id=student.id))
    db_session.flush()

    sess = Session(
        batch_id=batch.id,
        trainer_id=trainer.id,
        title="Active Session",
        date=date.today(),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    db_session.add(sess)
    db_session.commit()

    login_res = _login(client, email="student.two@test.dev", password="Pass@123")
    token = login_res.json()["access_token"]

    res = client.post(
        "/attendance/mark",
        json={"session_id": sess.id, "status": "present"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "present"


def test_post_monitoring_attendance_returns_405(client):
    res = client.post("/monitoring/attendance")
    assert res.status_code == 405


def test_protected_endpoint_without_token_returns_401(client):
    res = client.get("/programme/summary")
    assert res.status_code == 401


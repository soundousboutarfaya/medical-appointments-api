from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from main import app
from database import Base, get_db
import models
from auth import hash_password


# ===== SETUP: in-memory test database =====

# In-memory SQLite DB (discarded when tests finish)
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Required for in-memory SQLite
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


# Override get_db: tests use the test DB instead of the real one
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Default client: pre-authenticated as admin (see fixture below)
client = TestClient(app)
# Anonymous client: to test the 401 / 403 cases
client_anonymous = TestClient(app)
# Doctor client: to test admin-only restrictions
client_doctor = TestClient(app)


# ===== FIXTURE: fresh DB + test admin and doctor for each test =====

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)

    # Create a test admin and a test doctor
    db = TestingSessionLocal()
    db.add(models.User(
        email="admin@test.com",
        hashed_password=hash_password("admin1234"),
        role=models.UserRole.admin,
    ))
    db.add(models.User(
        email="doctor@test.com",
        hashed_password=hash_password("doctor1234"),
        role=models.UserRole.doctor,
    ))
    db.commit()
    db.close()

    # Authenticate client (admin) and client_doctor
    token_admin = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "admin1234"},
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token_admin}"

    token_doctor = client_doctor.post(
        "/auth/login",
        data={"username": "doctor@test.com", "password": "doctor1234"},
    ).json()["access_token"]
    client_doctor.headers["Authorization"] = f"Bearer {token_doctor}"

    yield

    client.headers.pop("Authorization", None)
    client_doctor.headers.pop("Authorization", None)
    Base.metadata.drop_all(bind=engine_test)


# ===== HELPERS: create entities for tests =====

def create_test_patient(last_name="Tremblay", first_name="Marie", age=45, health_card="TREM45120115"):
    """Helper to create a patient in tests."""
    return client.post(
        "/patients",
        json={"last_name": last_name, "first_name": first_name, "age": age, "health_card_number": health_card},
    )


def create_test_doctor(last_name="Lavoie", first_name="Pierre", specialty="cardiology", license_number="12345"):
    """Helper to create a doctor in tests."""
    return client.post(
        "/doctors",
        json={"last_name": last_name, "first_name": first_name, "specialty": specialty, "license_number": license_number},
    )


def create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00",
                            reason="Annual checkup", status="scheduled", mode="in_person"):
    """Helper to create an appointment in tests."""
    return client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": scheduled_at,
            "reason": reason,
            "status": status,
            "mode": mode,
        },
    )


# ===== TESTS =====

def test_read_root_serves_frontend():
    """The root serves the frontend application (HTML)."""
    response = client_anonymous.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_health_check():
    """Health endpoint for monitoring."""
    response = client_anonymous.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, my API is running!"}


def test_get_all_patients_empty():
    """At first, the patient list is empty."""
    response = client.get("/patients")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_patients_with_data():
    """After creation, the patients are returned."""
    create_test_patient()
    response = client.get("/patients")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_patient_valid():
    """Create a patient with valid data."""
    response = create_test_patient()
    assert response.status_code == 200
    assert response.json()["last_name"] == "Tremblay"
    assert "id" in response.json()


def test_create_patient_invalid_health_card():
    """A health card number with a bad format is rejected by Pydantic."""
    response = client.post(
        "/patients",
        json={"last_name": "Test", "first_name": "T", "age": 30, "health_card_number": "abc123"},
    )
    assert response.status_code == 422


def test_create_patient_without_health_card():
    """A patient without a health card number is rejected (required field)."""
    response = client.post(
        "/patients",
        json={"last_name": "Test", "first_name": "T", "age": 30},
    )
    assert response.status_code == 422


def test_create_patient_duplicate_health_card():
    """You cannot create two patients with the same health card number."""
    create_test_patient()
    response = create_test_patient()  # Same default health card number
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_patient_by_id_existing():
    """Retrieve an existing patient."""
    create_response = create_test_patient()
    patient_id = create_response.json()["id"]

    response = client.get(f"/patients/{patient_id}")
    assert response.status_code == 200
    assert response.json()["last_name"] == "Tremblay"


def test_get_patient_by_id_missing():
    """A non-existent patient returns 404."""
    response = client.get("/patients/9999")
    assert response.status_code == 404


def test_update_patient_existing():
    """Update an existing patient."""
    create_response = create_test_patient()
    patient_id = create_response.json()["id"]

    response = client.put(
        f"/patients/{patient_id}",
        json={"last_name": "Tremblay", "first_name": "Marie", "age": 46, "health_card_number": "TREM45120115"},
    )
    assert response.status_code == 200
    assert response.json()["age"] == 46


def test_update_patient_missing():
    """Updating a patient that does not exist returns 404."""
    response = client.put(
        "/patients/9999",
        json={"last_name": "Test", "first_name": "T", "age": 30, "health_card_number": "TEST12345678"},
    )
    assert response.status_code == 404


def test_update_patient_health_card_taken_by_other():
    """You cannot take another patient's health card number."""
    create_test_patient(health_card="TREM45120115")
    response_p2 = create_test_patient(last_name="Gagnon", first_name="Jean", age=67, health_card="GAGN23080742")
    p2_id = response_p2.json()["id"]

    # Try to set p1's health card number on p2
    response = client.put(
        f"/patients/{p2_id}",
        json={"last_name": "Gagnon", "first_name": "Jean", "age": 67, "health_card_number": "TREM45120115"},
    )
    assert response.status_code == 409


def test_delete_patient_existing():
    """Delete an existing patient."""
    create_response = create_test_patient()
    patient_id = create_response.json()["id"]

    response = client.delete(f"/patients/{patient_id}")
    assert response.status_code == 200
    assert "message" in response.json()

    # Verify it is really gone
    get_response = client.get(f"/patients/{patient_id}")
    assert get_response.status_code == 404


def test_delete_patient_missing():
    """Deleting a patient that does not exist returns 404."""
    response = client.delete("/patients/9999")
    assert response.status_code == 404


# ===== TESTS: DOCTORS =====

def test_get_all_doctors_empty():
    response = client.get("/doctors")
    assert response.status_code == 200
    assert response.json() == []


def test_create_doctor_valid():
    response = create_test_doctor()
    assert response.status_code == 200
    assert response.json()["last_name"] == "Lavoie"
    assert response.json()["specialty"] == "cardiology"
    assert "id" in response.json()


def test_create_doctor_invalid_license():
    """License number that does not match the format (5 digits)."""
    response = client.post(
        "/doctors",
        json={"last_name": "X", "first_name": "Y", "specialty": "z", "license_number": "abc"},
    )
    assert response.status_code == 422


def test_create_doctor_duplicate_license():
    create_test_doctor()
    response = create_test_doctor()
    assert response.status_code == 409


def test_get_doctor_by_id_existing():
    create_response = create_test_doctor()
    doctor_id = create_response.json()["id"]
    response = client.get(f"/doctors/{doctor_id}")
    assert response.status_code == 200
    assert response.json()["last_name"] == "Lavoie"


def test_get_doctor_by_id_missing():
    response = client.get("/doctors/9999")
    assert response.status_code == 404


def test_update_doctor_existing():
    create_response = create_test_doctor()
    doctor_id = create_response.json()["id"]
    response = client.put(
        f"/doctors/{doctor_id}",
        json={"last_name": "Lavoie", "first_name": "Pierre", "specialty": "neurology", "license_number": "12345"},
    )
    assert response.status_code == 200
    assert response.json()["specialty"] == "neurology"


def test_update_doctor_missing():
    response = client.put(
        "/doctors/9999",
        json={"last_name": "X", "first_name": "Y", "specialty": "z", "license_number": "12345"},
    )
    assert response.status_code == 404


def test_delete_doctor_existing():
    create_response = create_test_doctor()
    doctor_id = create_response.json()["id"]
    response = client.delete(f"/doctors/{doctor_id}")
    assert response.status_code == 200
    assert client.get(f"/doctors/{doctor_id}").status_code == 404


def test_delete_doctor_missing():
    response = client.delete("/doctors/9999")
    assert response.status_code == 404


# ===== TESTS: APPOINTMENTS =====

def test_create_appointment_valid():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id)
    assert response.status_code == 200
    assert response.json()["patient_id"] == patient_id
    assert response.json()["doctor_id"] == doctor_id
    assert response.json()["mode"] == "in_person"
    assert response.json()["status"] == "scheduled"


def test_create_appointment_virtual():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id, mode="virtual")
    assert response.status_code == 200
    assert response.json()["mode"] == "virtual"


def test_create_appointment_invalid_mode():
    """A mode other than in_person / virtual is rejected."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id, mode="hologram")
    assert response.status_code == 422


def test_create_appointment_missing_patient():
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(9999, doctor_id)
    assert response.status_code == 404
    assert "Patient" in response.json()["detail"]


def test_create_appointment_missing_doctor():
    patient_id = create_test_patient().json()["id"]
    response = create_test_appointment(patient_id, 9999)
    assert response.status_code == 404
    assert "Doctor" in response.json()["detail"]


def test_get_all_appointments():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    create_test_appointment(patient_id, doctor_id)
    response = client.get("/appointments")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_appointment_by_id_missing():
    response = client.get("/appointments/9999")
    assert response.status_code == 404


def test_update_appointment_status():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id).json()["id"]

    response = client.put(
        f"/appointments/{appt_id}",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "reason": "Annual checkup",
            "status": "confirmed",
            "mode": "in_person",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_delete_appointment_existing():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id).json()["id"]
    response = client.delete(f"/appointments/{appt_id}")
    assert response.status_code == 200
    assert client.get(f"/appointments/{appt_id}").status_code == 404


def test_delete_patient_deletes_their_appointments():
    """Cascade: deleting a patient also deletes their appointments."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id).json()["id"]

    client.delete(f"/patients/{patient_id}")
    assert client.get(f"/appointments/{appt_id}").status_code == 404


# ===== TESTS: STEP 3 — BUSINESS LOGIC =====
# Note: 2026-05-15 is a Friday. 2026-05-16 = Saturday, 2026-05-18 = Monday.

# --- Opening hours ---

def test_appointment_before_opening_rejected():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T07:00:00")
    assert response.status_code == 400
    assert "8:00" in response.json()["detail"]


def test_appointment_after_closing_rejected():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T18:30:00")
    assert response.status_code == 400


def test_appointment_overflowing_past_18_rejected():
    """A 60-min appointment starting at 17:30 ends at 18:30 -> must be rejected."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T17:30:00",
            "duration_minutes": 60,
            "mode": "in_person",
        },
    )
    assert response.status_code == 400


def test_appointment_weekend_rejected():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-16T10:00:00")
    assert response.status_code == 400
    assert "weekend" in response.json()["detail"]


# --- Double-booking ---

def test_double_booking_same_time_rejected():
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")
    assert response.status_code == 409


def test_double_booking_overlap_rejected():
    """A 30-min appointment at 10:00 -> another appointment at 10:15 overlaps."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:15:00")
    assert response.status_code == 409


def test_consecutive_appointments_accepted():
    """Appointment at 10:00 (30 min) then at 10:30 -> no overlap."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:30:00")
    assert response.status_code == 200


def test_double_booking_different_doctors_accepted():
    """Two doctors can have an appointment at the same time."""
    patient_id = create_test_patient().json()["id"]
    doctor1_id = create_test_doctor().json()["id"]
    doctor2_id = create_test_doctor(last_name="Roy", first_name="Jean", license_number="67890").json()["id"]
    create_test_appointment(patient_id, doctor1_id, scheduled_at="2026-05-15T10:00:00")
    response = create_test_appointment(patient_id, doctor2_id, scheduled_at="2026-05-15T10:00:00")
    assert response.status_code == 200


def test_cancelled_appointment_frees_the_slot(monkeypatch):
    """An appointment with status=cancelled no longer blocks the slot."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00").json()["id"]

    # Move "now" several days before the appointment so the 24h rule is satisfied
    monkeypatch.setattr(main, "_now", lambda: datetime(2026, 5, 13, 9, 0))

    cancellation = client.put(
        f"/appointments/{appt_id}",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "status": "cancelled",
            "mode": "in_person",
        },
    )
    assert cancellation.status_code == 200

    # Another appointment can now take the slot
    response = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")
    assert response.status_code == 200


# --- Available slots ---

def test_slots_empty_day():
    """A doctor with no appointments -> all slots from 8:00 to 17:30 available (20 slots of 30 min)."""
    doctor_id = create_test_doctor().json()["id"]
    response = client.get(f"/doctors/{doctor_id}/slots?day=2026-05-15")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-05-15"
    assert len(data["available_slots"]) == 20
    assert data["available_slots"][0] == "08:00"
    assert data["available_slots"][-1] == "17:30"


def test_slots_with_booked_appointment():
    """An appointment at 10:00 occupies the 10:00 slot."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00")

    response = client.get(f"/doctors/{doctor_id}/slots?day=2026-05-15")
    assert response.status_code == 200
    slots = response.json()["available_slots"]
    assert "10:00" not in slots
    assert "09:30" in slots
    assert "10:30" in slots


def test_slots_long_appointment_blocks_several_slots():
    """A 60-min appointment at 10:00 blocks the 10:00 and 10:30 slots."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "duration_minutes": 60,
            "mode": "in_person",
        },
    )
    slots = client.get(f"/doctors/{doctor_id}/slots?day=2026-05-15").json()["available_slots"]
    assert "10:00" not in slots
    assert "10:30" not in slots
    assert "11:00" in slots


def test_slots_weekend_empty():
    doctor_id = create_test_doctor().json()["id"]
    response = client.get(f"/doctors/{doctor_id}/slots?day=2026-05-16")
    assert response.status_code == 200
    assert response.json()["available_slots"] == []


def test_slots_missing_doctor():
    response = client.get("/doctors/9999/slots?day=2026-05-15")
    assert response.status_code == 404


# --- 24h cancellation rule ---

def test_cancellation_more_than_24h_accepted(monkeypatch):
    """Appointment more than 24h away -> cancellation allowed."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00").json()["id"]

    monkeypatch.setattr(main, "_now", lambda: datetime(2026, 5, 13, 9, 0))

    response = client.put(
        f"/appointments/{appt_id}",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "status": "cancelled",
            "mode": "in_person",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancellation_less_than_24h_rejected(monkeypatch):
    """Appointment less than 24h away -> cancellation rejected (400)."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00").json()["id"]

    # Simulate "now = May 14, 2026 at 15:00" -> appointment is in 19h, so less than 24h
    monkeypatch.setattr(main, "_now", lambda: datetime(2026, 5, 14, 15, 0))

    response = client.put(
        f"/appointments/{appt_id}",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "status": "cancelled",
            "mode": "in_person",
        },
    )
    assert response.status_code == 400
    assert "24h" in response.json()["detail"]


def test_change_other_than_cancellation_not_subject_to_24h(monkeypatch):
    """Confirming an appointment less than 24h away must still be possible."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    appt_id = create_test_appointment(patient_id, doctor_id, scheduled_at="2026-05-15T10:00:00").json()["id"]

    monkeypatch.setattr(main, "_now", lambda: datetime(2026, 5, 14, 15, 0))

    response = client.put(
        f"/appointments/{appt_id}",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "status": "confirmed",
            "mode": "in_person",
        },
    )
    assert response.status_code == 200


# ===== TESTS: STEP 4 — AUTHENTICATION AND ROLES =====

# --- Registration ---

def test_register_valid():
    response = client_anonymous.post(
        "/auth/register",
        json={"email": "new@test.com", "password": "secret123", "role": "doctor"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@test.com"
    assert response.json()["role"] == "doctor"
    assert "id" in response.json()
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


def test_register_duplicate_email():
    client_anonymous.post(
        "/auth/register",
        json={"email": "dup@test.com", "password": "secret123", "role": "doctor"},
    )
    response = client_anonymous.post(
        "/auth/register",
        json={"email": "dup@test.com", "password": "other456", "role": "doctor"},
    )
    assert response.status_code == 409


def test_register_invalid_email():
    response = client_anonymous.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "secret123", "role": "doctor"},
    )
    assert response.status_code == 422


def test_register_password_too_short():
    response = client_anonymous.post(
        "/auth/register",
        json={"email": "short@test.com", "password": "abc", "role": "doctor"},
    )
    assert response.status_code == 422


# --- Login ---

def test_login_valid_credentials():
    response = client_anonymous.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "admin1234"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password():
    response = client_anonymous.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_unknown_email():
    response = client_anonymous.post(
        "/auth/login",
        data={"username": "unknown@test.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_returns_current_profile():
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"
    assert response.json()["role"] == "admin"


# --- Endpoint protection ---

def test_protected_endpoint_without_token_returns_401():
    response = client_anonymous.get("/patients")
    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token_returns_401():
    headers = {"Authorization": "Bearer fake-token"}
    response = client_anonymous.get("/patients", headers=headers)
    assert response.status_code == 401


def test_root_stays_public():
    response = client_anonymous.get("/")
    assert response.status_code == 200


# --- Role control ---

def test_doctor_can_read_patients():
    response = client_doctor.get("/patients")
    assert response.status_code == 200


def test_doctor_cannot_create_patient():
    response = client_doctor.post(
        "/patients",
        json={"last_name": "X", "first_name": "Y", "age": 30, "health_card_number": "TEST12345678"},
    )
    assert response.status_code == 403


def test_doctor_cannot_create_doctor():
    response = client_doctor.post(
        "/doctors",
        json={"last_name": "X", "first_name": "Y", "specialty": "z", "license_number": "99999"},
    )
    assert response.status_code == 403


def test_doctor_can_create_appointment():
    """Medical staff (admin or doctor) can create an appointment."""
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]
    response = client_doctor.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T10:00:00",
            "mode": "in_person",
        },
    )
    assert response.status_code == 200


def test_admin_can_do_everything():
    """Sanity check: the admin can create patient, doctor and appointment."""
    p = create_test_patient()
    d = create_test_doctor()
    a = create_test_appointment(p.json()["id"], d.json()["id"])
    assert p.status_code == 200
    assert d.status_code == 200
    assert a.status_code == 200


# --- End-to-end integration test ---

def test_e2e_register_login_create_appointment():
    """Full scenario: a new doctor registers, logs in, creates an appointment."""
    # 1. Registration
    registration = client_anonymous.post(
        "/auth/register",
        json={"email": "new.doctor@test.com", "password": "mypass123", "role": "doctor"},
    )
    assert registration.status_code == 200

    # 2. Login
    login = client_anonymous.post(
        "/auth/login",
        data={"username": "new.doctor@test.com", "password": "mypass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Prerequisites created by the admin (patient + doctor record)
    patient_id = create_test_patient().json()["id"]
    doctor_id = create_test_doctor().json()["id"]

    # 4. The newly registered doctor creates an appointment
    creation = client_anonymous.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": "2026-05-15T14:00:00",
            "mode": "virtual",
        },
    )
    assert creation.status_code == 200
    assert creation.json()["mode"] == "virtual"

    # 5. Correct profile
    me = client_anonymous.get("/auth/me", headers=headers)
    assert me.json()["email"] == "new.doctor@test.com"
    assert me.json()["role"] == "doctor"

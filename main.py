from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from database import engine, Base, get_db
import models
from models import ConsultationMode, UserRole, AppointmentStatus
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_staff,
    verify_password,
)

# Clinic opening-hours constants
OPENING_HOUR = 8   # 8:00 AM
CLOSING_HOUR = 18  # 6:00 PM
SLOT_DURATION_MINUTES = 30
CANCELLATION_NOTICE_HOURS = 24


def _now() -> datetime:
    """Wrapped to make mocking easy in tests."""
    return datetime.now()

# Create all tables at startup (if they don't already exist)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Frontend static files (HTML, JS, CSS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===== PYDANTIC MODELS: PATIENTS =====

class PatientCreate(BaseModel):
    last_name: str
    first_name: str
    age: int
    health_card_number: str = Field(
        ...,
        pattern=r"^[A-Z]{4}\d{8}$",
        description="Health card number (RAMQ): 4 uppercase letters followed by 8 digits",
    )


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_name: str
    first_name: str
    age: int
    health_card_number: str


# ===== PYDANTIC MODELS: DOCTORS =====

class DoctorCreate(BaseModel):
    last_name: str
    first_name: str
    specialty: str
    license_number: str = Field(
        ...,
        pattern=r"^\d{5}$",
        description="License number: 5 digits (Collège des médecins du Québec)",
    )


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_name: str
    first_name: str
    specialty: str
    license_number: str


# ===== PYDANTIC MODELS: APPOINTMENTS =====

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, gt=0, le=240)
    reason: str | None = None
    status: AppointmentStatus = AppointmentStatus.scheduled
    mode: ConsultationMode


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int
    reason: str | None
    status: AppointmentStatus
    mode: ConsultationMode


# ===== PYDANTIC MODELS: AUTHENTICATION =====

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.doctor


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===== ENDPOINTS: AUTHENTICATION =====

@app.post("/auth/register", response_model=UserResponse)
def register(new_user: UserCreate, db: Session = Depends(get_db)):
    """Account creation. In production this should be restricted to admins."""
    existing = db.query(models.User).filter(models.User.email == new_user.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = models.User(
        email=new_user.email,
        hashed_password=hash_password(new_user.password),
        role=new_user.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(sub=user.email))


@app.get("/auth/me", response_model=UserResponse)
def read_my_profile(current: models.User = Depends(get_current_user)):
    return current


# ===== ENDPOINTS: ROOT =====

@app.get("/", response_class=FileResponse)
def read_root():
    """Serves the frontend application (single-page app)."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health_check():
    return {"message": "Hello, my API is running!"}


# ===== ENDPOINTS: PATIENTS =====

@app.get("/patients", response_model=list[PatientResponse])
def get_all_patients(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.Patient).all()


@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.post("/patients", response_model=PatientResponse)
def create_patient(
    new_patient: PatientCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    existing = db.query(models.Patient).filter(
        models.Patient.health_card_number == new_patient.health_card_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A patient with this health card number already exists"
        )

    db_patient = models.Patient(
        last_name=new_patient.last_name,
        first_name=new_patient.first_name,
        age=new_patient.age,
        health_card_number=new_patient.health_card_number,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    updated_patient: PatientCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    other = db.query(models.Patient).filter(
        models.Patient.health_card_number == updated_patient.health_card_number,
        models.Patient.id != patient_id
    ).first()
    if other:
        raise HTTPException(
            status_code=409,
            detail="This health card number is already used by another patient"
        )

    patient.last_name = updated_patient.last_name
    patient.first_name = updated_patient.first_name
    patient.age = updated_patient.age
    patient.health_card_number = updated_patient.health_card_number

    db.commit()
    db.refresh(patient)
    return patient


@app.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}


# ===== ENDPOINTS: DOCTORS =====

@app.get("/doctors", response_model=list[DoctorResponse])
def get_all_doctors(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.Doctor).all()


@app.get("/doctors/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(
    doctor_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@app.post("/doctors", response_model=DoctorResponse)
def create_doctor(
    new_doctor: DoctorCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    existing = db.query(models.Doctor).filter(
        models.Doctor.license_number == new_doctor.license_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A doctor with this license number already exists"
        )

    db_doctor = models.Doctor(**new_doctor.model_dump())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


@app.put("/doctors/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    updated_doctor: DoctorCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    other = db.query(models.Doctor).filter(
        models.Doctor.license_number == updated_doctor.license_number,
        models.Doctor.id != doctor_id
    ).first()
    if other:
        raise HTTPException(
            status_code=409,
            detail="This license number is already used by another doctor"
        )

    doctor.last_name = updated_doctor.last_name
    doctor.first_name = updated_doctor.first_name
    doctor.specialty = updated_doctor.specialty
    doctor.license_number = updated_doctor.license_number

    db.commit()
    db.refresh(doctor)
    return doctor


@app.delete("/doctors/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    db.delete(doctor)
    db.commit()
    return {"message": "Doctor deleted successfully"}


# ===== ENDPOINTS: APPOINTMENTS =====

def _verify_patient_and_doctor(appt: AppointmentCreate, db: Session):
    """Checks that the referenced patient and doctor exist."""
    if not db.query(models.Patient).filter(models.Patient.id == appt.patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.query(models.Doctor).filter(models.Doctor.id == appt.doctor_id).first():
        raise HTTPException(status_code=404, detail="Doctor not found")


def _verify_opening_hours(appt: AppointmentCreate):
    """Appointments only Monday to Friday, between 8:00 and 18:00 (end included)."""
    start = appt.scheduled_at
    end = start + timedelta(minutes=appt.duration_minutes)

    if start.weekday() >= 5:
        raise HTTPException(
            status_code=400,
            detail="The clinic is closed on weekends (Monday to Friday only)"
        )

    day_start = start.replace(hour=OPENING_HOUR, minute=0, second=0, microsecond=0)
    day_end = start.replace(hour=CLOSING_HOUR, minute=0, second=0, microsecond=0)

    if start < day_start or end > day_end:
        raise HTTPException(
            status_code=400,
            detail=f"Appointments must be between {OPENING_HOUR}:00 and {CLOSING_HOUR}:00"
        )


def _verify_time_conflict(appt: AppointmentCreate, db: Session, exclude_id: int | None = None):
    """Prevents double-booking: no overlap with another non-cancelled appointment for the same doctor."""
    new_start = appt.scheduled_at
    new_end = new_start + timedelta(minutes=appt.duration_minutes)

    query = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == appt.doctor_id,
        models.Appointment.status != AppointmentStatus.cancelled,
    )
    if exclude_id is not None:
        query = query.filter(models.Appointment.id != exclude_id)

    for existing in query.all():
        existing_start = existing.scheduled_at
        existing_end = existing_start + timedelta(minutes=existing.duration_minutes)
        if new_start < existing_end and existing_start < new_end:
            raise HTTPException(
                status_code=409,
                detail="This doctor already has an appointment at that time"
            )


@app.get("/appointments", response_model=list[AppointmentResponse])
def get_all_appointments(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.Appointment).all()


@app.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_by_id(
    appointment_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@app.post("/appointments", response_model=AppointmentResponse)
def create_appointment(
    new_appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_staff),
):
    _verify_patient_and_doctor(new_appointment, db)
    _verify_opening_hours(new_appointment)
    _verify_time_conflict(new_appointment, db)

    db_appt = models.Appointment(**new_appointment.model_dump())
    db.add(db_appt)
    db.commit()
    db.refresh(db_appt)
    return db_appt


@app.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    updated_appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_staff),
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    _verify_patient_and_doctor(updated_appointment, db)
    _verify_opening_hours(updated_appointment)
    _verify_time_conflict(updated_appointment, db, exclude_id=appointment_id)

    # Cancellation rule: at least 24h before the appointment
    is_cancelling = (
        updated_appointment.status == AppointmentStatus.cancelled
        and appt.status != AppointmentStatus.cancelled
    )
    if is_cancelling and appt.scheduled_at - _now() < timedelta(hours=CANCELLATION_NOTICE_HOURS):
        raise HTTPException(
            status_code=400,
            detail=f"Cancellation not allowed: at least {CANCELLATION_NOTICE_HOURS}h notice required"
        )

    appt.patient_id = updated_appointment.patient_id
    appt.doctor_id = updated_appointment.doctor_id
    appt.scheduled_at = updated_appointment.scheduled_at
    appt.duration_minutes = updated_appointment.duration_minutes
    appt.reason = updated_appointment.reason
    appt.status = updated_appointment.status
    appt.mode = updated_appointment.mode

    db.commit()
    db.refresh(appt)
    return appt


@app.delete("/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_staff),
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    db.delete(appt)
    db.commit()
    return {"message": "Appointment deleted successfully"}


# ===== ENDPOINT: AVAILABLE SLOTS LOOKUP =====

@app.get("/doctors/{doctor_id}/slots")
def get_available_slots(
    doctor_id: int,
    day: date,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Returns the free slots (no overlap with existing appointments) for a doctor on a given day."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if day.weekday() >= 5:
        return {"date": day.isoformat(), "available_slots": []}

    # Generate SLOT_DURATION_MINUTES-long slots from OPENING_HOUR to CLOSING_HOUR
    slots = []
    current_minutes = OPENING_HOUR * 60
    end_minutes = CLOSING_HOUR * 60
    while current_minutes + SLOT_DURATION_MINUTES <= end_minutes:
        h, m = divmod(current_minutes, 60)
        slots.append(datetime.combine(day, time(h, m)))
        current_minutes += SLOT_DURATION_MINUTES

    # Fetch the doctor's non-cancelled appointments for this day
    day_start = datetime.combine(day, time(0, 0))
    day_end = day_start + timedelta(days=1)
    day_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.status != AppointmentStatus.cancelled,
        models.Appointment.scheduled_at >= day_start,
        models.Appointment.scheduled_at < day_end,
    ).all()

    free_slots = []
    for slot_start in slots:
        slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
        overlaps = any(
            slot_start < a.scheduled_at + timedelta(minutes=a.duration_minutes)
            and a.scheduled_at < slot_end
            for a in day_appointments
        )
        if not overlaps:
            free_slots.append(slot_start.strftime("%H:%M"))

    return {"date": day.isoformat(), "available_slots": free_slots}

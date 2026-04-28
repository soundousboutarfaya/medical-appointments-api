from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from database import engine, Base, get_db
import models
from models import ModeConsultation, StatutRendezVous

# Crée toutes les tables au démarrage (si elles n'existent pas déjà)
Base.metadata.create_all(bind=engine)

app = FastAPI()


# ===== MODÈLES PYDANTIC : PATIENTS =====

class PatientCreate(BaseModel):
    nom: str
    prenom: str
    age: int
    numero_ramq: str = Field(
        ...,
        pattern=r"^[A-Z]{4}\d{8}$",
        description="Numéro RAMQ : 4 lettres majuscules suivies de 8 chiffres",
    )


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    age: int
    numero_ramq: str


# ===== MODÈLES PYDANTIC : MÉDECINS =====

class MedecinCreate(BaseModel):
    nom: str
    prenom: str
    specialite: str
    numero_permis: str = Field(
        ...,
        pattern=r"^\d{5}$",
        description="Numéro de permis : 5 chiffres (Collège des médecins du Québec)",
    )


class MedecinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    specialite: str
    numero_permis: str


# ===== MODÈLES PYDANTIC : RENDEZ-VOUS =====

class RendezVousCreate(BaseModel):
    patient_id: int
    medecin_id: int
    date_heure: datetime
    motif: str | None = None
    statut: StatutRendezVous = StatutRendezVous.prevu
    mode: ModeConsultation


class RendezVousResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    medecin_id: int
    date_heure: datetime
    motif: str | None
    statut: StatutRendezVous
    mode: ModeConsultation


# ===== ENDPOINTS : RACINE =====

@app.get("/")
def read_root():
    return {"message": "Bonjour, mon API fonctionne !"}


# ===== ENDPOINTS : PATIENTS =====

@app.get("/patients", response_model=list[PatientResponse])
def get_all_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).all()


@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return patient


@app.post("/patients", response_model=PatientResponse)
def create_patient(nouveau_patient: PatientCreate, db: Session = Depends(get_db)):
    existant = db.query(models.Patient).filter(
        models.Patient.numero_ramq == nouveau_patient.numero_ramq
    ).first()
    if existant:
        raise HTTPException(
            status_code=409,
            detail="Un patient avec ce numéro RAMQ existe déjà"
        )

    db_patient = models.Patient(
        nom=nouveau_patient.nom,
        prenom=nouveau_patient.prenom,
        age=nouveau_patient.age,
        numero_ramq=nouveau_patient.numero_ramq,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    patient_modifie: PatientCreate,
    db: Session = Depends(get_db)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    autre = db.query(models.Patient).filter(
        models.Patient.numero_ramq == patient_modifie.numero_ramq,
        models.Patient.id != patient_id
    ).first()
    if autre:
        raise HTTPException(
            status_code=409,
            detail="Ce numéro RAMQ est déjà utilisé par un autre patient"
        )

    patient.nom = patient_modifie.nom
    patient.prenom = patient_modifie.prenom
    patient.age = patient_modifie.age
    patient.numero_ramq = patient_modifie.numero_ramq

    db.commit()
    db.refresh(patient)
    return patient


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    db.delete(patient)
    db.commit()
    return {"message": "Patient supprimé avec succès"}


# ===== ENDPOINTS : MÉDECINS =====

@app.get("/medecins", response_model=list[MedecinResponse])
def get_all_medecins(db: Session = Depends(get_db)):
    return db.query(models.Medecin).all()


@app.get("/medecins/{medecin_id}", response_model=MedecinResponse)
def get_medecin_by_id(medecin_id: int, db: Session = Depends(get_db)):
    medecin = db.query(models.Medecin).filter(models.Medecin.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin introuvable")
    return medecin


@app.post("/medecins", response_model=MedecinResponse)
def create_medecin(nouveau_medecin: MedecinCreate, db: Session = Depends(get_db)):
    existant = db.query(models.Medecin).filter(
        models.Medecin.numero_permis == nouveau_medecin.numero_permis
    ).first()
    if existant:
        raise HTTPException(
            status_code=409,
            detail="Un médecin avec ce numéro de permis existe déjà"
        )

    db_medecin = models.Medecin(**nouveau_medecin.model_dump())
    db.add(db_medecin)
    db.commit()
    db.refresh(db_medecin)
    return db_medecin


@app.put("/medecins/{medecin_id}", response_model=MedecinResponse)
def update_medecin(
    medecin_id: int,
    medecin_modifie: MedecinCreate,
    db: Session = Depends(get_db)
):
    medecin = db.query(models.Medecin).filter(models.Medecin.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    autre = db.query(models.Medecin).filter(
        models.Medecin.numero_permis == medecin_modifie.numero_permis,
        models.Medecin.id != medecin_id
    ).first()
    if autre:
        raise HTTPException(
            status_code=409,
            detail="Ce numéro de permis est déjà utilisé par un autre médecin"
        )

    medecin.nom = medecin_modifie.nom
    medecin.prenom = medecin_modifie.prenom
    medecin.specialite = medecin_modifie.specialite
    medecin.numero_permis = medecin_modifie.numero_permis

    db.commit()
    db.refresh(medecin)
    return medecin


@app.delete("/medecins/{medecin_id}")
def delete_medecin(medecin_id: int, db: Session = Depends(get_db)):
    medecin = db.query(models.Medecin).filter(models.Medecin.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    db.delete(medecin)
    db.commit()
    return {"message": "Médecin supprimé avec succès"}


# ===== ENDPOINTS : RENDEZ-VOUS =====

def _verifier_patient_et_medecin(rdv: RendezVousCreate, db: Session):
    """Vérifie que le patient et le médecin référencés existent."""
    if not db.query(models.Patient).filter(models.Patient.id == rdv.patient_id).first():
        raise HTTPException(status_code=404, detail="Patient introuvable")
    if not db.query(models.Medecin).filter(models.Medecin.id == rdv.medecin_id).first():
        raise HTTPException(status_code=404, detail="Médecin introuvable")


@app.get("/rendezvous", response_model=list[RendezVousResponse])
def get_all_rendezvous(db: Session = Depends(get_db)):
    return db.query(models.RendezVous).all()


@app.get("/rendezvous/{rdv_id}", response_model=RendezVousResponse)
def get_rendezvous_by_id(rdv_id: int, db: Session = Depends(get_db)):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")
    return rdv


@app.post("/rendezvous", response_model=RendezVousResponse)
def create_rendezvous(nouveau_rdv: RendezVousCreate, db: Session = Depends(get_db)):
    _verifier_patient_et_medecin(nouveau_rdv, db)

    db_rdv = models.RendezVous(**nouveau_rdv.model_dump())
    db.add(db_rdv)
    db.commit()
    db.refresh(db_rdv)
    return db_rdv


@app.put("/rendezvous/{rdv_id}", response_model=RendezVousResponse)
def update_rendezvous(
    rdv_id: int,
    rdv_modifie: RendezVousCreate,
    db: Session = Depends(get_db)
):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")

    _verifier_patient_et_medecin(rdv_modifie, db)

    rdv.patient_id = rdv_modifie.patient_id
    rdv.medecin_id = rdv_modifie.medecin_id
    rdv.date_heure = rdv_modifie.date_heure
    rdv.motif = rdv_modifie.motif
    rdv.statut = rdv_modifie.statut
    rdv.mode = rdv_modifie.mode

    db.commit()
    db.refresh(rdv)
    return rdv


@app.delete("/rendezvous/{rdv_id}")
def delete_rendezvous(rdv_id: int, db: Session = Depends(get_db)):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")

    db.delete(rdv)
    db.commit()
    return {"message": "Rendez-vous supprimé avec succès"}

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from database import engine, Base, get_db
import models

# Crée toutes les tables au démarrage (si elles n'existent pas déjà)
Base.metadata.create_all(bind=engine)

app = FastAPI()


# ===== MODÈLES PYDANTIC (validation des données entrantes) =====

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
    model_config = ConfigDict(from_attributes=True)  # Permet de convertir un objet SQLAlchemy en JSON

    id: int
    nom: str
    prenom: str
    age: int
    numero_ramq: str


# ===== ENDPOINTS =====

@app.get("/")
def read_root():
    return {"message": "Bonjour, mon API fonctionne !"}


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
    # Vérifier que le RAMQ n'est pas déjà utilisé
    existant = db.query(models.Patient).filter(
        models.Patient.numero_ramq == nouveau_patient.numero_ramq
    ).first()
    if existant:
        raise HTTPException(
            status_code=409,
            detail="Un patient avec ce numéro RAMQ existe déjà"
        )

    # Créer le nouveau patient
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
    # Trouver le patient à modifier
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")

    # Vérifier que le nouveau RAMQ n'est pas pris par quelqu'un d'autre
    autre = db.query(models.Patient).filter(
        models.Patient.numero_ramq == patient_modifie.numero_ramq,
        models.Patient.id != patient_id
    ).first()
    if autre:
        raise HTTPException(
            status_code=409,
            detail="Ce numéro RAMQ est déjà utilisé par un autre patient"
        )

    # Mettre à jour
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
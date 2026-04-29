from datetime import date, datetime, time, timedelta

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

# Constantes des horaires d'ouverture de la clinique
HEURE_OUVERTURE = 8   # 8h00
HEURE_FERMETURE = 18  # 18h00
DUREE_CRENEAU_MINUTES = 30
HEURES_AVANT_ANNULATION = 24


def _maintenant() -> datetime:
    """Wrappé pour faciliter le mock dans les tests."""
    return datetime.now()

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
    duree_minutes: int = Field(default=30, gt=0, le=240)
    motif: str | None = None
    statut: StatutRendezVous = StatutRendezVous.prevu
    mode: ModeConsultation


class RendezVousResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    medecin_id: int
    date_heure: datetime
    duree_minutes: int
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


def _verifier_horaires_ouverture(rdv: RendezVousCreate):
    """RDV uniquement du lundi au vendredi, entre 8h et 18h (fin incluse)."""
    debut = rdv.date_heure
    fin = debut + timedelta(minutes=rdv.duree_minutes)

    if debut.weekday() >= 5:
        raise HTTPException(
            status_code=400,
            detail="La clinique est fermée le week-end (lundi au vendredi uniquement)"
        )

    debut_journee = debut.replace(hour=HEURE_OUVERTURE, minute=0, second=0, microsecond=0)
    fin_journee = debut.replace(hour=HEURE_FERMETURE, minute=0, second=0, microsecond=0)

    if debut < debut_journee or fin > fin_journee:
        raise HTTPException(
            status_code=400,
            detail=f"Les RDV doivent être entre {HEURE_OUVERTURE}h et {HEURE_FERMETURE}h"
        )


def _verifier_conflit_horaire(rdv: RendezVousCreate, db: Session, exclure_id: int | None = None):
    """Empêche le double-booking : aucun chevauchement avec un autre RDV non annulé du même médecin."""
    debut_nouveau = rdv.date_heure
    fin_nouveau = debut_nouveau + timedelta(minutes=rdv.duree_minutes)

    requete = db.query(models.RendezVous).filter(
        models.RendezVous.medecin_id == rdv.medecin_id,
        models.RendezVous.statut != StatutRendezVous.annule,
    )
    if exclure_id is not None:
        requete = requete.filter(models.RendezVous.id != exclure_id)

    for existant in requete.all():
        debut_existant = existant.date_heure
        fin_existant = debut_existant + timedelta(minutes=existant.duree_minutes)
        if debut_nouveau < fin_existant and debut_existant < fin_nouveau:
            raise HTTPException(
                status_code=409,
                detail="Ce médecin a déjà un rendez-vous à ce moment-là"
            )


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
    _verifier_horaires_ouverture(nouveau_rdv)
    _verifier_conflit_horaire(nouveau_rdv, db)

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
    _verifier_horaires_ouverture(rdv_modifie)
    _verifier_conflit_horaire(rdv_modifie, db, exclure_id=rdv_id)

    # Règle d'annulation : ≥ 24h avant le RDV
    on_annule = (
        rdv_modifie.statut == StatutRendezVous.annule
        and rdv.statut != StatutRendezVous.annule
    )
    if on_annule and rdv.date_heure - _maintenant() < timedelta(hours=HEURES_AVANT_ANNULATION):
        raise HTTPException(
            status_code=400,
            detail=f"Annulation impossible : il faut au moins {HEURES_AVANT_ANNULATION}h d'avance"
        )

    rdv.patient_id = rdv_modifie.patient_id
    rdv.medecin_id = rdv_modifie.medecin_id
    rdv.date_heure = rdv_modifie.date_heure
    rdv.duree_minutes = rdv_modifie.duree_minutes
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


# ===== ENDPOINT : RECHERCHE DE CRÉNEAUX DISPONIBLES =====

@app.get("/medecins/{medecin_id}/creneaux")
def get_creneaux_disponibles(medecin_id: int, jour: date, db: Session = Depends(get_db)):
    """Retourne les créneaux libres (pas de doublon avec les RDV existants) du médecin pour une journée."""
    medecin = db.query(models.Medecin).filter(models.Medecin.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    if jour.weekday() >= 5:
        return {"date": jour.isoformat(), "creneaux_disponibles": []}

    # Génère les créneaux de DUREE_CRENEAU_MINUTES de HEURE_OUVERTURE à HEURE_FERMETURE
    slots = []
    minutes_courantes = HEURE_OUVERTURE * 60
    fin_minutes = HEURE_FERMETURE * 60
    while minutes_courantes + DUREE_CRENEAU_MINUTES <= fin_minutes:
        h, m = divmod(minutes_courantes, 60)
        slots.append(datetime.combine(jour, time(h, m)))
        minutes_courantes += DUREE_CRENEAU_MINUTES

    # Récupère les RDV non annulés du médecin pour cette journée
    debut_jour = datetime.combine(jour, time(0, 0))
    fin_jour = debut_jour + timedelta(days=1)
    rdvs_du_jour = db.query(models.RendezVous).filter(
        models.RendezVous.medecin_id == medecin_id,
        models.RendezVous.statut != StatutRendezVous.annule,
        models.RendezVous.date_heure >= debut_jour,
        models.RendezVous.date_heure < fin_jour,
    ).all()

    creneaux_libres = []
    for slot_debut in slots:
        slot_fin = slot_debut + timedelta(minutes=DUREE_CRENEAU_MINUTES)
        chevauche = any(
            slot_debut < r.date_heure + timedelta(minutes=r.duree_minutes)
            and r.date_heure < slot_fin
            for r in rdvs_du_jour
        )
        if not chevauche:
            creneaux_libres.append(slot_debut.strftime("%H:%M"))

    return {"date": jour.isoformat(), "creneaux_disponibles": creneaux_libres}

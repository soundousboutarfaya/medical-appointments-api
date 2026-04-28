from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


# Modèle Pydantic : décrit à quoi doit ressembler un patient quand on en crée un
class PatientCreate(BaseModel):
    nom: str
    prenom: str
    age: int
    numero_ramq: str = Field(
        ...,
        pattern=r"^[A-Z]{4}\d{8}$",
        description="Numéro RAMQ : 4 lettres majuscules suivies de 8 chiffres (ex: TREM45120115)",
    )


# Notre "base de données" temporaire
patients = [
    {"id": 1, "nom": "Tremblay", "prenom": "Marie", "age": 45, "numero_ramq": "TREM45120115"},
    {"id": 2, "nom": "Gagnon", "prenom": "Jean", "age": 67, "numero_ramq": "GAGN23080742"},
    {"id": 3, "nom": "Lavoie", "prenom": "Sophie", "age": 32, "numero_ramq": "LAVS92110328"},
]


@app.get("/")
def read_root():
    return {"message": "Bonjour, mon API fonctionne !"}


@app.get("/patients")
def get_all_patients():
    return patients


@app.get("/patients/{patient_id}")
def get_patient_by_id(patient_id: int):
    for patient in patients:
        if patient["id"] == patient_id:
            return patient
    return {"erreur": "Patient introuvable"}


@app.post("/patients")
def create_patient(nouveau_patient: PatientCreate):
    # Vérifier qu'aucun patient n'a déjà ce numéro RAMQ
    for p in patients:
        if p["numero_ramq"] == nouveau_patient.numero_ramq:
            return {"erreur": "Un patient avec ce numéro RAMQ existe déjà"}

    # Génère un nouvel ID en prenant le plus grand ID existant + 1
    nouvel_id = max([p["id"] for p in patients]) + 1 if patients else 1

    # Construit le dictionnaire complet du patient
    patient_dict = {
        "id": nouvel_id,
        "nom": nouveau_patient.nom,
        "prenom": nouveau_patient.prenom,
        "age": nouveau_patient.age,
        "numero_ramq": nouveau_patient.numero_ramq,
    }

    # Ajoute le patient à notre "base de données"
    patients.append(patient_dict)

    # Retourne le patient créé
    return patient_dict
from fastapi.testclient import TestClient
from main import app

# Crée un client de test qui simule des requêtes HTTP vers notre API
client = TestClient(app)


def test_read_root():
    """Teste que la racine renvoie le message de bienvenue."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bonjour, mon API fonctionne !"}


def test_get_all_patients():
    """Teste qu'on récupère bien la liste de tous les patients."""
    response = client.get("/patients")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 3  # Au moins les 3 patients de base


def test_get_patient_by_id_existant():
    """Teste qu'on récupère bien un patient existant par son ID."""
    response = client.get("/patients/1")
    assert response.status_code == 200
    assert response.json()["nom"] == "Tremblay"
    assert response.json()["prenom"] == "Marie"


def test_get_patient_by_id_inexistant():
    """Teste le comportement quand le patient n'existe pas."""
    response = client.get("/patients/9999")
    assert response.status_code == 200
    assert "erreur" in response.json()


def test_create_patient_valide():
    """Teste la création d'un patient avec des données valides."""
    nouveau_patient = {
        "nom": "Bouchard",
        "prenom": "Pierre",
        "age": 50,
        "numero_ramq": "BOUP74050501",
    }
    response = client.post("/patients", json=nouveau_patient)
    assert response.status_code == 200
    assert response.json()["nom"] == "Bouchard"
    assert "id" in response.json()


def test_create_patient_ramq_invalide():
    """Teste qu'un RAMQ avec mauvais format est rejeté."""
    patient_invalide = {
        "nom": "Test",
        "prenom": "Patient",
        "age": 30,
        "numero_ramq": "abc123",  # Format invalide
    }
    response = client.post("/patients", json=patient_invalide)
    assert response.status_code == 422  # Erreur de validation Pydantic


def test_create_patient_sans_ramq():
    """Teste qu'un patient sans RAMQ est rejeté."""
    patient_sans_ramq = {
        "nom": "Test",
        "prenom": "Patient",
        "age": 30,
    }
    response = client.post("/patients", json=patient_sans_ramq)
    assert response.status_code == 422  # Champ requis manquant


def test_create_patient_ramq_duplique():
    """Teste qu'on ne peut pas créer 2 patients avec le même RAMQ."""
    patient = {
        "nom": "Tremblay",
        "prenom": "Sophie",
        "age": 30,
        "numero_ramq": "TREM45120115",  # RAMQ déjà utilisé
    }
    response = client.post("/patients", json=patient)
    assert response.status_code == 200
    assert "erreur" in response.json()
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
import models


# ===== SETUP : Base de données de test (en mémoire) =====

# DB SQLite en mémoire (disparaît à la fin des tests)
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Important pour SQLite en mémoire
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


# Override de get_db : nos tests utilisent la DB de test au lieu de la vraie
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ===== FIXTURE : préparer une DB fraîche pour chaque test =====

@pytest.fixture(autouse=True)
def setup_database():
    """
    Avant chaque test : crée des tables vides
    Après chaque test : supprime tout (DB fraîche pour le prochain)
    """
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


# ===== HELPER : créer un patient pour les tests =====

def creer_patient_test(nom="Tremblay", prenom="Marie", age=45, ramq="TREM45120115"):
    """Helper pour créer un patient dans les tests."""
    return client.post(
        "/patients",
        json={"nom": nom, "prenom": prenom, "age": age, "numero_ramq": ramq},
    )


# ===== TESTS =====

def test_read_root():
    """Teste que la racine renvoie le message de bienvenue."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bonjour, mon API fonctionne !"}


def test_get_all_patients_vide():
    """Au début, la liste des patients est vide."""
    response = client.get("/patients")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_patients_avec_donnees():
    """Après création, on retrouve bien les patients."""
    creer_patient_test()
    response = client.get("/patients")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_patient_valide():
    """Création d'un patient avec données valides."""
    response = creer_patient_test()
    assert response.status_code == 200
    assert response.json()["nom"] == "Tremblay"
    assert "id" in response.json()


def test_create_patient_ramq_invalide():
    """RAMQ avec mauvais format est rejeté par Pydantic."""
    response = client.post(
        "/patients",
        json={"nom": "Test", "prenom": "T", "age": 30, "numero_ramq": "abc123"},
    )
    assert response.status_code == 422


def test_create_patient_sans_ramq():
    """Patient sans RAMQ est rejeté (champ requis)."""
    response = client.post(
        "/patients",
        json={"nom": "Test", "prenom": "T", "age": 30},
    )
    assert response.status_code == 422


def test_create_patient_ramq_duplique():
    """On ne peut pas créer 2 patients avec le même RAMQ."""
    creer_patient_test()
    response = creer_patient_test()  # Même RAMQ par défaut
    assert response.status_code == 409
    assert "déjà" in response.json()["detail"]


def test_get_patient_by_id_existant():
    """Récupération d'un patient existant."""
    create_response = creer_patient_test()
    patient_id = create_response.json()["id"]

    response = client.get(f"/patients/{patient_id}")
    assert response.status_code == 200
    assert response.json()["nom"] == "Tremblay"


def test_get_patient_by_id_inexistant():
    """Patient inexistant renvoie 404."""
    response = client.get("/patients/9999")
    assert response.status_code == 404


def test_update_patient_existant():
    """Modification d'un patient existant."""
    create_response = creer_patient_test()
    patient_id = create_response.json()["id"]

    response = client.put(
        f"/patients/{patient_id}",
        json={"nom": "Tremblay", "prenom": "Marie", "age": 46, "numero_ramq": "TREM45120115"},
    )
    assert response.status_code == 200
    assert response.json()["age"] == 46


def test_update_patient_inexistant():
    """Modifier un patient qui n'existe pas renvoie 404."""
    response = client.put(
        "/patients/9999",
        json={"nom": "Test", "prenom": "T", "age": 30, "numero_ramq": "TEST12345678"},
    )
    assert response.status_code == 404


def test_update_patient_ramq_pris_par_autre():
    """On ne peut pas prendre le RAMQ d'un autre patient."""
    creer_patient_test(ramq="TREM45120115")
    response_p2 = creer_patient_test(nom="Gagnon", prenom="Jean", age=67, ramq="GAGN23080742")
    p2_id = response_p2.json()["id"]

    # Tente de mettre le RAMQ de p1 sur p2
    response = client.put(
        f"/patients/{p2_id}",
        json={"nom": "Gagnon", "prenom": "Jean", "age": 67, "numero_ramq": "TREM45120115"},
    )
    assert response.status_code == 409


def test_delete_patient_existant():
    """Suppression d'un patient existant."""
    create_response = creer_patient_test()
    patient_id = create_response.json()["id"]

    response = client.delete(f"/patients/{patient_id}")
    assert response.status_code == 200
    assert "message" in response.json()

    # Vérifier qu'il a vraiment disparu
    get_response = client.get(f"/patients/{patient_id}")
    assert get_response.status_code == 404


def test_delete_patient_inexistant():
    """Supprimer un patient qui n'existe pas renvoie 404."""
    response = client.delete("/patients/9999")
    assert response.status_code == 404
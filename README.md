# Medical Appointments API

API REST de gestion de rendez-vous médicaux développée en Python avec FastAPI.

Projet personnel d'apprentissage du développement backend, inspiré de mon expérience administrative en milieu médical (clinique, hôpital).

## Pourquoi ce projet

J'ai travaillé plusieurs années comme adjointe administrative dans des cliniques et hôpitaux, où j'ai utilisé quotidiennement des logiciels de gestion de rendez-vous, de dossiers patients et de prescriptions. Je connais les vrais problèmes du domaine : double-booking, gestion des disponibilités, confidentialité des données. Ce projet me permet de les attaquer du côté développeur cette fois.

## Stack technique

- **Python 3.13**
- **FastAPI** — framework web pour l'API REST
- **Uvicorn** — serveur ASGI
- **SQLAlchemy** — ORM
- **SQLite** (puis **PostgreSQL** plus tard) — base de données
- **Pytest** — tests automatisés

## Installation

### Prérequis

- Python 3.11 ou plus récent
- Git

### Étapes

```bash
# Cloner le repo
git clone https://github.com/soundousboutarfaya/medical-appointments-api.git
cd medical-appointments-api

# Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # sur Mac/Linux
# .\venv\Scripts\activate   # sur Windows

# Installer les dépendances
pip install fastapi uvicorn sqlalchemy pytest httpx

# Lancer le serveur
uvicorn main:app --reload
```

L'API est ensuite disponible sur `http://127.0.0.1:8000`.
La documentation interactive Swagger UI est sur `http://127.0.0.1:8000/docs`.

## Endpoints disponibles


| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Page d'accueil de l'API |
| GET | `/patients` | Liste tous les patients |
| GET | `/patients/{id}` | Récupère un patient par son ID |
| POST | `/patients` | Crée un nouveau patient (avec validation RAMQ) |
| PUT | `/patients/{id}` | Modifie un patient existant |
| DELETE | `/patients/{id}` | Supprime un patient |

## Roadmap
### Étape 1 — Setup et premiers endpoints ✅
- [x] Initialiser le projet et le repo GitHub
- [x] Configurer l'environnement virtuel Python
- [x] Installer FastAPI et Uvicorn
- [x] Créer un endpoint racine `GET /`
- [x] Créer un endpoint `GET /patients` (liste en mémoire)
- [x] Créer un endpoint `GET /patients/{id}` avec validation automatique
- [x] Ajouter `POST /patients` pour créer un patient
- [x] Ajouter validation du format RAMQ (regex Pydantic)
- [x] Vérifier l'unicité du numéro RAMQ
- [x] Écrire les premiers tests unitaires avec Pytest (8 tests)
- [x] Ajouter `PUT /patients/{id}` pour modifier
- [x] Ajouter `DELETE /patients/{id}` pour supprimer

### Étape 2 — Base de données
- [x] Intégrer SQLAlchemy avec SQLite
- [x] Migrer du stockage en mémoire vers la base de données
- [ ] Modéliser le schéma complet (médecins, rendez-vous)

### Étape 3 — Logique métier
- [ ] Empêcher le double-booking d'un médecin
- [ ] Valider les horaires d'ouverture
- [ ] Endpoint de recherche de créneaux disponibles
- [ ] Règle d'annulation (24h à l'avance minimum)

### Étape 4 — Sécurité et tests
- [ ] Authentification JWT
- [ ] Système de rôles (admin, médecin)
- [x] Tests unitaires avec Pytest
- [ ] Tests d'intégration

### Étape 5 — Déploiement
- [ ] Déployer sur Render ou Railway
- [ ] Documentation finale
- [ ] Captures d'écran de Swagger UI

## Ce que j'apprends en construisant ce projet

- Architecture d'une API REST
- Conception de schémas de bases de données relationnelles
- Validation de données avec Pydantic
- Authentification et sécurité d'API
- Tests automatisés
- Déploiement d'applications Python

## Auteure

**Soundous Boutarfaya**
Bachelière en informatique, Université de Montréal
soundousboutarfaya@yahoo.fr

## Licence

MIT

## Tests

Le projet inclut une suite de **14 tests unitaires** avec Pytest, exécutés sur une base SQLite **en mémoire** (isolée de `app.db`).

```bash
pytest -v
```

Tests actuellement couverts :

**Lecture (GET)**
- Endpoint racine
- Liste de tous les patients
- Récupération d'un patient par ID
- Gestion d'un ID inexistant

**Création (POST)**
- Création avec données valides
- Rejet des RAMQ au format invalide
- Rejet des patients sans RAMQ
- Détection des doublons de RAMQ

**Modification (PUT)**
- Modification d'un patient existant
- Gestion d'un patient inexistant

**Suppression (DELETE)**
- Suppression d'un patient existant
- Gestion d'un patient inexistant
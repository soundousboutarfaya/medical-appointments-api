# Medical Appointments API

[![CI](https://github.com/soundousboutarfaya/medical-appointments-api/actions/workflows/ci.yml/badge.svg)](https://github.com/soundousboutarfaya/medical-appointments-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-69%20passing-success)](test_main.py)

A REST API for managing medical appointments, built in Python with FastAPI.

A personal backend-development project, inspired by my administrative experience in medical settings (clinics, hospitals).

## Why this project

I worked for several years as an administrative assistant in clinics and hospitals, where I used appointment-scheduling, patient-record and prescription software every day. I know the real problems of the domain: double-booking, availability management, data confidentiality. This project lets me tackle them from the developer's side this time.

## Tech stack

- **Python 3.13**
- **FastAPI** — web framework for the REST API
- **Uvicorn** — ASGI server
- **SQLAlchemy** — ORM
- **SQLite** (then **PostgreSQL** later) — database
- **Pytest** — automated tests
- **python-jose** + **passlib/bcrypt** — JWT authentication and password hashing

## Screenshots

> Add your own captures to `docs/screenshots/` (see [docs/screenshots/README.md](docs/screenshots/README.md)).

| Swagger UI | Dashboard | Appointments |
| ---------- | --------- | ------------ |
| ![Swagger UI](docs/screenshots/swagger.png) | ![Dashboard](docs/screenshots/dashboard.png) | ![Appointments](docs/screenshots/appointments.png) |

## Installation

### Prerequisites

- Python 3.11 or newer
- Git

### Steps

```bash
# Clone the repo
git clone https://github.com/soundousboutarfaya/medical-appointments-api.git
cd medical-appointments-api

# Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate  # on Mac/Linux
# .\venv\Scripts\activate   # on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Then open .env and replace SECRET_KEY with a real random key

# Start the server
uvicorn main:app --reload
```

The API is then available at `http://127.0.0.1:8000`.
The interactive Swagger UI documentation is at `http://127.0.0.1:8000/docs`.

## Docker

```bash
# Build and run with Docker Compose
SECRET_KEY=your-secret docker compose up --build
```

Or with plain Docker:

```bash
docker build -t medical-appointments-api .
docker run -p 8000:8000 -e SECRET_KEY=your-secret medical-appointments-api
```

The API is then available at `http://127.0.0.1:8000`.

## Environment variables

| Variable | Description | Required in prod |
|----------|-------------|------------------|
| `SECRET_KEY` | Key used to sign JWTs. Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` | Yes |

In development a default key is used, but it is intentionally marked as insecure — always replace it in production.

## Available endpoints

### Authentication

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register` | Public | Creates a new account (role `admin` or `doctor`) |
| POST | `/auth/login` | Public | Exchanges email + password for a JWT |
| GET | `/auth/me` | Authenticated | Returns the current user's profile |

All endpoints below (except `/`) require an `Authorization: Bearer <token>` header.

### Resources

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/` | Public | API home page |
| GET | `/patients` | Authenticated | List all patients |
| GET | `/patients/{id}` | Authenticated | Get a patient by ID |
| POST | `/patients` | Admin | Create a new patient (with health card validation) |
| PUT | `/patients/{id}` | Admin | Update an existing patient |
| DELETE | `/patients/{id}` | Admin | Delete a patient |
| GET | `/doctors` | Authenticated | List all doctors |
| GET | `/doctors/{id}` | Authenticated | Get a doctor by ID |
| POST | `/doctors` | Admin | Create a new doctor (license number validation) |
| PUT | `/doctors/{id}` | Admin | Update an existing doctor |
| DELETE | `/doctors/{id}` | Admin | Delete a doctor |
| GET | `/appointments` | Authenticated | List all appointments |
| GET | `/appointments/{id}` | Authenticated | Get an appointment by ID |
| POST | `/appointments` | Admin / doctor | Create an appointment (in person or virtual) |
| PUT | `/appointments/{id}` | Admin / doctor | Update an existing appointment |
| DELETE | `/appointments/{id}` | Admin / doctor | Delete an appointment |
| GET | `/doctors/{id}/slots?day=YYYY-MM-DD` | Authenticated | List a doctor's free slots for a day |

## Roadmap

### Step 1 — Setup and first endpoints
- [x] Initialize the project and the GitHub repo
- [x] Set up the Python virtual environment
- [x] Install FastAPI and Uvicorn
- [x] Create a root endpoint `GET /`
- [x] Create a `GET /patients` endpoint (in-memory list)
- [x] Create a `GET /patients/{id}` endpoint with automatic validation
- [x] Add `POST /patients` to create a patient
- [x] Add health card format validation (Pydantic regex)
- [x] Enforce health card number uniqueness
- [x] Write the first unit tests with Pytest
- [x] Add `PUT /patients/{id}` to update
- [x] Add `DELETE /patients/{id}` to delete

### Step 2 — Database
- [x] Integrate SQLAlchemy with SQLite
- [x] Migrate from in-memory storage to the database
- [x] Model the full schema (doctors, appointments)
- [x] Full CRUD for doctors and appointments
- [x] Consultation mode (in person / virtual) on appointments

### Step 3 — Business logic
- [x] Prevent double-booking a doctor (overlap detection with variable duration)
- [x] Validate opening hours (8:00–18:00, Monday to Friday)
- [x] Available-slots lookup endpoint (30-min granularity)
- [x] Cancellation rule (at least 24h in advance)

### Step 4 — Security and tests
- [x] JWT authentication (login, /me, bcrypt hashing)
- [x] Role system (admin, doctor) with FastAPI dependencies
- [x] Unit tests with Pytest
- [x] Integration tests (end-to-end scenario register → login → create appointment)

### Step 5 — Deployment
- [x] Render preparation (`render.yaml`, `Procfile`, `requirements.txt`)
- [x] Environment variables documentation
- [x] Final documentation
- [ ] Actual deployment on Render (to be done from the Render dashboard)
- [ ] Swagger UI screenshots

### Deploying on Render

The project is ready to be deployed on [Render](https://render.com):

1. Push the code to GitHub
2. On Render: New → Blueprint → connect the repo
3. Render automatically detects `render.yaml` and provisions the service
4. The `SECRET_KEY` variable is generated automatically by Render

**Known limitation:** SQLite on Render's free plan is not persistent (the disk is ephemeral). For real production, migrate to PostgreSQL by editing `database.py` and adding `psycopg2-binary` to `requirements.txt`.

## What I'm learning by building this project

- REST API architecture
- Relational database schema design
- Data validation with Pydantic
- API authentication and security
- Automated testing
- Deploying Python applications

## Author

**Soundous Boutarfaya**
Bachelor's in Computer Science, Université de Montréal
soundousboutarfaya@yahoo.fr

## License

MIT

## Tests

The project includes a suite of **69 tests** with Pytest, run on an **in-memory** SQLite database (isolated from `app.db`).

```bash
pytest -v
```

Currently covered tests:

**Reads (GET)**
- Root endpoint
- List all patients
- Get a patient by ID
- Handling a non-existent ID

**Creation (POST)**
- Creation with valid data
- Rejection of invalid health card formats
- Rejection of patients without a health card number
- Health card duplicate detection

**Update (PUT)**
- Update an existing patient
- Handling a non-existent patient

**Deletion (DELETE)**
- Delete an existing patient
- Handling a non-existent patient
- Cascade: deleting a patient deletes their appointments

**Doctors**
- Full CRUD
- License number format validation (5 digits)
- License duplicate detection

**Appointments**
- In-person and virtual creation
- Rejection of invalid modes
- Verifying that the referenced patient and doctor exist
- Status update (scheduled / confirmed / cancelled / completed)

**Business logic**
- Rejection of appointments outside the 8:00–18:00 range or overflowing
- Rejection of weekend appointments
- Overlap detection (double-booking) with variable duration
- Acceptance of consecutive appointments and of different doctors at the same time
- Freeing the slot when an appointment is cancelled
- Computing a doctor's available slots for a day
- 24h cancellation rule (tested with time mocking)

**Authentication and roles**
- Registration with email and password-length validation
- Rejection of already-used emails
- Login by email + password, returning a JWT
- Rejection with a wrong password or unknown email
- `/auth/me` endpoint returning the profile
- Protected endpoints (401 without token, 401 with invalid token)
- Admin-only endpoints denied to a doctor (403)
- Medical-staff endpoints accessible to doctors

**Integration**
- End-to-end scenario: register → login → create appointment → read profile

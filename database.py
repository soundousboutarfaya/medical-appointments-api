from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de la base de données SQLite
# Le fichier app.db sera créé automatiquement dans ton dossier
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# Le "engine" = le moteur qui gère la connexion à la DB
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Spécifique à SQLite
)

# La "session factory" = elle crée des sessions pour parler à la DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# La classe parente pour tous nos modèles (= tables)
Base = declarative_base()


# Fonction utilitaire pour FastAPI
# Elle ouvre une session, la donne à l'endpoint, puis la ferme
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
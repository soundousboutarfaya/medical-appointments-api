from sqlalchemy import Column, Integer, String
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    numero_ramq = Column(String, unique=True, nullable=False, index=True)
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class StatutRendezVous(str, enum.Enum):
    prevu = "prevu"
    confirme = "confirme"
    annule = "annule"
    complete = "complete"


class ModeConsultation(str, enum.Enum):
    en_personne = "en_personne"
    virtuel = "virtuel"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    numero_ramq = Column(String, unique=True, nullable=False, index=True)

    rendezvous = relationship(
        "RendezVous",
        back_populates="patient",
        cascade="all, delete-orphan",
    )


class Medecin(Base):
    __tablename__ = "medecins"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    specialite = Column(String, nullable=False)
    numero_permis = Column(String, unique=True, nullable=False, index=True)

    rendezvous = relationship(
        "RendezVous",
        back_populates="medecin",
        cascade="all, delete-orphan",
    )


class RendezVous(Base):
    __tablename__ = "rendezvous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    medecin_id = Column(Integer, ForeignKey("medecins.id"), nullable=False, index=True)
    date_heure = Column(DateTime, nullable=False)
    duree_minutes = Column(Integer, nullable=False, default=30)
    motif = Column(String, nullable=True)
    statut = Column(
        Enum(StatutRendezVous),
        nullable=False,
        default=StatutRendezVous.prevu,
    )
    mode = Column(Enum(ModeConsultation), nullable=False)

    patient = relationship("Patient", back_populates="rendezvous")
    medecin = relationship("Medecin", back_populates="rendezvous")

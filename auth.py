import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import RoleUtilisateur, User

# Configuration — en production, SECRET_KEY doit être fourni par variable d'env
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    exception_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise exception_auth
    except JWTError:
        raise exception_auth

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise exception_auth
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != RoleUtilisateur.admin:
        raise HTTPException(
            status_code=403,
            detail="Action réservée aux administrateurs"
        )
    return current


def require_personnel(current: User = Depends(get_current_user)) -> User:
    """Admin ou médecin — utilisé pour les opérations cliniques (RDV)."""
    if current.role not in (RoleUtilisateur.admin, RoleUtilisateur.medecin):
        raise HTTPException(
            status_code=403,
            detail="Action réservée au personnel médical"
        )
    return current

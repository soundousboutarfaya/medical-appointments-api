import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import UserRole, User

# Configuration — in production, SECRET_KEY must come from an env variable
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
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise auth_exception
    except JWTError:
        raise auth_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise auth_exception
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Action restricted to administrators",
        )
    return current


def require_staff(current: User = Depends(get_current_user)) -> User:
    """Admin or doctor — used for clinical operations (appointments)."""
    if current.role not in (UserRole.admin, UserRole.doctor):
        raise HTTPException(
            status_code=403,
            detail="Action restricted to medical staff",
        )
    return current

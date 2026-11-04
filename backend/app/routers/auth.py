"""Rejestracja, logowanie i dane zalogowanego użytkownika."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserOut, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Uwierzytelnianie"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Rejestracja nowego użytkownika")
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Użytkownik o tym adresie e-mail już istnieje")

    user = User(email=email, password_hash=hash_password(data.password), risk_profile=data.risk_profile)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Logowanie - zwraca token dostępu")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut, summary="Dane zalogowanego użytkownika")
def me(user: User = Depends(get_current_user)):
    return user

@router.patch("/me", response_model=UserOut, summary="Zmiana profilu ryzyka")
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.risk_profile = data.risk_profile
    db.commit()
    db.refresh(user)
    return user
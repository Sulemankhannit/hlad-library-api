from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import LibraryUser
from app.core.security import create_jwt_access_token

router = APIRouter(tags=["Mock Authentication (Development Only)"])

@router.post("/token")     
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    Development-only mock token generator.
    - Username: User ID (24-hex) OR user Email.
    - Password: Optional role override ("owner", "admin", "member", "student").
    """
    query_val = form_data.username.strip()

    # 1. Lookup by primary key ID or by email
    user = session.get(LibraryUser, query_val)
    if not user and "@" in query_val:
        user = session.exec(select(LibraryUser).where(LibraryUser.email == query_val.lower())).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That user ID or email does not exist in the Library shadow database."
        )

    # 2. Determine role from password field or defaults
    valid_roles = ["owner", "admin", "member", "student"]
    pwd_role = (form_data.password or "").strip().lower()

    if pwd_role in valid_roles:
        assigned_role = pwd_role
    elif user.email in ["sulemankhanlovesspace@gmail.com", "admin@hlad.local"]:
        assigned_role = "owner"
    else:
        assigned_role = "student"

    access_token = create_jwt_access_token(
        subject_id=user.id,
        email=user.email,
        role=assigned_role
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": assigned_role
    }

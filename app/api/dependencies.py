from fastapi import Depends,HTTPException,status
import jwt
from sqlmodel import Session
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.core.security import token_validation
from app.models.user import LibraryUser
from app.db.session import get_session
from  typing import Annotated

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
) -> LibraryUser:
    
    
    payload = token_validation(token)

    
    user_id: str = payload.get("sub") or payload.get("id")
    email: str = payload.get("email")
    role: str = payload.get("role")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing the required user identifier ('sub' or 'id')."
        )

    # check if curretly the user exists in the specific LIBRARY DATABASE
    user = session.get(LibraryUser, user_id)  # also .get() is a special method to just look for or get the primary key, its not standard query!
                                              
    
    # just in time creation, when first time getting the jwt from the nextjs backend
    if not user:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing required 'email' for first-time profile creation."
            )
        print(f"\nNew JWT detected! Auto-creating library profile for: {email}\n")
        user = LibraryUser(
            id=user_id,
            email=email,
            trust_score=100
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # handle soft deactivation
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This account has been deactivated."
        )

    return user


def get_current_admin_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
) -> LibraryUser:
    """
    Enforces admin or owner privileges.
    Extracts the role from the validated JWT token payload.
    """
    payload = token_validation(token)
    role: str = payload.get("role", "")

    if role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or owner privileges required."
        )

    return get_current_user(token=token, session=session)



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

    
    user_id: str = payload.get("sub")
    email: str = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing the required 'sub' or 'email' ."
        )

    # check if curretly the user exists in the specific LIBRARY DATABASE
    user = session.get(LibraryUser, user_id)  # also .get() is a special method to just look for or get the primary key, its not standard query!
                                              
    
    # just in time creation, when first time getting the jwt from the nextjs backend
    if not user:
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


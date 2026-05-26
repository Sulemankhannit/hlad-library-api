from fastapi import Depends,HTTPException,status
import jwt
from sqlmodel import Session
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.core.security import token_validation
from app.models.user import LibraryUser
from app.db.session import get_session
from  typing import Annotated

oauth2scheme=OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
        token:Annotated[str,Depends(oauth2scheme)],
        session:Annotated[Session,Depends(get_session)]
)->LibraryUser:
    
    payload=token_validation(token)
    
    user_id=payload.get("sub") #get the userid from the payload
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. The token payload is missing subject identity"
        )
    
    user=session.get(LibraryUser,user_id) # security check, if curretly the user exists in the specific LIBRARY DATABASE
                                          # also .get() is a special method to just look for or get the primary key, its not standard query!
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your account profile is authentic but not yet synchronized with the Library service tracks. Please contact administration."
        )
    
    return user   
    

    

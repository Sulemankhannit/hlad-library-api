from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import LibraryUser
from app.core.security import create_jwt_access_token

router = APIRouter(tags=["Mock Authentication"])

@router.post("/token")     
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    
  
    
   
    mock_user_id = form_data.username
    

    # 2. Verify the ID actually exists in our shadow database
    user = session.get(LibraryUser, mock_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=" That user ID does not exist in the Library shadow database."
        )

    
    access_token = create_jwt_access_token(subject_id=user.id,email=user.email)

    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
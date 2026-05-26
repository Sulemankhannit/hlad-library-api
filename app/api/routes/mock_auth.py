from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import LibraryUser
from app.core.security import create_jwt_access_token

router = APIRouter(tags=["Mock Authentication"])

@router.post("/token")     #MOCK LOGIN ENDPOINT
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    
  
    
    # 1. Swagger UI sends the input from the "Username" box into form_data.username
    mock_user_id = form_data.username
    

    # 2. Verify the ID actually exists in our shadow database
    user = session.get(LibraryUser, mock_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mock Login Failed: That user ID does not exist in the Library shadow database."
        )

    # 3. Mint the cryptographically valid JWT token
    access_token = create_jwt_access_token(subject_id=user.id,email=user.email)

    # 4. Return it in the exact JSON format OAuth2 expects
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
from fastapi import HTTPException,APIRouter,status,Depends
from sqlmodel import select,Session
from typing import Annotated
from app.models.user import LibraryUser
from app.schemas.user import UserCreate,UserResponse
from app.db.session import get_session
router=APIRouter(prefix="/user",tags=["User"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_library_user(
    userdata: UserCreate,
    session: Annotated[Session, Depends(get_session)]
):
   
    if session.get(LibraryUser, userdata.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered."
        )

    new_user = LibraryUser(
        id=userdata.id, 
        email=userdata.email,
        trust_score=100
    )

    
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Database Error."
        )
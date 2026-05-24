from fastapi import HTTPException,APIRouter,status,Depends
from sqlmodel import select,Session
from typing import Annotated
from app.models.user import LibraryUser
from app.schemas.user import UserCreate,UserResponse
from app.db.session import get_session
router=APIRouter(prefix="/user",tags=["User"])

@router.post("/",response_model=UserResponse,status_code=201)
async def register_library_user(
    userdata:UserCreate,
    session:Annotated[Session,Depends(get_session)]
):
    query=select(LibraryUser).where(userdata.id==LibraryUser.id)
    existing_user=session.exec(query).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user already registered"
        )
    new_user=LibraryUser(id=userdata.id,trust_score=100)

    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Database error"
        )
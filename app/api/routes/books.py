from fastapi import HTTPException,APIRouter,Depends,status,Query
from sqlmodel import select,Session,func
from app.db.session import get_session
from app.schemas.book import BookCreate,BookResponse
from app.models.book import Book
from typing import Annotated
from app.api.dependencies import get_current_user
from app.models.user import LibraryUser

router=APIRouter(prefix="/books",tags=["Books"])

@router.post("/",response_model=BookResponse,status_code=201)
async def list_books(
    bookdata:BookCreate,
    session:Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    

    new_book=Book(title=bookdata.title,owner_id=current_user.id,is_available=True)

    try:
        session.add(new_book)
        session.commit()
        session.refresh(new_book)
        return new_book

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Database Error occured"
        )


@router.get("/",response_model=list[BookResponse])
async def get_books(
    session:Annotated[Session,Depends(get_session)],
    offset: int = Query(default=0, ge=0, description="The number of assets to skip over."),
    limit: int = Query(default=20, ge=1, le=100, description="The maximum batch slice returned."),
):
    query=select(Book).where(Book.is_available==True).where(Book.is_deleted==False).offset(offset).limit(limit)
    results=session.exec(query).all()
    return results
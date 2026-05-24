from fastapi import HTTPException,APIRouter,Depends,status,Query
from sqlmodel import select,Session,func
from app.db.session import get_session
from app.schemas.book import BookCreate,BookResponse
from app.models.book import Book
from typing import Annotated

router=APIRouter(prefix="/books",tags=["Books"])

@router.post("/",response_model=BookResponse,status_code=201)
async def list_books(
    bookdata:BookCreate,
    session:Annotated[Session,Depends(get_session)],
):
    mock_authenticated_user_id = "65f1a3b8c9d0e1f2a3b4c5d6"

    new_book=Book(title=bookdata.title,owner_id=mock_authenticated_user_id,is_available=True)

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
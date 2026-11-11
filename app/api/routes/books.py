import uuid
from fastapi import HTTPException,APIRouter,Depends,status,Query
from sqlmodel import select,Session,func,update
from app.db.session import get_session
from app.schemas.book import BookCreate,BookResponse,BookDeleteResponse
from app.models.book import Book
from app.models.request import BookRequest,RequestStatus
from app.models.ledger import BorrowLedger
from typing import Annotated
from app.api.dependencies import get_current_user
from app.models.user import LibraryUser

router=APIRouter(prefix="/books",tags=["Books"])

@router.post("/",response_model=BookResponse,status_code=201)
def list_books(
    bookdata:BookCreate,
    session:Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    

    new_book=Book(
        title=bookdata.title,
        author=bookdata.author,
        cover_url=bookdata.cover_url,
        owner_id=current_user.id,
        is_available=True
    )

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
def get_books(
    session:Annotated[Session,Depends(get_session)],
    offset: int = Query(default=0, ge=0, description="The number of assets to skip over."),
    limit: int = Query(default=20, ge=1, le=100, description="The maximum batch slice returned."),
):
    query=select(Book).where(Book.is_available==True).where(Book.is_deleted==False).offset(offset).limit(limit)
    results=session.exec(query).all()
    return results

@router.get("/all", response_model=list[BookResponse])
def get_all_books(
    session: Annotated[Session, Depends(get_session)],
    offset: int = Query(default=0, ge=0, description="The number of assets to skip over."),
    limit: int = Query(default=20, ge=1, le=100, description="The maximum batch slice returned."),
):
    """
    Returns all books in the library catalog, regardless of their current availability status.
    """
    query = select(Book).where(Book.is_deleted == False).offset(offset).limit(limit)
    results = session.exec(query).all()
    return results

@router.delete("/{book_id}", response_model=BookDeleteResponse, status_code=status.HTTP_200_OK)
def delete_book(
    book_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[LibraryUser, Depends(get_current_user)]
):
    """
    Soft-deletes a book copy from circulation:
    - Verifies the book exists and is not already deleted.
    - Enforces ownership: only the book owner can delete it.
    - Prevents deletion if the book is currently lent out or has an open loan.
    - Automatically cancels any pending borrow requests in the queue.
    - Soft-deletes by setting is_deleted=True and is_available=False.
    """
    target_book = session.exec(
        select(Book).where(Book.id == book_id).with_for_update()
    ).first()

    if not target_book or target_book.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The target book does not exist or has already been removed from circulation."
        )

    if target_book.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Denied. You are not the registered owner of this book copy."
        )

    if not target_book.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete this book while it is actively lended out to another member."
        )

    # Check for any active unreturned loan in the ledger
    active_loan = session.exec(
        select(BorrowLedger).where(
            BorrowLedger.book_id == target_book.id,
            BorrowLedger.returned_at == None
        )
    ).first()

    if active_loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete this book while an active unreturned loan exists in the ledger."
        )

    try:
        # Cancel any pending borrow requests for this book
        session.execute(
            update(BookRequest)
            .where(BookRequest.book_id == target_book.id)
            .where(BookRequest.status == RequestStatus.PENDING)
            .values(
                status=RequestStatus.CANCELED,
                owner_notes="System: Book copy has been removed from circulation by the owner."
            )
        )

        target_book.is_deleted = True
        target_book.is_available = False
        session.add(target_book)
        session.commit()

        return BookDeleteResponse(
            message=f"Book '{target_book.title}' has been successfully removed from circulation.",
            book_id=target_book.id
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Database Error occurred while deleting the book."
        )
    
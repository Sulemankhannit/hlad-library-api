from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Annotated
from app.db.session import get_session
from app.api.dependencies import get_current_user
from app.models.user import LibraryUser
from app.models.book import Book
from app.models.ledger import BorrowLedger
from app.schemas.ledger import ActiveLoanResponse

router = APIRouter(prefix="/ledger", tags=["Active Books"])

@router.get("/borrowing", response_model=list[ActiveLoanResponse])
def get_my_active_borrowed_books(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[LibraryUser, Depends(get_current_user)]
):
    """
    Borrower Dashboard: What books am I currently holding, and when are they due?
    """
    
    query = (
        select(BorrowLedger, Book, LibraryUser)
        .join(Book, BorrowLedger.book_id == Book.id)
        .join(LibraryUser, Book.owner_id == LibraryUser.id)
        .where(
            BorrowLedger.user_id == current_user.id,
            BorrowLedger.returned_at == None  
        )
    )
    
    results = session.exec(query).all()
    
    
    response_data = []
    for ledger, book, owner in results:
        response_data.append(
            ActiveLoanResponse(
                ledger_id=ledger.id,
                book_id=book.id,
                book_title=book.title,
                borrowed_at=ledger.borrowed_at,
                due_date=ledger.due_date,
                contact_email=owner.email
            )
        )
        
    return response_data


@router.get("/lending", response_model=list[ActiveLoanResponse])
def get_my_lent_out_books(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[LibraryUser, Depends(get_current_user)]
):
    """
    Owner Dashboard: Who has my books right now, and when are they giving them back?
    """
    
    query = (
        select(BorrowLedger, Book, LibraryUser)
        .join(Book, BorrowLedger.book_id == Book.id)
        .join(LibraryUser, BorrowLedger.user_id == LibraryUser.id)
        .where(
            Book.owner_id == current_user.id,
            BorrowLedger.returned_at == None  
        )
    )
    
    results = session.exec(query).all()
    
    response_data = []
    for ledger, book, borrower in results:
        response_data.append(
            ActiveLoanResponse(
                ledger_id=ledger.id,
                book_id=book.id,
                book_title=book.title,
                borrowed_at=ledger.borrowed_at,
                due_date=ledger.due_date,
                contact_email=borrower.email
            )
        )
        
    return response_data
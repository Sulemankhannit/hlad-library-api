from fastapi import HTTPException,Depends,APIRouter,status
from sqlmodel import Session,select

from app.db.session import get_session
from app.models.request import BookRequest,RequestStatus
from app.schemas.request import BookRequestCreate,BookRequestResponse
from app.models.book import Book
from app.models.user import LibraryUser
from typing import Annotated

router=APIRouter(prefix="/request",tags=["Request Queue"])

@router.post("/",response_model=BookRequestResponse)
async def book_borrow_request(
    bookdata:BookRequestCreate,
    session:Annotated[Session,Depends(get_session)]
):
    # ─── MOCK IDENTITY BOUNDARY ───
    # In full production, this profile ID is securely parsed out of the incoming JWT bearer credentials.
    # We choose a distinct 24-character user ID to mock a separate student trying to borrow.
    mock_borrower_id = "65f2b4c9d0e1f2a3b4c5d6e7"

    target_book=session.exec(select(Book).where(Book.id==bookdata.book_id)).first()

    if not target_book or target_book.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested book asset copy does not exist or has been permanently removed from circulation."
        )
    
    if not target_book.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This asset copy is currently unavailable. It has already been lended out to another member."
        )
    
    if target_book.owner_id==mock_borrower_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot request to borrow an asset copy that you already own."
        )
    
    existing_active_request=session.exec(
        select(BookRequest).where(
            BookRequest.receiver_id==mock_borrower_id,
            BookRequest.book_id==bookdata.book_id,
            BookRequest.status==RequestStatus.PENDING
            )
    ).first()

    if existing_active_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active pending request lock open for this book copy."
        )
    
    new_book_request=BookRequest(
        receiver_id=mock_borrower_id,
        book_id=bookdata.book_id,
        status=RequestStatus.PENDING
    )

    try:
        session.add(new_book_request)
        session.commit()
        session.refresh(new_book_request)
        return new_book_request
    except Exception as e:
        session.rollback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Critical storage engine transaction error occurred while writing request queue tracking row."
        )
        
        

    
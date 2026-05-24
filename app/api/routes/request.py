from fastapi import HTTPException,Depends,APIRouter,status
from sqlmodel import Session,select,update

from app.db.session import get_session
from app.models.request import BookRequest,RequestStatus
from app.schemas.request import BookRequestCreate,BookRequestResponse
from app.schemas.action import HandshakeAction,RequestActionPayload
from app.models.book import Book
from app.models.user import LibraryUser
from app.models.ledger import BorrowLedger
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
        
        




@router.post("/{request_id}/act", response_model=BookRequestResponse)  
def handle_custody_of_book(    # important and complex endpoint for deciding who the owner gives the book
    request_id: int,  
    owner_input: RequestActionPayload,
    session: Session = Depends(get_session)
):
    """
    Executes the peer-to-peer custody handshake negotiation.
    Utilizes row-level pessimistic locking (FOR UPDATE) inside an explicit 
    atomic context manager to completely eliminate double-approval write skew anomalies.
    """
    # ─── MOCK IDENTITY BOUNDARY ───
    # In full production, this is the securely parsed ID of the asset owner extracted from a JWT token.
    mock_owner_id = "65f1a3b8c9d0e1f2a3b4c5d6"

    # ─── OPEN EXPLICIT CONTEXT TRANSACTION ───
    with session.begin():
        
        # 1. ACQUIRE LOCK: Fetch the request row using a row-level pessimistic lock
        # This forces any parallel thread trying to act on this same request to wait in line.
        request_query = (
            select(BookRequest)
            .where(BookRequest.id == request_id)
            .with_for_update()  # Lock
        )
        target_request = session.exec(request_query).first() # find the request to be handled

        if not target_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The target borrow request record could not be found."
            )

        # 2.  Ensure the request  hasn't already been handled
        if target_request.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction aborted. This request has already been finalized with a status of '{target_request.status}'."
            )

        # 3. VERIFY IDENTITY
        target_book = session.exec(select(Book).where(Book.id == target_request.book_id)).first()
        
        if not target_book or target_book.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The asset copy tied to this transaction does not exist or has been removed from circulation."
            )

        if target_book.owner_id != mock_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not the registered owner of the asset copy tied to this request."
            )

        # ───  OWNER'S ACTIONS ───
        
        # OPTION A: THE REJECTION FLOW
        if owner_input.action == HandshakeAction.REJECT:
            target_request.status = RequestStatus.REJECTED
            target_request.owner_notes = owner_input.owner_notes
            
            session.add(target_request)
            # Context manager automatically commits here and releases row locks safely
            return target_request

        # OPTION B: THE APPROVAL FLOW (THE CRITICAL STATE MUTATION)
        if owner_input.action == HandshakeAction.APPROVE:
            
            # Double Check: Ensure the book copy hasn't been lended to someone else via a separate request loop
            if not target_book.is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This book copy has already been lended out to another member."
                )

            # A. Flip the core physical book availability flag to False
            target_book.is_available = False
            session.add(target_book)

            # B. Finalize the target request tracking row status to APPROVED
            target_request.status = RequestStatus.APPROVED  # for the approved request ,update the request row in db
            target_request.owner_notes = owner_input.owner_notes
            session.add(target_request)

            # C. log the new loan entry, that just happend, in database
            new_ledger_entry = BorrowLedger(
                user_id=target_request.receiver_id,
                book_id=target_request.book_id
                # borrowed_at automatically falls back to current UTC via default_factory
            )
            session.add(new_ledger_entry)

            # D. BULK AUTO-CANCEL COMPETITORS: Clear out all other parallel applicants cleanly
            session.execute(
                update(BookRequest)
                .where(BookRequest.book_id == target_book.id)
                .where(BookRequest.status == RequestStatus.PENDING)
                # Filter out the request we just approved so we don't overwrite its status
                .where(BookRequest.id != target_request.id)
                .values(
                    status=RequestStatus.REJECTED,
                    owner_notes="System: This book copy has been lended out to another member."
                )
            )

            # Context manager closes the block, runs the automatic commit, and drops all row locks
            return target_request
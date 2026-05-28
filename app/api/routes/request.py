from fastapi import HTTPException,Depends,APIRouter,status
from sqlmodel import Session,select,update
from datetime import datetime,timezone
from app.db.session import get_session
from app.models.request import BookRequest,RequestStatus
from app.schemas.request import BookRequestCreate,BookRequestResponse
from app.schemas.action import HandshakeAction,RequestActionPayload
from app.models.book import Book
from app.models.user import LibraryUser
from app.models.ledger import BorrowLedger
from typing import Annotated
from app.api.dependencies import get_current_user
router=APIRouter(prefix="/request",tags=["Request Queue"])

@router.post("/",response_model=BookRequestResponse)
async def book_borrow_request(
    bookdata:BookRequestCreate,
    session:Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    

    target_book=session.exec(select(Book).where(Book.id==bookdata.book_id)).first()

    if not target_book or target_book.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested book  copy does not exist or has been permanently removed from circulation."
        )
    
    if not target_book.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This book copy is currently unavailable. It has already been lended out to another member."
        )
    
    if target_book.owner_id==current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot request to borrow an book copy that you already own."
        )
    
    existing_active_request=session.exec(
        select(BookRequest).where(
            BookRequest.receiver_id==current_user.id,
            BookRequest.book_id==bookdata.book_id,
            BookRequest.status==RequestStatus.PENDING
            )
    ).first()

    if existing_active_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active pending request for this book copy."
        )
    
    new_book_request=BookRequest(
        receiver_id=current_user.id,
        book_id=bookdata.book_id,
        status=RequestStatus.PENDING
    )

    try:
        session.add(new_book_request)
        session.commit()
        session.refresh(new_book_request)
        return new_book_request
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Database error."
        )
    
        
        


@router.post("/{request_id}/act",response_model=BookRequestResponse)
async def handle_custody_of_book(
    request_id:int,
    owner_input:RequestActionPayload,
    session:Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    query=select(BookRequest).where(BookRequest.id==request_id).with_for_update()

    target_request=session.exec(query).first()
    if not target_request:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The target borrow request record could not be found."
            )
        #   Ensure the request  hasn't already been handled
    if target_request.status != RequestStatus.PENDING:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This request has already been finalized with a status of '{target_request.status}'."
            )
    
    target_book=session.exec(select(Book).where(Book.id==target_request.book_id)).first()

    if not target_book or target_book.is_deleted:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The book copy tied to this request does not exist or has been removed from circulation."
            )

    if target_book.owner_id != current_user.id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Denied You are not the registered owner of the book copy this request."
            )
    

        #  OWNER'S ACTIONS :-
        
        #  THE REJECTION 
    if owner_input.action == HandshakeAction.REJECT:
        target_request.status = RequestStatus.REJECTED
        if(owner_input.owner_notes):  ## added to prevent null overriding
            target_request.owner_notes = owner_input.owner_notes
         
            
        session.add(target_request)
        session.commit()
        session.refresh(target_request) 
        return target_request

        #  THE APPROVAL [ vulnerable to race conditions and anomalies, handled accrodingly]
    if owner_input.action == HandshakeAction.APPROVE:
            #  Ensure the book copy hasn't been lended to someone else via a separate request loop
            if not target_book.is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This book copy has already been lended out to another member."
                )

            #  Flip book availability  to False
            target_book.is_available = False
            session.add(target_book)

            
            target_request.status = RequestStatus.APPROVED  # for the approved request ,update the request row in db
            if(owner_input.owner_notes):
                target_request.owner_notes = owner_input.owner_notes
            
            session.add(target_request)

            #  log the new loan entry, that just happend, in database
            new_ledger_entry = BorrowLedger(
                user_id=target_request.receiver_id,
                book_id=target_request.book_id
                # borrowed_at automatically falls back to current UTC via default_factory
            )
            session.add(new_ledger_entry)

            #   Clear out all other parallel applicants 
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
            session.commit()
            session.refresh(target_request)
            session.refresh(new_ledger_entry)
            
            return target_request
        


@router.get("/borrower", response_model=list[BookRequestResponse])
def get_my_submitted_requests(
    session: Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    """
    Retrieves all borrow requests submitted by the current logged-in user.
    Allows borrowers to track if their requests are pending, approved, or rejected.
    """
    
   

    
    query = select(BookRequest).where(BookRequest.receiver_id == current_user.id)
    results = session.exec(query).all()
    return results


@router.get("/owner", response_model=list[BookRequestResponse])
def get_my_incoming_owner_requests(
    session: Annotated[Session,Depends(get_session)],
    current_user:Annotated[LibraryUser,Depends(get_current_user)]
):
    """
    Retrieves all incoming pending requests for books owned by the current user.
    Provides the core data feed for the owner's dashboard evaluation loop.
    """
    

    #  Find requests where the  book's owner matches the logged-in user
    query = (
        select(BookRequest)
        .join(Book, BookRequest.book_id == Book.id)
        .where(Book.owner_id == current_user.id)
        # sort by oldest first so the owner can address early applicants fairly
        .order_by(BookRequest.created_at.asc())
    )
    
    results = session.exec(query).all()
    return results



@router.post("/{request_id}/return", response_model=BookRequestResponse)
async def initiate_book_return(
    request_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[LibraryUser, Depends(get_current_user)]
):
    """
    Borrower Action: Signals to the owner that the book has been physically returned.
    Transitions the state from APPROVED -> RETURN_PENDING.
    """
    
    #  Fetch the request with a lock
    query = select(BookRequest).where(BookRequest.id == request_id).with_for_update()
    target_request = session.exec(query).first()
    
    if not target_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The target borrow request record could not be found."
        )

    #  Only the borrower can initiate a return
    if target_request.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=" Denied. You are not the borrower for this request."
        )

    #   can only return a book that is actively borrowed i.e approved
    if target_request.status != RequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f" Cannot return a book with status '{target_request.status}'. It must be 'approved'."
        )

    
    target_request.status = RequestStatus.RETURN_PENDING
    session.add(target_request)
    session.commit()
    session.refresh(target_request)

    return target_request


@router.post("/{request_id}/confirm-return", response_model=BookRequestResponse)
async def confirm_book_return(
    request_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[LibraryUser, Depends(get_current_user)]
):
    """
    Owner Action: Confirms the physical book has been returned.
    Transitions the state from RETURN_PENDING -> RETURNED.
    Frees up the asset and officially closes the BorrowLedger.
    """
    
    #  Fetch the request with a lock
    query = select(BookRequest).where(BookRequest.id == request_id).with_for_update()
    target_request = session.exec(query).first()
    
    if not target_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The target borrow request record could not be found."
        )

    # Fetch the Book & Verify Identity
    target_book = session.exec(select(Book).where(Book.id == target_request.book_id)).first()
    
    if target_book.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Denied. Only the registered owner can confirm the return of this asset."
        )

    
    if target_request.status != RequestStatus.RETURN_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The borrower must initiate the return first. Current status: '{target_request.status}'."
        )

    # fetch the ledger entry corresponding to the request
    ledger_query = select(BorrowLedger).where(
        BorrowLedger.book_id == target_book.id,
        BorrowLedger.user_id == target_request.receiver_id,
        BorrowLedger.returned_at == None 
    )
    active_ledger = session.exec(ledger_query).first()

   
    
    # Update status
    target_request.status = RequestStatus.RETURNED
    
    # Free up the  Book
    target_book.is_available = True
    
    #  Close the  Ledger
    if active_ledger:
        active_ledger.returned_at = datetime.now(timezone.utc)
        session.add(active_ledger)

    session.add(target_request)
    session.add(target_book)
    session.commit()
    session.refresh(target_request)

    return  target_request
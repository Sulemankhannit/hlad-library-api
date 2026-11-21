import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlmodel import Session, select, func, col, or_, update

from app.db.session import get_session
from app.api.dependencies import get_current_admin_user
from app.models.user import LibraryUser
from app.models.book import Book
from app.models.request import BookRequest, RequestStatus
from app.models.ledger import BorrowLedger
from app.schemas.admin import (
    AdminStatsResponse,
    AdminBookResponse,
    AdminBookUpdate,
    AdminLoanResponse,
    AdminForceReturnPayload,
    AdminUserResponse,
    AdminTrustScoreUpdate,
    AdminUserStatusUpdate,
)
from app.schemas.book import BookDeleteResponse
from app.services.email import send_email

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)]
):
    """
    Returns platform-wide statistics for the library admin dashboard.
    """
    now = datetime.now(timezone.utc)

    total_books = session.exec(select(func.count(Book.id))).one()
    available_books = session.exec(
        select(func.count(Book.id)).where(Book.is_available == True, Book.is_deleted == False)
    ).one()
    borrowed_books = session.exec(
        select(func.count(Book.id)).where(Book.is_available == False, Book.is_deleted == False)
    ).one()
    deleted_books = session.exec(
        select(func.count(Book.id)).where(Book.is_deleted == True)
    ).one()

    active_loans = session.exec(
        select(func.count(BorrowLedger.id)).where(BorrowLedger.returned_at == None)
    ).one()
    overdue_loans = session.exec(
        select(func.count(BorrowLedger.id)).where(
            BorrowLedger.returned_at == None,
            BorrowLedger.due_date < now
        )
    ).one()

    total_users = session.exec(select(func.count(LibraryUser.id))).one()
    active_users = session.exec(
        select(func.count(LibraryUser.id)).where(LibraryUser.is_active == True)
    ).one()

    pending_requests = session.exec(
        select(func.count(BookRequest.id)).where(BookRequest.status == RequestStatus.PENDING)
    ).one()

    return AdminStatsResponse(
        total_books=total_books,
        available_books=available_books,
        borrowed_books=borrowed_books,
        deleted_books=deleted_books,
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        total_users=total_users,
        active_users=active_users,
        pending_requests=pending_requests,
    )


@router.get("/books", response_model=list[AdminBookResponse])
def get_admin_books(
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    include_deleted: bool = Query(default=True),
    is_available: bool | None = Query(default=None),
    search: str | None = Query(default=None),
):
    """
    Returns full book catalog with owner and active loan details for admin moderation.
    """
    query = select(Book)

    if not include_deleted:
        query = query.where(Book.is_deleted == False)

    if is_available is not None:
        query = query.where(Book.is_available == is_available)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Book.title).like(term),
                func.lower(Book.author).like(term)
            )
        )

    books = session.exec(query.offset(offset).limit(limit)).all()
    if not books:
        return []

    # Collect owner IDs and unavailable book IDs for batch metadata resolution
    owner_ids = list({b.owner_id for b in books})
    users_query = select(LibraryUser).where(col(LibraryUser.id).in_(owner_ids))
    owners_map = {u.id: u.email for u in session.exec(users_query).all()}

    unavailable_book_ids = [b.id for b in books if not b.is_available and not b.is_deleted]
    active_loans_map = {}
    if unavailable_book_ids:
        loan_stmt = (
            select(BorrowLedger, LibraryUser)
            .join(LibraryUser, BorrowLedger.user_id == LibraryUser.id)
            .where(
                col(BorrowLedger.book_id).in_(unavailable_book_ids),
                BorrowLedger.returned_at == None
            )
        )
        for loan, borrower in session.exec(loan_stmt).all():
            active_loans_map[loan.book_id] = {
                "borrower_id": borrower.id,
                "borrower_email": borrower.email,
                "due_date": loan.due_date,
            }

    response = []
    for b in books:
        loan_info = active_loans_map.get(b.id, {})
        response.append(
            AdminBookResponse(
                id=b.id,
                title=b.title,
                author=b.author,
                cover_url=b.cover_url,
                owner_id=b.owner_id,
                owner_email=owners_map.get(b.owner_id),
                is_available=b.is_available,
                is_deleted=b.is_deleted,
                current_borrower_id=loan_info.get("borrower_id"),
                current_borrower_email=loan_info.get("borrower_email"),
                current_loan_due_date=loan_info.get("due_date"),
            )
        )

    return response


@router.patch("/books/{book_id}", response_model=AdminBookResponse)
def update_book_admin(
    book_id: uuid.UUID,
    payload: AdminBookUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)]
):
    """
    Admin ability to update book details, replace cover, or restore/delete status.
    """
    target_book = session.exec(select(Book).where(Book.id == book_id).with_for_update()).first()
    if not target_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found."
        )

    if payload.title is not None:
        target_book.title = payload.title.strip()
    if payload.author is not None:
        target_book.author = payload.author.strip()
    if payload.cover_url is not None:
        target_book.cover_url = payload.cover_url
    if payload.is_available is not None:
        target_book.is_available = payload.is_available
    if payload.is_deleted is not None:
        target_book.is_deleted = payload.is_deleted

    session.add(target_book)
    session.commit()
    session.refresh(target_book)

    owner = session.get(LibraryUser, target_book.owner_id)

    return AdminBookResponse(
        id=target_book.id,
        title=target_book.title,
        author=target_book.author,
        cover_url=target_book.cover_url,
        owner_id=target_book.owner_id,
        owner_email=owner.email if owner else None,
        is_available=target_book.is_available,
        is_deleted=target_book.is_deleted,
    )


@router.delete("/books/{book_id}", response_model=BookDeleteResponse)
def force_delete_book_admin(
    book_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)]
):
    """
    Admin force-deletion of any book from active circulation.
    Cancels pending requests for this book and soft-deletes the row.
    """
    target_book = session.exec(select(Book).where(Book.id == book_id).with_for_update()).first()
    if not target_book or target_book.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The target book does not exist or has already been removed from circulation."
        )

    # Cancel any pending requests in the queue
    session.execute(
        update(BookRequest)
        .where(BookRequest.book_id == target_book.id)
        .where(BookRequest.status == RequestStatus.PENDING)
        .values(
            status=RequestStatus.CANCELED,
            owner_notes=f"System: Book copy has been removed from circulation by administrator ({current_admin.email})."
        )
    )

    target_book.is_deleted = True
    target_book.is_available = False
    session.add(target_book)
    session.commit()

    return BookDeleteResponse(
        message=f"Book '{target_book.title}' has been successfully removed by admin.",
        book_id=target_book.id
    )


@router.get("/loans", response_model=list[AdminLoanResponse])
def get_admin_loans(
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    status_filter: str = Query(default="active", pattern="^(active|overdue|returned|all)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """
    Global loan monitor across all members. Filterable by active, overdue, returned, or all.
    """
    now = datetime.now(timezone.utc)

    # Alias or join borrower and owner users
    # Query: BorrowLedger + Book + Borrower(LibraryUser) + Owner(LibraryUser)
    query = (
        select(BorrowLedger, Book)
        .join(Book, BorrowLedger.book_id == Book.id)
    )

    if status_filter == "active":
        query = query.where(BorrowLedger.returned_at == None)
    elif status_filter == "overdue":
        query = query.where(BorrowLedger.returned_at == None, BorrowLedger.due_date < now)
    elif status_filter == "returned":
        query = query.where(BorrowLedger.returned_at != None)

    # Sort: overdue loans first, then newest borrowings
    query = query.order_by(BorrowLedger.returned_at.asc(), BorrowLedger.due_date.asc())

    ledger_records = session.exec(query.offset(offset).limit(limit)).all()
    if not ledger_records:
        return []

    # Batch load users
    user_ids = set()
    for ledger, book in ledger_records:
        user_ids.add(ledger.user_id)
        user_ids.add(book.owner_id)

    users_stmt = select(LibraryUser).where(col(LibraryUser.id).in_(list(user_ids)))
    user_map = {u.id: u.email for u in session.exec(users_stmt).all()}

    results = []
    for ledger, book in ledger_records:
        is_overdue = ledger.returned_at is None and (
            ledger.due_date.replace(tzinfo=timezone.utc) < now if ledger.due_date.tzinfo is None else ledger.due_date < now
        )
        results.append(
            AdminLoanResponse(
                ledger_id=ledger.id,
                book_id=book.id,
                book_title=book.title,
                borrower_id=ledger.user_id,
                borrower_email=user_map.get(ledger.user_id, "Unknown"),
                owner_id=book.owner_id,
                owner_email=user_map.get(book.owner_id, "Unknown"),
                borrowed_at=ledger.borrowed_at,
                due_date=ledger.due_date,
                returned_at=ledger.returned_at,
                is_overdue=is_overdue,
            )
        )

    return results


@router.post("/loans/{ledger_id}/force-return", response_model=AdminLoanResponse)
def force_return_loan_admin(
    ledger_id: int,
    payload: AdminForceReturnPayload,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    bgtasks: BackgroundTasks
):
    """
    Administrative escape hatch: Force closes a stuck loan, marks the book available,
    and updates the associated BookRequest status to RETURNED.
    """
    now = datetime.now(timezone.utc)

    ledger_entry = session.exec(
        select(BorrowLedger).where(BorrowLedger.id == ledger_id).with_for_update()
    ).first()

    if not ledger_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan ledger record not found."
        )

    if ledger_entry.returned_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This loan has already been closed."
        )

    # 1. Close ledger entry
    ledger_entry.returned_at = now
    session.add(ledger_entry)

    # 2. Release the book
    target_book = session.exec(
        select(Book).where(Book.id == ledger_entry.book_id).with_for_update()
    ).first()

    if target_book:
        target_book.is_available = True
        session.add(target_book)

    # 3. Synchronize corresponding BookRequest if open
    active_request = session.exec(
        select(BookRequest)
        .where(
            BookRequest.book_id == ledger_entry.book_id,
            BookRequest.receiver_id == ledger_entry.user_id,
            col(BookRequest.status).in_([RequestStatus.APPROVED, RequestStatus.RETURN_PENDING])
        )
        .with_for_update()
    ).first()

    if active_request:
        active_request.status = RequestStatus.RETURNED
        active_request.owner_notes = f"Admin Intervention: {payload.reason}"
        session.add(active_request)

    session.commit()
    session.refresh(ledger_entry)
    if target_book:
        session.refresh(target_book)

    # Fetch user emails for response and notifications
    borrower = session.get(LibraryUser, ledger_entry.user_id)
    owner = session.get(LibraryUser, target_book.owner_id) if target_book else None

    # Asynchronous emails to notify parties of administrative resolution
    book_title = target_book.title if target_book else "Book"
    html_notice = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #d97706;">Library Loan Closed by Admin</h2>
            <p>An administrator has officially resolved and closed the loan for <strong>{book_title}</strong>.</p>
            <p><strong>Reason:</strong> {payload.reason}</p>
            <p>The book copy has been marked as available.</p>
            <br>
            <p><em>- HLAD Library Administration</em></p>
        </body>
    </html>
    """

    if borrower:
        bgtasks.add_task(
            send_email,
            user_id=borrower.id,
            subject=f"Notice: Loan closed by Admin for {book_title}",
            html_content=html_notice
        )
    if owner:
        bgtasks.add_task(
            send_email,
            user_id=owner.id,
            subject=f"Notice: Loan closed by Admin for {book_title}",
            html_content=html_notice
        )

    return AdminLoanResponse(
        ledger_id=ledger_entry.id,
        book_id=ledger_entry.book_id,
        book_title=book_title,
        borrower_id=ledger_entry.user_id,
        borrower_email=borrower.email if borrower else "Unknown",
        owner_id=target_book.owner_id if target_book else "Unknown",
        owner_email=owner.email if owner else "Unknown",
        borrowed_at=ledger_entry.borrowed_at,
        due_date=ledger_entry.due_date,
        returned_at=ledger_entry.returned_at,
        is_overdue=False,
    )


@router.get("/users", response_model=list[AdminUserResponse])
def get_admin_users(
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None),
):
    """
    List library users with their trust score, owned book count, and active loan count.
    """
    query = select(LibraryUser)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(func.lower(LibraryUser.email).like(term))

    users = session.exec(query.offset(offset).limit(limit)).all()
    if not users:
        return []

    user_ids = [u.id for u in users]

    # Count books owned per user
    books_count_stmt = (
        select(Book.owner_id, func.count(Book.id))
        .where(col(Book.owner_id).in_(user_ids), Book.is_deleted == False)
        .group_by(Book.owner_id)
    )
    books_map = dict(session.exec(books_count_stmt).all())

    # Count active borrowings per user
    loans_count_stmt = (
        select(BorrowLedger.user_id, func.count(BorrowLedger.id))
        .where(col(BorrowLedger.user_id).in_(user_ids), BorrowLedger.returned_at == None)
        .group_by(BorrowLedger.user_id)
    )
    loans_map = dict(session.exec(loans_count_stmt).all())

    results = []
    for u in users:
        results.append(
            AdminUserResponse(
                id=u.id,
                email=u.email,
                trust_score=u.trust_score,
                is_active=u.is_active,
                books_owned_count=books_map.get(u.id, 0),
                active_borrowed_count=loans_map.get(u.id, 0),
            )
        )

    return results


@router.patch("/users/{user_id}/trust-score", response_model=AdminUserResponse)
def adjust_user_trust_score(
    user_id: str,
    payload: AdminTrustScoreUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    bgtasks: BackgroundTasks
):
    """
    Adjusts user trust score (either delta +/- or explicit score) with reason and bounds [0, 100].
    """
    target_user = session.exec(
        select(LibraryUser).where(LibraryUser.id == user_id).with_for_update()
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library user not found."
        )

    if payload.score is not None:
        new_score = payload.score
    elif payload.delta is not None:
        new_score = target_user.trust_score + payload.delta
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'score' or 'delta' must be provided."
        )

    # Clamp between 0 and 100
    target_user.trust_score = max(0, min(100, new_score))
    target_user.version_id += 1

    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    # Count owned and active
    books_count = session.exec(
        select(func.count(Book.id)).where(Book.owner_id == target_user.id, Book.is_deleted == False)
    ).one()
    loans_count = session.exec(
        select(func.count(BorrowLedger.id)).where(BorrowLedger.user_id == target_user.id, BorrowLedger.returned_at == None)
    ).one()

    # Email notification
    html_notice = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Trust Score Update</h2>
            <p>Hello,</p>
            <p>Your HLAD Library Trust Score has been updated to <strong>{target_user.trust_score}</strong>.</p>
            <p><strong>Reason:</strong> {payload.reason}</p>
            <br>
            <p><em>- HLAD Automated System</em></p>
        </body>
    </html>
    """
    bgtasks.add_task(
        send_email,
        user_id=target_user.id,
        subject="HLAD Library: Trust Score Updated",
        html_content=html_notice
    )

    return AdminUserResponse(
        id=target_user.id,
        email=target_user.email,
        trust_score=target_user.trust_score,
        is_active=target_user.is_active,
        books_owned_count=books_count,
        active_borrowed_count=loans_count,
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
def update_user_status(
    user_id: str,
    payload: AdminUserStatusUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[LibraryUser, Depends(get_current_admin_user)],
    bgtasks: BackgroundTasks
):
    """
    Activate or deactivate user account in the library system.
    """
    target_user = session.exec(
        select(LibraryUser).where(LibraryUser.id == user_id).with_for_update()
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library user not found."
        )

    target_user.is_active = payload.is_active
    target_user.version_id += 1

    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    books_count = session.exec(
        select(func.count(Book.id)).where(Book.owner_id == target_user.id, Book.is_deleted == False)
    ).one()
    loans_count = session.exec(
        select(func.count(BorrowLedger.id)).where(BorrowLedger.user_id == target_user.id, BorrowLedger.returned_at == None)
    ).one()

    status_text = "Activated" if payload.is_active else "Suspended"
    html_notice = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Account Status: {status_text}</h2>
            <p>Hello,</p>
            <p>Your HLAD Library access has been <strong>{status_text}</strong>.</p>
            <p><strong>Reason:</strong> {payload.reason}</p>
            <br>
            <p><em>- HLAD Library Administration</em></p>
        </body>
    </html>
    """
    bgtasks.add_task(
        send_email,
        user_id=target_user.id,
        subject=f"HLAD Library: Account Access {status_text}",
        html_content=html_notice
    )

    return AdminUserResponse(
        id=target_user.id,
        email=target_user.email,
        trust_score=target_user.trust_score,
        is_active=target_user.is_active,
        books_owned_count=books_count,
        active_borrowed_count=loans_count,
    )

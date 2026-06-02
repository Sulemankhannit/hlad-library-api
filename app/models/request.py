from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, UniqueConstraint,Index,text
import uuid

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"
    EXPIRED = "expired"                # Triggered by Cron if owner ignores for 48 hrs
    RETURN_PENDING = "return_pending"  # Borrower says: "I physically gave it back"
    RETURNED = "returned"              # Owner says: "Confirmed, I have it"

class BookRequest(SQLModel, table=True):
    """
    Handles the P2P request queue mechanism. 
    Allows multiple members to request an book copy simultaneously.
    """
    __tablename__: str = "book_request"

    id: int | None = Field(default=None, primary_key=True)
    
    
    receiver_id: str = Field(foreign_key="library_user.id", nullable=False, index=True)
    
    
    book_id: uuid.UUID = Field(foreign_key="book.id", nullable=False, index=True)
    
    
    status: RequestStatus = Field(default=RequestStatus.PENDING, nullable=False, index=True)
    
    # Optional feedback/reasons note left by the book owner during handling
    owner_notes: str | None = Field(default=None, max_length=255, nullable=True)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # constraints  to prevent duplicate active requests and thus prevent anomalies
    # __table_args__ = (    # previously had used it to protect the db form request spams, but cuased a bottleneck , you cant ever succefully get the same book twice!! dumb!
    #     UniqueConstraint(
    #         "receiver_id", "book_id", "status", 
    #         name="uq_active_user_book_request"
    #     ),
    # )

    # We use an Index instead of a UniqueConstraint so we can pass a WHERE clause.
    __table_args__ = (
        Index(
            "uq_active_user_book_request", 
            "receiver_id", 
            "book_id", 
            unique=True, 
            #This tells Postgres to ONLY enforce uniqueness on active lifecycles, thus only the final states can be duplicates, but the active ones can never be duplicates
            postgresql_where=text("status IN ('PENDING', 'APPROVED', 'RETURN_PENDING')")
        ),
    )
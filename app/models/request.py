from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, UniqueConstraint
import uuid

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"

class BookRequest(SQLModel, table=True):
    """
    Handles the P2P request queue mechanism. 
    Allows multiple members to request an asset copy simultaneously.
    """
    __tablename__: str = "book_request"

    id: int | None = Field(default=None, primary_key=True)
    
    # Soft FK targeting our user shadow registry profile
    receiver_id: str = Field(foreign_key="library_user.id", nullable=False, index=True)
    
    # Structural link connecting to our physical book entry
    book_id: uuid.UUID = Field(foreign_key="book.id", nullable=False, index=True)
    
    # State flags tracking the progress of the custody negotiation
    status: RequestStatus = Field(default=RequestStatus.PENDING, nullable=False, index=True)
    
    # Optional feedback note left by the asset owner during handling
    owner_notes: str | None = Field(default=None, max_length=255, nullable=True)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Hard database-tier engine guardrails blocking duplicate active requests
    __table_args__ = (
        UniqueConstraint(
            "receiver_id", "book_id", "status", 
            name="uq_active_user_book_request"
        ),
    )
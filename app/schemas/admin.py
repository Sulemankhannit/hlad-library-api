from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid


class AdminStatsResponse(BaseModel):
    total_books: int
    available_books: int
    borrowed_books: int
    deleted_books: int
    active_loans: int
    overdue_loans: int
    total_users: int
    active_users: int
    pending_requests: int


class AdminBookResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None = None
    cover_url: str | None = None
    owner_id: str
    owner_email: str | None = None
    is_available: bool
    is_deleted: bool
    current_borrower_id: str | None = None
    current_borrower_email: str | None = None
    current_loan_due_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminBookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    cover_url: str | None = None
    is_available: bool | None = None
    is_deleted: bool | None = None


class AdminLoanResponse(BaseModel):
    ledger_id: int
    book_id: uuid.UUID
    book_title: str
    borrower_id: str
    borrower_email: str
    owner_id: str
    owner_email: str
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    is_overdue: bool

    model_config = ConfigDict(from_attributes=True)


class AdminForceReturnPayload(BaseModel):
    reason: str = Field(default="Admin intervention", min_length=1, max_length=255)


class AdminUserResponse(BaseModel):
    id: str
    email: str
    trust_score: int
    is_active: bool
    books_owned_count: int
    active_borrowed_count: int

    model_config = ConfigDict(from_attributes=True)


class AdminTrustScoreUpdate(BaseModel):
    delta: int | None = None
    score: int | None = None
    reason: str = Field(..., min_length=1, max_length=255)


class AdminUserStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(..., min_length=1, max_length=255)

import uuid
from sqlmodel import SQLModel,Field
from datetime import datetime,timezone,timedelta
from app.core.config import settings
class BorrowLedger(SQLModel,table=True):
    __tablename__:str="borrow_ledger"
    id:int|None=Field(default=None,primary_key=True)
    user_id:str=Field(
        foreign_key="library_user.id",
        nullable=False,
        index=True,

    )
    book_id:uuid.UUID=Field(
        foreign_key="book.id",
        nullable=False,
        index=True,
        
    )
    borrowed_at:datetime=Field(
        default_factory=lambda:datetime.now(timezone.utc),
        nullable=False
    )
    due_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=settings.LENDED_DAYS),
        nullable=False
    )
    returned_at:datetime|None=Field(
        default=None,
        nullable=True
    )
    
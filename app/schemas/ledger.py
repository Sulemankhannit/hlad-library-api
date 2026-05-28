from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

class ActiveLoanResponse(BaseModel):
    ledger_id: int
    book_id: uuid.UUID
    book_title: str
    borrowed_at: datetime
    due_date: datetime
    
    # If I am borrowing, this is the Owner's email.
    # If I am the owner, this is the Borrower's email.
    contact_email: str 
    
    model_config = ConfigDict(from_attributes=True)
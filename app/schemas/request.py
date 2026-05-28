from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid
from app.models.request import RequestStatus

class BookRequestCreate(BaseModel):
    
    book_id: uuid.UUID = Field(..., description="The unique UUID of the book copy being requested.")

   


class BookRequestResponse(BaseModel):
    
    id: int
    receiver_id: str
    book_id: uuid.UUID
    status: RequestStatus
    owner_notes: str | None = Field(default=None)
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
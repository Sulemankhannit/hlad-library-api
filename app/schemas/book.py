from pydantic import BaseModel,Field,ConfigDict
import uuid

class BookCreate(BaseModel):
    
    title:str=Field(...,min_length=1,max_length=255,description="Official title of the book")
    author: str | None = Field(default=None, max_length=255, description="Author of the book")
    cover_url: str | None = Field(default=None, max_length=500, description="Cover image URL")

class BookResponse(BaseModel):
    """
    Defines the exact structural serialization output returned to the student catalog.
    Prevents leaking internal system tracks or raw operational structures.
    """
    id:uuid.UUID
    title:str
    owner_id:str
    is_available:bool
    author: str | None
    cover_url: str | None = None

    model_config=ConfigDict(from_attributes=True)

class BookCoverUpdate(BaseModel):
    cover_url: str | None = Field(default=None, max_length=500, description="Cover image URL")

class BookDeleteResponse(BaseModel):
    message: str
    book_id: uuid.UUID


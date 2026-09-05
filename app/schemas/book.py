from pydantic import BaseModel,Field,ConfigDict
import uuid

class BookCreate(BaseModel):
    
    title:str=Field(...,min_length=1,max_length=255,description="Official title of the book")
    author: str | None = Field(default=None, max_length=255, description="Author of the book")

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

    model_config=ConfigDict(from_attributes=True)

import uuid
from sqlmodel import SQLModel,Field

class Book(SQLModel,table=True):
    __tablename__:str="book"
    id:uuid.UUID=Field(
        primary_key=True,
        index=True,
        default_factory=uuid.uuid4,
        nullable=False
    )
    title:str=Field(max_length=255,nullable=False,index=True)
    owner_id:str=Field(foreign_key="library_user.id",nullable=False,index=True)
    is_available:bool=Field(default=True,nullable=False)

    
    
    # True means the user "deleted" this book copy. It vanishes from search feeds,
    # but the row stays alive on disk to protect historical ledger IDs and request metrics.
    is_deleted: bool = Field(default=False, nullable=False, index=True)

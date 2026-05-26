from sqlmodel import SQLModel,Field

class LibraryUser(SQLModel,table=True):
    __tablename__:str="library_user"
    id:str=Field(primary_key=True,index=True,min_length=24,max_length=24,nullable=False)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    trust_score:int=Field(default=100,nullable=False,description="Reputation of the user,based on timely return etc")
    # The Soft Delete Flag. If a student graduates, we flip this to False.
    # as we wont be pyhsically deleting the logs, to have a historical record of each user
    is_active: bool = Field(default=True, nullable=False)
    version_id:int=Field(default=1,nullable=False) # to prevent race conditions

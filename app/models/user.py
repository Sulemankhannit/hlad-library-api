from sqlmodel import SQLModel,Field

class LibraryUser(SQLModel,table=True):
    __tablename__:str="library_user"
    id:str=Field(primary_key=True,index=True,min_length=24,max_length=24,nullable=False)
    trust_score:int=Field(default=100,nullable=False,description="Reputation of the user,based on timely return etc")


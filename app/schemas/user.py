from pydantic import BaseModel,Field,ConfigDict


class UserCreate(BaseModel):
    id:str=Field(...,min_length=24,max_length=24,description="The unique 24-character hexadecimal profile ID.")


class UserResponse(BaseModel):
    id:str
    trust_score:int

    model_config=ConfigDict(from_attributes=True)

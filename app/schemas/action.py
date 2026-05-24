from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class HandshakeAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"

class RequestActionPayload(BaseModel):
    """
    API gatekeeper validating the owner's decision on a pending book request.
    """
    action: HandshakeAction = Field(..., description="The explicit decision: 'approve' or 'reject'.")
    
    # Optional reason for the decision
    owner_notes: str | None = Field(default=None, max_length=255, description="Optional feedback or reasoning for the decision.")

    model_config = ConfigDict(use_enum_values=True)
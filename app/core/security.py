import jwt
from jwt.exceptions import DecodeError,InvalidTokenError,InvalidAlgorithmError,InvalidSignatureError,ExpiredSignatureError
from fastapi import HTTPException,status
from datetime import datetime,timezone,timedelta
from app.core.config import settings

def token_validation(token:str)->dict:
   
   try:
      payload=jwt.decode(token,settings.JWT_SECRET,algorithms=settings.JWT_ALGORITHM)

      exp_timestamp=payload.get("exp") # this is pure number, times in second
      if not exp_timestamp:
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security validation aborted. Token payload is missing required expiration ('exp') claim tracks."
            )
    
      currenttime=datetime.now(timezone.utc)  # current time in server clock,in utc
      token_exp_time_in_utc=datetime.fromtimestamp(exp_timestamp,tz=timezone.utc)

      if(token_exp_time_in_utc<currenttime):
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access denied. The current session has expired. Please re-authenticate."
            )
    
      return payload
   except ExpiredSignatureError: # required, even though we are  manually checking expiry above [depth in defense],but the check is below/after jwt.decode, which internally also checks expiry
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied. The current session has expired. Please re-authenticate"
        )
   except InvalidSignatureError:   ## required, beacause we are using shared jwt key, token is only valid if generated from our nextjs backend
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The signature hash does not match our validation key."
        )
   except DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed credentials payload structure submitted. Token structure cannot be parsed."
        )
    

def create_jwt_access_token(subject_id:str,email:str)->str: # generating the mock token, since nextjs backend is not yet ready

    expiry_time=datetime.now(timezone.utc)+timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload_to_encode={
        "sub":subject_id,
        "exp":int(expiry_time.timestamp()),
        "role":"student",
        "email":email
    }

    encoded_jwt=jwt.encode(
        payload_to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
        
   

    
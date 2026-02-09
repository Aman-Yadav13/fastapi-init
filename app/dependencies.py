from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import requests
from jose import jwt
from app.database import SessionLocal
from sqlalchemy.orm import Session
import os 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_google_certs = {}

def get_google_certs():
    global _google_certs
    if not _google_certs:
        response = requests.get(GOOGLE_CERTS_URL)
        _google_certs = response.json()
    return _google_certs

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        certs = get_google_certs()
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        
        for key in certs["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Unable to find appropriate key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer=["https://accounts.google.com", "accounts.google.com"]
        )

        email = payload.get("email")
        
        if not email.endswith("@saviynt.com"):
             raise HTTPException(status_code=403, detail="Invalid domain")

        # 5. (Optional) Sync with your DB
        # Check if user exists in your Postgres DB, if not, create them.
        # user = crud.get_user_by_email(db, email)
        # if not user:
        #     user = crud.create_user(db, email=email)
            
        return payload # Or return the user object from your DB

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError:
        raise HTTPException(status_code=401, detail="Incorrect claims, check audience/issuer")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
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
        
        # 1. Get the Key ID (kid)
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

        # 2. Decode WITHOUT checking issuer here (we check it manually below)
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            # issuer=...  <-- REMOVED THIS LINE (It causes the error)
            options={"verify_at_hash": False} # Added for safety with Google tokens
        )

        # 3. Manual Issuer Check (The Fix)
        # Google can sign tokens as either of these two URLs
        valid_issuers = ["https://accounts.google.com", "accounts.google.com"]
        if payload.get("iss") not in valid_issuers:
            raise HTTPException(status_code=401, detail="Invalid issuer")

        # 4. Domain Check
        email = payload.get("email")
        if not email or not email.endswith("@saviynt.com"):
             raise HTTPException(status_code=403, detail="Invalid domain: @saviynt.com only")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError as e:
        print(f"DEBUG: Claim Error: {e}") # Print error to console if it happens again
        raise HTTPException(status_code=401, detail="Incorrect claims, check audience/issuer")
    except Exception as e:
        print(f"DEBUG: Validation Error: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
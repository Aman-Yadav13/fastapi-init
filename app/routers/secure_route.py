from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/secure-data")
def read_secure_data(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['email']}, this is secure data."}

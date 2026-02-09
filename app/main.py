from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routers import assets

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SRE Stack Catalogue API")

origins = [
    "http://localhost:3000",  
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)

@app.get("/")
def read_root():
    return {"message": "SRE Backend is running!"}
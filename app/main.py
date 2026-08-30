
from fastapi import FastAPI
from app.routers import notes
from app.auth import router as auth_router


app = FastAPI(title= "Notes API")

@app.get("/")
def root():
    return {"message": "notes api is running"}

app.include_router(notes.router)
app.include_router(auth_router.router)

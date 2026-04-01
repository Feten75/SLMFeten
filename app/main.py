from fastapi import FastAPI
from app.presentation.routes import router

app = FastAPI(title="SLM Inference API")

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to SLM API"}
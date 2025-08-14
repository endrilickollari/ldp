from fastapi import FastAPI
from app.api import jobs
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Large Document Processing API",
    description="An API to process large Excel and PDF files using OCR and LLMs.",
    version="1.0.0"
)

app.include_router(jobs.router, prefix="/v1", tags=["Jobs"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Document Processing API"}

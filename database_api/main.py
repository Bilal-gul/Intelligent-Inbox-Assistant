import pyodbc

from fastapi import FastAPI, HTTPException
from models import EmailAnalysis
from crud import save_email_analysis, get_all_emails, get_email_by_id

app = FastAPI(
    title="Intelligent Inbox Assistant - Database API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Intelligent Inbox Assistant Database API",
        "status": "running"
    }


@app.post("/api/v1/analyses", status_code=201)
def create_analysis(data: EmailAnalysis):
    try:
        email_id = save_email_analysis(data)

        return {
            "message": "Email analysis saved successfully",
            "email_id": email_id,
            "source_email_id": data.source_email_id
        }

    except pyodbc.IntegrityError as error:
        if "2601" in str(error) or "2627" in str(error):
            raise HTTPException(
                status_code=409,
                detail="Email already exists or a unique constraint was violated"
            )

        raise HTTPException(
            status_code=500,
            detail="Database integrity error"
        )

    except pyodbc.Error:
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@app.get("/api/v1/emails")
def list_emails():
    try:
        return get_all_emails()

    except pyodbc.Error:
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )    

@app.get("/api/v1/emails/{email_id}")
def get_email_detail(email_id: int):
    try:
        email = get_email_by_id(email_id)

        if email is None:
            raise HTTPException(
                status_code=404,
                detail="Email not found"
            )

        return email

    except pyodbc.Error as error:
        print("SQL Server hatası:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

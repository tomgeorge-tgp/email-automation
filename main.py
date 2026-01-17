
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import shutil
import os
from services.excel_service import read_excel
from services.batch_sender import send_bulk_emails

app = FastAPI()

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

@app.post("/send-bulk-emails")
async def send_bulk_emails_api(
    template_file: UploadFile = File(...),
    excel_file: UploadFile = File(...)
):
    try:
        template_path = f"uploads/{template_file.filename}"
        excel_path = f"uploads/{excel_file.filename}"

        with open(template_path, "wb") as f:
            shutil.copyfileobj(template_file.file, f)

        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel_file.file, f)

        with open(template_path, "r", encoding="utf-8") as f:
            template_str = f.read()

        users_df = read_excel(excel_path)
        
        if len(users_df) == 0:
             return {
                "status": "completed",
                "total": 0,
                "results": [],
                "message": "No users found in Excel file."
            }

        results = await send_bulk_emails(
            template_str=template_str,
            users_df=users_df,
            concurrency=10,
            batch_size=50
        )

        return {
            "status": "completed",
            "total": len(users_df),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

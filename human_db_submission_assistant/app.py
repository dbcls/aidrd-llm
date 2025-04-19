import os
import json
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

from models import ApplicationData
from tasks import process_application_task
from utils import extract_data_from_pdf

# Load environment variables
load_dotenv(override=True)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create a logger instance
logger = logging.getLogger("app")

# Initialize FastAPI app
app = FastAPI(
    title="Human Database Submission Assistant",
    description="FastAPI implementation of the Human Database Submission Assistant workflow",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.post("/api/applications", status_code=202)
async def submit_application(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Submit application for processing"""
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)

    # Save uploaded file
    file_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Generate task ID
    task_id = f"task_{os.urandom(4).hex()}"

    try:
        # Extract data from PDF
        application_data = await extract_data_from_pdf(file_path, task_id)

        # Process application in background
        background_tasks.add_task(
            process_application_task, application_data, background_tasks, task_id
        )

        return {"task_id": task_id, "message": "Application submitted for processing"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing application: {str(e)}"
        )


@app.get("/api/applications/{task_id}")
async def get_application_status(task_id: str):
    """Get application processing status"""
    # Check if result file exists
    if os.path.exists(f"results/{task_id}.json"):
        with open(f"results/{task_id}.json", "r", encoding="utf-8") as f:
            return json.load(f)

    # Check if error file exists
    if os.path.exists(f"results/{task_id}_error.txt"):
        with open(f"results/{task_id}_error.txt", "r", encoding="utf-8") as f:
            error = f.read()
        raise HTTPException(
            status_code=500, detail=f"Error processing application: {error}"
        )

    # Still processing
    return {"status": "processing", "task_id": task_id}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

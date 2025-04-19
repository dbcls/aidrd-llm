import os
import json
import logging
import glob
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from pyngrok import ngrok

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
            result = json.load(f)
        return {"status": "completed", "result": result["assessment"]}

    # Check if error file exists
    if os.path.exists(f"results/{task_id}_error.txt"):
        with open(f"results/{task_id}_error.txt", "r", encoding="utf-8") as f:
            error = f.read()
        return {"status": "error", "error": error}

    # Still processing
    return {"status": "processing", "task_id": task_id}


@app.get("/api/applications")
async def get_all_task_ids():
    """Get all existing task IDs"""
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)

    # Get list of all task files in the results directory
    result_files = glob.glob("results/task_*.json")
    error_files = glob.glob("results/task_*_error.txt")

    task_ids = []
    task_statuses = []

    # Extract task IDs from result files
    for file_path in result_files:
        # Extract the task ID from the filename (remove .json extension)
        task_id = os.path.basename(file_path).replace(".json", "")
        task_ids.append(task_id)
        task_statuses.append("completed")

    # Extract task IDs from error files
    for file_path in error_files:
        # Extract the task ID from the filename (remove _error.txt suffix)
        task_id = os.path.basename(file_path).replace("_error.txt", "")
        if task_id not in task_ids:  # Avoid duplicates
            task_ids.append(task_id)
            task_statuses.append("error")

    # Create a list of task data objects
    tasks = [
        {"task_id": task_id, "status": status}
        for task_id, status in zip(task_ids, task_statuses)
    ]

    return {"tasks": tasks, "count": len(tasks)}


if __name__ == "__main__":
    # Get port from environment variable or use default
    ngrok_auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    port = int(os.getenv("PORT", 8000))
    if ngrok_auth_token:
        ngrok.set_auth_token(ngrok_auth_token)
        # Use ngrok to create a public URL
        ngrok_domain = os.getenv("NGROK_DOMAIN")
        if ngrok_domain:
            logger.info(f"Using custom ngrok domain: {ngrok_domain}")
            public_url = ngrok.connect(port, domain=ngrok_domain)
        else:
            public_url = ngrok.connect(port)
        logger.info(f"Public URL: {public_url}")
    else:
        logger.warning("NGROK_AUTH_TOKEN not set. Ngrok will not be used.")

    # Run the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

# Human Database Submission Assistant

FastAPI implementation of the Human Database Submission Assistant workflow, which automates the evaluation of human database access applications.

## Features

- PDF document extraction to parse application forms
- Web scraping integration with HumanDBS to retrieve dataset information
- CrossRef API integration for analyzing research publications
- AI-powered evaluation of application compatibility
- Asynchronous processing with background tasks

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` with your Azure OpenAI credentials
4. Run the application:
   ```
   uvicorn app:app --reload
   ```

## API Endpoints

### Submit Application
```
POST /api/applications
```
Upload a PDF application form for processing.

### Check Application Status
```
GET /api/applications/{task_id}
```
Check the status or result of a submitted application.

## Workflow

1. Application form is uploaded and processed to extract:
   - Dataset IDs
   - Related research DOIs
   - Research abstract
   - Research purpose

2. For each dataset ID:
   - Search HumanDBS website
   - Extract dataset information
   - Generate summary

3. For each research DOI:
   - Query CrossRef API
   - Extract publication details
   - Process research abstracts

4. Assessment:
   - Compare dataset characteristics with researcher's expertise
   - Evaluate compatibility between research purpose and requested data
   - Generate recommendation

## Architecture

The system uses:
- FastAPI for the web server
- Azure OpenAI for document understanding and evaluation
- Asynchronous processing for handling multiple requests
- Background tasks for long-running operations
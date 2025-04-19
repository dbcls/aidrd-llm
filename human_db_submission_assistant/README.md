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

See http://localhost:8000/docs for details on available endpoints.

## Testing

- First, install the required dependencies for development and testing:

  ```
  pip install -r requirements-dev.txt
  ```

- To run the tests, use the following command:

  ```
  docker compose exec api pytest test_app.py::TestAPIEndpoints::test_submit_application -v
  ```

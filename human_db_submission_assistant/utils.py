import logging
from langchain_community.document_loaders import PyPDFLoader
from models import ApplicationData
from services.llm_service import extract_output_from_openai

logger = logging.getLogger("pdf_utils")


async def extract_data_from_pdf(file_path: str, task_id: str = None) -> ApplicationData:
    """Extract application data from PDF file"""
    # Load PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()

    # Combine pages content
    pdf_content = "\n".join([page.page_content for page in pages])

    # Extract data using OpenAI
    prompt = f"Extract the following information from this application form:\n\n{pdf_content}\n\n"
    prompt += "1. Application ID\n"
    prompt += "2. List of dataset IDs mentioned in the application\n"
    prompt += "3. List of DOIs for related published studies\n"
    prompt += "4. Research abstract section\n"
    prompt += "5. Research purpose section\n"

    return await extract_output_from_openai(prompt, ApplicationData, task_id=task_id)

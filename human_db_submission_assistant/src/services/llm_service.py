import os
import logging
from typing import Type
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure logger
logger = logging.getLogger("llm_service")

# Initialize LLM
llm = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_MODEL"],
    temperature=0.7,
    max_tokens=2000,
)


async def query_openai(
    prompt: str, system_message: str = None, task_id: str = None
) -> str:
    """Query OpenAI API"""
    # Log the prompt
    if task_id:
        task_logger = logging.getLogger(f"app.task.{task_id}")
        task_logger.info(
            f"System Message: {system_message}"
            if system_message
            else "No system message"
        )
        task_logger.info(f"User Prompt: {prompt}")

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    return llm.invoke(messages).content


async def extract_output_from_openai(
    prompt: str,
    output_model: Type[BaseModel],
    system_message: str = None,
    task_id: str = None,
) -> BaseModel:
    """Extract structured output from OpenAI"""
    # Log the prompt
    if task_id:
        task_logger = logging.getLogger(f"app.task.{task_id}")
        task_logger.info(
            f"System Message: {system_message}"
            if system_message
            else "No system message"
        )
        task_logger.info(f"User Prompt: {prompt}")

    messages = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))

    # Query LangChain with structured output
    return llm.with_structured_output(output_model).invoke(messages)


async def suggest_icd10_code(prompt: str, task_id: str = None) -> str:
    """Suggest ICD-10 code based on the prompt"""
    from src.models import ICD10Suggestion

    result = await extract_output_from_openai(prompt, ICD10Suggestion, task_id=task_id)
    if result:
        return f"{result.icd10_code} {result.title}"
    return None

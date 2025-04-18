import os
import json
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uvicorn
from bs4 import BeautifulSoup
from langchain.document_loaders import PyPDFLoader

from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv(override=True)


llm = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_MODEL"],
    temperature=0.7,
    max_tokens=2000,
)


# Initialize FastAPI app
app = FastAPI(
    title="Human Database Submission Assistant",
    description="FastAPI implementation of the Human Database Submission Assistant workflow",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ApplicationData(BaseModel):
    dataset_id_list: List[str] = Field(..., description="List of dataset IDs in the application")
    related_studies_published: List[str] = Field(..., description="List of DOIs for related published studies")
    research_abstract: str = Field(..., description="Abstract of the research using the requested data")
    research_purpose: str = Field(..., description="Purpose of the requested data usage")

class DatasetInfo(BaseModel):
    research_url: str = Field(..., description="URL of the human dataset")
    dataset_id: str = Field(..., description="ID of the dataset")

class ResearchInfo(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    source: str = Field(..., description="Source of the publication")
    doi: str = Field(..., description="DOI of the paper")
    contributions: Dict[str, str] = Field(..., description="Contributions in Japanese and English")
    abstract: str = Field(..., description="Abstract of the paper")

class AssessmentResult(BaseModel):
    dataset_summary: List[Dict[str, Any]] = Field(..., description="Summary of the datasets")
    related_studies: List[str] = Field(..., description="Summary of related studies")
    assessment: str = Field(..., description="Assessment of the application compatibility")

# Helper Functions
async def query_openai(prompt: str, system_message: str = None):
    """Query OpenAI API with retry logic"""
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    return llm.invoke(messages).content

async def extract_output_from_openai(prompt: str, output_model: BaseModel, system_message: str = None):
    # Initialize LangChain AzureChatOpenAI client
    # Define JSON schema parser
    # Build prompt template
    messages = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))

    # Query LangChain with structured output
    return llm.with_structured_output(output_model).invoke(messages)

async def extract_data_from_pdf(file_path: str) -> ApplicationData:
    """Extract application data from PDF file"""
    # Load PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    
    # Combine pages content
    pdf_content = "\n".join([page.page_content for page in pages])
    
    # Extract data using OpenAI
    prompt = f"Extract the following information from this application form:\n\n{pdf_content}\n\n"
    prompt += "1. List of dataset IDs mentioned in the application\n"
    prompt += "2. List of DOIs for related published studies\n"
    prompt += "3. Research abstract section\n"
    prompt += "4. Research purpose section"
    
    return await extract_output_from_openai(prompt, ApplicationData)

async def get_dataset_info(dataset_id: str) -> Optional[DatasetInfo]:
    """Get dataset information from HumandBS website"""
    search_url = f"https://humandbs.dbcls.jp/component/search/?searchword={dataset_id}&searchphrase=all"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as response:
            if response.status != 200:
                return None
            
            html = await response.text()
            
            # Extract human data URL using OpenAI
            prompt = f"Extract the URL of the human dataset from this search result. It should be in the form of 'https://humandbs.dbcls.jp/hum****-v**'. If you find multiple candidates, output the result with the largest version number.\n\n{html}"

            class ExtractionResult(BaseModel):
                human_data_url: str = Field(..., description="A URL of human dataset included in the given search result.")
            
            result = await extract_output_from_openai(prompt, ExtractionResult)
            human_data_url = result.human_data_url if result else None
            
            if not human_data_url or not human_data_url.startswith("https://humandbs.dbcls.jp/hum"):
                return None
                
            return DatasetInfo(research_url=human_data_url.strip(), dataset_id=dataset_id)

async def get_research_info(doi: str) -> Optional[ResearchInfo]:
    """Get research information from CrossRef API"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.crossref.org/works/{doi}") as response:
            if response.status != 200:
                return None
            
            data = await response.json()
            paper_info = data.get("message", {})
            
            # Extract paper information using OpenAI
            prompt = f"Extract key information from this academic paper data:\n\n{json.dumps(paper_info)}"
            
            system_message = "Extract information about an academic paper in the specified format."
            
            try:
                return await extract_output_from_openai(prompt, ResearchInfo, system_message)

            except Exception as e:
                print(f"Error extracting research info: {e}")
                return None

async def summarize_dataset(url: str) -> str:
    """Summarize dataset information from its URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return "データセット情報の取得に失敗しました。"
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Summarize dataset using OpenAI
            prompt = f"以下のデータセットの説明文からデータセットの要約を日本語で作成してください：\n\n{soup.get_text()}"
            
            system_message = """
            データセットの説明文を与えるので、データセットの要約を日本語で作成してください。要約のフォーマットは以下を参考にしてください：

            ◆hum0197.v18
            ●BBJの日本人集団腸内細菌叢のメタゲノムシークエンスデータ
            JGAS000205 / JGAD000290 / 95名
            JGAS000260 / JGAD000363 / 103名
            """
            
            summary = await query_openai(prompt, system_message)
            return summary

async def assess_application(
    dataset_summaries: List[Dict[str, Any]],
    research_summaries: List[str],
    research_abstract: str,
    research_purpose: str
) -> str:
    """Assess if the application meets the requirements"""
    prompt = f"""
    # 利用するデータセット情報の要約
    {json.dumps(dataset_summaries, ensure_ascii=False, indent=2)}

    # 研究者のこれまでの研究の概要
    {json.dumps(research_summaries, ensure_ascii=False, indent=2)}

    # 利用を希望するデータを使用した研究の概要
    {research_abstract}

    # 利用を希望するデータと利用目的
    {research_purpose}
    """
    
    system_message = """
    # タスク説明
    「利用するデータセット情報の要約」、「研究者のこれまでの研究の概要」、
    「利用を希望するデータを使用した研究の概要」、「利用を希望するデータと利用目的」を参照して、
    利用者が利用要件を満たしているかを判定し、根拠とともに回答してください。判定軸は以下のものとします。

    * データセットの扱う疾患と、研究者が扱ったことのある疾患の間の類似度
    * サンプル内の分子データに記載されている解析手法と、研究者が扱ったことのある解析手法の間の類似度
    """
    
    assessment = await query_openai(prompt, system_message)
    return assessment

# Background task to process application
async def process_application_task(
    application_data: ApplicationData,
    background_tasks: BackgroundTasks,
    task_id: str
):
    """Process application data in background"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        log_file_path = f"logs/{task_id}.log"

        # Open log file for writing
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write("Starting application processing...\n")

            # Get dataset information
            dataset_info_tasks = [get_dataset_info(dataset_id) for dataset_id in application_data.dataset_id_list]
            dataset_info_results = await asyncio.gather(*dataset_info_tasks)
            dataset_info_list = [di for di in dataset_info_results if di]
            log_file.write(f"Dataset information retrieved: {dataset_info_list}\n")

            # Group datasets by research URL
            dataset_mapping = {}
            for info in dataset_info_list:
                if info.research_url not in dataset_mapping:
                    dataset_mapping[info.research_url] = []
                dataset_mapping[info.research_url].append(info.dataset_id)

            # Get dataset summaries
            dataset_summary_tasks = []
            for url, dataset_ids in dataset_mapping.items():
                dataset_summary_tasks.append(summarize_dataset(url))
            dataset_summaries = await asyncio.gather(*dataset_summary_tasks)
            log_file.write(f"Dataset summaries retrieved: {dataset_summaries}\n")

            # Get research information
            research_info_tasks = [get_research_info(doi) for doi in application_data.related_studies_published]
            research_info_results = await asyncio.gather(*research_info_tasks)
            research_info_list = [ri for ri in research_info_results if ri]
            log_file.write(f"Research information retrieved: {research_info_list}\n")

            # Extract research abstracts
            research_abstracts = [ri.abstract for ri in research_info_list if ri.abstract]

            # Assess application
            assessment = await assess_application(
                dataset_summaries,
                research_abstracts,
                application_data.research_abstract,
                application_data.research_purpose
            )
            log_file.write(f"Assessment completed: {assessment}\n")

            # Store result
            result = {
                "dataset_summary": [
                    {"research_url": url, "dataset_id_list": ids, "summary": summary}
                    for (url, ids), summary in zip(dataset_mapping.items(), dataset_summaries)
                ],
                "related_studies": research_abstracts,
                "assessment": assessment
            }

            # Save result to a file or database
            with open(f"results/{task_id}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            log_file.write("Result saved successfully.\n")

    except Exception as e:
        # Log error
        error_message = f"Error processing application: {e}"
        print(error_message)
        with open(f"results/{task_id}_error.txt", "w", encoding="utf-8") as f:
            f.write(str(e))
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(error_message + "\n")

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
        application_data = await extract_data_from_pdf(file_path)
        
        # Process application in background
        background_tasks.add_task(
            process_application_task,
            application_data,
            background_tasks,
            task_id
        )
        
        return {"task_id": task_id, "message": "Application submitted for processing"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing application: {str(e)}")

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
        raise HTTPException(status_code=500, detail=f"Error processing application: {error}")

    # Still processing
    return {"status": "processing", "task_id": task_id}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
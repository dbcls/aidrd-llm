import os
import json
import aiohttp
import asyncio
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uvicorn
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from jinja2 import Environment, FileSystemLoader
import traceback

# Load environment variables
load_dotenv(override=True)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger instance
logger = logging.getLogger("app")

template_dir = "templates"
template_file = "report.jinja2"
env = Environment(loader=FileSystemLoader(template_dir))
report_template = env.get_template("report.jinja2")


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
    application_id: str = Field(..., description="ID of the application")
    dataset_id_list: List[str] = Field(..., description="List of dataset IDs in the application")
    related_studies_published: List[str] = Field(..., description="List of DOIs for related published studies")
    research_abstract: str = Field(..., description="Abstract of the research using the requested data in Japanese")
    research_purpose: str = Field(..., description="Purpose of the requested data usage in Japanese")

class DatasetInfo(BaseModel):
    research_url: str = Field(..., description="URL of the human dataset")
    dataset_id: str = Field(..., description="ID of the dataset")

class DatasetAnalysisResult(BaseModel):
    id: str = Field(..., description="ID of the dataset")
    icd10: str = Field(..., description="ICD-10 code related to the dataset. If not available, it will be empty.")
    purpose_similarity: bool = Field(..., description="Similarity of the dataset purpose to the research purpose")
    paper_similarity: bool = Field(..., description="Similarity of the dataset paper to the research paper")
    analysis_method_similarity: str = Field(..., description="Similarity of the analysis method to the research analysis")
    analysis_method_similarity_reason: str = Field(..., description="Reason for the analysis method similarity")
    analysis_method_details: str = Field(..., description="Details of the analysis method used in the research")
    url: str = Field(..., description="URL of the dataset")

class ResearchInfo(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    doi: str = Field(..., description="DOI of the paper")
    authors: List[str] = Field(..., description="List of authors of the paper")
    abstract: str = Field(..., description="Abstract of the paper")
    url: str = Field(..., description="URL of the paper")
    icd10: str = Field(..., description="ICD-10 code related to the research. If not available, it will be empty.")

class AssessmentResult(BaseModel):
    dataset_summary: List[Dict[str, Any]] = Field(..., description="Summary of the datasets")
    related_studies: List[str] = Field(..., description="Summary of related studies")
    assessment: str = Field(..., description="Assessment of the application compatibility")

# Helper Functions
async def query_openai(prompt: str, system_message: str = None, task_id: str = None):
    """Query OpenAI API with retry logic"""
    # Log the prompt
    if task_id:
        task_logger = logging.getLogger(f"app.task.{task_id}")
        task_logger.info(f"System Message: {system_message}" if system_message else "No system message")
        task_logger.info(f"User Prompt: {prompt}")
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    return llm.invoke(messages).content

async def extract_output_from_openai(prompt: str, output_model: BaseModel, system_message: str = None, task_id: str = None):
    # Log the prompt
    if task_id:
        task_logger = logging.getLogger(f"app.task.{task_id}")
        task_logger.info(f"System Message: {system_message}" if system_message else "No system message")
        task_logger.info(f"User Prompt: {prompt}")
    
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
    prompt += "1. Application ID\n"
    prompt += "2. List of dataset IDs mentioned in the application\n"
    prompt += "3. List of DOIs for related published studies\n"
    prompt += "4. Research abstract section\n"
    
    return await extract_output_from_openai(prompt, ApplicationData)

async def get_dataset_info(dataset_id: str, task_id: str = None) -> Optional[DatasetInfo]:
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
            
            result = await extract_output_from_openai(prompt, ExtractionResult, task_id=task_id)
            human_data_url = result.human_data_url if result else None
            
            if not human_data_url or not human_data_url.startswith("https://humandbs.dbcls.jp/hum"):
                return None
                
            return DatasetInfo(research_url=human_data_url.strip(), dataset_id=dataset_id)

async def get_research_info(doi: str, task_id: str = None) -> Optional[ResearchInfo]:
    """Get research information from CrossRef API"""
    paper_info = await fetch_from_doi(doi)
    if not paper_info:
        return None
    title = paper_info.get("title", "")
    authors = paper_info.get("authors", [])
    abstract = paper_info.get("abstract", "")

    icd_10 = await suggest_icd10_code("""# タスク説明
以下の論文情報をもとに、その論文に対応するICD-10コードを提案してください。
特定の疾病に対して言及していない場合は、空文字列を返してください。

# タイトル
{title}
                                      
# 概要
{abstract}                                
""")

    research_info = ResearchInfo(
        title=title,
        doi=doi,
        authors=authors,
        abstract=abstract,
        url=paper_info.get("url", ""),
        icd10=icd_10 if icd_10 else ""
    )
    return research_info

async def analyze_dataset(url: str, dataset_ids: List[str],  purpose_icd10: str, analysis_method: str, task_id: str = None) -> DatasetAnalysisResult:
    """Summarize dataset information from its URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return "データセット情報の取得に失敗しました。"
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            class DataSetSummary(BaseModel):
                id: str = Field(..., description="ID of the dataset")
                description: str = Field(..., description="Description of the dataset")
                icd10_code: str = Field(..., description="ICD-10 code related to the dataset")

            class ExtractionResult(BaseModel):
                dataset_summaries: List[DataSetSummary] = Field(..., description="List of dataset summaries")
                analysis_method: str = Field(..., description="Analysis method used in the research")
            
            # Summarize dataset using OpenAI
            prompt = f"""# データセットIDのリスト
{dataset_ids}

# 研究の説明
{soup.get_text()}"""
            
            system_message = """データセットのIDのリストと研究の説明を与えるので、研究の説明から、データセットごとの内容説明と関連するICD10コード、研究において用いられた解析手法をまとめてください。"""
            result = await extract_output_from_openai(prompt, ExtractionResult, system_message=system_message, task_id=task_id)

            class Simirarity(BaseModel):
                analysis_method_similarity: str = Field(..., description="Similarity of the analysis method to the research analysis. One of '低', '中', '高'.")
                analysis_method_similarity_reason: str = Field(..., description="Reason for the analysis method similarity.")
            prompt = f"""# タスク説明
今から行おうとしている研究の概要と、これまでに使用した解析手法を与えるので、どの程度その解析手法が研究内容に合致しているかを評価して「低」、「中」、「高」の3段階で評価してください。判断の理由も記載してください。

# 行おうとしている研究の概要
{analysis_method}

# これまでに使用した解析手法
{result.analysis_method}"""

            similarity_result = await extract_output_from_openai(prompt, Simirarity, task_id=task_id)
            dataset_analysis_result_list = []
            if result:
                for summary in result.dataset_summaries:

                    dataset_analysis_result_list.append(DatasetAnalysisResult(
                        id=summary.id,
                        icd10=summary.icd10_code,
                        purpose_similarity=check_similarity_of_icd10(purpose_icd10, summary.icd10_code),  # Placeholder
                        paper_similarity=True,   
                        analysis_method_details=result.analysis_method,
                        analysis_method_similarity=similarity_result.analysis_method_similarity,
                        analysis_method_similarity_reason=similarity_result.analysis_method_similarity_reason,
                        url=url
                    ))
            else:
                return None
            return dataset_analysis_result_list

async def suggest_icd10_code(prompt:str) -> str:
    """Suggest ICD-10 code based on the prompt"""
    class ICD10Suggestion(BaseModel):
        icd10_code: str = Field(..., description="ICD-10 code suggested by OpenAI")
        title: str = Field(..., description="Title of the ICD-10 code in Japanese")
    
    result = await extract_output_from_openai(prompt, ICD10Suggestion)
    if result:
        return f"{result.icd10_code} {result.title}"
    return None


async def create_assessment_report(
    application_id: str,
    abstract_icd10: str,
    dataset_info_list: List[DatasetAnalysisResult],
    research_info_list: List[ResearchInfo],
    research_abstract: str,
    task_id: str = None
) -> str:
    """Create report to assess if the application meets the requirements"""


    # Prepare data for the template
    template_data = {
        "application_id": application_id,
        "abstract": research_abstract,
        "abstract_icd10": abstract_icd10,
        "papers": research_info_list,
        "datasets": dataset_info_list,
    }

    # Render the template
    report = report_template.render(template_data)

    # Save the report to a file
    report_path = f"results/{task_id}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report


async def fetch_from_doi(doi: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.crossref.org/works/{doi}/transform/application/vnd.citationstyles.csl+json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                content_type = resp.content_type
                if 'application/octet-stream' in content_type:
                    raw_data = await resp.read()
                    data = json.loads(raw_data.decode('utf-8'))
                else:
                    data = await resp.json()
                
                title = data.get("title", "")

                # 著者リスト
                authors = []
                for a in data.get("author", []):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    full_name = " ".join(filter(None, [given, family]))
                    if full_name:
                        authors.append(full_name)

                # abstract フィールド（存在しないケースもある）
                abstract = data.get("abstract")
                if not abstract:
                    abstract = await fetch_abstract_europepmc(doi)

                url = ""
                if "link" in data:
                    for link in data["link"]:
                        url = link.get("URL", "")
                        if link.get("content-type") == "text/html": # HTMLリンクを優先
                            break
                        

                return {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "url": url
                }
            else:
                logging.error(f"Error fetching DOI data: {resp.status}")
                return None

async def fetch_abstract_europepmc(doi: str) -> Optional[str]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": f"DOI:{doi}",
        "format": "json",
        "resultType": "core"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                records = (await resp.json()).get("resultList", {}).get("result", [])
                if records:
                    return records[0].get("abstractText")
            return None


def check_similarity_of_icd10(a:str, b:str) -> bool:
    """Check if two ICD-10 codes are similar"""
    if b.startswith(a) or a.startswith(b): 
        # どちらかがどちらかを含む場合は類似と判定
        return True
    if b[:-1] == a[:-1]:
        # 末尾の1文字を除いて同じ場合は類似と判定
        return True
    return False
    


# Background task to process application
async def process_application_task(
    application_data: ApplicationData,
    background_tasks: BackgroundTasks,
    task_id: str
):
    """Process application data in background"""
    try:
        # Set up file handler for this task
        os.makedirs("logs", exist_ok=True)
        task_logger = logging.getLogger(f"app.task.{task_id}")
        task_logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(f"logs/{task_id}.log")
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the handler to logger
        task_logger.addHandler(file_handler)
        
        # Start logging
        task_logger.info("Starting application processing...")


        abstract_icd10 = await suggest_icd10_code(f"""# タスク説明
以下の研究概要をもとに、その研究概要に対応するICD-10コードを提案してください。

# 研究概要
{application_data.research_abstract}""")
        task_logger.info(f"ICD-10 code suggested for abstract: {abstract_icd10}")
        
        application_data.dataset_id_list = application_data.dataset_id_list[:5] # Limit to first dataset for testing

        # Get dataset information
        dataset_info_tasks = [get_dataset_info(dataset_id, task_id=task_id) for dataset_id in application_data.dataset_id_list]
        dataset_info_results = await asyncio.gather(*dataset_info_tasks)
        dataset_info_list = [di for di in dataset_info_results if di]
        task_logger.info(f"Dataset information retrieved: {dataset_info_list}")

        # Group datasets by research URL
        dataset_mapping = {}
        for info in dataset_info_list:
            if info.research_url not in dataset_mapping:
                dataset_mapping[info.research_url] = []
            dataset_mapping[info.research_url].append(info.dataset_id)

        # Get dataset summaries
        dataset_analysis_tasks = []
        for url, dataset_ids in dataset_mapping.items():
            dataset_analysis_tasks.append(analyze_dataset(url, dataset_ids, abstract_icd10, application_data.research_abstract, task_id=task_id))
        dataset_analysis_result = await asyncio.gather(*dataset_analysis_tasks)
        dataset_analysis_result = [summary for sublist in dataset_analysis_result for summary in sublist] # Flatten the list
        task_logger.info(f"Dataset analysis_result retrieved: {dataset_analysis_result}")

        # Get research information
        research_info_tasks = [get_research_info(doi, task_id=task_id) for doi in application_data.related_studies_published]
        research_info_results = await asyncio.gather(*research_info_tasks)
        research_info_list = [ri for ri in research_info_results if ri]
        task_logger.info(f"Research information retrieved: {research_info_list}")

        # Assess application
        assessment = await create_assessment_report(
            application_data.application_id,
            abstract_icd10,
            dataset_analysis_result,
            research_info_list,
            research_abstract=application_data.research_abstract,
            task_id=task_id
        )
        task_logger.info(f"Assessment completed: {assessment}")

        # Store result
        result = {
            "assessment": assessment
        }

        # Save result to a file or database
        with open(f"results/{task_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        task_logger.info("Result saved successfully.")
        
        # Remove file handler to avoid resource leaks
        task_logger.removeHandler(file_handler)
        file_handler.close()

    except Exception as e:
        # Log error
        error_stacktrace = traceback.format_exc()
        with open(f"results/{task_id}_error.txt", "w", encoding="utf-8") as f:
            f.write(error_stacktrace)
        if 'task_logger' in locals():
            task_logger.error(error_stacktrace)
            if 'file_handler' in locals():
                task_logger.removeHandler(file_handler)
                file_handler.close()
        else:
            logger.error(error_stacktrace)

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
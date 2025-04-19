# models.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ApplicationData(BaseModel):
    application_id: str = Field(..., description="ID of the application")
    dataset_id_list: List[str] = Field(
        ..., description="List of dataset IDs in the application"
    )
    related_studies_published: List[str] = Field(
        ..., description="List of DOIs for related published studies"
    )
    research_abstract: str = Field(
        ..., description="Abstract of the research using the requested data in Japanese"
    )
    research_purpose: str = Field(
        ..., description="Purpose of the requested data usage in Japanese"
    )


class DatasetInfo(BaseModel):
    research_url: str = Field(..., description="URL of the human dataset")
    dataset_id: str = Field(..., description="ID of the dataset")


class DatasetAnalysisResult(BaseModel):
    id: str = Field(..., description="ID of the dataset")
    icd10: str = Field(
        ...,
        description="ICD-10 code related to the dataset. If not available, it will be empty.",
    )
    purpose_similarity: bool = Field(
        ..., description="Similarity of the dataset purpose to the research purpose"
    )
    paper_similarity: bool = Field(
        ..., description="Similarity of the dataset paper to the research paper"
    )
    analysis_method_similarity: str = Field(
        ..., description="Similarity of the analysis method to the research analysis"
    )
    analysis_method_similarity_reason: str = Field(
        ..., description="Reason for the analysis method similarity"
    )
    analysis_method_details: str = Field(
        ..., description="Details of the analysis method used in the research"
    )
    url: str = Field(..., description="URL of the dataset")


class ResearchInfo(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    doi: str = Field(..., description="DOI of the paper")
    authors: List[str] = Field(..., description="List of authors of the paper")
    abstract: str = Field(..., description="Abstract of the paper")
    url: str = Field(..., description="URL of the paper")
    icd10: str = Field(
        ...,
        description="ICD-10 code related to the research. If not available, it will be empty.",
    )


class AssessmentResult(BaseModel):
    dataset_summary: List[Dict[str, Any]] = Field(
        ..., description="Summary of the datasets"
    )
    related_studies: List[str] = Field(..., description="Summary of related studies")
    assessment: str = Field(
        ..., description="Assessment of the application compatibility"
    )


# Models for LLM structured output
class DataSetSummary(BaseModel):
    id: str = Field(..., description="ID of the dataset")
    description: str = Field(..., description="Description of the dataset")
    icd10_code: str = Field(..., description="ICD-10 code related to the dataset")


class DatasetExtractionResult(BaseModel):
    dataset_summaries: List[DataSetSummary] = Field(
        ..., description="List of dataset summaries"
    )
    analysis_method: str = Field(
        ..., description="Analysis method used in the research"
    )


class Similarity(BaseModel):
    analysis_method_similarity: str = Field(
        ...,
        description="Similarity of the analysis method to the research analysis. One of '低', '中', '高'.",
    )
    analysis_method_similarity_reason: str = Field(
        ..., description="Reason for the analysis method similarity."
    )


class ICD10Suggestion(BaseModel):
    icd10_code: str = Field(..., description="ICD-10 code suggested by OpenAI")
    title: str = Field(..., description="Title of the ICD-10 code in Japanese")


class DatasetUrlExtractionResult(BaseModel):
    human_data_url: str = Field(
        ..., description="A URL of human dataset included in the given search result."
    )

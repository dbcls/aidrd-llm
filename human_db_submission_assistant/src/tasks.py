import os
import json
import asyncio
import logging
import traceback
from typing import List
from fastapi import BackgroundTasks

from src.models import ApplicationData, DatasetAnalysisResult, ResearchInfo
from src.services.llm_service import suggest_icd10_code
from src.services.dataset_service import get_dataset_info, analyze_dataset
from src.services.research_service import get_research_info
from src.services.assessment_service import create_assessment_report


async def process_application_task(
    application_data: ApplicationData, background_tasks: BackgroundTasks, task_id: str
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
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        # Add the handler to logger
        task_logger.addHandler(file_handler)

        # Start logging
        task_logger.info("Starting application processing...")

        # Get ICD-10 code for abstract
        abstract_icd10 = await suggest_icd10_code(
            f"""# タスク説明
以下の研究概要をもとに、その研究概要に対応するICD-10コードを提案してください。

# 研究概要
{application_data.research_abstract}""",
            task_id=task_id,
        )
        task_logger.info(f"ICD-10 code suggested for abstract: {abstract_icd10}")

        # Limit to first few datasets for testing
        application_data.dataset_id_list = application_data.dataset_id_list[:5]

        # Get dataset information
        dataset_info_tasks = [
            get_dataset_info(dataset_id, task_id=task_id)
            for dataset_id in application_data.dataset_id_list
        ]
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
            dataset_analysis_tasks.append(
                analyze_dataset(
                    url,
                    dataset_ids,
                    abstract_icd10,
                    application_data.research_abstract,
                    task_id=task_id,
                )
            )
        dataset_analysis_result = await asyncio.gather(*dataset_analysis_tasks)
        dataset_analysis_result = [
            summary for sublist in dataset_analysis_result for summary in sublist
        ]  # Flatten the list
        task_logger.info(
            f"Dataset analysis_result retrieved: {dataset_analysis_result}"
        )

        # Get research information
        research_info_tasks = [
            get_research_info(doi, task_id=task_id)
            for doi in application_data.related_studies_published
        ]
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
            task_id=task_id,
        )
        task_logger.info(f"Assessment completed: {assessment}")

        # Store result
        result = {"assessment": assessment}

        # Save result to a file or database
        os.makedirs("results", exist_ok=True)
        with open(f"results/{task_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        task_logger.info("Result saved successfully.")

        # Remove file handler to avoid resource leaks
        task_logger.removeHandler(file_handler)
        file_handler.close()

    except Exception as e:
        # Log error
        error_stacktrace = traceback.format_exc()
        os.makedirs("results", exist_ok=True)
        with open(f"results/{task_id}_error.txt", "w", encoding="utf-8") as f:
            f.write(error_stacktrace)
        if "task_logger" in locals():
            task_logger.error(error_stacktrace)
            if "file_handler" in locals():
                task_logger.removeHandler(file_handler)
                file_handler.close()
        else:
            logging.getLogger("app").error(error_stacktrace)

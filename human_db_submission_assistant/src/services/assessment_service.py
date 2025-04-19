import os
import logging
from typing import List
from jinja2 import Environment, FileSystemLoader
from models import DatasetAnalysisResult, ResearchInfo

logger = logging.getLogger("assessment_service")

# Initialize Jinja2 environment
template_dir = "templates"
env = Environment(loader=FileSystemLoader(template_dir))
report_template = env.get_template("report.jinja2")


async def create_assessment_report(
    application_id: str,
    abstract_icd10: str,
    dataset_info_list: List[DatasetAnalysisResult],
    research_info_list: List[ResearchInfo],
    research_abstract: str,
    task_id: str = None,
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

    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)

    # Save the report to a file
    report_path = f"results/{task_id}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report

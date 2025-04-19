import aiohttp
import logging
from typing import List, Optional
from bs4 import BeautifulSoup

from src.models import (
    DatasetInfo,
    DatasetAnalysisResult,
    DatasetUrlExtractionResult,
    DatasetExtractionResult,
    Similarity,
)
from src.services.llm_service import extract_output_from_openai

logger = logging.getLogger("dataset_service")


async def get_dataset_info(
    dataset_id: str, task_id: str = None
) -> Optional[DatasetInfo]:
    """Get dataset information from HumandBS website"""
    search_url = f"https://humandbs.dbcls.jp/component/search/?searchword={dataset_id}&searchphrase=all"

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as response:
            if response.status != 200:
                return None

            html = await response.text()

            # Extract human data URL using OpenAI
            prompt = f"Extract the URL of the human dataset from this search result. It should be in the form of 'https://humandbs.dbcls.jp/hum****-v**'. If you find multiple candidates, output the result with the largest version number.\n\n{html}"

            result = await extract_output_from_openai(
                prompt, DatasetUrlExtractionResult, task_id=task_id
            )
            human_data_url = result.human_data_url if result else None

            if not human_data_url or not human_data_url.startswith(
                "https://humandbs.dbcls.jp/hum"
            ):
                return None

            return DatasetInfo(
                research_url=human_data_url.strip(), dataset_id=dataset_id
            )


async def analyze_dataset(
    url: str,
    dataset_ids: List[str],
    purpose_icd10: str,
    analysis_method: str,
    task_id: str = None,
) -> List[DatasetAnalysisResult]:
    """Summarize dataset information from its URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch dataset info from {url}")
                return []

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Summarize dataset using OpenAI
            prompt = f"""# データセットIDのリスト
{dataset_ids}

# 研究の説明
{soup.get_text()}"""

            system_message = """データセットのIDのリストと研究の説明を与えるので、研究の説明から、データセットごとの内容説明と関連するICD10コード、研究において用いられた解析手法をまとめてください。"""
            result = await extract_output_from_openai(
                prompt,
                DatasetExtractionResult,
                system_message=system_message,
                task_id=task_id,
            )

            if not result:
                return []

            prompt = f"""# タスク説明
今から行おうとしている研究の概要と、これまでに使用した解析手法を与えるので、どの程度その解析手法が研究内容に合致しているかを評価して「低」、「中」、「高」の3段階で評価してください。判断の理由も記載してください。

# 行おうとしている研究の概要
{analysis_method}

# これまでに使用した解析手法
{result.analysis_method}"""

            similarity_result = await extract_output_from_openai(
                prompt, Similarity, task_id=task_id
            )
            dataset_analysis_result_list = []

            for summary in result.dataset_summaries:
                dataset_analysis_result_list.append(
                    DatasetAnalysisResult(
                        id=summary.id,
                        icd10=summary.icd10_code,
                        purpose_similarity=check_similarity_of_icd10(
                            purpose_icd10, summary.icd10_code
                        ),
                        paper_similarity=True,
                        analysis_method_details=result.analysis_method,
                        analysis_method_similarity=similarity_result.analysis_method_similarity,
                        analysis_method_similarity_reason=similarity_result.analysis_method_similarity_reason,
                        url=url,
                    )
                )

            return dataset_analysis_result_list


def check_similarity_of_icd10(a: str, b: str) -> bool:
    """Check if two ICD-10 codes are similar"""
    if not a or not b:
        return False
    if b.startswith(a) or a.startswith(b):
        # どちらかがどちらかを含む場合は類似と判定
        return True
    if b[:-1] == a[:-1]:
        # 末尾の1文字を除いて同じ場合は類似と判定
        return True
    return False

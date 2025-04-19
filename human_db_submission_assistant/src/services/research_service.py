import json
import aiohttp
import logging
from typing import Dict, Any, Optional, List

from src.models import ResearchInfo
from src.services.llm_service import suggest_icd10_code

logger = logging.getLogger("research_service")


async def get_research_info(doi: str, task_id: str = None) -> Optional[ResearchInfo]:
    """Get research information from CrossRef API"""
    paper_info = await fetch_from_doi(doi)
    if not paper_info:
        return None

    title = paper_info.get("title", "")
    authors = paper_info.get("authors", [])
    abstract = paper_info.get("abstract", "")

    icd_10 = await suggest_icd10_code(
        f"""# タスク説明
以下の論文情報をもとに、その論文に対応するICD-10コードを提案してください。
特定の疾病に対して言及していない場合は、空文字列を返してください。

# タイトル
{title}
                                      
# 概要
{abstract}                                
""",
        task_id,
    )

    research_info = ResearchInfo(
        title=title,
        doi=doi,
        authors=authors,
        abstract=abstract,
        url=paper_info.get("url", ""),
        icd10=icd_10 if icd_10 else "",
    )
    return research_info


async def fetch_from_doi(doi: str) -> Optional[Dict[str, Any]]:
    """Fetch paper information from DOI"""
    url = f"https://api.crossref.org/works/{doi}/transform/application/vnd.citationstyles.csl+json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                content_type = resp.content_type
                if "application/octet-stream" in content_type:
                    raw_data = await resp.read()
                    data = json.loads(raw_data.decode("utf-8"))
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
                        if link.get("content-type") == "text/html":  # HTMLリンクを優先
                            break

                return {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "url": url,
                }
            else:
                logger.error(f"Error fetching DOI data: {resp.status}")
                return None


async def fetch_abstract_europepmc(doi: str) -> Optional[str]:
    """Fetch abstract from Europe PMC if not available in CrossRef"""
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": f"DOI:{doi}", "format": "json", "resultType": "core"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                records = (await resp.json()).get("resultList", {}).get("result", [])
                if records:
                    return records[0].get("abstractText")
            return None

import requests
import json
import argparse
import dotenv
import os
import re
import traceback
import markdown
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
from pydantic import BaseModel
from firecrawl import FirecrawlApp
from langchain_openai import AzureChatOpenAI
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache

headers = {"Content-Type": "application/json"}

dotenv.load_dotenv()

chat_model = AzureChatOpenAI(
    azure_deployment=os.environ.get("AZURE_DEPLOYMENT_ID"),
    temperature=0.4,
    max_retries=3,
)


def scrape_doc_file(url, base_url=""):
    # Define the payload
    try:
        response = requests.get(url, timeout=(10, 30))
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None
    return response, url


def extract_links_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    links = []
    for a_tag in soup.find_all("a"):
        text = a_tag.text.strip()
        if not text and a_tag.find("img"):
            # imgタグからalt属性が取得できるのであれば取得する
            text = a_tag.find("img").get("alt")
        links.append({"text": text, "url": a_tag.get("href")})

    return links


def get_base_url(url: str) -> str:
    """
    指定されたURLから最後のパスセグメントを削除し、ベースURLを取得する。

    :param url: 入力URL
    :return: 最後のパスセグメントを除いたベースURL
    """
    if url.endswith("/"):
        url = url.rstrip("/")

    base_url = url.rsplit("/", 1)[0]
    return base_url


class RelevanceCheckResult(BaseModel):
    is_relevant: bool


def check_relevance_of_content(markdown_content, purpose):
    MAX_LENGTH = 10000
    if len(markdown_content) > MAX_LENGTH:
        markdown_content = markdown_content[:MAX_LENGTH]

    task_instruction = f"""
<task_instruction>
Check the relevance of the following text with the theme of "{purpose}".
If relevant, return True. Otherwise, return False.
If you are unable to determine the relevance, return True.
</task_instruction>

<text>
{markdown_content}
</text>
"""

    return chat_model.with_structured_output(RelevanceCheckResult).invoke(
        task_instruction
    )["is_relevant"]


def check_relevance_of_url(url, purpose, link_title=None):

    task_instruction = f"""
# Task Instruction
Check the relevance of the following URL for the theme of "{purpose}".
If the URL is relevant, return True. Otherwise, return False.
If you are unable to determine the relevance, return True.

# URL
{url}
"""
    if link_title:
        task_instruction += f"\n# Title\n{link_title}"

    return chat_model.with_structured_output(RelevanceCheckResult).invoke(
        task_instruction
    )["is_relevant"]


def crawl_pages(
    start_url,
    max_page_count,
    max_depth,
    firecrawl_host,
    allow_backward_crawling,
    crawling_purpose,
    max_link_per_page,
):
    app = FirecrawlApp(api_url=firecrawl_host)
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
    file_download_dir = f"downloaded_files/{unique_id}"
    os.makedirs(file_download_dir, exist_ok=True)
    base_url = get_base_url(start_url)
    file_download_count = 0
    traversed_urls = set()
    scraping_results = []
    irrelevant_urls = []
    url_queue = [(start_url, 0)]
    while len(url_queue) > 0 and len(traversed_urls) < max_page_count:
        target_url, depth = url_queue.pop(0)
        if depth > max_depth or target_url in traversed_urls:
            continue
        print(f"Scraping file: {target_url}")
        doc_file_extensions = ["pdf", "docx", "xlsx", "xls"]
        traversed_urls.add(target_url)

        try:
            if any([target_url.lower().endswith(ext) for ext in doc_file_extensions]):
                file_url = link
                response, file_url = scrape_doc_file(file_url)
                if response is None:
                    print("Failed to scrape the file.")
                else:
                    print(f"Response status code: {response.status_code}")
                if response is not None and response.status_code == 200:
                    file_name = f"{file_download_count}_{file_url.split('/')[-1]}"
                    file_path = os.path.join(file_download_dir, file_name)
                    print(f"Saving file to: {file_path}")
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    scraping_results.append(
                        {
                            "content": None,
                            "provider": "simple-download",
                            "metadata": {
                                "sourceURL": file_url,
                                "filePath": file_path,
                            },
                        }
                    )
            else:
                response = app.scrape_url(
                    url=target_url,
                    params={
                        "formats": ["markdown", "html"],
                    },
                )
                """
                Example response:
                {
                "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples in documents. You may use this\ndomain in literature without prior coordination or asking for permission.\n\n[More information...](https://www.iana.org/domains/example)",
                "html": "...",
                "metadata": {
                    "title": "Example Domain",
                    "viewport": "width=device-width, initial-scale=1",
                    "scrapeId": "35740f4a-3107-456a-885a-754d88add4b6",
                    "sourceURL": "https://example.com",
                    "url": "https://example.com/",
                    "statusCode": 200
                },
                "scrape_id": "35740f4a-3107-456a-885a-754d88add4b6"
                }
                """
                result_markdown = response["markdown"]
                links = extract_links_from_html(response["html"])

                if crawling_purpose:
                    relevance = check_relevance_of_content(
                        result_markdown, crawling_purpose
                    )
                    if not relevance:
                        print(f"Skipping irrelevant content: {target_url}")
                        irrelevant_urls.append(target_url)
                        continue

                link_count = 0
                for link in links:
                    url = link["url"]
                    if url in traversed_urls:
                        continue
                    link_count += 1
                    if link_count > max_link_per_page:
                        break
                    if allow_backward_crawling or url.startswith(base_url):
                        if not crawling_purpose or check_relevance_of_url(
                            url, crawling_purpose, link["text"]
                        ):
                            canonical_url = url[:-1] if url.endswith("/") else url
                            print(f"Adding URL to queue: {canonical_url}")
                            url_queue.append((canonical_url, depth + 1))
                        else:
                            print(f"Skipping irrelevant URL: {url}")
                            irrelevant_urls.append(url)

                scraping_results.append(
                    {
                        "content": result_markdown,
                        "provider": "firecrawl",
                        "metadata": response["metadata"],
                    }
                )
            file_download_count += 1
            print(f"Crawling completed : {file_download_count} / {max_page_count}.")
            if file_download_count >= max_page_count:
                break
        except Exception as e:
            print(f"An error occurred. skipping...: {e}\n{traceback.format_exc()}")
            continue
    return scraping_results, irrelevant_urls


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Crawl pages starting from a given URL."
    )
    parser.add_argument("start_url", type=str, help="The starting URL for the crawl")
    parser.add_argument(
        "output_file", type=str, help="The output file to save the results"
    )
    parser.add_argument(
        "--firecrawl-host",
        type=str,
        default="http://127.0.0.1:3002/",
        help="The Firecrawl endpoint to use",
    )
    parser.add_argument(
        "--max-page-count",
        type=int,
        default=100,
        help="The maximum number of pages to crawl (including files other than HTML)",
    )
    parser.add_argument(
        "--max-depth", type=int, default=5, help="The maximum depth to crawl"
    )
    parser.add_argument(
        "--allow-backward-crawling",
        action="store_true",
        help="Allow external content links",
    )
    parser.add_argument(
        "--crawling-purpose",
        type=str,
        default="",
        help="The purpose of crawling the pages. This will be used to filter the results using LLM",
    )
    parser.add_argument(
        "--max-link-per-page",
        type=int,
        default=20,
        help="The maximum number of links to follow per page",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    start_url = args.start_url
    output_file = args.output_file

    # Call the function to start crawling
    result_json, irrelevant_urls = crawl_pages(
        start_url,
        args.max_page_count,
        args.max_depth,
        args.firecrawl_host,
        args.allow_backward_crawling,
        args.crawling_purpose,
        args.max_link_per_page,
    )

    # If the directory does not exist, create it
    dir_name = os.path.dirname(output_file)
    if dir_name != "":
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    json.dump(result_json, open(output_file, "w"), indent=2, ensure_ascii=False)
    set_llm_cache(SQLiteCache(database_path=".langchain.db"))

    if irrelevant_urls:
        print("The following URLs were found to be irrelevant:")
        for url in irrelevant_urls:
            print(url)

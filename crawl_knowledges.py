import requests
import json
import argparse
import os
import re
import traceback
import markdown
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
from firecrawl import FirecrawlApp


headers = {"Content-Type": "application/json"}


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


def crawl_pages(
    start_url,
    max_page_count,
    max_depth,
    firecrawl_host,
    allow_backward_crawling,
    crawling_purpose,
):
    app = FirecrawlApp(api_url=firecrawl_host)
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
    file_download_dir = f"downloaded_files/{unique_id}"
    os.makedirs(file_download_dir, exist_ok=True)
    base_url = get_base_url(start_url)
    file_download_count = 0
    traversed_urls = set()
    scraping_results = []
    try:
        url_stack = [(start_url, 0)]
        while len(url_stack) > 0 and len(traversed_urls) < max_page_count:
            target_url, depth = url_stack.pop(0)
            if depth > max_depth or target_url in traversed_urls:
                continue
            print(f"Scraping file: {target_url}")
            doc_file_extensions = ["pdf", "docx", "xlsx", "xls"]
            traversed_urls.add(target_url)

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
                for link in links:
                    # TODO: evaluate relevance of the link
                    # TODO: use max_depth to limit the depth of the crawl
                    if allow_backward_crawling or link["url"].startswith(base_url):
                        canonical_url = (
                            link["url"][:-1]
                            if link["url"].endswith("/")
                            else link["url"]
                        )
                        url_stack.append((canonical_url, depth + 1))
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
        return scraping_results
    except Exception as e:
        print(f"An error occurred: {e}\n{traceback.format_exc()}")
        return scraping_results


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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    start_url = args.start_url
    output_file = args.output_file

    # Call the function to start crawling
    result_json = crawl_pages(
        start_url,
        args.max_page_count,
        args.max_depth,
        args.firecrawl_host,
        args.allow_backward_crawling,
        args.crawling_purpose,
    )

    # If the directory does not exist, create it
    dir_name = os.path.dirname(output_file)
    if dir_name != "":
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    json.dump(result_json, open(output_file, "w"), indent=2)

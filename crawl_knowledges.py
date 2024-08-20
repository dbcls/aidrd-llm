import requests
import json
import argparse
import os
from datetime import datetime
from time import sleep

headers = {'Content-Type': 'application/json'}


def scrape_single_page(url, base_url = ''):
    # Define the payload
    response = requests.get(url)
    if response.status_code != 200 and base_url != '':
        # Firecrawlが返してくるlinksOnPageは、
        # 例えば"https://www.example.com/page.html" の中に
        # "a/b.pdf" というリンクがある場合、
        # "https://www.example.com/page.html/a/b.pdf" という形で返ってくる。
        # これは正しくない場合があり、"https://www.example.com/a/b.pdf" という形に修正する必要があるため、base_urlを使って修正してリトライする。
        base_url_without_last_segment = '/'.join(base_url.split('/')[:-1])
        retry_url = base_url_without_last_segment + url.replace(base_url, '')
        print("Trial failed. Retrying with the corrected URL:", retry_url)
        return scrape_single_page(retry_url)
    return response, url

        

def crawl_pages(start_url, max_page_count, max_depth, firecrawl_host):
    if not firecrawl_host.endswith("/"):
        endpoint = f"{firecrawl_host}/v0/crawl"
    else:
        endpoint = f"{firecrawl_host}v0/crawl"
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
    pdf_download_dir = f"downloaded_pdfs/{unique_id}"
    os.makedirs(pdf_download_dir, exist_ok=True)
    pdf_download_count = 0    
    try:
        # Define the payload
        payload = {
            "url": start_url,
            "crawlerOptions": {
                "limit": max_page_count,
                "maxDepth": max_depth,
            },
            "pageOptions": {
                "onlyMainContent": True,                
            }
        }
        print(payload)
        
        # Send the POST request
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        result = None
        # Check if the request was successful
        if response.status_code == 200:
            print("Crawling started successfully.")
            result = response.json()
            job_id = result["jobId"]
            print(f"Job ID: {job_id}")
            while True:
                sleep(1)
                response = requests.get(f"{endpoint}/status/{job_id}")
                if response.status_code == 200:
                    status = response.json()
                    if status["status"] == "completed":
                        print("Crawling completed.")
                        result_for_html = status["data"]
                        if len(result_for_html) < max_page_count:
                            traversed_urls = [page["metadata"]["sourceURL"] for page in result_for_html]
                            traversed_urls = set(traversed_urls)
                            # Scrape PDF files
                            for page in result_for_html:
                                if "linksOnPage" not in page:
                                    continue
                                for link in page["linksOnPage"]:
                                    if len(result_for_html) >= max_page_count:
                                        break
                                    if link in traversed_urls:
                                        continue
                                    if link.lower().endswith(".pdf"):
                                        pdf_url = link
                                        print(f"Scraping PDF file: {pdf_url}")
                                        response, pdf_url = scrape_single_page(pdf_url, base_url=page["metadata"]["sourceURL"])
                                        if response.status_code == 200:
                                            pdf_download_count += 1
                                            pdf_file_name = f"{pdf_download_count}_{pdf_url.split('/')[-1]}"
                                            pdf_file_path = os.path.join(pdf_download_dir, pdf_file_name)
                                            print(f"Saving PDF file to: {pdf_file_path}")
                                            with open(pdf_file_path, 'wb') as f:
                                                f.write(response.content)
                                            result_for_html.append({
                                                "content": None,
                                                "provider": "simple-download",
                                                "metadata": {
                                                    "sourceURL": pdf_url,
                                                    "filePath": pdf_file_path
                                                }
                                            })
                                    traversed_urls.add(link)
                                if len(result_for_html) >= max_page_count:
                                    break
                        return result_for_html
                        # TODO: scrape other files: docx, xlsx, etc.
                    elif status["status"] == "failed":
                        print("Crawling failed.")
                        return {}
                    else:
                        print(f"Current progres: {status['current']} / {status['total']}")
                else:
                    print(f"Failed to get job status. Status code: {response.status_code}")
                    return {}

        else:
            print(f"Failed to start crawling. Status code: {response.status_code}")
            print("Response:", response.text)
            return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

def parse_arguments():
    parser = argparse.ArgumentParser(description="Crawl pages starting from a given URL.")
    parser.add_argument('start_url', type=str, help='The starting URL for the crawl')
    parser.add_argument('output_file', type=str, help='The output file to save the results')
    parser.add_argument('--firecrawl-host', type=str, default='http://127.0.0.1:3002/', help='The Firecrawl endpoint to use')
    parser.add_argument('--max-page-count', type=int, default=100, help='The maximum number of pages to crawl (including files other than HTMLs)')
    parser.add_argument('--max-depth', type=int, default=5, help='The maximum depth to crawl')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    start_url = args.start_url
    output_file = args.output_file

    # Call the function to start crawling
    result_json = crawl_pages(start_url, args.max_page_count, args.max_depth, args.firecrawl_host)
    json.dump(result_json, open(output_file, 'w'), indent=2)
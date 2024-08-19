# A script to upload knowledge in given json file to the remote Dify server.
# Script to evaluate the accuracy of retrieval using dataset in evaluation_data.json

import json
import requests
import csv
from io import BytesIO
from datetime import datetime
import dotenv
import os
import argparse
from time import sleep

# TODO: アップロードしたナレッジのパーミッションが only_me になってしまい、DBを直接変更しない限り確認できないように見受けられる（APIが無い？）

dotenv.load_dotenv()

headers = {
    "Authorization": f"Bearer {os.environ.get('KNOWLEDGE_API_KEY')}",
    "Content-Type": "application/json"
}


def get_existing_knowledge_base_id(knowledge_base_name):
    page = 1
    url = f"{os.environ.get('API_BASE_URL')}/datasets?limit=100"
    response = requests.get(url, headers=headers).json()
    for dataset in response["data"]:
        if dataset["name"] == knowledge_base_name:
            return dataset["id"]
    while response["has_more"]:
        page += 1
        response = requests.get(f"{url}&page={page}", headers=headers).json()
        for dataset in response["data"]:
            if dataset["name"] == knowledge_base_name:
                return dataset["id"]
    return None


def create_knowledge_base(knowledge_base_name):
    url = f"{os.environ.get('API_BASE_URL')}/datasets"
    data = {
        "name": knowledge_base_name,
    }
    response = requests.post(url, headers=headers, json=data).json()
    return response["id"]

def get_existing_document_names(knowledge_base_id):
    page = 1
    url = f"{os.environ.get('API_BASE_URL')}/datasets/{knowledge_base_id}/documents?limit=100"
    response = requests.get(url, headers=headers).json()
    document_names = [document["name"] for document in response["data"]]
    while response["has_more"]:
        page += 1
        response = requests.get(f"{url}&page={page}", headers=headers).json()
        document_names += [document["name"] for document in response["data"]]
    return document_names


def add_document_to_knowledge_base(knowledge_base_id, document, indexing_technique, process_rule):
    url = f"{os.environ.get('API_BASE_URL')}/datasets/{knowledge_base_id}/document/create_by_file"

    headers_for_add = {
        "Authorization": f"Bearer {os.environ.get('KNOWLEDGE_API_KEY')}",
    }

    data = {
        "indexing_technique": indexing_technique,
        "process_rule": process_rule
    }

    file_url = document["metadata"]["sourceURL"]

    if "filePath" in document["metadata"]:
        document_content = open(document["metadata"]["filePath"], "rb")
    else:
        document_content = BytesIO(document["content"].encode())

    files = {
        "file": (file_url, document_content),
        "data": (None, json.dumps(data), "text/plain")
    }
    response = requests.post(url, headers=headers_for_add, files=files, data=data).json()
    print(response)
    return response["batch"]

def check_if_embedding_is_in_progress(knowledge_base_id, batch_id):
    url = f"{os.environ.get('API_BASE_URL')}/datasets/{knowledge_base_id}/documents/{batch_id}/indexing-status"
    print(url)
    response = requests.get(url, headers=headers).json()
    return response["data"][0]["indexing_status"] == "indexing"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Crawl pages starting from a given URL.")
    parser.add_argument('knowledge_file', type=str, help='The JSON file containing the knowledge to upload')
    parser.add_argument('knowledge_base_name', type=str, help='The name of the knowledge base to be created')
    parser.add_argument('--indexing-technique', type=str, default="high_quality", help='The indexing technique to be used. high_quality or economy')
    parser.add_argument('--processing-mode', type=str, default="automatic", help='The processing mode to be used. automatic or custom')
    parser.add_argument('--segment-separator', type=str, default="\n", help='The segment separator to be used. Only used if processing mode is custom.')
    parser.add_argument('--segment-max-tokens', type=int, default=1000, help='The maximum number of tokens per segment. Only used if processing mode is custom.')
    parser.add_argument('--remove-extra-spaces', action="store_true", help='Remove extra spaces. Only used if processing mode is custom.')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    knowledge_json = json.load(open(args.knowledge_file))
    knowledge_base_id = get_existing_knowledge_base_id(args.knowledge_base_name)
    if knowledge_base_id is None:
        knowledge_base_id = create_knowledge_base(args.knowledge_base_name)

    process_rule = {
        "mode": args.processing_mode
    }
    if args.processing_mode == "custom":
        rules = {}
        rules["segmentation"] = {}
        rules["segmentation"]["separator"] = args.segment_separator
        rules["segmentation"]["max_tokens"] = args.segment_max_tokens
        if args.remove_extra_spaces:
            rules["pre_processing_rules"] = [{"id": "remove_extra_spaces", "enabled": True}]
        process_rule["rules"] = rules
    i = 0
    length = len(knowledge_json)
    existing_documents = get_existing_document_names(knowledge_base_id)
    queued_documents = []
    MAX_QUEUED_DOCUMENTS = 1
    
    for document in knowledge_json:
        i += 1
        document_name = document["metadata"]["sourceURL"]
        if document_name in existing_documents:
            print(f"Document {i} / {length}: {document_name} already exists. Skipping.")
            continue
        print(f"Adding document {i} / {length}: {document_name}")
        queued_documents.append(add_document_to_knowledge_base(knowledge_base_id, document, args.indexing_technique, process_rule))
        while len(queued_documents) >= MAX_QUEUED_DOCUMENTS:
            print("Waiting for documents to be indexed...")
            sleep(1)
            for batch_id in queued_documents:
                if not check_if_embedding_is_in_progress(knowledge_base_id, batch_id):
                    queued_documents.remove(batch_id)
                    break              
        sleep(10)
    
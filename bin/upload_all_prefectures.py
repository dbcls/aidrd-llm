# A script to crawl all prefectures in Japan using crawl_knowledges.py and prefecture_portal_url.csv
import csv
import json
import os


def upload_all_prefectures():
    with open("prefecture_portal_url.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        for row in reader:
            prefecture_name = row[0]
            prefecture_url = row[1]
            source_file_name = f"crawled_knowledges/{prefecture_name}.json"
            print(f"Uploading {prefecture_name}...")
            command = f"python upload_knowledge.py {source_file_name} {prefecture_name}"
            os.system(command)


if __name__ == "__main__":
    upload_all_prefectures()

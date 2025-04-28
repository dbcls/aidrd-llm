# A script to crawl all prefectures in Japan using crawl_knowledges.py and prefecture_portal_url.csv
import csv
import json
import os


def crawl_all_prefectures():
    with open("prefecture_portal_url.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        for row in reader:
            prefecture_name = row[0]
            prefecture_url = row[1]
            allow_backward_crawling = row[2].lower() == "true"
            output_file_name = f"crawled_knowledges/{prefecture_name}.json"
            if os.path.exists(output_file_name):
                existing_entry_counts = len(json.load(open(output_file_name)))
                if (
                    existing_entry_counts > 100
                ):  # すでに存在していてしかも中身が十分にある場合はスキップ
                    print(f"Skipping {prefecture_name}...")
                    continue
            print(f"Crawling {prefecture_name}...")
            command = f"python crawl_knowledges.py {prefecture_url} {output_file_name} --max-page-count 1000"
            if allow_backward_crawling:
                command += " --allow-backward-crawling"
            os.system(command)


if __name__ == "__main__":
    crawl_all_prefectures()

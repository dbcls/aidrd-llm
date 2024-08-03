# Script to evaluate the accuracy of retrieval using dataset in evaluation_data.json

import json
import requests
import dotenv
import os

dotenv.load_dotenv()


def query_to_api(query):
    url = f"{os.environ.get('API_BASE_URL')}/chat-messages"
    headers = {
        "Authorization": f"Bearer {os.environ.get('CHATBOT_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": {},
        "user": os.environ.get("DIFY_USER"),
        "query": query,
        "response_mode": "blocking",
    }
    response = requests.post(url, headers=headers, json=data).json()
    answer = response["answer"]
    soucre_url_list = [resource["document_name"] for resource in response["metadata"]["retriever_resources"]]
    return answer, soucre_url_list



if __name__ == "__main__":
    with open("evaluation_data.json") as f:
        evaluation_data = json.load(f)

    source_url_accuracy = {
        "true_positive": 0,
        "false_positive": 0,
        "false_negative": 0,
    }
    correct = 0
    total = 0
    for data in evaluation_data:
        total += 1
        query = data["query"]
        expected_answer = data["expected_answer"]
        expected_source_url_list = data["source_url_list"]
        actual_answer, actual_source_url_list = query_to_api(query)
        actual_source_url_list = list(set(actual_source_url_list))
        print(f"Query: {query}")
        print(f"Expected Answer: {expected_answer}")
        print(f"Retrieved Answer: {actual_answer}")
        print(f"Expected Source URLs: {expected_source_url_list}")
        print(f"Source URLs: {actual_source_url_list}")
        local_true_positive = 0
        local_false_positive = 0
        local_false_negative = 0
        for source_url in expected_source_url_list:
            if source_url in actual_source_url_list:
                local_true_positive += 1
            else:
                local_false_negative += 1
        for source_url in actual_source_url_list:
            if source_url not in expected_source_url_list:
                local_false_positive += 1
        source_url_accuracy["true_positive"] += local_true_positive
        source_url_accuracy["false_positive"] += local_false_positive
        source_url_accuracy["false_negative"] += local_false_negative
        f1_score = 2 * local_true_positive / (2 * local_true_positive + local_false_positive + local_false_negative)
        print(f"F1 Score: {f1_score}")        
        print("") # For delimiter

    f1_score = 2 * source_url_accuracy["true_positive"] / (2 * source_url_accuracy["true_positive"] + source_url_accuracy["false_positive"] + source_url_accuracy["false_negative"])
    print(f"Total F1 Score: {f1_score}")
    
 
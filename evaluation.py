# Script to evaluate the accuracy of retrieval using dataset in evaluation_data.json

import json
import requests
import csv
from datetime import datetime
import dotenv
import os

from typing import List, Tuple

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.callbacks.manager import get_openai_callback

from langchain_openai import AzureChatOpenAI

dotenv.load_dotenv()


def query_to_api(query):
    url = f"{os.environ.get('API_BASE_URL')}/chat-messages"
    headers = {
        "Authorization": f"Bearer {os.environ.get('CHATBOT_API_KEY')}",
        "Content-Type": "application/json",
    }
    data = {
        "inputs": {},
        "user": os.environ.get("DIFY_USER"),
        "query": query,
        "response_mode": "blocking",
    }
    response = requests.post(url, headers=headers, json=data).json()
    answer = response["answer"]
    if "metadata" not in response or "retriever_resources" not in response["metadata"]:
        return answer, []
    soucre_url_list = [
        resource["document_name"]
        for resource in response["metadata"]["retriever_resources"]
    ]
    return answer, soucre_url_list


def evaluate_by_llm(expected_answer, actual_answer):
    chat_model = AzureChatOpenAI(
        azure_deployment=os.environ.get("AZURE_DEPLOYMENT_ID"),
        api_version="2024-05-01-preview",
        temperature=0.4,
        max_retries=3,
    )

    class EvaluationResult(BaseModel):
        similarity: int = Field(description="The similarity score from 1 to 5")

    query = f"""e
Here we have two answers. The first answer is the expected answer and the second answer is the actual answer.
Please evaluate the similarity actual answer based on the expected answer and compute the score from 1 to 5.
Below are the details for different scores:
- Score 1: the actual answer has little to no semantic similarity to the expected answer.
- Score 2: the actual answer displays partial semantic similarity to the expected answer on some aspects.
- Score 3: the actual answer has moderate semantic similarity to the expected answer.
- Score 4: the actual answer aligns with the expected answer in most aspects and has substantial semantic similarity.
- Score 5: the actual answer closely aligns with the expected answer in all significant aspects.


### Expected Answer
```
{expected_answer}
```
### Actual Answer
```
{actual_answer}
```
"""

    parser = PydanticOutputParser(pydantic_object=EvaluationResult)

    prompt = PromptTemplate(
        template="Answer the user query.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | chat_model | parser

    evaluation_result = chain.invoke({"query": query})
    return evaluation_result.similarity


if __name__ == "__main__":

    with get_openai_callback() as cb:
        with open("evaluation_data.json") as f:
            evaluation_data = json.load(f)

        source_url_accuracy = {
            "true_positive": 0,
            "false_positive": 0,
            "false_negative": 0,
        }
        total = 0
        similarity_score_sum = 0

        # get current date and time for csv file name
        current_date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        csv_file = open(
            f"evaluation_results_{current_date_time}.csv",
            mode="w",
            newline="",
            encoding="utf-8-sig",
        )
        fieldnames = [
            "Number",
            "query",
            "expected_source_urls",
            "actual_source_urls",
            "source_urls_f1_score",
            "expected_answer",
            "actual_answer",
            "answer_similarity",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for data in evaluation_data:
            total += 1
            query = data["query"]
            expected_answer = data["expected_answer"]
            expected_source_url_list = data["source_url_list"]
            actual_answer, actual_source_url_list = query_to_api(query)
            actual_source_url_list = list(set(actual_source_url_list))
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
            source_f1_score = (
                2
                * local_true_positive
                / (
                    2 * local_true_positive
                    + local_false_positive
                    + local_false_negative
                )
            )
            answer_similarity_score = evaluate_by_llm(expected_answer, actual_answer)
            similarity_score_sum += answer_similarity_score
            print(f"Query: {query}")
            print(f"Expected Source URLs: {expected_source_url_list}")
            print(f"Source URLs: {actual_source_url_list}")
            print(f"Source F1 Score: {source_f1_score}")
            print(f"Expected Answer: {expected_answer}")
            print(f"Retrieved Answer: {actual_answer}")
            print(f"Answer Similarity Score: {answer_similarity_score}")
            print("")  # For delimiter

            writer.writerow(
                {
                    "Number": total,
                    "query": query,
                    "expected_source_urls": "\n".join(expected_source_url_list),
                    "actual_source_urls": "\n".join(actual_source_url_list),
                    "source_urls_f1_score": source_f1_score,
                    "expected_answer": expected_answer,
                    "actual_answer": actual_answer,
                    "answer_similarity": answer_similarity_score,
                }
            )

        f1_score = (
            2
            * source_url_accuracy["true_positive"]
            / (
                2 * source_url_accuracy["true_positive"]
                + source_url_accuracy["false_positive"]
                + source_url_accuracy["false_negative"]
            )
        )
        print(f"Total F1 Score: {f1_score}")
        print(f"Average Answer Similarity Score: {similarity_score_sum / total}")
        writer.writerow(
            {
                "Number": "Total",
                "query": "",
                "expected_source_urls": "",
                "actual_source_urls": "",
                "source_urls_f1_score": f1_score,
                "expected_answer": "",
                "actual_answer": "",
                "answer_similarity": similarity_score_sum / total,
            }
        )
        csv_file.close()
        print(cb)

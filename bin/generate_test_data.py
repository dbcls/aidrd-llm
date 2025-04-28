import argparse
import csv
import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from ragas.testset import TestsetGenerator
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain.docstore.document import Document
from ragas.testset.synthesizers import default_query_distribution
from ragas.testset.synthesizers.single_hop.specific import (
    SingleHopSpecificQuerySynthesizer,
)
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache


load_dotenv(override=True)

generator_llm = LangchainLLMWrapper(
    AzureChatOpenAI(
        azure_deployment=os.environ.get("AZURE_DEPLOYMENT_ID"),
        temperature=0.4,
        max_retries=3,
    )
)
generator_embeddings = LangchainEmbeddingsWrapper(
    AzureOpenAIEmbeddings(
        azure_deployment=os.environ.get("AZURE_EMBEDDING_DEPLOYMENT_ID")
    )
)


async def create_test_data(doc_list, num_test_cases, with_multi_hop, use_japanese):

    if with_multi_hop:
        # Default query distribution:
        # [
        #     (SingleHopSpecificQuerySynthesizer(llm=llm), 0.5),
        #     (MultiHopAbstractQuerySynthesizer(llm=llm), 0.25),
        #     (MultiHopSpecificQuerySynthesizer(llm=llm), 0.25),
        # ]
        distribution = default_query_distribution(generator_llm)
    else:
        synthesizer = SingleHopSpecificQuerySynthesizer(llm=generator_llm)
        # Change the property name from default "entities" to "headlines" because Entity Extraction seems to be fragile and leads to empty results
        synthesizer.property_name = "headlines"

        distribution = [
            (synthesizer, 1.0),
        ]

    testset_list = []

    if use_japanese:
        for query, _ in distribution:
            prompts = await query.adapt_prompts("japanese", llm=generator_llm)
            query.set_prompts(**prompts)

    generator = TestsetGenerator(
        llm=generator_llm, embedding_model=generator_embeddings
    )
    if with_multi_hop:
        dataset = generator.generate_with_langchain_docs(
            doc_list,
            testset_size=num_test_cases * len(doc_list),
            query_distribution=distribution,
        )
    else:
        for doc in doc_list:
            print(f"Generating test data for {doc.metadata['source']}...")
            try:
                dataset = generator.generate_with_langchain_docs(
                    [doc],
                    testset_size=num_test_cases,
                    query_distribution=distribution,
                )
                testset = dataset.to_list()
                for test in testset:
                    test["document_name"] = doc.metadata["source"]
                testset_list += testset
            except Exception as e:
                logging.exception(
                    f"Failed to generate test data for {doc.metadata['source']}"
                )

    return testset_list


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate test data for RAG with the given documents."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-f",
        "--files",
        type=str,
        nargs="+",
        help="The input files to generate test data from",
    )
    group.add_argument(
        "-j",
        "--json",
        type=str,
        help="The input JSON file to generate test data from",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="test_data.csv",
        type=str,
        help="The output file to save the results",
    )
    parser.add_argument(
        "--with_multi_hop",
        action="store_true",
        help="Whether to generate test cases which require reasoning over multiple documents",
    )
    parser.add_argument(
        "-n",
        "--num_test_cases",
        default=5,
        type=int,
        help="The number of test cases to generate for each document",
    )
    parser.add_argument(
        "--use_japanese",
        action="store_true",
        help="Whether to use Japanese language for the test data",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    set_llm_cache(SQLiteCache(database_path=".langchain.db"))

    docs = []
    if args.files:
        for file in args.files:
            file_name = file.split("/")[-1]
            loader = UnstructuredFileLoader(file)
            doc = loader.load()
            doc.metadata["source"] = file_name
            docs.append(doc)
    elif args.json:
        knowledge_json = json.load(open(args.json))
        for document in knowledge_json:
            length = len(knowledge_json)
            if document is None or "metadata" not in document:
                continue
            document_name = document["metadata"]["sourceURL"]
            doc = Document(
                page_content=document["content"],
                metadata={
                    "source": document["metadata"]["sourceURL"],
                },
            )
            docs.append(doc)

    test_data = asyncio.run(
        create_test_data(
            docs,
            args.num_test_cases,
            args.with_multi_hop,
            args.use_japanese,
        )
    )

    output_file = args.output
    with open(output_file, "w", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            [
                "query",
                "expected_answer",
                "reference_contexts",
                "synthesizer_name",
                "document_name",
            ],
        )
        writer.writeheader()
        for test in test_data:
            writer.writerow(
                {
                    "query": test["user_input"],
                    "expected_answer": test["reference"],
                    "reference_contexts": test["reference_contexts"],
                    "synthesizer_name": test["synthesizer_name"],
                    "document_name": test["document_name"],
                }
            )

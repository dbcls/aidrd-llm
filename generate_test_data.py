import argparse
import csv
import asyncio
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from ragas.testset import TestsetGenerator
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from ragas.testset.synthesizers import default_query_distribution
from ragas.testset.synthesizers.single_hop.specific import (
    SingleHopSpecificQuerySynthesizer,
)
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache


# from ragas.testset.evolutions import simple, reasoning, multi_context


async def main(file_list, output_file, num_test_cases, with_multi_hop, use_japanese):
    generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
    generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

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

    all_docs = []

    for file in file_list:
        file_name = file.split("/")[-1]
        print("Processing file: ", file_name)
        loader = UnstructuredFileLoader(file)
        docs = loader.load()

        print("Loaded documents: ", len(docs))

        generator = TestsetGenerator(
            llm=generator_llm, embedding_model=generator_embeddings
        )

        if not with_multi_hop:
            dataset = generator.generate_with_langchain_docs(
                docs, testset_size=num_test_cases, query_distribution=distribution
            )

            testset = dataset.to_list()
            for test in testset:
                test["document_name"] = file_name

            testset_list += testset
        else:
            all_docs += docs

    if with_multi_hop:
        dataset = generator.generate_with_langchain_docs(
            all_docs,
            testset_size=num_test_cases * len(file_list),
            query_distribution=distribution,
        )

        testset_list = dataset.to_list()

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
        for test in testset_list:
            writer.writerow(
                {
                    "query": test["user_input"],
                    "expected_answer": test["reference"],
                    "reference_contexts": test["reference_contexts"],
                    "synthesizer_name": test["synthesizer_name"],
                    "document_name": test["document_name"],
                }
            )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate test data for RAG with the given documents."
    )

    parser.add_argument(
        "files", type=str, nargs="+", help="The input files to generate test data from"
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
    asyncio.run(
        main(
            args.files,
            args.output,
            args.num_test_cases,
            args.with_multi_hop,
            args.use_japanese,
        )
    )

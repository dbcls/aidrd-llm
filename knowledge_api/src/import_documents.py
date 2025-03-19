import argparse
import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader

from langchain.docstore.document import Document
import csv
import json
import dotenv
from time import sleep
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings


dotenv.load_dotenv(override=True)

embeddings = AzureOpenAIEmbeddings(
    azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT_ID"]
)


def create_vector_store_from_dir(
    document_dir_path: str,
    max_chunk_size=600,
    extended_chunk_nums=1,
) -> FAISS:
    loader = DirectoryLoader(
        document_dir_path,
    )
    print("Loading documents...")
    docs = loader.load_and_split(
        RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
        )
    )
    print(f"Loaded {len(docs)} documents.")
    for i, doc in enumerate(docs):
        doc.metadata["extended_chunks"] = []
        for j in range(i - extended_chunk_nums, i + extended_chunk_nums + 1):
            if j >= 0 and j < len(docs):
                doc.metadata["extended_chunks"].append(docs[j].page_content)
    return FAISS.from_documents(docs, embeddings)


def create_vector_store_from_json(
    json_path: str,
    max_chunk_size=600,
    extended_chunk_nums=1,
):
    knowledge_json = json.load(open(json_path))
    docs = []
    for document in knowledge_json:
        if document is None or "metadata" not in document:
            print(f"Document has no metadata. Skipping.")
            continue

        document_name = document["metadata"]["sourceURL"]
        print(f"Adding document: {document_name}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
        )

        splitted_docs = splitter.create_documents([document["content"]])
        print(f"Loaded {len(splitted_docs)} documents.")
        for i, splitted_doc in enumerate(splitted_docs):
            extended_chunks = []
            for j in range(i - extended_chunk_nums, i + extended_chunk_nums + 1):
                if j >= 0 and j < len(splitted_docs):
                    extended_chunks.append(splitted_docs[j].page_content)
            extended_doc = Document(
                page_content=splitted_doc.page_content,
                metadata={
                    "source": document["metadata"]["sourceURL"],
                    "title": (
                        document["metadata"]["title"]
                        if "title" in document["metadata"]
                        else ""
                    ),
                    "extended_chunks": extended_chunks,
                },
            )
            docs.append(extended_doc)
    print(f"Loaded {len(docs)} documents.")
    print(f"Creating vector store ...")
    batch_size = 100
    batched_docs = [docs[i : i + batch_size] for i in range(0, len(docs), batch_size)]
    vector_store = None

    processed_docs = 0
    for batch in batched_docs:
        if vector_store is None:
            vector_store = FAISS.from_documents(batch, embeddings)
        else:
            vector_store.add_documents(batch)
        processed_docs += len(batch)
        print(f"Processed {processed_docs} out of {len(docs)} documents.")
        sleep(5)  # Sleep for 5 seconds to avoid Azure rate limit

    return vector_store


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a vector store from a directory of documents."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--document-dir", type=str, help="Path to the directory of documents."
    )
    input_group.add_argument(
        "--json",
        type=str,
        help="Path to the JSON file containing knowledges.",
    )

    parser.add_argument(
        "--max-chunk-size", type=int, default=600, help="Maximum size of each chunk."
    )
    parser.add_argument(
        "--extended-chunk-nums",
        type=int,
        default=1,
        help="The number of consecutive chunks that will be saved in the metadata named 'extended_chunks'. For example, if this value is 2, the two chunks before and after each chunk will be saved in the metadata."
        "This is useful to consider longer context for each chunk.",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Path to save the vector store. If not provided, the vector store will be saved in VECTOR_STORE_PATH environment variable.",
    )
    args = parser.parse_args()

    vector_store_path = args.output_path or os.environ.get("VECTOR_STORE_PATH")

    if args.json:
        vector_store = create_vector_store_from_json(
            args.json,
            max_chunk_size=args.max_chunk_size,
            extended_chunk_nums=args.extended_chunk_nums,
        )
    else:
        vector_store = create_vector_store_from_dir(
            args.document_dir,
            max_chunk_size=args.max_chunk_size,
            extended_chunk_nums=args.extended_chunk_nums,
        )
    vector_store.save_local(vector_store_path)
    print(f"Vector store saved at {vector_store_path}")

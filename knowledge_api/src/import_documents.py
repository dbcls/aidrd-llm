import argparse
import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader

from langchain.docstore.document import Document
import csv
import dotenv
from langchain_openai import AzureOpenAIEmbeddings


dotenv.load_dotenv(override=True)


def create_vector_store(
    document_dir_path: str, max_chunk_size=2000, preffered_chunk_size=500
) -> FAISS:
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT_ID"]
    )
    loader = DirectoryLoader(
        document_dir_path,
        loader_kwargs={
            "chunking_strategy": "basic",
            "max_characters": max_chunk_size,
            "new_after_n_chars": preffered_chunk_size,
        },
    )
    print("Loading documents...")
    docs = loader.load()
    print(f"Loaded {len(docs)} documents.")
    return FAISS.from_documents(docs, embeddings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a vector store from a directory of documents."
    )
    parser.add_argument(
        "document_dir_path", type=str, help="Path to the directory of documents."
    )
    parser.add_argument(
        "--max-chunk-size", type=int, default=2000, help="Maximum size of each chunk."
    )
    parser.add_argument(
        "--preferred-chunk-size",
        type=int,
        default=500,
        help="Preferred size of each chunk.",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Path to save the vector store. If not provided, the vector store will be saved in VECTOR_STORE_PATH environment variable.",
    )
    args = parser.parse_args()

    vector_store_path = args.output_path or os.environ.get("VECTOR_STORE_PATH")

    vector_store = create_vector_store(
        args.document_dir_path,
        max_chunk_size=args.max_chunk_size,
        preffered_chunk_size=args.preferred_chunk_size,
    )
    vector_store.save_local(vector_store_path)
    print(f"Vector store saved at {vector_store_path}")

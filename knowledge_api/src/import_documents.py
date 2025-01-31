import argparse
import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader

from langchain.docstore.document import Document
import csv
import dotenv
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings


dotenv.load_dotenv(override=True)


def create_vector_store(
    document_dir_path: str,
    max_chunk_size=600,
    extended_chunk_nums=1,
) -> FAISS:
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT_ID"]
    )
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a vector store from a directory of documents."
    )
    parser.add_argument(
        "document_dir_path", type=str, help="Path to the directory of documents."
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

    vector_store = create_vector_store(
        args.document_dir_path,
        max_chunk_size=args.max_chunk_size,
        extended_chunk_nums=args.extended_chunk_nums,
    )
    vector_store.save_local(vector_store_path)
    print(f"Vector store saved at {vector_store_path}")

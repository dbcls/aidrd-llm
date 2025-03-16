import uvicorn
import dotenv
from pydantic import BaseModel, Field
import os
import sys
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings


app = FastAPI()

dotenv.load_dotenv()

if not os.getenv("EXTERNAL_KNOWLEDGE_API_KEY"):
    raise ValueError(
        "API key is not set. Configure 'EXTERNAL_KNOWLEDGE_API_KEY' in environment variables."
    )
else:
    api_key = os.getenv("EXTERNAL_KNOWLEDGE_API_KEY")

api_key_header = APIKeyHeader(name="Authorization", auto_error=True)


def verify_token(auth_header: str = Depends(api_key_header)):
    if auth_header is not None:
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Authorization header must be Bearer token"
            )
    token = auth_header.split(" ")[1]
    if token != api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token",
        )


class RetrievalParameter(BaseModel):
    top_k: int = Field(description="Maximum number of retrieval", example=10)
    score_threshold: float = Field(
        ...,
        description="The threshold of score",
        example=0.5,
    )


class RequestBody(BaseModel):
    knowledge_id: str = Field(description="ID of knowledge", example="AAA-BBB-CCC")
    query: str = Field(description="Query", example="What is Perkinson's disease?")
    retrieval_setting: RetrievalParameter = Field(
        description="Parameters for retrieval"
    )


embeddings = AzureOpenAIEmbeddings(
    azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT_ID"]
)

vector_store_path = os.environ["VECTOR_STORE_PATH"]
if not os.path.exists(vector_store_path):
    vector_store = FAISS.from_documents([], embeddings)
else:
    vector_store = FAISS.load_local(
        os.environ["VECTOR_STORE_PATH"],
        embeddings,
        allow_dangerous_deserialization=True,
    )


#
# Endpoints
#
@app.post("/retrieval")
async def retrieval(
    request: RequestBody,
    token: str = Depends(verify_token),
):
    docs = vector_store.similarity_search_with_score(
        request.query, top_k=request.retrieval_setting.top_k
    )

    result = [
        {
            "content": (
                "".join(doc.metadata["extended_chunks"])
                if "extended_chunks" in doc.metadata
                else doc.page_content
            ),
            "score": float(score),
            "title": doc.metadata.get("source"),
            "metadata": doc.metadata,
        }
        for doc, score in docs
        if score >= request.retrieval_setting.score_threshold
    ]

    return JSONResponse(
        content={"records": result[: request.retrieval_setting.top_k]}, status_code=200
    )


if __name__ == "__main__":
    if os.environ.get("USE_NGROK_FOR_EXTERNAL_KNOWLEDGE"):
        from pyngrok import ngrok

        # Set auth_token for ngrok
        ngrok.set_auth_token(os.environ.get("NGROK_AUTH_TOKEN"))
        ngrok.kill()
        public_url = ngrok.connect(8000).public_url
        print(f"Public URL: {public_url}")

    uvicorn.run(
        "api:app",
        log_level="debug",
        reload=True,
    )

# API for Dify Knowledge

This is the API that works as an external knowledge base of Dify.

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Config App

Create a file named `.env` in the root directory. Setting the following content:

```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_EMBEDDING_DEPLOYMENT_ID=
EXTERNAL_KNOWLEDGE_API_KEY=
VECTOR_STORE_PATH=
USE_NGROK_FOR_EXTERNAL_KNOWLEDGE=false
NGROK_AUTH_TOKEN=
```

### Start the app

Start the app as a docker container. The default port is 8000.
If you want to use ngrok for external knowledge, set `USE_NGROK_FOR_EXTERNAL_KNOWLEDGE` to `true` and set `NGROK_AUTH_TOKEN` to your ngrok auth token.
The public URL of the external knowledge will be printed in the console.

```bash
docker compose up -d
```

### Loading Knowledge

To load knowledge, first create a directory named `knowledge_docs` in this directory.
Then, put the knowledge documents in the `knowledge_docs` directory.
After that, you can use the following command:

```bash
docker compose exec api python src/import_documents.py knowledge_docs/
```

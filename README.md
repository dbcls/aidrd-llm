# AIDRD LLM

## Quick Start

### Prerequisites

- Docker

### Installation

```
cp .env.example .env
docker-compose up -d
```

## Crawl documents for knowledge base

- To crawl the document for the knowledge base, prepare Firecrawl endpoint.

  - Official: https://github.com/mendableai/firecrawl/blob/main/SELF_HOST.md
  - Japanese blog: https://zenn.dev/kun432/scraps/58fce97899cfdd

- Run the following command to crawl the documents.
  - If you prepare the firecrawl endpoint other than `localhost:3002`, specify the endpoint by `--firecrawl-host` option.
  - Note that you should execute this command outside the docker container to access the local firecrawl endpoint.

```
python crawl_knowledges.py <URL_TO_START_CRAWLING> <OUTPUT_FILE_NAME> --max-page-count <MAX_PAGE_COUNT> --max-depth <MAX_DEPTH>
```

- For example:

```
python crawl_knowledges.py "https://www.hokeniryo.metro.tokyo.lg.jp/kenkou/nanbyo/portal/" tokyo.json --max-page-count 1000 --max-depth 5
```

- The crawled documents will be saved in `tokyo.json` and PDFs are saved in `downloaded_pdfs` directory.

## Upload knowledge base to Dify

- To upload the knowledge base to Dify, update the `.env` file with the required values

```
KNOWLEDGE_API_KEY=<DIFY_KNOWLEDGE_API_KEY>
API_BASE_URL=<DIFY_BASE_URL> # e.g. http://aidrd.japaneast.cloudapp.azure.com/v1
```

- Run the following command to upload the knowledge base to Dify
  - Note that you should execute this command in the same directory as the crawled knowledge JSON file because the JSON file includes relative paths to the PDFs.

```
python upload_knowledge.py <CRAWLED_KNOWLEDGE_FILE> <KNOWLEDGE_BASE_NAME>
```

- For example:

```
python upload_knowledge.py tokyo.json tokyo-knowledges
```

- At Dify 0.6.15, The created knowledge base has `only_me` visibility by default and visible only for the owner of Dify workspace.
- If you cannot see the uploaded knowledge base, please execute the following SQL query to change the visibility.

```sql
UPDATE datasets set permission = 'all_team_members' WHERE name = '<KNOWLEDGE_BASE_NAME>';
```

## Evaluation

- To evaluate the accuracy of your Dify chatbot, update the `.env` file with the required values

```
API_BASE_URL=<YOUR_DIFY_BASE_URL>
CHATBOT_API_KEY=<YOUR_CHATBOT_API_KEY>
DIFY_USER=<DIFY_USER_NAME> # Just for logging purposes. Can be anything
AZURE_DEPLOYMENT_ID=<YOUR_AZURE_DEPLOYMENT_ID> # The deployment id of your LLM model. This model evaluates the chatbot responses
```

- Restart the container

```
docker-compose restart
```

- Run the evaluation script
  - The evaluation data should be located in evaluation_data.json

```
docker-compose exec app python evaluation.py
```

- The evaluation results will be located in `evaluation_results_<timestamp>.json`

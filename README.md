# AIDRD LLM

## Quick Start

### Prerequisites

- Docker

### Installation

```
cp .env.example .env
docker-compose up -d
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

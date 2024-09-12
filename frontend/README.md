# Nanbyo support chat

## Quick Start

### Prerequisites
- Docker and Docker Compose

### Config App
Create a file named `.env.local` in the current directory and copy the contents from `.env.example`. Setting the following content:
```
# Dify APP ID
NEXT_PUBLIC_APP_ID=
# API Key for the Dify chatbot and knowledge API
NEXT_PUBLIC_APP_KEY=
NEXT_PUBLIC_KNOWLEDGE_API_KEY=
# API url prefix such as https://api.dify.ai
NEXT_PUBLIC_API_URL=

# Basic Auth
BASIC_AUTH_ENABLED=true # set to false to disable basic auth
BASIC_AUTH_ID=<id of basic auth>
BASIC_AUTH_PASSWORD=<password of basic auth>

# Whether to add the text fragment to the citation URLs
NEXT_PUBLIC_CITE_WITH_FRAGMENTS=true
```

### Start the app

* Start the app as a docker container (the default port is 3000)

```bash
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

* For production deployment, please switch the following lines in `docker-compose.yåml` file.

```yaml
    # command: npm run dev                              # for development
    command: sh -c "npm run build && npm run start" # for production
```
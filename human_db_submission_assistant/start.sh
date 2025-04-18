#!/bin/bash

# Load environment variables from .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "Error: .env file not found. Please create a .env file and try again."
  exit 1
fi

# Check the value of DEPLOY_MODE
if [ "$DEPLOY_MODE" == "development" ]; then
  echo "Starting in development mode..."
  docker compose -f docker-compose.yml -f docker-compose-dev.yml up -d
elif [ "$DEPLOY_MODE" == "production" ]; then
  echo "Starting in production mode..."
  docker compose -f docker-compose.yml up -d
else
  echo "Error: Invalid DEPLOY_MODE value. Please set it to 'development' or 'production' in the .env file."
  exit 1
fi

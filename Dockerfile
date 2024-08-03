FROM python:3.11-slim

WORKDIR /src

RUN apt-get update && apt-get install --no-install-recommends -y gcc g++ git procps


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


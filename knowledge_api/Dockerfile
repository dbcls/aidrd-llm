FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y gcc g++ git procps libopencv-dev poppler-utils tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


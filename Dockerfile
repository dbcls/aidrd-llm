FROM python:3.12-slim

WORKDIR /src

RUN apt-get update && apt-get install --no-install-recommends -y gcc g++ git procps libopencv-dev poppler-utils tesseract-ocr

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m nltk.downloader punkt_tab
RUN python -m nltk.downloader averaged_perceptron_tagger_eng


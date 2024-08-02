FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /src

RUN apt-get update && apt-get install --no-install-recommends -y gcc g++ git procps


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 日本語環境の追加
RUN apt-get update && apt-get install -y locales language-pack-ja-base language-pack-ja \
    && sed -i -e 's/# \(ja_JP.UTF-8\)/\1/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=ja_JP.UTF-8

ENV LANG ja_JP.UTF-8
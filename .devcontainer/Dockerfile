FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system dependencies required by the project (pdf2image needs poppler)
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

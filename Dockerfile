FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN chown 1000:0 /app && chmod 777 /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=1000:0 src/ ./src/
COPY --chown=1000:0 main.py .
COPY --chown=1000:0 prompt.txt .

RUN chmod -R g+w /app

USER 1000

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY prompt.txt .

RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "main.py", "--mode", "auto"]

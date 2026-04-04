import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.config import settings
from src.paperless_client import PaperlessClient
from src.llm_client import OllamaClient
from src.utils import logger, get_user_prompt
from src.processor import process_single_document

class WebhookPayload(BaseModel):
    document_id: int | None = None
    id: int | None = None

    def get_id(self) -> int:
        if self.document_id is not None:
            return self.document_id
        if self.id is not None:
            return self.id
        raise ValueError("No document ID found in payload")


def handle_webhook_task(doc_id: int, p_client: PaperlessClient, o_client: OllamaClient, dry_run: bool):
    try:
        p_client.refresh_metadata()
        prompt = get_user_prompt(p_client)
        process_single_document(doc_id, prompt, p_client, o_client, dry_run)
    except Exception as e:
        logger.error(f"Error in background task for document {doc_id}: {e}")


def run_webhook_mode(p_client: PaperlessClient, o_client: OllamaClient, dry_run: bool):
    """Starts a FastAPI server for webhooks."""
    app = FastAPI(title="PaperLlama Webhook Server")

    @app.post("/webhook")
    async def handle_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
        try:
            doc_id = payload.get_id()
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        logger.info(f"Webhook received for document {doc_id}")
        
        # Schedule the processing task in the background
        background_tasks.add_task(
            handle_webhook_task, 
            doc_id, 
            p_client, 
            o_client, 
            dry_run
        )
        return {"status": "Processing scheduled", "document_id": doc_id}

    logger.info(f"Starting webhook mode on {settings.webhook_host}:{settings.webhook_port}")
    uvicorn.run(app, host=settings.webhook_host, port=settings.webhook_port)

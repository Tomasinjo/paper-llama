import argparse
import sys
import time
from src.config import settings
from src.paperless_client import PaperlessClient
from src.llm_client import OllamaClient
from src.utils import logger, get_user_prompt


def process_single_document(doc_id: int, p_client: PaperlessClient, o_client: OllamaClient, dry_run: bool):
    try:
        doc = p_client.get_document(doc_id)
        logger.info(f"Processing Document {doc.id}: '{doc.title}'")
        
        if not doc.content:
            logger.warning(f"Document {doc.id} has no OCR content. Skipping.")
            return

        llm_result = o_client.process_document(doc.content)
        logger.info(f"LLM Suggestions: {llm_result.model_dump_json()}")
        
        if dry_run:
            logger.info("Not updating document due to dry run")
            return

        p_client.update_document(doc, llm_result)

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}", exc_info=True)


def run_auto_mode(p_client: PaperlessClient, o_client: OllamaClient, dry_run: bool):
    """Continuous loop for docker usage"""
    logger.info(f"Starting automatic mode (Interval: {settings.scan_interval}s)")
    
    while True:
        try:
            docs = p_client.get_documents_to_process()
            
            if not docs:
                logger.info("No new documents found.")
            else:
                logger.info(f"Found {len(docs)} documents to process.")
                for doc in docs:
                    process_single_document(doc.id, p_client, o_client, dry_run)
        
        except Exception as e:
            logger.error(f"Error in auto loop: {e}")
        
        logger.info(f"Sleeping for {settings.scan_interval} seconds...")
        time.sleep(settings.scan_interval)


def run():
    parser = argparse.ArgumentParser(description="PaperLlama")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto", help="Execution mode")
    parser.add_argument("--doc-id", type=int, help="Document ID for manual mode")
    parser.add_argument("--dry-run", action="store_true", help="Log changes without applying them to Paperless")
    
    args = parser.parse_args()

    try:
        p_client = PaperlessClient()
        o_client = OllamaClient(user_prompt=get_user_prompt(p_client))
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")
        sys.exit(1)



    if args.mode == "manual":
        if not args.doc_id:
            logger.error("Manual mode requires --doc-id")
            sys.exit(1)
        process_single_document(args.doc_id, p_client, o_client, args.dry_run)
        
    elif args.mode == "auto":
        run_auto_mode(p_client, o_client, args.dry_run)

if __name__ == "__main__":
    run()

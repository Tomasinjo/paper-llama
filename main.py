import argparse
import sys
import time
from src.config import settings
from src.paperless_client import PaperlessClient
from src.llm_client import OllamaClient
from src.utils import logger, get_user_prompt, pdf_to_images



def process_single_document(doc_id: int, 
                            prompt: str, 
                            p_client: PaperlessClient, 
                            o_client: OllamaClient, 
                            dry_run: bool):
    try:
        logger.info(f"Processing Document {doc_id}")
        
        doc = p_client.get_document(doc_id)

        if settings.ocr_source == 'llm':
            pdf_bytes = p_client.get_original_pdf(doc_id)
            images = pdf_to_images(pdf_bytes)
            if len(images) > settings.llm_ocr_source_page_limit:
                logger.warning(f"Document {doc_id} has {len(images)} pages which is more than configured limit {settings.llm_ocr_source_page_limit}. Falling back to paperless OCR.")
                ocr_text = doc.content
            else:
                logger.info(f"Retrieved PDF for Document {doc_id} ({len(pdf_bytes)} bytes)")
                ocr_text = o_client.perform_ocr(images)
        else:
            ocr_text = doc.content

        # Process the OCR text with LLM for classification
        llm_result = o_client.process_document(prompt, ocr_text)
        logger.info(f"LLM Suggestions: {llm_result.model_dump_json()}")
        
        if dry_run:
            logger.warning("Not updating document due to dry run")
            return
        
        logger.info(f"Updating Document {doc.id}: '{doc.title}'")
        p_client.send_ocr(doc_id, ocr_text)
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
                p_client.refresh_metadata()
                prompt = get_user_prompt(p_client)
                for doc in docs:
                    process_single_document(doc.id, prompt, p_client, o_client, dry_run)
        
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
        o_client = OllamaClient()
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")
        sys.exit(1)



    if args.mode == "manual":
        if not args.doc_id:
            logger.error("Manual mode requires --doc-id")
            sys.exit(1)
        p_client.refresh_metadata()
        prompt = get_user_prompt(p_client)
        process_single_document(args.doc_id, prompt, p_client, o_client, args.dry_run)
        
    elif args.mode == "auto":
        run_auto_mode(p_client, o_client, args.dry_run)

if __name__ == "__main__":
    run()

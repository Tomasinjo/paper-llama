from src.config import settings
from src.paperless_client import PaperlessClient
from src.llm_client import OllamaClient
from src.utils import logger, pdf_to_images

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

import requests
import json
import base64
import io
from typing import List
from PIL import Image
from src.config import settings
from src.utils import logger, extract_json_from_text
from src.models import LLMResponse

class OllamaClient:
    def __init__(self, user_prompt):
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.user_prompt = user_prompt
        logger.debug(f"User prompt is:\n\n{user_prompt}")

    def process_document(self, ocr_text: str) -> LLMResponse:
        full_prompt = f"{self.user_prompt}\n\n{ocr_text[:64000]}" # Truncate to avoid context limits if necessary

        logger.debug(f"Sending prompt to Ollama (len={len(full_prompt)})")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json" # Force json mode if model supports it
                },
                timeout=120
            )
            response.raise_for_status()
            result_text = response.json().get("response", "")
            
            logger.info("Received response from Ollama")
            logger.debug(f"Raw Response: {result_text}")

            data = extract_json_from_text(result_text)
            return LLMResponse(**data)

        except Exception as e:
            logger.error(f"Ollama API Error: {str(e)}")
            raise

    def perform_ocr(self, images: list[Image.Image]) -> str:
        """
        Perform OCR on images with LLM vision.
        
        Args:
            images: list of PIL images
            
        Returns:
            The OCR text extracted from the document
        """

        ocr_text_parts = []
        
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1}/{len(images)}...")
            
            # Convert image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Send to Ollama for OCR
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": "Extract all text from this image. Return only the text content without any additional commentary.",
                        "images": [img_base64],
                        "stream": False
                    },
                    timeout=120
                )
                response.raise_for_status()
                page_text = response.json().get("response", "")
                ocr_text_parts.append(page_text)
                logger.debug(f"Extracted {len(page_text)} characters from page {i+1}")
                
            except Exception as e:
                logger.error(f"Error processing page {i+1} with Ollama: {str(e)}")
                ocr_text_parts.append(f"[OCR Error on page {i+1}]")
        
        full_ocr_text = "\n\n".join(ocr_text_parts)
        logger.info(f"OCR complete. Total text length: {len(full_ocr_text)} characters")
        logger.debug(f"OCR text:\n{full_ocr_text}")
        return full_ocr_text
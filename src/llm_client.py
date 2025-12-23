import requests
import json
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
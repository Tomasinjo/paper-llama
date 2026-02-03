import logging
import json
import re
from PIL import Image
from pdf2image import convert_from_bytes
from src.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("classifier.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("paper-llama")

logger = setup_logging()

def extract_json_from_text(text: str) -> dict:
    """
    JSON extraction from LLM response. Handles markdown code blocks or raw JSON.
    """
    try:
        # Try raw parse first
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Look for markdown code blocks
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Look for bracketed content
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from LLM response")


def get_user_prompt(p_client):
    with open(settings.prompt_file, 'r') as f:
        user_prompt_template = f.read()

    replacable = re.findall(r'%\w+%', user_prompt_template)
    logger.info(f"Found the following variables to replace in prompt: {replacable}")
    to_replace = {}
    for vtag in replacable:
        if vtag == "%TAGS%":
            user_prompt_template = user_prompt_template.replace(
                vtag,
                json.dumps(list(p_client._tags_map.keys()))
            )
        elif vtag == "%TYPES%":
            user_prompt_template = user_prompt_template.replace(
                vtag,
                json.dumps(list(p_client._types_map.keys()))
            )
        elif vtag == "%CORRESPONDENTS%":
            user_prompt_template = user_prompt_template.replace(
                vtag,
                json.dumps(list(p_client._correspondents_map.keys()))
            )
    return user_prompt_template


def pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    logger.info("Converting PDF to images for OCR...")
    images = convert_from_bytes(pdf_bytes)
    logger.info(f"Converted PDF to {len(images)} page(s)")
    return images
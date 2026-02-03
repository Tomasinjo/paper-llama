from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    paperless_url: str
    paperless_token: str
    paperless_ai_tag: str = "ai-processed"
    
    ollama_url: str
    ollama_model: str
    
    prompt_file: str = "prompt.txt"
    log_level: str = "INFO"
    override_existing_tags: bool = True
    ocr_source: Literal["paperless", "llm"] = "paperless"
    llm_ocr_source_page_limit: int

    scan_interval: int = 600  # seconds, default 10 minuts
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    paperless_url: str
    paperless_token: str
    paperless_ai_tag: str = "ai-processed"
    
    ollama_url: str
    ollama_model: str
    
    prompt_file: str = "prompt.txt"
    log_level: str = "INFO"
    override_existing_tags: bool = True

    scan_interval: int = 600  # seconds, default 10 minuts

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
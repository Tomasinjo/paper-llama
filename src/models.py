from typing import List, Optional
from pydantic import BaseModel, Field

class PaperlessDocument(BaseModel):
    id: int
    title: str
    content: str  # OCR text
    tags: List[int] = []
    correspondent: Optional[int] = None
    document_type: Optional[int] = None
    created: str

class LLMResponse(BaseModel):
    title: Optional[str] = None
    created: Optional[str] = None
    correspondent: Optional[str] = None
    document_type: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
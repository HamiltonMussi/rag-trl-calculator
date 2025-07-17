from pydantic import BaseModel
from typing import List, Optional

class Ask(BaseModel):
    question: str
    technology_id: str
    doc_ids: Optional[List[str]] = None

class FileUpload(BaseModel):
    technology_id: str
    filename: str
    content_base64: str
    chunk_index: int = 0
    final: bool = True

class ProcessingStatus(BaseModel):
    technology_id: str 
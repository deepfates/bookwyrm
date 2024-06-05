from pydantic import BaseModel, validator
from typing import List, Dict
import numpy as np

class Document(BaseModel):
    text: str
    source: str
    metadata: Dict
    num_files: int = 0
    num_chars: int = 0
    num_tokens: int = 0

class TextChunk(BaseModel):
    text: str
    document_index: int = 0
    local_index: int = 0
    global_index: int = 0

class DocumentRecord(BaseModel):
    index: int
    uri: str
    metadata: Dict
import base64

class Bookwyrm(BaseModel):
    documents: List[DocumentRecord]
    chunks: List[TextChunk]
    embeddings: str

    class Config:
        arbitrary_types_allowed = True

    @validator('embeddings', pre=True)
    def convert_np_array_to_base64(cls, v):
        """Convert numpy array to base64 string during model creation"""
        return base64.b64encode(v.tostring()).decode('utf-8')

    @validator('embeddings', pre=False)
    def convert_base64_to_np_array(cls, v):
        """Convert base64 string back to numpy array when accessing the field"""
        return np.fromstring(base64.b64decode(v), dtype=np.float32)
    
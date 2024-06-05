import json
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
    
class Bookwyrm(BaseModel):
    documents: List[DocumentRecord]
    chunks: List[TextChunk]
    embeddings: np.ndarray

    class Config:
        arbitrary_types_allowed = True

    def to_json(self):
        return json.dumps(self.dict(), indent=4, cls=NumpyEncoder)

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

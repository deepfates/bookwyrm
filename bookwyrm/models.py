import json
from pydantic import BaseModel
from typing import List, Dict
import numpy as np

class Document(BaseModel):
    """
    Represents a document with its text, source, and metadata.

    Attributes:
        text (str): The text content of the document.
        source (str): The source of the document.
        metadata (Dict): Metadata associated with the document.
        num_files (int): Number of files in the document. Default is 0.
        num_chars (int): Number of characters in the document. Default is 0.
        num_tokens (int): Number of tokens in the document. Default is 0.
    """
    text: str
    source: str
    metadata: Dict
    num_files: int = 0
    num_chars: int = 0
    num_tokens: int = 0

class TextChunk(BaseModel):
    """
    Represents a chunk of text from a document.

    Attributes:
        text (str): The text content of the chunk.
        document_index (int): Index of the document this chunk belongs to. Default is 0.
        local_index (int): Local index of the chunk within the document. Default is 0.
        global_index (int): Global index of the chunk across all documents. Default is 0.
    """
    text: str
    document_index: int = 0
    local_index: int = 0
    global_index: int = 0

class DocumentRecord(BaseModel):
    """
    Represents a record of a document with its index, URI, and metadata.

    Attributes:
        index (int): Index of the document.
        uri (str): URI of the document.
        metadata (Dict): Metadata associated with the document.
    """
    index: int
    uri: str
    metadata: Dict
    
class Bookwyrm(BaseModel):
    """
    Represents the Bookwyrm model containing documents, chunks, and embeddings.

    Attributes:
        documents (List[DocumentRecord]): List of document records.
        chunks (List[TextChunk]): List of text chunks.
        embeddings (np.ndarray): Array of embeddings.
    """
    documents: List[DocumentRecord]
    chunks: List[TextChunk]
    embeddings: np.ndarray

    class Config:
        arbitrary_types_allowed = True

    def to_json(self) -> str:
        """
        Convert the Bookwyrm instance to a JSON string.

        Returns:
            str: JSON string representation of the Bookwyrm instance.
        """
        return json.dumps(self.dict(), indent=4, cls=NumpyEncoder)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Bookwyrm':
        """
        Create a Bookwyrm instance from a JSON string.

        Args:
            json_str (str): JSON string representing a Bookwyrm instance.

        Returns:
            Bookwyrm: An instance of the Bookwyrm class.
        """
        data = json.loads(json_str)
        documents = [DocumentRecord(**doc) for doc in data['documents']]
        chunks = [TextChunk(**chunk) for chunk in data['chunks']]
        embeddings = np.array(data['embeddings'])
        return cls(documents=documents, chunks=chunks, embeddings=embeddings)
    
    

class NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for numpy arrays.
    """
    def default(self, obj):
        """
        Convert numpy arrays to lists for JSON serialization.

        Args:
            obj: Object to be serialized.

        Returns:
            list: List representation of the numpy array.
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

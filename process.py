from typing import List
import asyncio
import numpy as np
from tqdm import tqdm
import logging
from utils import embedding_api
from models import Document, TextChunk

def chunk(documents: List[Document], window_size: int = 800, overlap: int = 0) -> List[TextChunk]:
    """
    Chunk the documents into smaller pieces.
    Keeping the order and tagging the chunks with the document index, local index, and global index.
    Flattening all the documents into one list of chunks.

    Args:
        documents (List[Document]): List of documents to chunk.
        window_size (int): Size of each chunk window.
        overlap (int): Overlap between chunks.

    Returns:
        List[TextChunk]: List of text chunks.
    """
    chunks = []
    g = 0
    for i, document in enumerate(tqdm(documents, desc="Chunking documents")):
        text = document.text
        logging.info(f"Chunking document {i} with {len(text)} characters")
        for j in range(0, len(text), window_size):
            chunk = TextChunk(
                text=text[j:j+window_size],
                document_index=i,
                local_index=j,
                global_index=g
            )
            chunks.append(chunk)
            g += 1
    logging.info(f"Chunked {len(chunks)} chunks")
    return chunks

def encode(chunks: List[TextChunk]) -> np.ndarray:
    """
    Encode the chunks using the embedding API.
    The embedding API takes a list of texts and returns a list of embeddings.
    It does batching for us.

    Args:
        chunks (List[TextChunk]): List of text chunks to encode.

    Returns:
        np.ndarray: Array of embeddings.
    """
    texts = [chunk.text for chunk in chunks]
    logging.info(f"Encoding {len(chunks)} chunks")
    try:
        embeddings = embedding_api(texts)
        logging.info(embeddings)
        logging.info(f"Received {len(embeddings)} embeddings")
        logging.info(f"Embedding shape: {embeddings[0].shape}")
        logging.info(f"Embedding type: {type(embeddings[0])}")
        return embeddings
    except Exception as e:
        # Handle potential errors from the embedding API
        logging.error(f"Error encoding chunks: {e}")
        return np.array([])

def process_chunks(documents: List[Document]) -> np.ndarray:
    """
    Process the documents by chunking and encoding them.

    Args:
        documents (List[Document]): List of documents to process.

    Returns:
        np.ndarray: Array of embeddings for the document chunks.
    """
    logging.info("Starting to process documents")
    chunks = chunk(documents)
    embeddings = encode(chunks)
    logging.info("Finished processing documents")
    return embeddings

if __name__ == "__main__":
    from scrape import scrape
    processed_data = scrape()
    result = process_chunks(processed_data)
    print(len(result))

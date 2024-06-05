import logging

from .scrape import scrape
from .process import chunk, encode
from .models import DocumentRecord, Bookwyrm
from .utils import test_tasks

async def process_documents(urls: list) -> Bookwyrm:
    """
    Process the documents by chunking and encoding them.

    Args: 
        urls (list): List of URLs to process.

    Returns:
        dict: Dictionary with keys 'documents', 'chunks', and 'embeddings'.
    """
    documents = await scrape(urls)
    chunks = chunk(documents)
    data = await encode(chunks) 
    logging.info("Finished processing documents")
    logging.info(f"Embeddings shape: {data.shape}")
    logging.info(f"Documents: {len(documents)}")
    logging.info(f"Chunks: {len(chunks)}")
    
    bookwyrm = Bookwyrm(
        documents=[DocumentRecord(index=i, uri=document.source, metadata=document.metadata) for i, document in enumerate(documents)],
        chunks=chunks,
        embeddings=data
    )

    logging.info("Finished processing documents")

    return bookwyrm

async def main():
    urls = test_tasks
    output = await process_documents(urls)
    return output 

if __name__ == "__main__":
    import asyncio
    out = asyncio.run(main())
    with open("wyrm.json", "w") as f:       
        f.write(out.to_json())

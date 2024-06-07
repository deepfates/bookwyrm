import aiohttp
from io import BytesIO
from PyPDF2 import PdfReader

from bookwyrm.models import Document
from .document import create_document

async def process_arxiv_pdf(arxiv_abs_url) -> Document:
    pdf_url = arxiv_abs_url.replace("/abs/", "/pdf/") + ".pdf"
    async with aiohttp.ClientSession() as session:
        async with session.get(pdf_url) as response:
            response.raise_for_status()
            pdf_content = await response.read()

    text = []
    with BytesIO(pdf_content) as pdf_file:
        pdf_reader = PdfReader(pdf_file)
        for page in range(len(pdf_reader.pages)):
            text.append(pdf_reader.pages[page].extract_text())

    return create_document(' '.join(text), arxiv_abs_url)

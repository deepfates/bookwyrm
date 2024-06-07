import logging
import aiohttp
from bs4 import BeautifulSoup
from io import BytesIO
from PyPDF2 import PdfReader

from bookwyrm.models import Document
from .document import create_document
from .scrape import is_same_domain, is_within_depth


async def crawl_and_extract_text(base_url, max_depth=2, include_pdfs=True, ignore_epubs=True) -> Document:
    async with aiohttp.ClientSession() as session:
        processed_urls = set()
        all_text = ""

        async def crawl(url, depth=0):
            nonlocal all_text
            if depth > max_depth or url in processed_urls:
                return

            processed_urls.add(url)

            async with session.get(url) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    try:
                        soup = BeautifulSoup(await response.text(), "html.parser")
                        text = soup.get_text()
                        all_text += f"\n\n# URL: {url}\n{text}"
                          
                        for link in soup.find_all("a"):
                            href = link.get("href")
                            if href and href.startswith("http") and is_same_domain(base_url, href) and is_within_depth(base_url, href, max_depth):
                                await crawl(href, depth + 1)
                    except UnicodeDecodeError:
                        logging.info(f"Skipping URL {url} due to encoding issues.")
                        all_text += f"\n\n# URL: {url}\nSkipped due to encoding issues."
                      
                elif include_pdfs and "application/pdf" in content_type:
                    content = await response.read()
                    with BytesIO(content) as file:
                        reader = PdfReader(file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text()
                    all_text += f"\n\n# PDF URL: {url}\n{text}"
                elif ignore_epubs and "application/epub" in content_type:
                    pass
                else:
                    all_text += f"\n\n# URL: {url}\nUnsupported content type: {content_type}"

        await crawl(base_url)

        return create_document(all_text, base_url)



import aiohttp
from bookwyrm.models import Document
from .document import create_document


async def process_doi_or_pmid(identifier) -> Document:
    url = f"https://api.semanticscholar.org/v1/paper/{identifier}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

            # if there is no data, we need to return an empty document
            if not data:
                return create_document("", identifier)
            
            title = data.get("title", "")
            abstract = data.get("abstract", "")
            authors = ", ".join([author["name"] for author in data.get("authors", [])])
            year = data.get("year", "")
            venue = data.get("venue", "")
            url = data.get("url", "")

            text = f"# Title: {title}\n\n"
            text += f"## Authors: {authors}\n\n"
            text += f"## Year: {year}\n\n"
            text += f"## Venue: {venue}\n\n"
            text += f"## URL: {url}\n\n"
            text += f"## Abstract:\n{abstract}\n"

            return create_document(text, identifier)
       
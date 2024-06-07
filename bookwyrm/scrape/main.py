import asyncio
import logging
import os
import re
from typing import List
from urllib.parse import urlparse

from bookwyrm.models import Document
from bookwyrm.utils import TEST_TASKS
from .doi import process_doi_or_pmid
from .github import process_github_repo, process_github_pull_request, process_github_issue
from .arxiv import process_arxiv_pdf
from .youtube import fetch_youtube_transcript
from .web import crawl_and_extract_text
from .local import process_local_folder
# Configure logging
logging.basicConfig(level=logging.INFO)

def get_task_type(task) -> str:
    parsed_url = urlparse(task)
    if parsed_url.netloc == "github.com":
        if "/pull/" in parsed_url.path:
            return "github_pull_request"
        elif "/issues/" in parsed_url.path:
            return "github_issue"
        else:
            return "github_repo"
    elif parsed_url.netloc == "arxiv.org":
        return "arxiv"
    elif os.path.exists(task):
        return "local_folder"
    elif "youtube.com" in task or "youtu.be" in task:
        return "youtube_transcript"
    elif parsed_url.scheme in ["http", "https"]:
        return "web_content"
    elif re.match(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", task, re.IGNORECASE):
        return "doi_or_pmid"
    else:
        raise ValueError(f"Unsupported task: {task}")


async def process_task(task) -> Document:
    task_type = get_task_type(task)
    match task_type:
        case "github_repo":
            return await process_github_repo(task)
        case "github_pull_request":
            return await process_github_pull_request(task)
        case "github_issue":
            return await process_github_issue(task)
        case "arxiv":
            return await process_arxiv_pdf(task)
        case "local_folder":
            return await process_local_folder(task)
        case "youtube_transcript":
            return await fetch_youtube_transcript(task)
        case "web_content":
            return await crawl_and_extract_text(task, max_depth=2, include_pdfs=True, ignore_epubs=True)
        case "doi_or_pmid":
            return await process_doi_or_pmid(task)
        case _:
            raise ValueError(f"Unsupported task: {task}")

async def scrape_async(tasks) -> List[Document]:
    processed_data_list = await asyncio.gather(*[process_task(task) for task in tasks])
    return processed_data_list

async def scrape(tasks = TEST_TASKS) -> List[Document]:
    data = await scrape_async(tasks)
    return data


if __name__ == "__main__":
    processed_data = scrape()
    logging.info(processed_data)

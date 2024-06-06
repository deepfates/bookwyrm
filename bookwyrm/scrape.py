import asyncio
import time

from typing import List
from urllib.parse import urlparse
import re
import os
import logging
from io import BytesIO
import aiohttp

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from nbconvert import PythonExporter
import nbformat
import nltk
from nltk.corpus import stopwords

from dotenv import load_dotenv

from .models import Document
from .utils import get_token_count, test_tasks

# Load the .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)


nltk.download("stopwords", quiet=True)
stop_words = set(stopwords.words("english"))


TOKEN = os.getenv('GITHUB_TOKEN', 'default_token_here')
if TOKEN == 'default_token_here':
    logging.warning("GITHUB_TOKEN environment variable not set. Using default token.")

headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {TOKEN}"
    }


def create_document(text, source, metadata=None):
    if metadata is None:
        metadata = {}
    return Document(
        text=text,
        source=source,
        metadata=metadata,
        num_files=len(text.split("# ---")),
        num_chars=len(text),
        num_tokens=get_token_count(text)
    )

async def handle_rate_limit(response):
    if response.status == 403 and "X-RateLimit-Remaining" in response.headers:
        remaining = int(response.headers["X-RateLimit-Remaining"])
        if remaining == 0:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            sleep_time = max(0, reset_time - time.time())
            logging.info(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

async def process_file_in_repo(file, repo_content, session):
    logging.info(f"Processing {file['path']}...")

    temp_file = f"temp_{file['name']}"
    await download_file(file["download_url"], temp_file, session)

    repo_content.append(f"# {'-' * 3}\n")
    repo_content.append(f"# Filename: {file['path']}\n")
    repo_content.append(f"# {'-' * 3}\n\n")

    if file["name"].endswith(".ipynb"):
        repo_content.append(process_ipynb_file(temp_file))
    else:
        with open(temp_file, "r", encoding='utf-8', errors='ignore') as f:
            repo_content.append(f.read())

    repo_content.append("\n\n")
    os.remove(temp_file)

async def process_directory(url, repo_content, session):
    async with session.get(url, headers=headers) as response:
        await handle_rate_limit(response)
        response.raise_for_status()
        files = await response.json()

        tasks = []
        for file in files:
            if file["type"] == "file" and is_allowed_filetype(file["name"]):
                tasks.append(process_file_in_repo(file, repo_content, session))
            elif file["type"] == "dir":
                tasks.append(process_directory(file["url"], repo_content, session))

        await asyncio.gather(*tasks)

async def download_file(url, dest, session):
    async with session.get(url) as response:
        await handle_rate_limit(response)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            f.write(await response.read())

async def process_github_repo(repo_url) -> Document:
    api_base_url = "https://api.github.com/repos/"
    repo_url_parts = repo_url.split("https://github.com/")[-1].split("/")
    repo_name = "/".join(repo_url_parts[:2])

    subdirectory = ""
    if len(repo_url_parts) > 4 and repo_url_parts[2] == "tree":
        subdirectory = "/".join(repo_url_parts[4:])

    contents_url = f"{api_base_url}{repo_name}/contents"
    if subdirectory:
        contents_url = f"{contents_url}/{subdirectory}"

    repo_content: List[str] = []

    async with aiohttp.ClientSession() as session:
        await process_directory(contents_url, repo_content, session)

    logging.info("All files processed.")
    return create_document("\n".join(repo_content), repo_url)

def is_allowed_filetype(filename):
    allowed_extensions = ['.py', '.txt', '.js', '.tsx', '.ts', '.md', '.cjs', '.html', '.json', '.ipynb', '.h', '.localhost', '.sh', '.yaml', '.example']
    return any(filename.endswith(ext) for ext in allowed_extensions)

def process_ipynb_file(temp_file):
    with open(temp_file, "r", encoding='utf-8', errors='ignore') as f:
        notebook_content = f.read()

    exporter = PythonExporter()
    python_code, _ = exporter.from_notebook_node(nbformat.reads(notebook_content, as_version=4))
    return python_code

async def process_github_file(file_url, session) -> str:
    raw_url = file_url.replace("/blob/", "/raw/")
    async with session.get(raw_url) as response:
        content = await response.text()
        return f"# File: {file_url}\n{content}"

async def process_github_pull_request(pull_request_url) -> Document:
    async with aiohttp.ClientSession() as session:
        # Extract repository owner, repository name, and pull request number from the URL
        url_parts = pull_request_url.split("/")
        repo_owner = url_parts[3]
        repo_name = url_parts[4]
        pull_request_number = url_parts[-1]

        # Make API requests to retrieve pull request information
        api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pull_request_number}"

        # Retrieve pull request details
        async with session.get(api_base_url, headers=headers) as response:
            pull_request_data = await response.json()

        # Retrieve pull request diff
        diff_url = pull_request_data["diff_url"]
        async with session.get(diff_url, headers=headers) as response:
            pull_request_diff = await response.text()

        # Retrieve pull request comments and review comments
        comments_url = pull_request_data["comments_url"]
        review_comments_url = pull_request_data["review_comments_url"]
        async with session.get(comments_url, headers=headers) as response:
            comments_data = await response.json()
        async with session.get(review_comments_url, headers=headers) as response:
            review_comments_data = await response.json()

        # Combine comments and review comments into a single list
        all_comments = comments_data + review_comments_data

        # Sort comments based on their position in the diff
        all_comments.sort(key=lambda comment: comment.get("position") or float("inf"))

        # Format the retrieved pull request information
        formatted_text = f"# Pull Request Information\n\n"
        formatted_text += f"## Title: {pull_request_data['title']}\n\n"
        formatted_text += f"## Description:\n{pull_request_data['body']}\n\n"
        formatted_text += f"## Merge Details:\n"
        formatted_text += f"{pull_request_data['user']['login']} wants to merge {pull_request_data['commits']} commit into {repo_owner}:{pull_request_data['base']['ref']} from {pull_request_data['head']['label']}\n\n"
        formatted_text += f"## Diff and Comments:\n"

        # Iterate through the diff and interleave comments
        diff_lines = pull_request_diff.split("\n")
        comment_index = 0
        for line in diff_lines:
            formatted_text += f"{line}\n"
            while comment_index < len(all_comments) and all_comments[comment_index].get("position") == diff_lines.index(line):
                comment = all_comments[comment_index]
                formatted_text += f"\n### Review Comment by {comment['user']['login']}:\n"
                formatted_text += f"{comment['body']}\n\n"
                formatted_text += f"Path: {comment['path']}\n"
                formatted_text += f"Line: {comment['original_line']}\n\n"
                comment_index += 1

        # Process the entire repository
        repo_url = f"https://github.com/{repo_owner}/{repo_name}"
        repo_content = await process_github_repo(repo_url)

        # Concatenate the pull request information and repository content
        final_output = f"{formatted_text}\n\n# Repository Content\n\n{repo_content.text}"

        return create_document(final_output, pull_request_url)

async def process_github_issue(issue_url) -> Document:
    async with aiohttp.ClientSession() as session:
        # Extract repository owner, repository name, and issue number from the URL
        url_parts = issue_url.split("/")
        repo_owner = url_parts[3]
        repo_name = url_parts[4]
        issue_number = url_parts[-1]

        # Make API requests to retrieve issue information
        api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"

        # Retrieve issue details
        async with session.get(api_base_url, headers=headers) as response:
            issue_data = await response.json()

        # Retrieve issue comments
        comments_url = issue_data["comments_url"]
        async with session.get(comments_url, headers=headers) as response:
            comments_data = await response.json()

        # Format the retrieved issue information
        formatted_text = f"# Issue Information\n\n"
        formatted_text += f"## Title: {issue_data['title']}\n\n"
        formatted_text += f"## Description:\n{issue_data['body']}\n\n"
        formatted_text += f"## Comments:\n"
        for comment in comments_data:
            formatted_text += f"\n### Comment by {comment['user']['login']}:\n"
            formatted_text += f"{comment['body']}\n"

        # Process the entire repository
        repo_url = f"https://github.com/{repo_owner}/{repo_name}"
        repo_content = await process_github_repo(repo_url)

        # Concatenate the issue information and repository content
        final_output = f"{formatted_text}\n\n# Repository Content\n\n{repo_content.text}"

        return create_document(final_output, issue_url)

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

async def process_file(file_path, output):
    logging.info(f"Processing {file_path}...")

    output.append(f"# {'-' * 3}\n")
    output.append(f"# Filename: {file_path}\n")
    output.append(f"# {'-' * 3}\n\n")

    if file_path.endswith(".ipynb"):
        output.append(process_ipynb_file(file_path))
    else:
        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
            output.append(f.read())

    output.append("\n\n")

async def process_local_folder(local_path) -> Document:
    output: List[str] = []
    tasks = []

    for root, dirs, files in os.walk(local_path):
        for file in files:
            if is_allowed_filetype(file):
                file_path = os.path.join(root, file)
                tasks.append(process_file(file_path, output))

    await asyncio.gather(*tasks)

    final_text = "\n".join(output)
    return create_document(final_text, local_path)


async def fetch_youtube_transcript(video_url) -> Document:
    def extract_video_id(video_url):
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
        return None

    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube video URL")

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        transcript = formatter.format_transcript(transcript_list)
        return create_document(transcript, video_url)
    except Exception as e:
        raise ValueError(f"Failed to retrieve YouTube transcript: {str(e)}")

# Add the preprocess_text function
def preprocess_text(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as input_file:
        input_text = input_file.read()

    text = re.sub(r"[\n\r]+", "\n", input_text)
    text = re.sub(r"[^a-zA-Z0-9\s_.,!?:;@#$%^&*()+\-=[\]{}|\\<>`~'\"/]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.lower()

    words = text.split()
    words = [word for word in words if word not in stop_words]
    text = " ".join(words)

    with open(output_file, "w", encoding="utf-8") as output_file:
        output_file.write(text.strip())

# Add the is_same_domain function
def is_same_domain(base_url, new_url):
    return urlparse(base_url).netloc == urlparse(new_url).netloc

# Add the is_within_depth function
def is_within_depth(base_url, current_url, max_depth):
    base_parts = urlparse(base_url).path.rstrip('/').split('/')
    current_parts = urlparse(current_url).path.rstrip('/').split('/')

    if current_parts[:len(base_parts)] != base_parts:
        return False

    return len(current_parts) - len(base_parts) <= max_depth

# Update the crawl_and_extract_text function
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

async def scrape(tasks = test_tasks) -> List[Document]:
    processed_data = await scrape_async(tasks)
    return processed_data
    
if __name__ == "__main__":
    processed_data = scrape()
    logging.info(processed_data)

import time
import os
import aiohttp
import asyncio
import logging
from typing import List
from dotenv import load_dotenv

from bookwyrm.models import Document
from .document import create_document
from .scrape import is_allowed_filetype, process_ipynb_file


load_dotenv()

TOKEN = os.getenv('GITHUB_TOKEN', 'default_token_here')
if TOKEN == 'default_token_here':
    logging.warning("GITHUB_TOKEN environment variable not set. Using default token.")
else:
    logging.info("GITHUB_TOKEN environment variable set.")

headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {TOKEN}"
}

RATE_LIMIT_REMAINING = 5000
RATE_LIMIT_RESET = 0

async def process_file_in_repo(file, repo_content, session, semaphore):
    async with semaphore:
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

        # Add a delay between file processing
        await asyncio.sleep(1)  # Adjust the delay as needed

async def process_directory(url, repo_content, session, semaphore):
    async with session.get(url, headers=headers) as response:
        print(headers)
        await handle_rate_limit(response)
        response.raise_for_status()
        files = await response.json()

        tasks = []
        for file in files:
            if file["type"] == "file" and is_allowed_filetype(file["name"]):
                tasks.append(process_file_in_repo(file, repo_content, session, semaphore))
            elif file["type"] == "dir":
                tasks.append(process_directory(file["url"], repo_content, session, semaphore))

        await asyncio.gather(*tasks)

        # Add a delay between directory processing
        await asyncio.sleep(1)  # Adjust the delay as needed

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

    semaphore = asyncio.Semaphore(10)  # Limit the number of concurrent requests
    async with aiohttp.ClientSession() as session:
        await process_directory(contents_url, repo_content, session, semaphore)

    logging.info("All files processed.")
    return create_document("\n".join(repo_content), repo_url)

async def handle_rate_limit(response):
    global RATE_LIMIT_REMAINING, RATE_LIMIT_RESET

    RATE_LIMIT_REMAINING = int(response.headers.get("X-RateLimit-Remaining", 0))
    RATE_LIMIT_RESET = int(response.headers.get("X-RateLimit-Reset", 0))

    if RATE_LIMIT_REMAINING <= 0:
        current_time = int(time.time())
        wait_time = RATE_LIMIT_RESET - current_time + 1
        logging.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
        await asyncio.sleep(wait_time)

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

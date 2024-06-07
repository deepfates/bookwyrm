import logging
import os
import asyncio
from typing import List

from bookwyrm.models import Document
from .document import create_document
from .scrape import is_allowed_filetype, process_ipynb_file

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

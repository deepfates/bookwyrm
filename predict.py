# Prediction interface for Cog ⚙️
# https://github.com/replicate/cog/blob/main/docs/python.md

import logging
from cog import BasePredictor, Input
from bookwyrm import process_documents
from scrape import scrape
from process import chunk, encode
from typing import List, Any
from models import Document, DocumentRecord, TextChunk, Bookwyrm
import asyncio

from cog import BasePredictor, Input
from scrape import scrape
from process import chunk, encode
from utils import test_tasks

class Predictor(BasePredictor):
    def predict(
        self,
        urls: List[str] = Input(description="List of URLs to process.", default=test_tasks)
    ) -> dict:
        return process_documents(urls)

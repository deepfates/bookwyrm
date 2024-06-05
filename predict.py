# Prediction interface for Cog ⚙️
# https://github.com/replicate/cog/blob/main/docs/python.md

from typing import List
import asyncio
from cog import BasePredictor, Input


from bookwyrm import process_documents
from bookwyrm.utils import test_tasks

class Predictor(BasePredictor):
    def predict(
        self,
        urls: List[str] = Input(description="List of URLs to process.", default=test_tasks)
    ) -> dict:
        loop = asyncio.get_event_loop()
        output = loop.run_until_complete(process_documents(urls))
        return {"output": output.to_json()}

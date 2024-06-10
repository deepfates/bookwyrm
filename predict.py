# Prediction interface for Cog ⚙️
# https://github.com/replicate/cog/blob/main/docs/python.md

from typing import List
import asyncio
from cog import BasePredictor, Input # type: ignore


from bookwyrm import process_documents
from bookwyrm.utils import TEST_TASKS

class Predictor(BasePredictor):
    def predict( # type: ignore
        self,
        urls: List[str] = Input(description="List of URLs to process.", default=TEST_TASKS)
    ) -> dict:
        loop = asyncio.get_event_loop()
        output = loop.run_until_complete(process_documents(urls))
        return {"output": output.to_json()}

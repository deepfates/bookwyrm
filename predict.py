# Prediction interface for Cog ⚙️
# https://github.com/replicate/cog/blob/main/docs/python.md

from typing import List
from cog import BasePredictor, Input


from bookwyrm import process_documents
from utils import test_tasks

class Predictor(BasePredictor):
    def predict(
        self,
        urls: List[str] = Input(description="List of URLs to process.", default=test_tasks)
    ) -> dict:
        output = process_documents(urls)
        return {"output": output.to_json()}

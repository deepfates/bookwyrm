import numpy as np
import replicate # type: ignore
import json 
import tiktoken
import asyncio
from tqdm import tqdm

def get_token_count(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(text))
    return num_tokens

async def embedding_api(texts, batch_size=200):
    all_embeddings = []

    async def fetch_embeddings(batch_texts):
        resp = await replicate.async_run(
            "replicate/all-mpnet-base-v2:b6b7585c9640cd7a9572c6e129c9549d79c9c31f0d3fdce7baac7c67ca38f305",
            input={"text_batch": json.dumps(batch_texts)},
        )
        return [o['embedding'] for o in resp]

    tasks = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch_texts = texts[i:i + batch_size]
        tasks.append(fetch_embeddings(batch_texts))

    results = await asyncio.gather(*tasks)

    for result in results:
        all_embeddings.extend(result)

    return np.array(all_embeddings)

TEST_TASKS = [
        # "./data/",
        # "https://arxiv.org/pdf/2004.07606",
        # "https://www.youtube.com/watch?v=KZ_NlnmPQYk",
        # "https://llm.datasette.io/en/stable/",
        # "10.1053/j.ajkd.2017.08.002",
        # "https://github.com/rtyley/small-test-repo",
        "https://github.com/deepfates/concat"
        # "https://github.com/replicate/replicate-python"
        # "https://github.com/replicate/replicate-elixir"
    ]

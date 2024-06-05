import numpy as np
import replicate
import json 
import tiktoken
import asyncio

def get_token_count(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(text))
    return num_tokens

def embedding_api(texts):
    resp =  replicate.run(
        "replicate/all-mpnet-base-v2:b6b7585c9640cd7a9572c6e129c9549d79c9c31f0d3fdce7baac7c67ca38f305",
        input={"text_batch": json.dumps(texts)},
    )
    flattened_embeds = [o['embedding'] for o in resp]
    return np.array(flattened_embeds)

test_tasks = [
        "./data/",
        "https://github.com/rtyley/small-test-repo",
        "https://arxiv.org/pdf/2004.07606",
        "https://www.youtube.com/watch?v=KZ_NlnmPQYk",
        "https://llm.datasette.io/en/stable/",
        "10.1053/j.ajkd.2017.08.002",
    ]
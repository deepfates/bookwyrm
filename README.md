# 🐉 bookwyrm 

This is an ingestion pipeline for Github repos, website, documents, and more.

It takes a list of URLs and outputs a bookwyrm: a long string of docs and embeddings, easily indexed. 

If you've ever wanted to:

- Chat with PDF
- Chat with repo
- Chat with video
- Chat with notebook
- Chat with website
- Chat with files

Well, this doesn't let you do that. It just processes them and spits out chunks of text with embeddings.

When you want to actually chat with it, that's what [concat](https://github.com/deepfates/concat) is for.

<!-- Describe the different types of data we can scrape -->

# Usage

## Using with Cog
Use Cog to run predictions:
```sh
cog predict -i urls='["https://github.com/replicate/cog"]'
```

## Using with Python

### Setting Up the Environment
1. **Create a new virtual environment**:
   ```sh
   python3 -m venv .venv
   ```

2. **Activate the virtual environment**:
   - For `bash` or `zsh`:
     ```sh
     source .venv/bin/activate
     ```
   - For `fish`:
     ```sh
     source .venv/bin/activate.fish
     ```


3. **Install the required dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

### Running the Pipeline

1. **Run the main script**:
   ```sh
   python -m bookwyrm.bookwyrm
   ```

This will process the test URLs and save the output to `wyrm.json`.

### Use as a library

```python
import asyncio

from bookwyrm.bookwyrm import process_documents

urls = ["https://llm.datasette.io/en/stable/"]
output = asyncio.run(process_documents(urls))
with open("wyrm.json", "w") as f:
    f.write(output.to_json())
```

Run the test script:
```sh
python test_script.py
```

This should process the URLs and save the output to `wyrm.json`, confirming that your environment is correctly set up.

---


Modified versions of the following third-party software components are included in this project:
```
Project: n-levels-of-rag
Source: https://github.com/jxnl/n-levels-of-rag
License: MIT
Copyright: 2024 Jason Liu
Files: README.md
```

```
Project: 1filellm
Source: https://github.com/jimmc414/1filellm
License: MIT
Copyright: 2024 Jim McMillan
Files: onefilellm.py
```

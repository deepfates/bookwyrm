# 🐉 Bookwyrm 

This is an ingestion pipeline for Github repos, website, documents, and more.

It takes a list of URLs and outputs a bookwyrm: a long string of docs and embeddings, easily indexed. 

If you've ever wanted to:

> Chat with PDF
> Chat with repo
> Chat with video
> Chat with notebook
> Chat with website
> Chat with files

Well, this doesn't let you do that. It just process them and spits out chunks of text with embeddings.

When you want to actually chat with it, that's what [concat](https://github.com/deepfates/concat) is for.

---


Modified versions of the following third-party software components are included in this project:

Project: n-levels-of-rag
Source: https://github.com/jxnl/n-levels-of-rag
License: MIT
Copyright: 2024 Jason Liu
Files: README.md

Project: 1filellm
Source: https://github.com/jimmc414/1filellm
License: MIT
Copyright: 2024 Jim McMillan
Files: onefilellm.py

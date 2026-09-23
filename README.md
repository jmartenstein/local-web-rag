# local-web-rag

Experimental repository for local LLM sand RAGs.

The purpose of this tool is to optimize the local LLM and RAG process, the way that my brain (Justin Martenstein) thinks about things logically, especially in terms of date pipelines.

We want to be able to do a comprehensive web search on a topic (such as fantasy football, or writing a consulting proposal), store the results locally, and then feed those data files into whatever coding agent is being used at the time.

## ddg_search_example.py

The `ddg_search_example.py` script provides a command-line interface for performing DuckDuckGo searches and storing results locally for RAG processing.

### Features
- Performs web searches using DuckDuckGo's search API
- Saves search results to local JSON files with timestamps
- Formats results for RAG (Retrieval-Augmented Generation) processing
- Handles errors gracefully

### Usage

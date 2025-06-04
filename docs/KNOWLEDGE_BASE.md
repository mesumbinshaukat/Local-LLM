# Knowledge Base Guide

## Adding Knowledge
- Place your documents (PDF, .txt, .md, code) in the `knowledge/` directory.
- Subfolders are supported for organization.

## Ingesting Knowledge
- Run:
  ```sh
  python main.py ingest
  ```
- All files are processed recursively and added to ChromaDB.

## Using Knowledge in Chat
- The LLM will automatically use your ingested knowledge for RAG.
- Sources and metadata are shown in the UI for each RAG result.

## Managing Knowledge
- Use the Knowledge tab in the app to view, add, or remove documents.
- Re-ingest after adding or removing files. 
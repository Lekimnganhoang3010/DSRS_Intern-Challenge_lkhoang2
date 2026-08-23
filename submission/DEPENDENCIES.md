# Dependencies

I did not add any dependencies beyond the frozen packages provided by the challenge.

The pipeline uses:

- `httpx` for SEC HTTP requests.
- `lxml` for XML parsing.
- `pyarrow` for schema-controlled Parquet output.
- `openai` through the frozen `agents/llm.py` interface.

These were already included in the frozen `requirements.txt`.

## Anything you considered and rejected

I did not use an end-to-end 13F retrieval or parsing library. I used the provided
general-purpose HTTP, XML, and Arrow libraries so that CIK reconciliation, EDGAR
retrieval, namespace handling, duplicate preservation, and schema conversion remain
explicit in my code.
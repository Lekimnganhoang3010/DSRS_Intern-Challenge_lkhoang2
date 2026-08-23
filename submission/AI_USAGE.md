# AI Usage

## Tools used

- ChatGPT/Codex for implementation guidance, code explanation, debugging, test design,
  and documentation drafting.
- Ollama 0.32.14 with `llama3.2:3b` as the local OpenAI-compatible model used to test
  the agent interface and question planner.

## Where you used them

| Chapter | How you used AI |
|---|---|
| 1 · Source | I used ChatGPT to break the requirements into implementation steps and help draft the SEC client, caching, rate limiting, CIK reconciliation, filing discovery, and XML-download logic. I executed each step, inspected the SEC responses, and used observed filing results to correct matching and document-selection errors. |
| 2 · Interrogate | I used ChatGPT to design the EDA checks and explain XML structure, namespaces, optional fields, duplicates, declared totals, and notice filings. I ran the exploration against all downloaded files and retained evidence-based findings in `submission/eda.py`. |
| 3 · Structure | I used ChatGPT to help implement namespace-tolerant XML helpers, cover-page and holdings parsing, Arrow schemas, Parquet writing, and validation checks. I tested individual filings, ran `verify.py`, and confirmed byte-identical output across repeated runs. |
| 4 · Serve | I used ChatGPT to design the separation between model planning and deterministic Python execution, and to help implement read-only data access, structured plans, semantic validation, query functions, failure handling, and usage recording. Ollama was used to test all ten example questions locally. |
| 5 · Show | I used ChatGPT to organize the submission checklist, document assumptions and AI usage, plan final testing, and prepare the video walkthrough. |

## What you would change

AI assistance was substantial, especially for Python syntax and initial implementation
drafts. I reviewed and executed the code incrementally, tested intermediate outputs, and
can explain the high-level pipeline and major design decisions. I am still developing
fluency with some lower-level syntax, particularly XML/XPath handling, type annotations,
and class-based state management.

Given more time, I would rewrite selected modules independently as a comprehension
exercise, add broader unit tests for query variations and issuer matching, and test the
planner against a smaller Gemma-family model closer to the grading model. I would also
consider a more formal issuer-resolution layer instead of normalized substring matching.